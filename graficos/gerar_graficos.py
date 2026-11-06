"""Gera as figuras da subseção 4.1 a partir dos resultados dos benchmarks."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.benchmark_paths import diretorio_campanha, validar_run_id

BASE_DIR = Path(__file__).resolve().parents[1]
CORES = {"ETL": "#2ca25f", "ELT": "#2b6cb0"}
VOLUMES_ESPERADOS = {100_000, 250_000, 500_000, 1_000_000}
COLUNAS_OBRIGATORIAS = {
    "run_id", "modalidade", "monitoramento_ativo",
    "intervalo_monitoramento_s", "dataset", "volume_configurado",
    "arquitetura", "rodada", "tempo_total", "throughput",
}


def converter_tempo(serie: pd.Series, caminho: Path) -> pd.Series:
    valores = pd.to_numeric(serie.astype("string").str.strip().str.replace(",", ".", regex=False), errors="coerce")
    if valores.isna().any():
        raise ValueError(f"{caminho}: tempo_total inválido.")
    if (valores < 0).any():
        raise ValueError(f"{caminho}: tempo_total não pode ser negativo.")
    return valores


def carregar_resultados(campanha_dir: Path) -> pd.DataFrame:
    desempenho_dir = campanha_dir / "desempenho"
    arquivos = {
        ("ENEM", "ETL"): desempenho_dir / "enem_etl.csv",
        ("ENEM", "ELT"): desempenho_dir / "enem_elt.csv",
        ("TSE", "ETL"): desempenho_dir / "tse_etl.csv",
        ("TSE", "ELT"): desempenho_dir / "tse_elt.csv",
    }
    partes = []
    for (dataset_esperado, arquitetura_esperada), caminho in arquivos.items():
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo de resultados não encontrado: {caminho}")
        df = pd.read_csv(caminho, sep=";")
        ausentes = COLUNAS_OBRIGATORIAS - set(df.columns)
        if ausentes:
            raise ValueError(f"{caminho}: colunas obrigatórias ausentes: {sorted(ausentes)}")
        modalidades = df["modalidade"].astype("string").str.strip().str.lower()
        if modalidades.ne("desempenho").any():
            raise ValueError(f"{caminho}: resultados de modalidades diferentes foram misturados.")
        monitoramento = (
            df["monitoramento_ativo"].astype("string").str.strip().str.lower()
        )
        if not monitoramento.isin(("false", "0")).all():
            raise ValueError(f"{caminho}: resultado de desempenho com monitoramento ativo.")
        intervalos = df["intervalo_monitoramento_s"].astype("string").str.strip()
        if intervalos.fillna("").ne("").any():
            raise ValueError(f"{caminho}: desempenho não deve ter intervalo de monitoramento.")
        if df["dataset"].astype("string").str.upper().ne(dataset_esperado).any():
            raise ValueError(f"{caminho}: a coluna dataset não corresponde ao arquivo.")
        if df["arquitetura"].astype("string").str.upper().ne(arquitetura_esperada).any():
            raise ValueError(f"{caminho}: a coluna arquitetura não corresponde ao arquivo.")
        df["dataset"], df["arquitetura"] = dataset_esperado, arquitetura_esperada
        df["volume_configurado"] = pd.to_numeric(df["volume_configurado"], errors="raise")
        df["rodada"] = pd.to_numeric(df["rodada"], errors="raise")
        if df["rodada"].isna().any() or not df["rodada"].isin(range(1, 6)).all():
            raise ValueError(f"{caminho}: esperadas apenas as rodadas válidas de 1 a 5.")
        if set(df["volume_configurado"]) != VOLUMES_ESPERADOS:
            raise ValueError(f"{caminho}: volumes encontrados não correspondem aos quatro volumes esperados.")
        df["tempo_total_s"] = converter_tempo(df["tempo_total"], caminho)
        partes.append(df)
    resultados = pd.concat(partes, ignore_index=True)
    if resultados.duplicated(
        ["modalidade", "dataset", "arquitetura", "volume_configurado", "rodada"]
    ).any():
        raise ValueError("Há execuções duplicadas para a mesma combinação de cenário e rodada.")
    contagens = resultados.groupby(["dataset", "arquitetura"]).size()
    if not (contagens == 20).all() or len(contagens) != 4:
        raise ValueError(f"Quantidade inesperada de execuções válidas: {contagens.to_dict()}")
    return resultados


def formatar_segundos(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def configurar_eixos(ax: plt.Axes, limite_y: float | None = None) -> None:
    ax.set_ylabel("Tempo médio total (s)")
    if limite_y is not None:
        ax.set_ylim(0, limite_y)
    ax.yaxis.grid(True, color="#d9d9d9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#777777")
    ax.spines["bottom"].set_color("#777777")


def adicionar_rotulos(ax: plt.Axes, barras) -> None:
    for barra in barras:
        altura = barra.get_height()
        ax.annotate(formatar_segundos(altura), (barra.get_x() + barra.get_width() / 2, altura),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9)


def salvar(fig: plt.Figure, nome: str, figuras_dir: Path) -> None:
    figuras_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figuras_dir / f"{nome}.pdf", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def gerar_figura_geral(df: pd.DataFrame, figuras_dir: Path) -> None:
    medias = df.groupby("arquitetura")["tempo_total_s"].mean().reindex(["ETL", "ELT"])
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    barras = ax.bar(medias.index, medias.values, color=[CORES[a] for a in medias.index], width=0.58)
    configurar_eixos(ax, limite_y=25)
    ax.set_xlabel("Arquitetura")
    adicionar_rotulos(ax, barras)
    fig.tight_layout()
    salvar(fig, "tempo_medio_geral", figuras_dir)


def gerar_figura_dataset(df: pd.DataFrame, figuras_dir: Path) -> None:
    medias = df.groupby(["dataset", "arquitetura"])["tempo_total_s"].mean().unstack("arquitetura").reindex(index=["ENEM", "TSE"], columns=["ETL", "ELT"])
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    posicoes, largura = range(len(medias.index)), 0.34
    barras = []
    for i, arquitetura in enumerate(["ETL", "ELT"]):
        barras.extend(ax.bar([p + (i - 0.5) * largura for p in posicoes], medias[arquitetura].values,
                             width=largura, color=CORES[arquitetura], label=arquitetura))
    configurar_eixos(ax, limite_y=25)
    ax.set_xlabel("Conjunto de dados")
    ax.set_xticks(list(posicoes), medias.index)
    ax.legend(frameon=False, ncols=2)
    adicionar_rotulos(ax, barras)
    fig.tight_layout()
    salvar(fig, "tempo_medio_dataset", figuras_dir)


def gerar_figura_linhas(df: pd.DataFrame, dataset: str, figuras_dir: Path) -> None:
    medias = (
        df[df["dataset"] == dataset]
        .groupby(["volume_configurado", "arquitetura"])["tempo_total_s"]
        .mean()
        .unstack("arquitetura")
        .reindex(index=sorted(VOLUMES_ESPERADOS), columns=["ETL", "ELT"])
    )
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    posicoes = list(range(len(medias.index)))
    for arquitetura in ["ETL", "ELT"]:
        ax.plot(
            posicoes,
            medias[arquitetura].values,
            color=CORES[arquitetura],
            marker="o",
            linewidth=2,
            markersize=5,
            label=arquitetura,
        )
    configurar_eixos(ax, limite_y=50)
    ax.set_xlabel("Volume nominal (registros)")
    ax.set_xticks(posicoes, [f"{volume // 1000:,}".replace(",", ".") + " mil" for volume in medias.index])
    ax.legend(frameon=False, ncols=2)
    fig.tight_layout()
    salvar(fig, f"tempo_medio_volume_{dataset.lower()}", figuras_dir)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        campanha_dir = diretorio_campanha(validar_run_id(args.run_id))
    except ValueError as erro:
        parser.error(str(erro))
    figuras_dir = campanha_dir / "graficos" / "tempo_processamento"
    try:
        df = carregar_resultados(campanha_dir)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    contagens = df.groupby(["dataset", "arquitetura"]).size().rename("observacoes")
    medias = df.groupby(["dataset", "arquitetura"])["tempo_total_s"].mean().rename("media_s")
    print("Observações utilizadas:")
    print(contagens.to_string())
    print("\nMédias calculadas (s):")
    print(medias.to_frame().round(3).to_string())
    print("\nMédia geral por arquitetura (s):")
    print(df.groupby("arquitetura")["tempo_total_s"].mean().round(3).to_string())
    gerar_figura_geral(df, figuras_dir)
    gerar_figura_dataset(df, figuras_dir)
    gerar_figura_linhas(df, "ENEM", figuras_dir)
    gerar_figura_linhas(df, "TSE", figuras_dir)
    print(f"\nFiguras salvas em: {figuras_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
