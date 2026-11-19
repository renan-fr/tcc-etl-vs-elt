from __future__ import annotations

import argparse
from datetime import datetime
import importlib.metadata
import json
import os
import platform
import queue
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
import threading
import traceback
from typing import TextIO
from urllib.parse import unquote, urlsplit

import psycopg2
import psutil
from dotenv import dotenv_values, load_dotenv

try:
    from src.benchmark_paths import (
        criar_diretorio_campanha,
        criar_diretorios_modalidades,
        DATASETS,
        validar_run_id,
    )
except ModuleNotFoundError:  # execução direta: python src/benchmark.py
    from benchmark_paths import (
        criar_diretorio_campanha,
        criar_diretorios_modalidades,
        DATASETS,
        validar_run_id,
    )


BASE_DIR = Path(__file__).resolve().parents[1]
VOLUMES_PADRAO = [100_000, 250_000, 500_000, 1_000_000]
SEED_PADRAO = 20241027
MODALIDADES = ("desempenho", "recursos")
DEPENDENCIAS_AMBIENTE = (
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("python-dotenv", "python-dotenv"),
    ("SQLAlchemy", "sqlalchemy"),
    ("psycopg2", "psycopg2-binary"),
    ("psutil", "psutil"),
)
PARAMETROS_POSTGRES = (
    "shared_buffers",
    "work_mem",
    "maintenance_work_mem",
    "effective_cache_size",
    "max_parallel_workers",
    "max_parallel_workers_per_gather",
    "jit",
    "fsync",
    "synchronous_commit",
    "random_page_cost",
    "default_statistics_target",
    "autovacuum",
)
PADRAO_URL_CREDENCIAL = re.compile(
    r"(?i)\b(?:postgres(?:ql)?)(?:\+[^\s:]+)?://[^\s'\"]+"
)
PADRAO_CREDENCIAL = re.compile(
    r"(?i)(?P<prefix>[\"']?\b(?:[a-z0-9]+[_-])*"
    r"(?:password|passwd|pwd|senha|token|secret|api[_-]?key|database[_-]?url)"
    r"[\"']?(?:\s*[:=]\s*|\s+))"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)"
)
VARIAVEIS_AMBIENTE_SENSIVEIS = (
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "POSTGRES_URL",
)
MENSAGEM_SANITIZACAO_INDISPONIVEL = "<mensagem_omitida_por_falha_na_sanitizacao>"
TAMANHO_MINIMO_SEGREDO_ISOLADO = 8
TEMPO_LIMITE_ENCERRAMENTO_S = 5.0
TEMPO_LIMITE_THREAD_S = 5.0


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def obter_commit_git() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def salvar_metadados(caminho: Path, metadados: dict[str, object]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)


def _sanitizar_texto(texto: str, valores_sensiveis: tuple[str, ...] = ()) -> str:
    texto = PADRAO_URL_CREDENCIAL.sub("<url_postgresql_redigida>", texto)
    texto = PADRAO_CREDENCIAL.sub(
        lambda correspondencia: (
            f"{correspondencia.group('prefix')}<valor_redigido>"
        ),
        texto,
    )
    for valor in sorted(set(valores_sensiveis), key=len, reverse=True):
        if len(valor) < TAMANHO_MINIMO_SEGREDO_ISOLADO:
            continue
        inicio = r"(?<![a-zA-Z0-9])" if valor[0].isalnum() else ""
        fim = r"(?![a-zA-Z0-9])" if valor[-1].isalnum() else ""
        texto = re.sub(
            inicio + re.escape(valor) + fim,
            "<valor_redigido>",
            texto,
        )
    return texto


def _sanitizar_texto_seguro(
    texto: str,
    valores_sensiveis: tuple[str, ...] = (),
) -> str:
    try:
        return _sanitizar_texto(texto, valores_sensiveis)
    except BaseException:
        sufixo = "\n" if texto.endswith("\n") else ""
        return MENSAGEM_SANITIZACAO_INDISPONIVEL + sufixo


