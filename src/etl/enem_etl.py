from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path
import argparse
from typing import Any

import pandas as pd
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


VALORES_DESCONHECIDOS: list[dict[str, object]] = []
VALOR_NAO_INFORMADO = "Não informado"


@dataclass(frozen=True)
class ResultadoValidacao:
    tabela: str
    erros: list[str]
    alertas: list[str]

    @property
    def valido(self) -> bool:
        return not self.erros


ConexaoPostgres = str | dict[str, Any]


def _registrar_desconhecidos(
    serie: pd.Series,
    mapeamento: dict,
    coluna: str,
) -> None:
    conhecidos = set(mapeamento)
    desconhecidos = serie.dropna()[~serie.dropna().isin(conhecidos)]

    for valor, quantidade in desconhecidos.value_counts().items():
        VALORES_DESCONHECIDOS.append(
            {
                "coluna": coluna,
                "valor_original": valor,
                "quantidade": int(quantidade),
            }
        )


def _mapear_texto(
    serie: pd.Series,
    mapeamento: dict,
    coluna: str,
) -> pd.Series:
    _registrar_desconhecidos(serie, mapeamento, coluna)
    return serie.map(mapeamento).fillna(VALOR_NAO_INFORMADO)


def _mapear_booleano(
    serie: pd.Series,
    mapeamento: dict,
    coluna: str,
) -> pd.Series:
    _registrar_desconhecidos(serie, mapeamento, coluna)
    return serie.map(mapeamento).astype("boolean")


def relatorio_valores_desconhecidos() -> pd.DataFrame:
    """Retorna os códigos desconhecidos encontrados durante a transformação."""
    return pd.DataFrame(
        VALORES_DESCONHECIDOS,
        columns=["coluna", "valor_original", "quantidade"],
    )


def limpar_relatorio_valores_desconhecidos() -> None:
    VALORES_DESCONHECIDOS.clear()

# CONFIGURAÇÕES
# -------------

BASE_DIR = Path(__file__).resolve().parents[2]

PASTA_ENEM = (
    BASE_DIR
    / "data"
    / "raw"
    / "enem"
    / "microdados_enem_2024"
    / "DADOS"
)

CAMINHO_PARTICIPANTES = PASTA_ENEM / "PARTICIPANTES_2024.csv"
CAMINHO_RESULTADOS = PASTA_ENEM / "RESULTADOS_2024.csv"

TABELA_PARTICIPANTES = "enem_participantes"
TABELA_RESULTADOS = "enem_resultados"

CONTRATO_PARTICIPANTES = [
    ("id_participante", "TEXT"),
    ("faixa_etaria", "TEXT"),
    ("sexo", "TEXT"),
    ("cor_raca", "TEXT"),
    ("situacao_conclusao", "TEXT"),
    ("treineiro", "BOOLEAN"),
    ("municipio_prova", "TEXT"),
    ("uf_prova", "TEXT"),
    ("faixa_renda", "TEXT"),
    ("possui_internet", "BOOLEAN"),
    ("tipo_escola_em", "TEXT"),
    ("regiao_prova", "TEXT"),
]

CONTRATO_RESULTADOS = [
    ("id_resultado", "TEXT"),
    ("municipio_escola", "TEXT"),
    ("uf_escola", "TEXT"),
    ("dependencia_escola", "TEXT"),
    ("localizacao_escola", "TEXT"),
    ("presenca_cn", "TEXT"),
    ("presenca_ch", "TEXT"),
    ("presenca_lc", "TEXT"),
    ("presenca_mt", "TEXT"),
    ("presenca_redacao", "TEXT"),
    ("nota_cn", "NUMERIC"),
    ("nota_ch", "NUMERIC"),
    ("nota_lc", "NUMERIC"),
    ("nota_mt", "NUMERIC"),
    ("nota_redacao", "NUMERIC"),
    ("regiao_escola", "TEXT"),
    ("nota_media_objetivas", "NUMERIC"),
    ("presente_completo", "BOOLEAN"),
]

