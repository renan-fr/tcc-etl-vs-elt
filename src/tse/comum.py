from __future__ import annotations

from pathlib import Path

import pandas as pd


COLUNAS_CHAVE_ORIGEM = [
    "ANO_ELEICAO",
    "CD_ELEICAO",
    "NR_TURNO",
    "CD_MUNICIPIO",
    "NR_ZONA",
    "CD_CARGO",
]
COLUNAS_MANIFESTO = ["SG_UF", *COLUNAS_CHAVE_ORIGEM]


def arquivos_estaduais(pasta: Path) -> list[Path]:
    """Retorna os CSVs estaduais em ordem de UF, excluindo o consolidado BRASIL."""
    arquivos = [
        caminho
        for caminho in pasta.glob("*.csv")
        if not caminho.stem.upper().endswith("_BRASIL")
    ]
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV estadual encontrado em {pasta}.")
    return sorted(arquivos, key=lambda caminho: caminho.name)


def normalizar_chaves(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza as chaves usadas igualmente por todas as fontes do TSE."""
    resultado = df.copy()
    for coluna in COLUNAS_CHAVE_ORIGEM:
        if coluna not in resultado.columns:
            raise ValueError(f"Coluna obrigatoria ausente para a chave: {coluna}")
        resultado[coluna] = resultado[coluna].astype("string").str.strip()

    # O arquivo munzona preserva zeros a esquerda, enquanto secao e candidato
    # publicam o mesmo codigo como numero. A forma canonica do TSE tem 5 posicoes.
    resultado["CD_MUNICIPIO"] = resultado["CD_MUNICIPIO"].str.zfill(5)
    return resultado


def _indice_chaves(df: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(df[COLUNAS_CHAVE_ORIGEM])


def ler_manifesto_chaves(caminho: Path) -> pd.DataFrame:
    chaves = pd.read_csv(caminho, dtype="string")
    chaves = normalizar_chaves(chaves)
    colunas = [coluna for coluna in COLUNAS_MANIFESTO if coluna in chaves.columns]
    return chaves[colunas].drop_duplicates(ignore_index=True)


def salvar_manifesto_chaves(chaves: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    colunas = [coluna for coluna in COLUNAS_MANIFESTO if coluna in chaves.columns]
    chaves[colunas].drop_duplicates().to_csv(
        caminho,
        index=False,
        encoding="utf-8",
    )


def selecionar_secoes(
    pasta: Path,
    colunas: list[str],
    limite: int | None,
    chunksize: int = 100_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Seleciona ate o volume nominal sem cortar a ultima chave logica."""
    if limite is not None and limite < 1:
        raise ValueError("limite deve ser maior que zero ou None.")

    partes: list[pd.DataFrame] = []
    chaves_selecionadas: pd.DataFrame | None = None
    linhas_antes_corte = 0

    for caminho in arquivos_estaduais(pasta):
        for trecho in pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype="string",
            usecols=colunas,
            chunksize=chunksize,
        ):
            trecho = normalizar_chaves(trecho)

            if limite is None:
                partes.append(trecho)
                continue

            if chaves_selecionadas is None:
                faltantes = limite - linhas_antes_corte
                if len(trecho) < faltantes:
                    partes.append(trecho)
                    linhas_antes_corte += len(trecho)
                    continue

                prefixo = trecho.iloc[:faltantes]
                colunas_manifesto = [
                    coluna for coluna in COLUNAS_MANIFESTO if coluna in trecho.columns
                ]
                chaves_anteriores = (
                    pd.concat(
                        [parte[colunas_manifesto] for parte in partes],
                        ignore_index=True,
                    )
                    if partes
                    else pd.DataFrame(columns=colunas_manifesto)
                )
                chaves_selecionadas = pd.concat(
                    [chaves_anteriores, prefixo[colunas_manifesto]],
                    ignore_index=True,
                ).drop_duplicates(ignore_index=True)
                mascara = _indice_chaves(trecho).isin(_indice_chaves(chaves_selecionadas))
                partes.append(trecho.loc[mascara])
                continue

            mascara = _indice_chaves(trecho).isin(_indice_chaves(chaves_selecionadas))
            if mascara.any():
                partes.append(trecho.loc[mascara])

        if limite is not None and chaves_selecionadas is not None:
            # CD_MUNICIPIO identifica o municipio nacionalmente; uma chave
            # selecionada em uma UF nao reaparece nos arquivos seguintes.
            break

    if not partes:
        return pd.DataFrame(columns=colunas), pd.DataFrame(columns=COLUNAS_CHAVE_ORIGEM)

    secoes = pd.concat(partes, ignore_index=True)
    if chaves_selecionadas is None:
        colunas_manifesto = [
            coluna for coluna in COLUNAS_MANIFESTO if coluna in secoes.columns
        ]
        chaves_selecionadas = secoes[colunas_manifesto].drop_duplicates(
            ignore_index=True
        )
    else:
        mascara = _indice_chaves(secoes).isin(_indice_chaves(chaves_selecionadas))
        secoes = secoes.loc[mascara].reset_index(drop=True)

    return secoes, chaves_selecionadas


def filtrar_fonte_por_chaves(
    pasta: Path,
    colunas: list[str],
    chaves: pd.DataFrame,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Le uma fonte e preserva somente o conjunto compartilhado de chaves."""
    if chaves.empty:
        return pd.DataFrame(columns=colunas)

    chaves_normalizadas = normalizar_chaves(chaves)
    ufs = (
        set(chaves_normalizadas["SG_UF"].dropna().astype(str))
        if "SG_UF" in chaves_normalizadas.columns
        else None
    )
    chaves_logicas = chaves_normalizadas[COLUNAS_CHAVE_ORIGEM].drop_duplicates()
    indice_chaves = _indice_chaves(chaves_logicas)
    partes: list[pd.DataFrame] = []

    for caminho in arquivos_estaduais(pasta):
        uf_arquivo = caminho.stem.rsplit("_", 1)[-1]
        if ufs is not None and uf_arquivo not in ufs:
            continue
        for trecho in pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype="string",
            usecols=colunas,
            chunksize=chunksize,
        ):
            trecho = normalizar_chaves(trecho)
            mascara = _indice_chaves(trecho).isin(indice_chaves)
            if mascara.any():
                partes.append(trecho.loc[mascara])

    if not partes:
        return pd.DataFrame(columns=colunas)
    return pd.concat(partes, ignore_index=True)