def _valores_sensiveis_ambiente(ambiente: dict[str, str]) -> tuple[str, ...]:
    valores = {
        valor
        for nome in VARIAVEIS_AMBIENTE_SENSIVEIS
        if (valor := ambiente.get(nome))
    }
    for nome in ("DATABASE_URL", "POSTGRES_URL"):
        url = ambiente.get(nome)
        if not url:
            continue
        try:
            senha = urlsplit(url).password
        except ValueError:
            continue
        if senha:
            valores.add(senha)
            valores.add(unquote(senha))
    return tuple(valores)


def _mensagem_erro_segura(
    erro: BaseException,
    valores_sensiveis: tuple[str, ...] = (),
) -> str:
    try:
        mensagem = str(erro)
    except BaseException:
        return "mensagem_indisponivel"
    return _sanitizar_texto_seguro(mensagem, valores_sensiveis)[:500]


def _erro_persistivel(
    erro: BaseException,
    contexto: str,
    valores_sensiveis: tuple[str, ...] = (),
) -> dict[str, str]:
    return {
        "tipo": type(erro).__name__,
        "contexto": contexto,
        "mensagem": _mensagem_erro_segura(erro, valores_sensiveis),
    }


def _traceback_seguro(
    erro: BaseException,
    valores_sensiveis: tuple[str, ...],
) -> str:
    try:
        texto = "".join(traceback.format_exception(erro))
    except BaseException:
        return f"{type(erro).__name__}: <traceback_indisponivel>\n"
    return _sanitizar_texto_seguro(texto, valores_sensiveis)


def _marcar_erro_reportado(erro: BaseException) -> None:
    try:
        setattr(erro, "_benchmark_erro_reportado", True)
    except BaseException:
        pass


def _erro_ja_reportado(erro: BaseException) -> bool:
    try:
        return bool(getattr(erro, "_benchmark_erro_reportado", False))
    except BaseException:
        return False


def _registrar_falha_campanha(
    erro: BaseException,
    *,
    valores_sensiveis: tuple[str, ...],
    metadados: dict[str, object] | None = None,
    metadados_caminho: Path | None = None,
    log_caminho: Path | None = None,
    arquivo_log: TextIO | None = None,
    contexto: str = "execucao_pipeline",
) -> None:
    if metadados is not None and metadados_caminho is not None:
        metadados["status"] = (
            "interrompida" if isinstance(erro, KeyboardInterrupt) else "falhou"
        )
        metadados["fim"] = agora_iso()
        metadados["erro"] = _erro_persistivel(
            erro,
            contexto,
            valores_sensiveis,
        )
        try:
            salvar_metadados(metadados_caminho, metadados)
        except Exception as erro_metadados:
            print(
                "Falha adicional ao salvar campanha.json: "
                f"{_mensagem_erro_segura(erro_metadados, valores_sensiveis)}",
                file=sys.stderr,
            )

    texto_erro = _traceback_seguro(erro, valores_sensiveis)
    sys.stderr.write(texto_erro)
    sys.stderr.flush()

    erro_log: BaseException | None = None
    registrado = False
    if arquivo_log is not None:
        try:
            arquivo_log.write(texto_erro)
            arquivo_log.flush()
            registrado = True
        except Exception as erro_escrita:
            erro_log = erro_escrita
    if not registrado and log_caminho is not None:
        try:
            with log_caminho.open("a", encoding="utf-8", buffering=1) as log:
                log.write(texto_erro)
            registrado = True
        except Exception as erro_escrita:
            erro_log = erro_escrita
    if not registrado and erro_log is not None:
        print(
            "Falha adicional ao registrar a exceção em campanha.log: "
            f"{_mensagem_erro_segura(erro_log, valores_sensiveis)}",
            file=sys.stderr,
        )
    _marcar_erro_reportado(erro)


def _ambiente_declarado() -> dict[str, str]:
    return {
        "fabricante_modelo": "Acer Aspire 16 A16-71M-55H0",
        "processador": "Intel Core Ultra 5 115U",
        "memoria_ram": "16 GB",
        "armazenamento": "SSD",
        "sistema_operacional": "Windows 11",
        "postgresql": "local",
        "fontes_csv": "locais",
        "rede_durante_benchmark": "sem transferência de rede",
        "origem": "declaração metodológica do experimento; não é verificação do host atual",
    }