# EXTRAÇÃO
# ----------

def extrair_participantes(limite: int | None = None) -> pd.DataFrame:
    return pd.read_csv(
        CAMINHO_PARTICIPANTES,
        sep=";",
        encoding="latin-1",
        usecols=COLUNAS_PARTICIPANTES,
        nrows=limite,
    )


def extrair_resultados(limite: int | None = None) -> pd.DataFrame:
    return pd.read_csv(
        CAMINHO_RESULTADOS,
        sep=";",
        encoding="latin-1",
        usecols=COLUNAS_RESULTADOS,
        nrows=limite,
    )

# MAPEAMENTO
# ------------

MAP_FAIXA_ETARIA = {
    1: "Menor de 17 anos",
    2: "17 anos",
    3: "18 anos",
    4: "19 anos",
    5: "20 anos",
    6: "21 anos",
    7: "22 anos",
    8: "23 anos",
    9: "24 anos",
    10: "25 anos",
    11: "Entre 26 e 30 anos",
    12: "Entre 31 e 35 anos",
    13: "Entre 36 e 40 anos",
    14: "Entre 41 e 45 anos",
    15: "Entre 46 e 50 anos",
    16: "Entre 51 e 55 anos",
    17: "Entre 56 e 60 anos",
    18: "Entre 61 e 65 anos",
    19: "Entre 66 e 70 anos",
    20: "Maior de 70 anos",
}

MAP_SEXO = {
    "M": "Masculino",
    "F": "Feminino",
}

MAP_COR_RACA = {
    0: "Não declarado",
    1: "Branca",
    2: "Preta",
    3: "Parda",
    4: "Amarela",
    5: "Indígena",
    6: "Não dispõe da informação",
}

MAP_SITUACAO_CONCLUSAO = {
    1: "Já concluí o Ensino Médio",
    2: "Estou cursando e concluirei o Ensino Médio em 2024",
    3: "Estou cursando e concluirei o Ensino Médio após 2024",
    4: "Não concluí e não estou cursando o Ensino Médio",
}

MAP_TREINEIRO = {
    0: False,
    1: True,
}

MAP_RENDA = {
    "A": "Nenhuma Renda",
    "B": "Até R$ 1.412,00",
    "C": "De R$ 1.412,01 até R$ 2.118,00",
    "D": "De R$ 2.118,01 até R$ 2.824,00",
    "E": "De R$ 2.824,01 até R$ 3.530,00",
    "F": "De R$ 3.530,01 até R$ 4.236,00",
    "G": "De R$ 4.236,01 até R$ 5.648,00",
    "H": "De R$ 5.648,01 até R$ 7.060,00",
    "I": "De R$ 7.060,01 até R$ 8.472,00",
    "J": "De R$ 8.472,01 até R$ 9.884,00",
    "K": "De R$ 9.884,01 até R$ 11.296,00",
    "L": "De R$ 11.296,01 até R$ 12.708,00",
    "M": "De R$ 12.708,01 até R$ 14.120,00",
    "N": "De R$ 14.120,01 até R$ 16.944,00",
    "O": "De R$ 16.944,01 até R$ 21.180,00",
    "P": "De R$ 21.180,01 até R$ 28.240,00",
    "Q": "Acima de R$ 28.240,00",
}

MAP_TIPO_ESCOLA_EM = {
    "A": "Somente em escola pública",
    "B": "Parte em escola pública e parte em escola privada sem bolsa integral",
    "C": "Parte em escola pública e parte em escola privada com bolsa integral",
    "D": "Somente em escola privada sem bolsa integral",
    "E": "Somente em escola privada com bolsa integral",
    "F": "Não frequentei escola de Ensino Médio",
}

