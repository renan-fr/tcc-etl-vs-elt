"""Gera os graficos de CPU media total da campanha oficial de recursos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from src.benchmark_paths import diretorio_campanha, validar_run_id


BASE_DIR = Path(__file__).resolve().parents[1]
CORES = {"ETL": "#2ca25f", "ELT": "#2b6cb0"}
VOLUMES = [100_000, 250_000, 500_000, 1_000_000]
ROTULOS_VOLUMES = ["100 mil", "250 mil", "500 mil", "1 milhão"]
DESLOCAMENTOS = {"ETL": -0.06, "ELT": 0.06}
JITTER = [-0.032, -0.016, 0.0, 0.016, 0.032]
COLUNAS_OBRIGATORIAS = {
    "run_id",
    "modalidade",
    "monitoramento_ativo",
    "dataset",
    "volume_configurado",
    "arquitetura",
    "rodada",
    "cpu_media_total",
}


def converter_numero(serie: pd.Series, caminho: Path, coluna: str) -> pd.Series:
    valores = pd.to_numeric(
        serie.astype("string").str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )
    if valores.isna().any() or (valores < 0).any():
        raise ValueError(f"{caminho}: {coluna} deve conter apenas valores validos e nao negativos.")
    return valores


def carregar_resultados(campanha_dir: Path, run_id: str) -> pd.DataFrame:
    recursos_dir = campanha_dir / "recursos"
    arquivos = {
        ("ENEM", "ETL"): recursos_dir / "enem_etl.csv",
        ("ENEM", "ELT"): recursos_dir / "enem_elt.csv",
        ("TSE", "ETL"): recursos_dir / "tse_etl.csv",
        ("TSE", "ELT"): recursos_dir / "tse_elt.csv",
    }
    partes = []

    for (dataset, arquitetura), caminho in arquivos.items():
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo de recursos nao encontrado: {caminho}")
        df = pd.read_csv(caminho, sep=";")
        ausentes = COLUNAS_OBRIGATORIAS - set(df.columns)
        if ausentes:
            raise ValueError(f"{caminho}: colunas obrigatorias ausentes: {sorted(ausentes)}")
        if df["run_id"].astype("string").str.strip().ne(run_id).any():
            raise ValueError(f"{caminho}: ha dados de outra campanha.")
        if df["modalidade"].astype("string").str.strip().str.lower().ne("recursos").any():
            raise ValueError(f"{caminho}: ha dados de outra modalidade.")
        monitoramento = df["monitoramento_ativo"].astype("string").str.strip().str.lower()
        if not monitoramento.isin(("true", "1")).all():
            raise ValueError(f"{caminho}: ha execucao sem monitoramento ativo.")
        if df["dataset"].astype("string").str.strip().str.upper().ne(dataset).any():
            raise ValueError(f"{caminho}: dataset nao corresponde ao arquivo.")
        if df["arquitetura"].astype("string").str.strip().str.upper().ne(arquitetura).any():
            raise ValueError(f"{caminho}: arquitetura nao corresponde ao arquivo.")

        df = df.copy()
        df["dataset"] = dataset
        df["arquitetura"] = arquitetura
        df["volume_configurado"] = pd.to_numeric(df["volume_configurado"], errors="raise")
        df["rodada"] = pd.to_numeric(df["rodada"], errors="raise")
        df["cpu_media_total"] = converter_numero(df["cpu_media_total"], caminho, "cpu_media_total")
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


def configurar_eixos(ax: plt.Axes, posicoes: list[int], rotulo_y: str) -> None:
    ax.set_xlabel("Volume nominal (registros)")
    ax.set_ylabel(rotulo_y)
    ax.set_xticks(posicoes, ROTULOS_VOLUMES)
    ax.set_ylim(bottom=0)
    ax.yaxis.grid(True, color="#d9d9d9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#777777")
    ax.spines["bottom"].set_color("#777777")


def adicionar_legenda(ax: plt.Axes) -> None:
    medias = [
        Line2D(
            [],
            [],
            color=CORES[arquitetura],
            marker="o",
            linewidth=2,
            markersize=5,
            label=f"{arquitetura} — média",
        )
        for arquitetura in ("ETL", "ELT")
    ]
    rodadas = Line2D(
        [],
        [],
        color=CORES["ETL"],
        marker="o",
        linestyle="none",
        markersize=5,
        alpha=0.55,
        markeredgecolor="white",
        markeredgewidth=0.4,
        label="rodadas individuais",
    )
    intervalo = ax.errorbar(
        [float("nan")],
        [float("nan")],
        yerr=[[1.0], [1.0]],
        color=CORES["ETL"],
        linestyle="none",
        capsize=4,
        elinewidth=1.2,
        label="mín.–máx.",
    )
    ax.legend(
        handles=[medias[0], medias[1], rodadas, intervalo],
        frameon=False,
        ncols=2,
        loc="best",
    )


def gerar_grafico(df: pd.DataFrame, dataset: str, destino: Path) -> None:
    dados = df[df["dataset"] == dataset]
    resumo = dados.groupby(["volume_configurado", "arquitetura"])["cpu_media_total"].agg(
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
                dados[(dados["arquitetura"] == arquitetura) & (dados["volume_configurado"] == volume)]
                .sort_values("rodada")["cpu_media_total"]
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

    configurar_eixos(ax, posicoes, "CPU média total (%)")
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
        "ENEM": imagens_dir / "cpu_media_enem.png",
        "TSE": imagens_dir / "cpu_media_tse.png",
    }
    for dataset, destino in destinos.items():
        gerar_grafico(resultados, dataset, destino)

    contagens = resultados.groupby(["dataset", "arquitetura", "volume_configurado"]).size()
    print("Rodadas validas por combinacao:")
    print(contagens.to_string())
    print("\nArquivos gerados:")
    for destino in destinos.values():
        print(destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