def _ambiente_indisponivel(erro: BaseException) -> dict[str, object]:
    return {
        "status": "falha_na_coleta",
        "origem": "captura automática no início da campanha",
        "erro": {
            "tipo": type(erro).__name__,
            "contexto": "coleta_ambiente",
        },
        "declarado_para_campanha_oficial": _ambiente_declarado(),
        "capturado_automaticamente": None,
    }


def _versoes_dependencias() -> dict[str, str | None]:
    versoes: dict[str, str | None] = {}
    for nome, distribuicao in DEPENDENCIAS_AMBIENTE:
        try:
            versoes[nome] = importlib.metadata.version(distribuicao)
        except importlib.metadata.PackageNotFoundError:
            versoes[nome] = None
    return versoes


def _configuracao_postgres() -> tuple[
    str | None, dict[str, object], dict[str, object]
]:
    arquivo_env = dotenv_values(BASE_DIR / ".env")
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if database_url:
        try:
            partes = urlsplit(database_url)
            porta = partes.port
        except ValueError:
            return database_url, {}, {
                "host": None,
                "porta": None,
                "banco": None,
            }
        resumo = {
            "host": partes.hostname,
            "porta": porta,
            "banco": unquote(partes.path.lstrip("/")) or None,
        }
        return database_url, {}, resumo

    def valor(nome: str, padrao: str | None = None) -> str | None:
        atual = os.getenv(nome)
        if atual is not None:
            return atual
        arquivo = arquivo_env.get(nome)
        return str(arquivo) if arquivo is not None else padrao

    porta = valor("POSTGRES_PORT", "5432")
    try:
        porta_numero: int | None = int(porta) if porta is not None else None
    except ValueError:
        porta_numero = None
    parametros = {
        "host": valor("POSTGRES_HOST", "localhost"),
        "port": porta_numero,
        "dbname": valor("POSTGRES_DB"),
        "user": valor("POSTGRES_USER"),
        "password": valor("POSTGRES_PASSWORD"),
    }
    resumo = {
        "host": parametros["host"],
        "porta": parametros["port"],
        "banco": parametros["dbname"],
    }
    return None, parametros, resumo


def _consultar_postgres_ambiente(
    database_url: str | None,
    configuracao: dict[str, object],
) -> dict[str, object]:
    resultado: dict[str, object] = {
        "versao_servidor": None,
        "configuracoes": {parametro: None for parametro in PARAMETROS_POSTGRES},
        "status": "indisponivel",
        "origem": "consultas somente leitura na conexao da campanha",
    }
    if database_url is None and not all(
        configuracao.get(nome)
        for nome in ("dbname", "user", "password")
    ):
        resultado["status"] = "nao_consultado_configuracao_incompleta"
        return resultado

    conexao = None
    cursor = None
    try:
        conexao = (
            psycopg2.connect(database_url)
            if database_url
            else psycopg2.connect(**configuracao)
        )
        cursor = conexao.cursor()
        cursor.execute("SELECT version()")
        versao = cursor.fetchone()
        resultado["versao_servidor"] = versao[0] if versao else None
        configuracoes = resultado["configuracoes"]
        assert isinstance(configuracoes, dict)
        for parametro in PARAMETROS_POSTGRES:
            cursor.execute(f"SHOW {parametro}")
            valor = cursor.fetchone()
            configuracoes[parametro] = valor[0] if valor else None
        resultado["status"] = "consultado"
    except Exception as erro:  # conexão é diagnóstico; não altera a campanha
        resultado["status"] = "indisponivel"
        resultado["erro_tipo"] = type(erro).__name__
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conexao is not None:
            try:
                conexao.close()
            except Exception:
                pass
    return resultado