MAP_DEPENDENCIA_ESCOLA = {
    1: "Federal",
    2: "Estadual",
    3: "Municipal",
    4: "Privada",
}

MAP_LOCALIZACAO_ESCOLA = {
    1: "Urbana",
    2: "Rural",
}

MAP_PRESENCA = {
    0: "Faltou à prova",
    1: "Presente na prova",
    2: "Eliminado na prova",
}

MAP_INTERNET = {
    "A": False,
    "B": True,
}

MAP_REGIAO = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",

    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",

    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",

    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",

    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

# PARTICIPANTES
# --------------

COLUNAS_PARTICIPANTES = [
    "NU_INSCRICAO",
    "TP_FAIXA_ETARIA",
    "TP_SEXO",
    "TP_COR_RACA",
    "TP_ST_CONCLUSAO",
    "IN_TREINEIRO",
    "NO_MUNICIPIO_PROVA",
    "SG_UF_PROVA",
    "Q007",
    "Q020",
    "Q023",
]


def transformar_participantes(df: pd.DataFrame) -> pd.DataFrame:

    df = df[COLUNAS_PARTICIPANTES].copy()

    df["TP_FAIXA_ETARIA"] = _mapear_texto(
        df["TP_FAIXA_ETARIA"], MAP_FAIXA_ETARIA, "TP_FAIXA_ETARIA"
    )
    df["TP_SEXO"] = _mapear_texto(df["TP_SEXO"], MAP_SEXO, "TP_SEXO")
    df["TP_COR_RACA"] = _mapear_texto(
        df["TP_COR_RACA"], MAP_COR_RACA, "TP_COR_RACA"
    )
    df["TP_ST_CONCLUSAO"] = _mapear_texto(
        df["TP_ST_CONCLUSAO"],
        MAP_SITUACAO_CONCLUSAO,
        "TP_ST_CONCLUSAO",
    )
    df["IN_TREINEIRO"] = _mapear_booleano(
        df["IN_TREINEIRO"], MAP_TREINEIRO, "IN_TREINEIRO"
    )
    df["Q007"] = _mapear_texto(df["Q007"], MAP_RENDA, "Q007")
    df["Q020"] = _mapear_booleano(df["Q020"], MAP_INTERNET, "Q020")
    df["Q023"] = _mapear_texto(
        df["Q023"], MAP_TIPO_ESCOLA_EM, "Q023"
    )

    uf_prova = df["SG_UF_PROVA"].copy()
    df["REGIAO_PROVA"] = _mapear_texto(
        uf_prova, MAP_REGIAO, "SG_UF_PROVA"
    )
    df["SG_UF_PROVA"] = uf_prova.fillna(VALOR_NAO_INFORMADO)
    df["NO_MUNICIPIO_PROVA"] = df["NO_MUNICIPIO_PROVA"].fillna(
        VALOR_NAO_INFORMADO
    )
    df["NU_INSCRICAO"] = df["NU_INSCRICAO"].astype("string")

    df = df.rename(
        columns={
            "NU_INSCRICAO": "id_participante",
            "TP_FAIXA_ETARIA": "faixa_etaria",
            "TP_SEXO": "sexo",
            "TP_COR_RACA": "cor_raca",
            "TP_ST_CONCLUSAO": "situacao_conclusao",
            "IN_TREINEIRO": "treineiro",
            "NO_MUNICIPIO_PROVA": "municipio_prova",
            "SG_UF_PROVA": "uf_prova",
            "Q007": "faixa_renda",
            "Q020": "possui_internet",
            "Q023": "tipo_escola_em",
            "REGIAO_PROVA": "regiao_prova",
        }
    )

    return df


# RESULTADOS
# -----------

COLUNAS_RESULTADOS = [
    "NU_SEQUENCIAL",
    "NO_MUNICIPIO_ESC",
    "SG_UF_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    "TP_LOCALIZACAO_ESC",
    "TP_PRESENCA_CN",
    "TP_PRESENCA_CH",
    "TP_PRESENCA_LC",
    "TP_PRESENCA_MT",
    "TP_STATUS_REDACAO",
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
]


