"""Gera os graficos de tempo total da campanha oficial de desempenho."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from graficos.gerar_graficos_cpu import (
    BASE_DIR,
    CORES,
    DESLOCAMENTOS,
    JITTER,
    VOLUMES,
    adicionar_legenda,
    configurar_eixos,
    converter_numero,
)
from src.benchmark_paths import diretorio_campanha, validar_run_id


COLUNA_TEMPO = "tempo_total"
COLUNAS_OBRIGATORIAS = {
    "run_id",
    "modalidade",
    "monitoramento_ativo",
    "intervalo_monitoramento_s",
    "dataset",
    "volume_configurado",
    "arquitetura",
    "rodada",
    COLUNA_TEMPO,
}


def carregar_resultados(campanha_dir: Path, run_id: str) -> pd.DataFrame:
    desempenho_dir = campanha_dir / "desempenho"
    arquivos = {
        ("ENEM", "ETL"): desempenho_dir / "enem_etl.csv",
        ("ENEM", "ELT"): desempenho_dir / "enem_elt.csv",
        ("TSE", "ETL"): desempenho_dir / "tse_etl.csv",
        ("TSE", "ELT"): desempenho_dir / "tse_elt.csv",
    }
    partes = []

    for (dataset, arquitetura), caminho in arquivos.items():
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo de desempenho nao encontrado: {caminho}")
        df = pd.read_csv(caminho, sep=";")
        ausentes = COLUNAS_OBRIGATORIAS - set(df.columns)
        if ausentes:
            raise ValueError(f"{caminho}: colunas obrigatorias ausentes: {sorted(ausentes)}")
        if df["run_id"].astype("string").str.strip().ne(run_id).any():
            raise ValueError(f"{caminho}: ha dados de outra campanha.")
        if df["modalidade"].astype("string").str.strip().str.lower().ne("desempenho").any():
            raise ValueError(f"{caminho}: ha dados de outra modalidade.")
        monitoramento = df["monitoramento_ativo"].astype("string").str.strip().str.lower()
        if not monitoramento.isin(("false", "0")).all():
            raise ValueError(f"{caminho}: ha execucao de desempenho com monitoramento ativo.")
        intervalos = df["intervalo_monitoramento_s"].astype("string").str.strip()
        if intervalos.fillna("").ne("").any():
            raise ValueError(f"{caminho}: desempenho nao deve ter intervalo de monitoramento.")
        if df["dataset"].astype("string").str.strip().str.upper().ne(dataset).any():
            raise ValueError(f"{caminho}: dataset nao corresponde ao arquivo.")
        if df["arquitetura"].astype("string").str.strip().str.upper().ne(arquitetura).any():
            raise ValueError(f"{caminho}: arquitetura nao corresponde ao arquivo.")

        df = df.copy()
        df["dataset"] = dataset
        df["arquitetura"] = arquitetura
        df["volume_configurado"] = pd.to_numeric(df["volume_configurado"], errors="raise")
        df["rodada"] = pd.to_numeric(df["rodada"], errors="raise")
        df[COLUNA_TEMPO] = converter_numero(df[COLUNA_TEMPO], caminho, COLUNA_TEMPO)
        partes.append(df)

    resultados = pd.concat(partes, ignore_index=True)
    chaves = ["dataset", "arquitetura", "volume_configurado", "rodada"]
    if resultados.duplicated(chaves).any():
        raise ValueError("Ha execucoes duplicadas para a mesma combinacao e rodada.")
    if set(resultados["volume_configurado"]) != set(VOLUMES):
        raise ValueError("Os volumes encontrados nao correspondem aos quatro volumes esperados.")
    if not resultados["rodada"].isin(range(1, 6)).all():
        raise ValueError("Foram encontradas rodadas fora do intervalo de 1 a 5.")

    grupos = resultados.groupby(["dataset", "arquitetura", "volume_configurado"])
    contagens = grupos.size()
    rodadas = grupos["rodada"].nunique()
    combinacoes_esperadas = {
        (dataset, arquitetura, volume)
        for dataset in ("ENEM", "TSE")
        for arquitetura in ("ETL", "ELT")
        for volume in VOLUMES
    }
    if (
        set(contagens.index) != combinacoes_esperadas
        or not (contagens == 5).all()
        or not (rodadas == 5).all()
    ):
        raise ValueError(
            "Cada combinacao dataset x arquitetura x volume deve ter exatamente cinco rodadas validas: "
            f"{contagens.to_dict()}"
        )
    return resultados


def gerar_grafico(df: pd.DataFrame, dataset: str, destino: Path) -> None:
    dados = df[df["dataset"] == dataset]
    resumo = dados.groupby(["volume_configurado", "arquitetura"])[COLUNA_TEMPO].agg(
        ["mean", "min", "max"]
    )
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    posicoes = list(range(len(VOLUMES)))

    for arquitetura in ("ETL", "ELT"):
        estatisticas = resumo.xs(arquitetura, level="arquitetura").reindex(VOLUMES)
        x_medias = [x + DESLOCAMENTOS[arquitetura] for x in posicoes]
        medias = estatisticas["mean"].to_numpy()
        erros = [
            medias - estatisticas["min"].to_numpy(),
            estatisticas["max"].to_numpy() - medias,
        ]
        ax.errorbar(
            x_medias,
            medias,
            yerr=erros,
            color=CORES[arquitetura],
            marker="o",
            linewidth=2,
            markersize=5,
            capsize=4,
            elinewidth=1.2,
            label=arquitetura,
            zorder=3,
        )
        for indice, volume in enumerate(VOLUMES):
            observacoes = (
                dados[
                    (dados["arquitetura"] == arquitetura)
                    & (dados["volume_configurado"] == volume)
                ]
                .sort_values("rodada")[COLUNA_TEMPO]
                .to_numpy()
            )
            ax.scatter(
                [x_medias[indice] + ajuste for ajuste in JITTER],
                observacoes,
                color=CORES[arquitetura],
                s=20,
                alpha=0.55,
                edgecolors="white",
                linewidths=0.4,
                zorder=4,
            )

    ax.margins(y=0.125)
    configurar_eixos(ax, posicoes, "Tempo total (s)")
    adicionar_legenda(ax)
    fig.tight_layout()
    fig.savefig(destino, dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        run_id = validar_run_id(args.run_id)
        campanha_dir = diretorio_campanha(run_id)
        resultados = carregar_resultados(campanha_dir, run_id)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    imagens_dir = BASE_DIR / "imagens"
    imagens_dir.mkdir(parents=True, exist_ok=True)
    destinos = {
        "ENEM": imagens_dir / "tempo_total_enem.png",
        "TSE": imagens_dir / "tempo_total_tse.png",
    }
    for dataset, destino in destinos.items():
        gerar_grafico(resultados, dataset, destino)

    grupos = ["dataset", "arquitetura", "volume_configurado"]
    contagens = resultados.groupby(grupos).size()
    resumo = resultados.groupby(grupos)[COLUNA_TEMPO].agg(["mean", "min", "max"])
    print("Rodadas validas por combinacao:")
    print(contagens.to_string())
    print("\nResumo de tempo total (s):")
    print(resumo.round(3).to_string())
    print("\nArquivos gerados:")
    for destino in destinos.values():
        print(destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