def coletar_ambiente() -> dict[str, object]:
    """Captura o ambiente uma vez, sem assumir que este host é o oficial."""
    database_url, parametros, conexao_resumo = _configuracao_postgres()
    postgres = _consultar_postgres_ambiente(database_url, parametros)
    try:
        memoria_total = psutil.virtual_memory().total
    except Exception:
        memoria_total = None
    capturado = {
        "capturado_em": agora_iso(),
        "sistema_operacional": {
            "nome": platform.system() or None,
            "versao": platform.version() or None,
            "release": platform.release() or None,
            "arquitetura": platform.machine() or None,
            "origem": "platform",
        },
        "python": {
            "versao": platform.python_version() or None,
            "implementacao": platform.python_implementation() or None,
            "arquitetura": f"{struct.calcsize('P') * 8}-bit",
            "origem": "platform",
        },
        "dependencias": {
            nome: versao for nome, versao in _versoes_dependencias().items()
        },
        "postgresql": {
            **conexao_resumo,
            **postgres,
        },
        "hardware": {
            "processador": platform.processor() or None,
            "cpus_logicas": os.cpu_count(),
            "memoria_ram_total_bytes": memoria_total,
            "origem": "platform, os e psutil",
        },
    }
    return {
        "status": "capturado_no_host_da_campanha",
        "origem": "captura automática no início da campanha; valores null não foram observados",
        "declarado_para_campanha_oficial": _ambiente_declarado(),
        "capturado_automaticamente": capturado,
    }


def validar_git_limpo() -> None:
    resultado = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0 or resultado.stdout.strip():
        raise SystemExit(
            "A campanha oficial exige uma arvore Git limpa. "
            "Registre as alteracoes antes de executar."
        )


def comando(
    modalidade: str,
    dataset: str,
    arquitetura: str,
    volume: int,
    modo: str,
    rodada: int | None,
) -> list[str]:
    argumentos = [
        sys.executable,
        str(BASE_DIR / "src" / dataset / f"{arquitetura}.py"),
        "--limite",
        str(volume),
        "--modo",
        modo,
    ]
    if rodada is not None:
        argumentos.extend(["--rodada", str(rodada)])
    if modalidade == "desempenho":
        argumentos.append("--sem-monitoramento")
    return argumentos


def _registrar_mensagem(
    arquivo_log: TextIO,
    mensagem: str,
    valores_sensiveis: tuple[str, ...] = (),
) -> None:
    texto = _sanitizar_texto_seguro(mensagem + "\n", valores_sensiveis)
    sys.stdout.write(texto)
    sys.stdout.flush()
    arquivo_log.write(texto)
    arquivo_log.flush()


def _replicar_fluxo(
    origem: TextIO,
    destino: TextIO,
    arquivo_log: TextIO,
    lock: threading.Lock,
    nome_fluxo: str,
    falhas: queue.Queue[tuple[str, BaseException]],
    valores_sensiveis: tuple[str, ...],
) -> None:
    try:
        try:
            for trecho in iter(origem.readline, ""):
                trecho_seguro = _sanitizar_texto_seguro(trecho, valores_sensiveis)
                with lock:
                    destino.write(trecho_seguro)
                    destino.flush()
                    arquivo_log.write(trecho_seguro)
                    arquivo_log.flush()
        finally:
            origem.close()
    except BaseException as erro:
        falhas.put((nome_fluxo, erro))


class ErroCapturaFluxo(RuntimeError):
    """Indica que uma thread deixou de capturar stdout ou stderr."""


class ErroEncerramentoProcesso(RuntimeError):
    """Indica que não foi possível confirmar o encerramento do subprocesso."""


def _propagar_falha_captura(
    falhas: queue.Queue[tuple[str, BaseException]],
) -> None:
    try:
        nome_fluxo, erro = falhas.get_nowait()
    except queue.Empty:
        return
    raise ErroCapturaFluxo(
        f"Falha ao capturar {nome_fluxo} do subprocesso: "
        f"{_mensagem_erro_segura(erro)}"
    ) from erro