def transformar_resultados(df: pd.DataFrame) -> pd.DataFrame:

    df = df[COLUNAS_RESULTADOS].copy()

    uf_escola = df["SG_UF_ESC"].copy()
    df["REGIAO_ESCOLA"] = _mapear_texto(
        uf_escola, MAP_REGIAO, "SG_UF_ESC"
    )
    df["SG_UF_ESC"] = uf_escola.fillna(VALOR_NAO_INFORMADO)
    df["NO_MUNICIPIO_ESC"] = df["NO_MUNICIPIO_ESC"].fillna(
        VALOR_NAO_INFORMADO
    )

    df["TP_DEPENDENCIA_ADM_ESC"] = _mapear_texto(
        df["TP_DEPENDENCIA_ADM_ESC"],
        MAP_DEPENDENCIA_ESCOLA,
        "TP_DEPENDENCIA_ADM_ESC",
    )

    df["TP_LOCALIZACAO_ESC"] = _mapear_texto(
        df["TP_LOCALIZACAO_ESC"],
        MAP_LOCALIZACAO_ESCOLA,
        "TP_LOCALIZACAO_ESC",
    )

    df["TP_PRESENCA_REDACAO"] = df["TP_STATUS_REDACAO"].notna().map(
        {True: 1, False: 0}
    )

    for coluna in [
        "TP_PRESENCA_CN",
        "TP_PRESENCA_CH",
        "TP_PRESENCA_LC",
        "TP_PRESENCA_MT",
        "TP_PRESENCA_REDACAO",
    ]:
        df[coluna] = _mapear_texto(df[coluna], MAP_PRESENCA, coluna)

    colunas_notas = [
        "NU_NOTA_CN",
        "NU_NOTA_CH",
        "NU_NOTA_LC",
        "NU_NOTA_MT",
    ]

    df["NOTA_MEDIA_OBJETIVAS"] = df[colunas_notas].mean(
        axis=1,
        skipna=False,
    ).round(2)

    df["PRESENTE_COMPLETO"] = (
        (df["TP_PRESENCA_CN"] == "Presente na prova")
        & (df["TP_PRESENCA_CH"] == "Presente na prova")
        & (df["TP_PRESENCA_LC"] == "Presente na prova")
        & (df["TP_PRESENCA_MT"] == "Presente na prova")
        & (df["TP_PRESENCA_REDACAO"] == "Presente na prova")
    )

    df["NU_SEQUENCIAL"] = df["NU_SEQUENCIAL"].astype("string")

    df = df.rename(
        columns={
            "NU_SEQUENCIAL": "id_resultado",
            "NO_MUNICIPIO_ESC": "municipio_escola",
            "SG_UF_ESC": "uf_escola",
            "REGIAO_ESCOLA": "regiao_escola",
            "TP_DEPENDENCIA_ADM_ESC": "dependencia_escola",
            "TP_LOCALIZACAO_ESC": "localizacao_escola",
            "TP_PRESENCA_CN": "presenca_cn",
            "TP_PRESENCA_CH": "presenca_ch",
            "TP_PRESENCA_LC": "presenca_lc",
            "TP_PRESENCA_MT": "presenca_mt",
            "TP_PRESENCA_REDACAO": "presenca_redacao",
            "NU_NOTA_CN": "nota_cn",
            "NU_NOTA_CH": "nota_ch",
            "NU_NOTA_LC": "nota_lc",
            "NU_NOTA_MT": "nota_mt",
            "NU_NOTA_REDACAO": "nota_redacao",
            "NOTA_MEDIA_OBJETIVAS": "nota_media_objetivas",
            "PRESENTE_COMPLETO": "presente_completo",
        }
    )

    return df[[coluna for coluna, _ in CONTRATO_RESULTADOS]]


