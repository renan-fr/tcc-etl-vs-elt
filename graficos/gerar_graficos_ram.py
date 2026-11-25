"""Gera os graficos de USS media total da campanha oficial de recursos."""

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
    carregar_resultados,
    configurar_eixos,
    converter_numero,
)
from src.benchmark_paths import diretorio_campanha, validar_run_id


COLUNA_USS = "ram_media_total_mb"


def validar_uss(resultados: pd.DataFrame, campanha_dir: Path) -> pd.DataFrame:
    if COLUNA_USS not in resultados.columns:
        raise ValueError(f"Coluna obrigatoria ausente: {COLUNA_USS}")
    resultados = resultados.copy()
    resultados[COLUNA_USS] = converter_numero(
        resultados[COLUNA_USS], campanha_dir / "recursos", COLUNA_USS
    )
    if resultados[COLUNA_USS].isna().any():
        raise ValueError("Ha execucoes sem valor consolidado de USS media total.")
    return resultados


def gerar_grafico(df: pd.DataFrame, dataset: str, destino: Path) -> None:
    dados = df[df["dataset"] == dataset]
    resumo = dados.groupby(["volume_configurado", "arquitetura"])[COLUNA_USS].agg(
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
                .sort_values("rodada")[COLUNA_USS]
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

    configurar_eixos(ax, posicoes, "Memória USS média total (MiB)")
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
        resultados = validar_uss(
            carregar_resultados(campanha_dir, run_id), campanha_dir
        )
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    imagens_dir = BASE_DIR / "imagens"
    imagens_dir.mkdir(parents=True, exist_ok=True)
    destinos = {
        "ENEM": imagens_dir / "ram_media_enem.png",
        "TSE": imagens_dir / "ram_media_tse.png",
    }
    for dataset, destino in destinos.items():
        gerar_grafico(resultados, dataset, destino)

    contagens = resultados.groupby(
        ["dataset", "arquitetura", "volume_configurado"]
    ).size()
    medias = resultados.groupby(
        ["dataset", "arquitetura", "volume_configurado"]
    )[COLUNA_USS].mean()
    print("Rodadas validas por combinacao:")
    print(contagens.to_string())
    print("\nMedias de USS total (MiB):")
    print(medias.round(2).to_string())
    print("\nArquivos gerados:")
    for destino in destinos.values():
        print(destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