def _encerrar_processo(processo: subprocess.Popen[str]) -> None:
    """Encerra e coleta um subprocesso que ainda esteja ativo."""
    if processo.poll() is not None:
        return
    falhas: list[str] = []
    try:
        processo.terminate()
    except BaseException as erro:
        falhas.append(f"terminate: {_mensagem_erro_segura(erro)}")
    try:
        processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO_S)
        return
    except subprocess.TimeoutExpired:
        pass
    except BaseException as erro:
        falhas.append(f"wait após terminate: {_mensagem_erro_segura(erro)}")
    try:
        processo.kill()
    except BaseException as erro:
        falhas.append(f"kill: {_mensagem_erro_segura(erro)}")
    try:
        processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO_S)
        return
    except subprocess.TimeoutExpired:
        falhas.append("timeout após kill")
    except BaseException as erro:
        falhas.append(f"wait após kill: {_mensagem_erro_segura(erro)}")
    if processo.poll() is not None:
        return
    detalhes = "; ".join(falhas) if falhas else "processo permaneceu ativo"
    raise ErroEncerramentoProcesso(
        "Não foi possível confirmar o encerramento do subprocesso: " + detalhes
    )


def executar_pipeline(
    argumentos: list[str],
    *,
    ambiente: dict[str, str],
    arquivo_log: TextIO,
) -> None:
    """Executa um pipeline e replica stdout/stderr incrementalmente no log."""
    valores_sensiveis = _valores_sensiveis_ambiente(ambiente)
    processo = subprocess.Popen(
        argumentos,
        cwd=BASE_DIR,
        env=ambiente,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert processo.stdout is not None
    assert processo.stderr is not None
    lock = threading.Lock()
    falhas: queue.Queue[tuple[str, BaseException]] = queue.Queue()
    threads = [
        threading.Thread(
            target=_replicar_fluxo,
            args=(
                processo.stdout,
                sys.stdout,
                arquivo_log,
                lock,
                "stdout",
                falhas,
                valores_sensiveis,
            ),
            name="benchmark-stdout",
            daemon=True,
        ),
        threading.Thread(
            target=_replicar_fluxo,
            args=(
                processo.stderr,
                sys.stderr,
                arquivo_log,
                lock,
                "stderr",
                falhas,
                valores_sensiveis,
            ),
            name="benchmark-stderr",
            daemon=True,
        ),
    ]
    threads_iniciadas: list[threading.Thread] = []
    falha_execucao: BaseException | None = None
    try:
        for thread in threads:
            thread.start()
            threads_iniciadas.append(thread)
        while processo.poll() is None:
            try:
                nome_fluxo, erro = falhas.get(timeout=0.05)
            except queue.Empty:
                continue
            raise ErroCapturaFluxo(
                f"Falha ao capturar {nome_fluxo} do subprocesso: "
                f"{_mensagem_erro_segura(erro)}"
            ) from erro
        codigo = processo.returncode
    except BaseException as erro:
        falha_execucao = erro
        try:
            _encerrar_processo(processo)
        except BaseException as erro_encerramento:
            erro.add_note(
                "Falha adicional ao encerrar o subprocesso: "
                f"{_mensagem_erro_segura(erro_encerramento)}"
            )
        raise
    finally:
        for thread in threads_iniciadas:
            thread.join(timeout=TEMPO_LIMITE_THREAD_S)
        threads_ativas = [thread for thread in threads_iniciadas if thread.is_alive()]
        for thread, fluxo in zip(threads, (processo.stdout, processo.stderr)):
            if thread.is_alive():
                continue
            try:
                fluxo.close()
            except Exception:
                pass
        if threads_ativas:
            nomes = ", ".join(thread.name for thread in threads_ativas)
            mensagem = (
                "Threads de captura não finalizaram no prazo e permanecerão daemon: "
                + nomes
            )
            if falha_execucao is not None:
                falha_execucao.add_note(mensagem)
            else:
                raise ErroCapturaFluxo(mensagem)
    _propagar_falha_captura(falhas)
    if codigo != 0:
        raise subprocess.CalledProcessError(codigo, argumentos)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orquestra a campanha global e randomizada de ENEM e TSE."
    )
    parser.add_argument("--volumes", nargs="+", type=int, default=VOLUMES_PADRAO)
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id", default="oficial_01")
    args = parser.parse_args()

    if args.rodadas < 1 or any(volume < 1 for volume in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    try:
        run_id = validar_run_id(args.run_id)
    except ValueError as erro:
        parser.error(str(erro))

    # Deve ocorrer antes de criar, limpar ou alterar qualquer resultado.
    validar_git_limpo()

    ausentes = [
        BASE_DIR
        / "data"
        / "benchmark"
        / "tse"
        / "subconjuntos"
        / f"chaves_{volume}.csv"
        for volume in args.volumes
        if not (
            BASE_DIR
            / "data"
            / "benchmark"
            / "tse"
            / "subconjuntos"
            / f"chaves_{volume}.csv"
        ).is_file()
    ]
    if ausentes:
        parser.error("Manifestos TSE ausentes:\n" + "\n".join(map(str, ausentes)))

    try:
        campanha_dir = criar_diretorio_campanha(run_id)
    except FileExistsError as erro:
        parser.error(str(erro))
    metadados_caminho = campanha_dir / "campanha.json"
    log_caminho = campanha_dir / "campanha.log"
    valores_sensiveis: tuple[str, ...] = ()
    try:
        criar_diretorios_modalidades(campanha_dir)
        log_caminho.touch()
        with log_caminho.open("a", encoding="utf-8", buffering=1) as arquivo_log:
            _registrar_mensagem(arquivo_log, f"Campanha: {run_id}")
            _registrar_mensagem(arquivo_log, f"Seed: {args.seed}")
        load_dotenv(BASE_DIR / ".env")
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            log_caminho=log_caminho,
            contexto="inicializacao_campanha",
        )
        raise

    valores_sensiveis = _valores_sensiveis_ambiente(dict(os.environ))
    try:
        ambiente_metadados = coletar_ambiente()
    except Exception as erro:
        ambiente_metadados = _ambiente_indisponivel(erro)
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            log_caminho=log_caminho,
            contexto="inicializacao_campanha",
        )
        raise
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = run_id
    ambiente["BENCHMARK_OUTPUT_DIR"] = str(campanha_dir)
    ambiente["BENCHMARK_ORCHESTRATOR_RUN_ID"] = run_id
    ambiente["PYTHONIOENCODING"] = "utf-8"
    ambiente["PYTHONUNBUFFERED"] = "1"
    valores_sensiveis = _valores_sensiveis_ambiente(ambiente)
    rng = random.Random(args.seed)
    cenarios = [
        (modalidade, dataset, volume, arquitetura)
        for modalidade in MODALIDADES
        for dataset in DATASETS
        for volume in args.volumes
        for arquitetura in ("etl", "elt")
    ]
    fases = [
        ("aquecimento", None),
        *[("medir", rodada) for rodada in range(1, args.rodadas + 1)],
    ]

    total = len(cenarios) * len(fases)
    aquecimentos = len(cenarios)
    medicoes_validas = len(cenarios) * args.rodadas
    try:
        commit_git = obter_commit_git()
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            log_caminho=log_caminho,
            contexto="inicializacao_campanha",
        )
        raise
    metadados: dict[str, object] = {
        "run_id": run_id,
        "status": "em_andamento",
        "inicio": agora_iso(),
        "fim": None,
        "commit_git": commit_git,
        "ambiente": ambiente_metadados,
        "seed": args.seed,
        "datasets": list(DATASETS),
        "volumes": args.volumes,
        "rodadas": args.rodadas,
        "combinacoes": len(cenarios),
        "cenarios_processamento": len(cenarios) // len(MODALIDADES),
        "modalidades": {
            "desempenho": {
                "monitoramento_ativo": False,
                "intervalo_monitoramento_s": None,
                "metricas_oficiais": [
                    "tempo_leitura",
                    "tempo_transformacao",
                    "tempo_carga",
                    "tempo_total",
                    "throughput",
                ],
                "metricas_recursos": None,
            },
            "recursos": {
                "monitoramento_ativo": True,
                "intervalo_monitoramento_s": 0.5,
                "metricas_oficiais": ["cpu_*", "ram_*"],
                "metricas_experimentais": [
                    "cpu_times_python_s",
                    "cpu_times_postgres_s",
                    "cpu_times_total_s",
                    "cpu_times_status",
                ],
                "diagnosticos_cpu_times": [
                    "cpu_times_leituras_validas",
                    "cpu_times_leituras_validas_python",
                    "cpu_times_leituras_validas_postgres",
                    "cpu_times_processos_novos",
                    "cpu_times_processos_encerrados",
                    "cpu_times_processos_incompletos",
                ],
                "metricas_diagnosticas": [
                    "tempo_leitura",
                    "tempo_transformacao",
                    "tempo_carga",
                    "tempo_total",
                    "throughput",
                ],
            },
        },
        "aquecimentos": aquecimentos,
        "medicoes_validas": medicoes_validas,
        "execucoes_previstas": total,
        "execucoes_concluidas": 0,
    }
    try:
        salvar_metadados(metadados_caminho, metadados)
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            metadados=metadados,
            metadados_caminho=metadados_caminho,
            log_caminho=log_caminho,
            contexto="inicializacao_campanha",
        )
        raise
    indice = 0
    try:
        arquivo_log = log_caminho.open("a", encoding="utf-8", buffering=1)
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            metadados=metadados,
            metadados_caminho=metadados_caminho,
            log_caminho=log_caminho,
            contexto="inicializacao_campanha",
        )
        raise
    with arquivo_log:
        try:
            for modo, rodada in fases:
                ordem = cenarios.copy()
                rng.shuffle(ordem)
                for modalidade, dataset, volume, arquitetura in ordem:
                    indice += 1
                    _registrar_mensagem(
                        arquivo_log,
                        f"\n=== {indice}/{total} | {modo} | {dataset.upper()} | "
                        f"{modalidade.upper()} | {volume} | {arquitetura.upper()} ===",
                    )
                    executar_pipeline(
                        comando(
                            modalidade,
                            dataset,
                            arquitetura,
                            volume,
                            modo,
                            rodada,
                        ),
                        ambiente=ambiente,
                        arquivo_log=arquivo_log,
                    )
                    metadados["execucoes_concluidas"] = indice
                    salvar_metadados(metadados_caminho, metadados)
        except BaseException as erro:
            _registrar_falha_campanha(
                erro,
                valores_sensiveis=valores_sensiveis,
                metadados=metadados,
                metadados_caminho=metadados_caminho,
                log_caminho=log_caminho,
                arquivo_log=arquivo_log,
            )
            raise

    metadados["status"] = "concluida"
    metadados["fim"] = agora_iso()
    try:
        salvar_metadados(metadados_caminho, metadados)
    except BaseException as erro:
        _registrar_falha_campanha(
            erro,
            valores_sensiveis=valores_sensiveis,
            metadados=metadados,
            metadados_caminho=metadados_caminho,
            log_caminho=log_caminho,
            contexto="finalizacao_campanha",
        )
        raise


def _executar_cli() -> None:
    try:
        main()
    except SystemExit as erro:
        if isinstance(erro.code, str):
            valores = _valores_sensiveis_ambiente(dict(os.environ))
            raise SystemExit(_sanitizar_texto_seguro(erro.code, valores)) from None
        raise
    except KeyboardInterrupt as erro:
        if not _erro_ja_reportado(erro):
            valores = _valores_sensiveis_ambiente(dict(os.environ))
            sys.stderr.write(_traceback_seguro(erro, valores))
            sys.stderr.flush()
        raise SystemExit(130) from None
    except BaseException as erro:
        if not _erro_ja_reportado(erro):
            valores = _valores_sensiveis_ambiente(dict(os.environ))
            sys.stderr.write(_traceback_seguro(erro, valores))
            sys.stderr.flush()
        raise SystemExit(1) from None


if __name__ == "__main__":
    _executar_cli()
