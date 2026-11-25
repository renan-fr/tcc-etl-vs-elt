"""Valida o impacto da remocao de processos antes da leitura de USS.

O experimento executa cada pipeline uma unica vez sob um unico monitor. A
consolidacao ``original`` e produzida pelo proprio ``MonitorRecursos``; a
consolidacao ``corrigida`` reutiliza exatamente as mesmas amostras e exclui as
que perderam processos PostgreSQL durante a leitura de CPU.

Este modulo e deliberadamente separado do orquestrador e dos pipelines
oficiais. Seus artefatos sao gravados somente em
``data/experimentos/uss_validation``.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import importlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any, Iterable


SRC_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import psutil  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

try:  # Importacao como pacote nos testes; como script no experimento.
    from .. import resource_monitor as rm  # type: ignore[import-not-found]  # noqa: E402
except ImportError:  # pragma: no cover - exercitado pela invocacao do script
    import resource_monitor as rm  # type: ignore[no-redef]  # noqa: E402


INTERVALO_SEGUNDOS = 0.5
SEED = 20241027
SAIDA_RAIZ = BASE_DIR / "data" / "experimentos" / "uss_validation"
CENARIOS = (
    ("enem", 100_000),
    ("enem", 1_000_000),
    ("tse", 100_000),
)
CHAVES_RAM = ("python", "postgres", "total")


def _identidade_json(identidade: tuple[int, float]) -> dict[str, int | float]:
    return {"pid": identidade[0], "create_time": identidade[1]}


def _media_pico(valores: Iterable[float]) -> dict[str, float | None]:
    serie = list(valores)
    if not serie:
        return {"media_mb": None, "pico_mb": None}
    mb = 1024 * 1024
    return {
        "media_mb": sum(serie) / len(serie) / mb,
        "pico_mb": max(serie) / mb,
    }


def _diferenca(corrigido: float | None, original: float | None) -> dict[str, float | None]:
    if corrigido is None or original is None:
        return {"absoluta_mb": None, "percentual": None}
    absoluta = corrigido - original
    percentual = absoluta / original * 100.0 if original else None
    return {"absoluta_mb": absoluta, "percentual": percentual}


class MonitorUSSValidacao(rm.MonitorRecursos):
    """Instrumenta o monitor oficial sem alterar sua coleta ou consolidacao."""

    def __init__(self, intervalo_segundos: float = INTERVALO_SEGUNDOS, **kwargs: Any) -> None:
        self._auditoria_amostras: list[dict[str, Any]] = []
        self._auditoria_eventos: list[dict[str, Any]] = []
        self._auditoria_indice: int | None = None
        self._auditoria_identidades_por_objeto: dict[int, tuple[int, float]] = {}
        self._auditoria_cpu_removidos: list[tuple[int, float]] = []
        self._auditoria_uss_postgres: dict[tuple[int, float], int | None] = {}
        self._auditoria_uss_python: int | None = None
        super().__init__(intervalo_segundos=intervalo_segundos, **kwargs)

    def _evento(
        self,
        tipo: str,
        identidade: tuple[int, float] | None = None,
        **detalhes: Any,
    ) -> None:
        evento: dict[str, Any] = {
            "tipo": tipo,
            "amostra": self._auditoria_indice,
            "registrado_em": datetime.now().astimezone().isoformat(),
        }
        if identidade is not None:
            evento.update(_identidade_json(identidade))
        evento.update(detalhes)
        self._auditoria_eventos.append(evento)

    def _descobrir_e_inicializar_processos(self) -> set[tuple[int, float]]:
        novos = super()._descobrir_e_inicializar_processos()
        for identidade in sorted(novos):
            self._evento("processo_descoberto", identidade)
        return novos

    def _ler_cpu(self, processo: psutil.Process, rotulo: str) -> float | None:
        valor = rm.MonitorRecursos._ler_cpu(processo, rotulo)
        if rotulo == "PostgreSQL" and valor is None:
            identidade = self._auditoria_identidades_por_objeto.get(id(processo))
            if identidade is not None:
                self._auditoria_cpu_removidos.append(identidade)
                self._evento("processo_removido_durante_cpu", identidade)
        return valor

    def _ler_ram_python(self, processo: psutil.Process) -> int | None:
        valor = rm.MonitorRecursos._ler_ram_python(processo)
        self._auditoria_uss_python = valor
        return valor

    def _ler_ram_postgres(
        self,
        processo: psutil.Process,
        identidade_esperada: tuple[int, float],
    ) -> int | None:
        valor = rm.MonitorRecursos._ler_ram_postgres(processo, identidade_esperada)
        self._auditoria_uss_postgres[identidade_esperada] = valor
        if valor is None:
            self._evento("processo_encerrado_durante_uss", identidade_esperada)
        return valor

    def _registrar_amostra(self) -> None:
        quantidade_antes = len(self._amostras)
        self._auditoria_indice = quantidade_antes + 1
        self._auditoria_identidades_por_objeto = {
            id(processo): identidade
            for identidade, processo in self._processos_postgres.items()
        }
        self._auditoria_cpu_removidos = []
        self._auditoria_uss_postgres = {}
        self._auditoria_uss_python = None

        super()._registrar_amostra()
        if len(self._amostras) == quantidade_antes:
            return

        removidos = set(self._auditoria_cpu_removidos)
        identidades = set(self._auditoria_uss_postgres) | removidos
        processos = []
        for identidade in sorted(identidades):
            processos.append(
                {
                    **_identidade_json(identidade),
                    "uss_bytes": self._auditoria_uss_postgres.get(identidade),
                    "leitura_uss_realizada": identidade in self._auditoria_uss_postgres,
                    "removido_durante_cpu": identidade in removidos,
                }
            )

        amostra_oficial = dict(self._amostras[-1])
        self._auditoria_amostras.append(
            {
                "indice": self._auditoria_indice,
                "registrada_em": datetime.now().astimezone().isoformat(),
                "python": {
                    **_identidade_json(self._identidade_python),
                    "uss_bytes": self._auditoria_uss_python,
                },
                "postgres": processos,
                "processos_removidos_durante_cpu": [
                    _identidade_json(item) for item in sorted(removidos)
                ],
                "afetada_pela_correcao": bool(removidos),
                "agregados_oficiais": amostra_oficial,
            }
        )

    def consolidar_duplo(self) -> dict[str, Any]:
        """Finaliza uma unica coleta e consolida os dois criterios."""
        resultado_oficial = self.parar()
        amostras = self._auditoria_amostras

        def valores(componente: str, corrigido: bool) -> list[float]:
            chave = f"ram_{componente}"
            saida = []
            for auditada in amostras:
                if corrigido and auditada["afetada_pela_correcao"]:
                    continue
                base = auditada["agregados_oficiais"]
                if componente == "postgres" and base.get(
                    "ram_postgres_convencional", False
                ):
                    continue
                valor = base.get(chave)
                if valor is not None:
                    saida.append(float(valor))
            return saida

        metricas: dict[str, dict[str, dict[str, float | None]]] = {
            "original": {},
            "corrigida": {},
        }
        contagens_validas: dict[str, dict[str, int]] = {
            "original": {},
            "corrigida": {},
        }
        for criterio, corrigido in (("original", False), ("corrigida", True)):
            for componente in CHAVES_RAM:
                serie = valores(componente, corrigido)
                metricas[criterio][componente] = _media_pico(serie)
                contagens_validas[criterio][componente] = len(serie)

        diferencas: dict[str, dict[str, dict[str, float | None]]] = {}
        for componente in CHAVES_RAM:
            diferencas[componente] = {}
            for estatistica in ("media_mb", "pico_mb"):
                diferencas[componente][estatistica] = _diferenca(
                    metricas["corrigida"][componente][estatistica],
                    metricas["original"][componente][estatistica],
                )

        adicionais = sum(
            bool(amostra["afetada_pela_correcao"])
            and amostra["agregados_oficiais"].get("ram_postgres") is not None
            and not amostra["agregados_oficiais"].get(
                "ram_postgres_convencional", False
            )
            for amostra in amostras
        )
        return {
            "intervalo_monitoramento_s": self.intervalo_segundos,
            "amostras_totais": len(amostras),
            "amostras_postgres_reais": sum(
                not amostra["agregados_oficiais"].get(
                    "ram_postgres_convencional", False
                )
                for amostra in amostras
            ),
            "amostras_validas": contagens_validas,
            "amostras_adicionalmente_descartadas": adicionais,
            "metricas_uss": metricas,
            "diferencas_corrigida_menos_original": diferencas,
            "resultado_oficial_completo": resultado_oficial,
        }

    def amostras_auditoria(self) -> list[dict[str, Any]]:
        return [dict(amostra) for amostra in self._auditoria_amostras]

    def eventos_auditoria(self) -> list[dict[str, Any]]:
        return [dict(evento) for evento in self._auditoria_eventos]


def _escrever_jsonl(caminho: Path, itens: Iterable[dict[str, Any]]) -> None:
    with caminho.open("w", encoding="utf-8", newline="\n") as arquivo:
        for item in itens:
            arquivo.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
            arquivo.write("\n")


def _carregar_pipeline(dataset: str):
    diretorio = SRC_DIR / dataset
    sys.path.insert(0, str(diretorio))
    try:
        return importlib.import_module("elt")
    finally:
        sys.path.remove(str(diretorio))


def _executar_pipeline(dataset: str, volume: int) -> None:
    pipeline = _carregar_pipeline(dataset)
    if dataset == "enem":
        pipeline.executar_elt(
            os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL"),
            volume,
            os.getenv("POSTGRES_SCHEMA_ENEM_ELT_RAW", pipeline.SCHEMA_RAW),
            os.getenv("POSTGRES_SCHEMA_ENEM_ELT_FINAL", pipeline.SCHEMA_FINAL),
            validar=False,
        )
        return

    manifesto = (
        BASE_DIR
        / "data"
        / "benchmark"
        / "tse"
        / "subconjuntos"
        / f"chaves_{volume}.csv"
    )
    if not manifesto.is_file():
        raise FileNotFoundError(f"Manifesto TSE ausente: {manifesto}")
    args = argparse.Namespace(
        limite=volume,
        manifesto_chaves=manifesto,
        database_url=os.getenv("DATABASE_URL"),
        schema_raw=os.getenv("POSTGRES_SCHEMA_TSE_ELT_RAW", pipeline.SCHEMA_RAW),
        schema_staging=os.getenv(
            "POSTGRES_SCHEMA_TSE_ELT_STAGING", pipeline.SCHEMA_STAGING
        ),
        schema_final=os.getenv(
            "POSTGRES_SCHEMA_TSE_ELT_FINAL", pipeline.SCHEMA_FINAL
        ),
        benchmark=False,
        sem_validacao=True,
        monitorar_recursos=False,
        modalidade="recursos",
        rodada=None,
        benchmark_output=None,
    )
    pipeline.executar(args)


def _worker(args: argparse.Namespace) -> None:
    load_dotenv(BASE_DIR / ".env")
    destino = Path(args.output_dir).resolve()
    destino.mkdir(parents=True, exist_ok=False)
    monitor = MonitorUSSValidacao(intervalo_segundos=INTERVALO_SEGUNDOS)
    monitor.iniciar()
    try:
        _executar_pipeline(args.dataset, args.volume)
        resumo = monitor.consolidar_duplo()
    except BaseException:
        monitor._abortar()
        raise

    resumo.update(
        {
            "dataset": args.dataset,
            "arquitetura": "elt",
            "volume_configurado": args.volume,
            "fase": args.fase,
            "rodada": args.rodada,
            "finalizada_em": datetime.now().astimezone().isoformat(),
        }
    )
    (destino / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _escrever_jsonl(destino / "amostras.jsonl", monitor.amostras_auditoria())
    _escrever_jsonl(destino / "eventos.jsonl", monitor.eventos_auditoria())


def _linha_resumo(resumo: dict[str, Any], caminho: Path) -> dict[str, Any]:
    linha: dict[str, Any] = {
        "dataset": resumo["dataset"],
        "arquitetura": resumo["arquitetura"],
        "volume_configurado": resumo["volume_configurado"],
        "fase": resumo["fase"],
        "rodada": resumo["rodada"],
        "amostras_totais": resumo["amostras_totais"],
        "amostras_postgres_reais": resumo["amostras_postgres_reais"],
        "amostras_adicionalmente_descartadas": resumo[
            "amostras_adicionalmente_descartadas"
        ],
        "diretorio_execucao": str(caminho.relative_to(BASE_DIR)),
    }
    for criterio in ("original", "corrigida"):
        for componente in CHAVES_RAM:
            linha[f"amostras_validas_{criterio}_{componente}"] = resumo[
                "amostras_validas"
            ][criterio][componente]
            for estatistica in ("media_mb", "pico_mb"):
                linha[f"uss_{estatistica}_{criterio}_{componente}"] = resumo[
                    "metricas_uss"
                ][criterio][componente][estatistica]
                diferenca = resumo["diferencas_corrigida_menos_original"][
                    componente
                ][estatistica]
                linha[f"diferenca_absoluta_{estatistica}_{componente}"] = diferenca[
                    "absoluta_mb"
                ]
                linha[f"diferenca_percentual_{estatistica}_{componente}"] = diferenca[
                    "percentual"
                ]
    return linha


def _orquestrar(args: argparse.Namespace) -> None:
    destino = SAIDA_RAIZ / args.run_id
    destino.mkdir(parents=True, exist_ok=False)
    rng = random.Random(args.seed)
    fases = [("aquecimento", None), *[("medicao", i) for i in range(1, 6)]]
    plano: list[tuple[str, int | None, str, int]] = []
    for fase, rodada in fases:
        ordem = list(CENARIOS)
        rng.shuffle(ordem)
        plano.extend((fase, rodada, dataset, volume) for dataset, volume in ordem)

    commit_git = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BASE_DIR,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    metadados = {
        "run_id": args.run_id,
        "status": "em_andamento",
        "inicio": datetime.now().astimezone().isoformat(),
        "commit_git": commit_git,
        "python": sys.version,
        "psutil": psutil.__version__,
        "seed": args.seed,
        "intervalo_monitoramento_s": INTERVALO_SEGUNDOS,
        "aquecimentos": 1,
        "medicoes_por_cenario": 5,
        "cenarios": [
            {"dataset": dataset, "arquitetura": "elt", "volume": volume}
            for dataset, volume in CENARIOS
        ],
        "plano": [
            {"fase": fase, "rodada": rodada, "dataset": dataset, "volume": volume}
            for fase, rodada, dataset, volume in plano
        ],
    }
    metadados_path = destino / "experimento.json"
    metadados_path.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    linhas = []
    try:
        for indice, (fase, rodada, dataset, volume) in enumerate(plano, start=1):
            nome = f"{indice:02d}_{fase}_{dataset}_elt_{volume}"
            execucao_dir = destino / nome
            comando = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker",
                "--dataset",
                dataset,
                "--volume",
                str(volume),
                "--fase",
                fase,
                "--output-dir",
                str(execucao_dir),
            ]
            if rodada is not None:
                comando.extend(["--rodada", str(rodada)])
            print(f"[{indice}/{len(plano)}] {fase}: {dataset.upper()} ELT {volume}")
            subprocess.run(comando, cwd=BASE_DIR, check=True)
            resumo = json.loads((execucao_dir / "resumo.json").read_text(encoding="utf-8"))
            linhas.append(_linha_resumo(resumo, execucao_dir))
    except BaseException:
        metadados["status"] = "falhou"
        metadados["fim"] = datetime.now().astimezone().isoformat()
        metadados_path.write_text(
            json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise

    with (destino / "resumos.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    metadados["status"] = "concluido"
    metadados["fim"] = datetime.now().astimezone().isoformat()
    metadados_path.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnostico isolado da remocao de processos antes da USS."
    )
    parser.add_argument("--run-id")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dataset", choices=("enem", "tse"), help=argparse.SUPPRESS)
    parser.add_argument("--volume", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--fase", choices=("aquecimento", "medicao"), help=argparse.SUPPRESS)
    parser.add_argument("--rodada", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", help=argparse.SUPPRESS)
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.worker:
        faltantes = [
            nome
            for nome in ("dataset", "volume", "fase", "output_dir")
            if getattr(args, nome) is None
        ]
        if faltantes:
            parser.error("worker sem argumentos: " + ", ".join(faltantes))
        _worker(args)
        return
    if not args.run_id:
        parser.error("--run-id e obrigatorio")
    if any(
        caractere
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
        for caractere in args.run_id
    ):
        parser.error("--run-id contem caracteres invalidos")
    _orquestrar(args)


if __name__ == "__main__":
    main()
