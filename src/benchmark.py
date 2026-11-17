from __future__ import annotations

import argparse
from datetime import datetime
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
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
    r"(?i)\b(?:[a-z0-9]+[_-])*"
    r"(password|passwd|pwd|senha|token|secret|api[_-]?key|database[_-]?url)"
    r"(?:\s*[:=]\s*|\s+)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


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


def _mensagem_erro_segura(erro: BaseException) -> str:
    try:
        mensagem = str(erro)
    except Exception:
        return "mensagem_indisponivel"
    mensagem = PADRAO_URL_CREDENCIAL.sub("<url_postgresql_redigida>", mensagem)
    mensagem = PADRAO_CREDENCIAL.sub(
        lambda correspondencia: f"{correspondencia.group(1)}=<valor_redigido>",
        mensagem,
    )
    return mensagem[:500]


def _erro_persistivel(erro: BaseException, contexto: str) -> dict[str, str]:
    return {
        "tipo": type(erro).__name__,
        "contexto": contexto,
        "mensagem": _mensagem_erro_segura(erro),
    }


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
    criar_diretorios_modalidades(campanha_dir)

    metadados_caminho = campanha_dir / "campanha.json"

    load_dotenv(BASE_DIR / ".env")
    try:
        ambiente_metadados = coletar_ambiente()
    except Exception as erro:
        ambiente_metadados = _ambiente_indisponivel(erro)
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = run_id
    ambiente["BENCHMARK_OUTPUT_DIR"] = str(campanha_dir)
    ambiente["BENCHMARK_ORCHESTRATOR_RUN_ID"] = run_id
    ambiente["PYTHONIOENCODING"] = "utf-8"
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

    print(f"Campanha: {run_id}")
    print(f"Seed: {args.seed}")
    total = len(cenarios) * len(fases)
    aquecimentos = len(cenarios)
    medicoes_validas = len(cenarios) * args.rodadas
    metadados: dict[str, object] = {
        "run_id": run_id,
        "status": "em_andamento",
        "inicio": agora_iso(),
        "fim": None,
        "commit_git": obter_commit_git(),
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
    salvar_metadados(metadados_caminho, metadados)
    indice = 0
    try:
        for modo, rodada in fases:
            ordem = cenarios.copy()
            rng.shuffle(ordem)
            for modalidade, dataset, volume, arquitetura in ordem:
                indice += 1
                print(
                    f"\n=== {indice}/{total} | {modo} | {dataset.upper()} | "
                    f"{modalidade.upper()} | {volume} | {arquitetura.upper()} ==="
                )
                subprocess.run(
                    comando(modalidade, dataset, arquitetura, volume, modo, rodada),
                    cwd=BASE_DIR,
                    env=ambiente,
                    check=True,
                )
                metadados["execucoes_concluidas"] = indice
                salvar_metadados(metadados_caminho, metadados)
    except BaseException as erro:
        metadados["status"] = (
            "interrompida" if isinstance(erro, KeyboardInterrupt) else "falhou"
        )
        metadados["fim"] = agora_iso()
        metadados["erro"] = _erro_persistivel(erro, "execucao_pipeline")
        salvar_metadados(metadados_caminho, metadados)
        raise

    metadados["status"] = "concluida"
    metadados["fim"] = agora_iso()
    salvar_metadados(metadados_caminho, metadados)


if __name__ == "__main__":
    main()
