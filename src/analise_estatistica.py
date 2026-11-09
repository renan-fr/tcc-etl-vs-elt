"""Consolida estatisticamente uma campanha de benchmark ETL x ELT.

Uso:
    python src/analise_estatistica.py <run_id>

O módulo não depende de PostgreSQL, pandas ou dos datasets oficiais. Ele lê os
CSVs já produzidos pelo benchmark, valida a campanha inteira e só então grava
os resultados em ``<campanha>/analise``.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import statistics
import sys
from typing import Iterable

try:
    from src.benchmark_paths import CAMPANHAS_DIR, diretorio_campanha, validar_run_id
except ModuleNotFoundError:  # execução direta: python src/analise_estatistica.py
    from benchmark_paths import CAMPANHAS_DIR, diretorio_campanha, validar_run_id


MODALIDADES = ("desempenho", "recursos")
ARQUITETURAS = ("etl", "elt")
EXPECTED_ROUNDS = frozenset(range(1, 6))
IDENTITY_FIELDS = (
    "run_id", "modalidade", "dataset", "arquitetura", "volume_configurado", "rodada"
)
PERFORMANCE_METRICS = ("tempo_total", "throughput")
DIAGNOSTIC_TIME_METRICS = ("tempo_leitura", "tempo_transformacao", "tempo_carga")
RESOURCE_METRIC_ALIASES = {
    "cpu_media": ("cpu_media_total", "cpu_media"),
    "cpu_pico": ("cpu_pico_total", "cpu_pico"),
    "ram_media": ("ram_media_total_mb", "ram_media_mb", "ram_media"),
    "ram_pico": ("ram_pico_total_mb", "ram_pico_mb", "ram_pico"),
}
OPTIONAL_RESOURCE_METRICS = (
    "cpu_media_python", "cpu_pico_python", "ram_media_python_mb", "ram_pico_python_mb",
    "cpu_media_postgres", "cpu_pico_postgres", "ram_media_postgres_mb", "ram_pico_postgres_mb",
)


class AnaliseError(ValueError):
    """Erro de validação que deve ser apresentado ao usuário sem traceback."""


def _numero(valor: str | None, campo: str, arquivo: Path, linha: int) -> float:
    texto = "" if valor is None else valor.strip()
    if not texto:
        raise AnaliseError(f"{arquivo}:{linha}: métrica obrigatória vazia: {campo}")
    try:
        numero = float(texto.replace(".", "").replace(",", ".") if "," in texto else texto)
    except ValueError as erro:
        raise AnaliseError(f"{arquivo}:{linha}: valor não numérico em {campo}: {valor!r}") from erro
    if not math.isfinite(numero):
        raise AnaliseError(f"{arquivo}:{linha}: valor numérico inválido em {campo}: {valor!r}")
    return numero


def _rodada(valor: str | None, arquivo: Path, linha: int) -> int | None:
    texto = "" if valor is None else valor.strip().lower()
    if texto in {"aquecimento", "warmup", "warming_up", "certificacao", "certificação"}:
        return None
    try:
        rodada = int(texto)
    except ValueError as erro:
        raise AnaliseError(f"{arquivo}:{linha}: rodada inválida: {valor!r}") from erro
    if rodada <= 0:
        return None
    return rodada


def _ler_modalidade(campanha: Path, modalidade: str, run_id: str) -> list[dict[str, object]]:
    pasta = campanha / modalidade
    if not pasta.is_dir():
        raise AnaliseError(f"Diretório obrigatório ausente: {pasta}")
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        raise AnaliseError(f"Nenhum CSV encontrado em {pasta}")
    registros: list[dict[str, object]] = []
    vistos: set[tuple[str, str, str, str, int]] = set()
    metricas_recursos: tuple[str, ...] | None = None
    for arquivo in arquivos:
        with arquivo.open("r", encoding="utf-8-sig", newline="") as stream:
            leitor = csv.DictReader(stream, delimiter=";")
            campos = set(leitor.fieldnames or ())
            ausentes = set(IDENTITY_FIELDS) - campos
            if ausentes:
                raise AnaliseError(f"{arquivo}: colunas obrigatórias ausentes: {sorted(ausentes)}")
            for numero_linha, bruto in enumerate(leitor, start=2):
                if (bruto.get("run_id") or "").strip() != run_id:
                    raise AnaliseError(f"{arquivo}:{numero_linha}: registro pertence a outro run_id")
                if (bruto.get("modalidade") or "").strip() != modalidade:
                    raise AnaliseError(f"{arquivo}:{numero_linha}: modalidade incompatível com o diretório")
                rodada = _rodada(bruto.get("rodada"), arquivo, numero_linha)
                if rodada is None:  # aquecimento/certificação não participa da análise
                    continue
                dataset = (bruto.get("dataset") or "").strip().lower()
                arquitetura = (bruto.get("arquitetura") or "").strip().lower()
                volume = (bruto.get("volume_configurado") or "").strip()
                if not dataset or arquitetura not in ARQUITETURAS or not volume:
                    raise AnaliseError(f"{arquivo}:{numero_linha}: identidade experimental incompleta")
                try:
                    volume_num = int(volume)
                except ValueError as erro:
                    raise AnaliseError(f"{arquivo}:{numero_linha}: volume inválido: {volume!r}") from erro
                chave = (modalidade, dataset, arquitetura, str(volume_num), rodada)
                if chave in vistos:
                    raise AnaliseError(f"{arquivo}:{numero_linha}: rodada duplicada para {chave}")
                vistos.add(chave)
                registro: dict[str, object] = {
                    "run_id": run_id, "modalidade": modalidade, "dataset": dataset,
                    "arquitetura": arquitetura, "volume_configurado": volume_num, "rodada": rodada,
                    "_arquivo": str(arquivo), "_linha": numero_linha, "_campos": campos,
                }
                if modalidade == "desempenho":
                    metricas = PERFORMANCE_METRICS + DIAGNOSTIC_TIME_METRICS
                else:
                    disponiveis = tuple(
                        metrica for metrica in OPTIONAL_RESOURCE_METRICS
                        if metrica in campos
                    )
                    metricas = tuple(RESOURCE_METRIC_ALIASES) + disponiveis
                    if metricas_recursos is None:
                        metricas_recursos = metricas
                    elif metricas != metricas_recursos:
                        raise AnaliseError(f"{arquivo}: esquema de métricas de recursos inconsistente")
                for metrica in metricas:
                    campo = metrica
                    if modalidade == "recursos":
                        campo = (
                            next((nome for nome in RESOURCE_METRIC_ALIASES[metrica] if nome in campos), "")
                            if metrica in RESOURCE_METRIC_ALIASES
                            else metrica
                        )
                    registro[metrica] = _numero(bruto.get(campo), campo or metrica, arquivo, numero_linha)
                registros.append(registro)
    return registros


def _validar_completude(registros: list[dict[str, object]], modalidade: str) -> None:
    grupos: dict[tuple[str, int], dict[str, set[int]]] = {}
    for registro in registros:
        chave = (str(registro["dataset"]), int(registro["volume_configurado"]))
        grupos.setdefault(chave, {}).setdefault(str(registro["arquitetura"]), set()).add(int(registro["rodada"]))
    if not grupos:
        raise AnaliseError(f"Nenhuma execução válida encontrada para {modalidade}")
    erros: list[str] = []
    for (dataset, volume), arquiteturas in sorted(grupos.items()):
        for arquitetura in ARQUITETURAS:
            rodadas = arquiteturas.get(arquitetura, set())
            if rodadas != EXPECTED_ROUNDS:
                erros.append(f"{modalidade}: {dataset}/{volume}/{arquitetura}: esperadas {sorted(EXPECTED_ROUNDS)}, encontradas {sorted(rodadas)}")
    if erros:
        raise AnaliseError("Cenários incompletos:\n" + "\n".join(erros))


def _estatisticas(valores: Iterable[float]) -> tuple[float, float, float]:
    lista = list(valores)
    return statistics.fmean(lista), statistics.stdev(lista), statistics.median(lista)


def _agrupar(registros: list[dict[str, object]], metricas: tuple[str, ...]) -> list[dict[str, object]]:
    grupos: dict[tuple[str, int, str], list[dict[str, object]]] = {}
    for registro in registros:
        chave = (str(registro["dataset"]), int(registro["volume_configurado"]), str(registro["arquitetura"]))
        grupos.setdefault(chave, []).append(registro)
    saida: list[dict[str, object]] = []
    for (dataset, volume, arquitetura), itens in sorted(grupos.items()):
        base = {"dataset": dataset, "volume_configurado": volume, "arquitetura": arquitetura, "n_execucoes": len(itens)}
        for metrica in metricas:
            media, desvio, mediana = _estatisticas(float(item[metrica]) for item in itens)
            base.update({f"{metrica}_media": media, f"{metrica}_desvio_padrao": desvio, f"{metrica}_mediana": mediana})
        saida.append(base)
    return saida


def _comparar(desempenho: list[dict[str, object]]) -> list[dict[str, object]]:
    agrupado = _agrupar(desempenho, ("tempo_total",))
    por_chave = {(r["dataset"], r["volume_configurado"], r["arquitetura"]): r for r in agrupado}
    cenarios = sorted({(r["dataset"], r["volume_configurado"]) for r in agrupado})
    saida = []
    for dataset, volume in cenarios:
        etl = por_chave.get((dataset, volume, "etl"))
        elt = por_chave.get((dataset, volume, "elt"))
        if etl is None or elt is None:
            raise AnaliseError(f"Comparação impossível: falta ETL ou ELT em {dataset}/{volume}")
        media_etl = float(etl["tempo_total_media"])
        reducao = ((media_etl - float(elt["tempo_total_media"])) / media_etl) * 100 if media_etl else 0.0
        saida.append({
            "dataset": dataset, "volume_configurado": volume,
            "tempo_total_etl_media": media_etl,
            "tempo_total_etl_desvio_padrao": etl["tempo_total_desvio_padrao"],
            "tempo_total_etl_mediana": etl["tempo_total_mediana"],
            "tempo_total_elt_media": elt["tempo_total_media"],
            "tempo_total_elt_desvio_padrao": elt["tempo_total_desvio_padrao"],
            "tempo_total_elt_mediana": elt["tempo_total_mediana"],
            "reducao_tempo_pct": reducao,
        })
    return saida


def _escrever(caminho: Path, linhas: list[dict[str, object]]) -> None:
    campos = list(linhas[0]) if linhas else []
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as stream:
        escritor = csv.DictWriter(stream, fieldnames=campos, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({campo: str(valor).replace(".", ",") if isinstance(valor, float) else valor for campo, valor in linha.items()})
    temporario.replace(caminho)


def analisar_campanha(run_id: str, base_dir: Path | None = None) -> Path:
    run_id = validar_run_id(run_id)
    campanha = (base_dir or CAMPANHAS_DIR) / run_id
    if not campanha.is_dir():
        raise AnaliseError(f"Campanha não encontrada: {campanha}")
    desempenho = _ler_modalidade(campanha, "desempenho", run_id)
    recursos = _ler_modalidade(campanha, "recursos", run_id)
    _validar_completude(desempenho, "desempenho")
    _validar_completude(recursos, "recursos")
    saidas = {
        "analise_desempenho.csv": _agrupar(desempenho, PERFORMANCE_METRICS + DIAGNOSTIC_TIME_METRICS),
        "analise_recursos.csv": _agrupar(
            recursos,
            tuple(RESOURCE_METRIC_ALIASES)
            + tuple(metrica for metrica in OPTIONAL_RESOURCE_METRICS if metrica in recursos[0]),
        ),
        "comparacao_etl_elt.csv": _comparar(desempenho),
    }
    destino = campanha / "analise"
    destino.mkdir(exist_ok=True)
    for nome, linhas in saidas.items():
        _escrever(destino / nome, linhas)
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolida estatísticas de uma campanha ETL x ELT.")
    parser.add_argument("run_id", help="identificador em data/benchmark/campanhas/<run_id>")
    args = parser.parse_args(argv)
    try:
        destino = analisar_campanha(args.run_id)
    except (AnaliseError, ValueError, OSError) as erro:
        print(f"Erro na análise: {erro}", file=sys.stderr)
        return 1
    print(f"Análise criada em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