# VALIDAÇÃO
# ---------

def _validar_colunas(
    df: pd.DataFrame,
    contrato: list[tuple[str, str]],
    erros: list[str],
) -> None:
    esperadas = [coluna for coluna, _ in contrato]
    encontradas = list(df.columns)
    if encontradas != esperadas:
        erros.append(
            "Estrutura de colunas divergente. "
            f"Esperadas: {esperadas}. Encontradas: {encontradas}."
        )


def _validar_identificador(
    df: pd.DataFrame,
    coluna: str,
    erros: list[str],
) -> None:
    nulos = int(df[coluna].isna().sum())
    duplicados = int(df[coluna].duplicated().sum())
    if nulos:
        erros.append(f"{coluna} possui {nulos} valores nulos.")
    if duplicados:
        erros.append(f"{coluna} possui {duplicados} valores duplicados.")


def _validar_dominio(
    df: pd.DataFrame,
    coluna: str,
    valores_validos: set[object],
    erros: list[str],
) -> None:
    valores = df[coluna].dropna()
    invalidos = valores[~valores.isin(valores_validos)]
    if not invalidos.empty:
        amostra = invalidos.drop_duplicates().head(10).tolist()
        erros.append(
            f"{coluna} possui {len(invalidos)} valores fora do domínio: {amostra}."
        )


def _validar_notas(
    df: pd.DataFrame,
    colunas: list[str],
    erros: list[str],
) -> None:
    for coluna in colunas:
        valores = df[coluna].dropna()
        invalidos = valores[(valores < 0) | (valores > 1000)]
        if not invalidos.empty:
            erros.append(
                f"{coluna} possui {len(invalidos)} notas fora do intervalo 0-1000."
            )


def _validar_regiao(
    df: pd.DataFrame,
    coluna_uf: str,
    coluna_regiao: str,
    erros: list[str],
) -> None:
    ufs = df[coluna_uf]
    regioes_esperadas = ufs.map(MAP_REGIAO).fillna(VALOR_NAO_INFORMADO)
    divergentes = df[
        (ufs != VALOR_NAO_INFORMADO)
        & (df[coluna_regiao] != regioes_esperadas)
    ]
    if not divergentes.empty:
        erros.append(
            f"{coluna_uf} e {coluna_regiao} possuem "
            f"{len(divergentes)} combinações inconsistentes."
        )


def _adicionar_alertas_ausencias(
    df: pd.DataFrame,
    tabela: str,
    alertas: list[str],
) -> None:
    nulos = df.isna().sum()
    for coluna, quantidade in nulos[nulos > 0].items():
        alertas.append(f"{tabela}.{coluna} possui {int(quantidade)} valores nulos.")

    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        quantidade = int((df[coluna] == VALOR_NAO_INFORMADO).sum())
        if quantidade:
            alertas.append(
                f"{tabela}.{coluna} possui {quantidade} valores "
                f"'{VALOR_NAO_INFORMADO}'."
            )


def validar_participantes(
    df: pd.DataFrame,
    linhas_origem: int | None = None,
) -> ResultadoValidacao:
    erros: list[str] = []
    alertas: list[str] = []

    _validar_colunas(df, CONTRATO_PARTICIPANTES, erros)
    if erros:
        return ResultadoValidacao(TABELA_PARTICIPANTES, erros, alertas)

    if linhas_origem is not None and len(df) != linhas_origem:
        erros.append(
            f"Quantidade de linhas divergente: origem={linhas_origem}, final={len(df)}."
        )

    _validar_identificador(df, "id_participante", erros)

    _validar_dominio(
        df,
        "faixa_etaria",
        set(MAP_FAIXA_ETARIA.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df, "sexo", set(MAP_SEXO.values()) | {VALOR_NAO_INFORMADO}, erros
    )
    _validar_dominio(
        df,
        "cor_raca",
        set(MAP_COR_RACA.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df,
        "situacao_conclusao",
        set(MAP_SITUACAO_CONCLUSAO.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df,
        "faixa_renda",
        set(MAP_RENDA.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df,
        "tipo_escola_em",
        set(MAP_TIPO_ESCOLA_EM.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df,
        "regiao_prova",
        set(MAP_REGIAO.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_regiao(df, "uf_prova", "regiao_prova", erros)

    _adicionar_alertas_ausencias(df, TABELA_PARTICIPANTES, alertas)

    return ResultadoValidacao(TABELA_PARTICIPANTES, erros, alertas)


def validar_resultados(
    df: pd.DataFrame,
    linhas_origem: int | None = None,
) -> ResultadoValidacao:
    erros: list[str] = []
    alertas: list[str] = []

    _validar_colunas(df, CONTRATO_RESULTADOS, erros)
    if erros:
        return ResultadoValidacao(TABELA_RESULTADOS, erros, alertas)

    if linhas_origem is not None and len(df) != linhas_origem:
        erros.append(
            f"Quantidade de linhas divergente: origem={linhas_origem}, final={len(df)}."
        )

    _validar_identificador(df, "id_resultado", erros)

    _validar_dominio(
        df,
        "dependencia_escola",
        set(MAP_DEPENDENCIA_ESCOLA.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    _validar_dominio(
        df,
        "localizacao_escola",
        set(MAP_LOCALIZACAO_ESCOLA.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )
    for coluna in [
        "presenca_cn",
        "presenca_ch",
        "presenca_lc",
        "presenca_mt",
        "presenca_redacao",
    ]:
        _validar_dominio(
            df,
            coluna,
            set(MAP_PRESENCA.values()) | {VALOR_NAO_INFORMADO},
            erros,
        )
    _validar_dominio(
        df,
        "regiao_escola",
        set(MAP_REGIAO.values()) | {VALOR_NAO_INFORMADO},
        erros,
    )

    colunas_notas = [
        "nota_cn",
        "nota_ch",
        "nota_lc",
        "nota_mt",
        "nota_redacao",
        "nota_media_objetivas",
    ]
    _validar_notas(df, colunas_notas, erros)
    _validar_regiao(df, "uf_escola", "regiao_escola", erros)

    media_esperada = df[["nota_cn", "nota_ch", "nota_lc", "nota_mt"]].mean(
        axis=1,
        skipna=False,
    ).round(2)
    media_divergente = ~(
        df["nota_media_objetivas"].eq(media_esperada)
        | (df["nota_media_objetivas"].isna() & media_esperada.isna())
    )
    if media_divergente.any():
        erros.append(
            "nota_media_objetivas possui "
            f"{int(media_divergente.sum())} valores inconsistentes."
        )

    presente_esperado = (
        (df["presenca_cn"] == "Presente na prova")
        & (df["presenca_ch"] == "Presente na prova")
        & (df["presenca_lc"] == "Presente na prova")
        & (df["presenca_mt"] == "Presente na prova")
        & (df["presenca_redacao"] == "Presente na prova")
    )
    presente_divergente = df["presente_completo"] != presente_esperado
    if presente_divergente.any():
        erros.append(
            "presente_completo possui "
            f"{int(presente_divergente.sum())} valores inconsistentes."
        )

    pares_presenca_nota = {
        "presenca_cn": "nota_cn",
        "presenca_ch": "nota_ch",
        "presenca_lc": "nota_lc",
        "presenca_mt": "nota_mt",
        "presenca_redacao": "nota_redacao",
    }
    for coluna_presenca, coluna_nota in pares_presenca_nota.items():
        inconsistentes = df[
            (df[coluna_presenca] != "Presente na prova")
            & df[coluna_nota].notna()
        ]
        if not inconsistentes.empty:
            alertas.append(
                f"{coluna_nota} possui {len(inconsistentes)} notas com "
                f"{coluna_presenca} diferente de presente."
            )

    _adicionar_alertas_ausencias(df, TABELA_RESULTADOS, alertas)

    return ResultadoValidacao(TABELA_RESULTADOS, erros, alertas)


# CARGA
# -----

def obter_conexao_postgres(database_url: str | None = None) -> ConexaoPostgres:
    if database_url:
        return database_url

    conexao = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }

    faltantes = [
        variavel
        for variavel, valor in {
            "POSTGRES_DB": conexao["dbname"],
            "POSTGRES_USER": conexao["user"],
            "POSTGRES_PASSWORD": conexao["password"],
        }.items()
        if not valor
    ]
    if faltantes:
        raise ValueError(
            "Variáveis de conexão ausentes no .env: " + ", ".join(faltantes)
        )

    return conexao


def _conectar_postgres(conexao_postgres: ConexaoPostgres):
    if isinstance(conexao_postgres, str):
        return psycopg2.connect(conexao_postgres)
    return psycopg2.connect(**conexao_postgres)


def _criar_tabela(
    cursor,
    schema: str,
    tabela: str,
    contrato: list[tuple[str, str]],
) -> None:
    colunas = [
        sql.SQL("{} {}").format(sql.Identifier(nome), sql.SQL(tipo))
        for nome, tipo in contrato
    ]
    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
    )
    cursor.execute(
        sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
            sql.Identifier(schema),
            sql.Identifier(tabela),
            sql.SQL(", ").join(colunas),
        )
    )


def _preparar_dataframe_para_copy(df: pd.DataFrame) -> pd.DataFrame:
    preparado = df.copy()
    for coluna in preparado.select_dtypes(include=["boolean", "bool"]).columns:
        preparado[coluna] = preparado[coluna].map(
            {True: "true", False: "false", pd.NA: None}
        )
    return preparado


def _copy_dataframe(
    cursor,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
) -> None:
    buffer = StringIO()
    _preparar_dataframe_para_copy(df).to_csv(
        buffer,
        index=False,
        header=True,
        na_rep="",
    )
    buffer.seek(0)

    colunas = [sql.Identifier(coluna) for coluna in df.columns]
    comando = sql.SQL(
        "COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(tabela),
        sql.SQL(", ").join(colunas),
    )
    cursor.copy_expert(comando.as_string(cursor), buffer)


def carregar_tabela(
    df: pd.DataFrame,
    conexao_postgres: ConexaoPostgres,
    schema: str,
    tabela: str,
    contrato: list[tuple[str, str]],
    if_exists: str = "replace",
) -> None:
    if if_exists not in {"replace", "append"}:
        raise ValueError("if_exists deve ser 'replace' ou 'append'.")

    with _conectar_postgres(conexao_postgres) as conexao:
        with conexao.cursor() as cursor:
            _carregar_tabela_cursor(
                cursor,
                df,
                schema,
                tabela,
                contrato,
                if_exists,
            )


def _carregar_tabela_cursor(
    cursor,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    contrato: list[tuple[str, str]],
    if_exists: str,
) -> None:
    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
    )
    if if_exists == "replace":
        cursor.execute(
            sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                sql.Identifier(schema),
                sql.Identifier(tabela),
            )
        )
    _criar_tabela(cursor, schema, tabela, contrato)
    _copy_dataframe(cursor, df, schema, tabela)


def carregar_enem(
    participantes: pd.DataFrame,
    resultados: pd.DataFrame,
    conexao_postgres: ConexaoPostgres,
    schema: str = "public",
    if_exists: str = "replace",
) -> None:
    if if_exists not in {"replace", "append"}:
        raise ValueError("if_exists deve ser 'replace' ou 'append'.")

    with _conectar_postgres(conexao_postgres) as conexao:
        with conexao.cursor() as cursor:
            _carregar_tabela_cursor(
                cursor,
                participantes,
                schema,
                TABELA_PARTICIPANTES,
                CONTRATO_PARTICIPANTES,
                if_exists,
            )
            _carregar_tabela_cursor(
                cursor,
                resultados,
                schema,
                TABELA_RESULTADOS,
                CONTRATO_RESULTADOS,
                if_exists,
            )

# MAIN
# -------

def _imprimir_validacao(resultado: ResultadoValidacao) -> None:
    print(f"Validação {resultado.tabela}:")
    if resultado.valido:
        print("  Erros críticos: nenhum")
    else:
        print("  Erros críticos:")
        for erro in resultado.erros:
            print(f"  - {erro}")

    if resultado.alertas:
        print("  Alertas:")
        for alerta in resultado.alertas:
            print(f"  - {alerta}")
    else:
        print("  Alertas: nenhum")


def main(
    limite: int | None,
    database_url: str | None,
    schema: str,
    if_exists: str,
    somente_validar: bool,
) -> None:
    limpar_relatorio_valores_desconhecidos()

    participantes = extrair_participantes(limite)
    resultados = extrair_resultados(limite)

    participantes_tratados = transformar_participantes(participantes)
    resultados_tratados = transformar_resultados(resultados)

    print("Participantes:", participantes_tratados.shape)
    print("Resultados:", resultados_tratados.shape)

    desconhecidos = relatorio_valores_desconhecidos()
    if desconhecidos.empty:
        print("Valores desconhecidos: nenhum")
    else:
        print("Valores desconhecidos:")
        print(desconhecidos.to_string(index=False))

    validacao_participantes = validar_participantes(
        participantes_tratados,
        linhas_origem=len(participantes),
    )
    validacao_resultados = validar_resultados(
        resultados_tratados,
        linhas_origem=len(resultados),
    )

    _imprimir_validacao(validacao_participantes)
    _imprimir_validacao(validacao_resultados)

    erros = validacao_participantes.erros + validacao_resultados.erros
    if erros:
        raise SystemExit("Carga interrompida por erros críticos de validação.")

    if somente_validar:
        print("Carga ignorada (--somente-validar).")
        return

    try:
        conexao_postgres = obter_conexao_postgres(database_url)
    except ValueError as erro:
        raise SystemExit(str(erro)) from erro

    carregar_enem(
        participantes_tratados,
        resultados_tratados,
        conexao_postgres=conexao_postgres,
        schema=schema,
        if_exists=if_exists,
    )

    print(
        "Carga concluída: "
        f"{schema}.{TABELA_PARTICIPANTES} e {schema}.{TABELA_RESULTADOS}."
    )


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Pipeline ETL dos microdados do ENEM 2024"
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=100_000,
        help="Quantidade máxima de linhas lidas de cada arquivo. Use 0 para ler tudo.",
    )

    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL"),
        help=(
            "URL de conexão PostgreSQL opcional. Se omitida, usa POSTGRES_HOST, "
            "POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER e POSTGRES_PASSWORD."
        ),
    )

    parser.add_argument(
        "--schema",
        default=(
            os.getenv("POSTGRES_SCHEMA_ETL")
            or os.getenv("POSTGRES_SCHEMA")
            or "etl"
        ),
        help="Schema de destino no PostgreSQL.",
    )

    parser.add_argument(
        "--if-exists",
        choices=["replace", "append"],
        default="replace",
        help="Estratégia de carga para as tabelas finais.",
    )

    parser.add_argument(
        "--somente-validar",
        action="store_true",
        help="Executa extração, transformação e validação sem carregar no banco.",
    )

    args = parser.parse_args()

    limite = None if args.limite == 0 else args.limite

    main(
        limite=limite,
        database_url=args.database_url,
        schema=args.schema,
        if_exists=args.if_exists,
        somente_validar=args.somente_validar,
    )
