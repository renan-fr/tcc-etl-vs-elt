import pandas as pd
import numpy as np

LIMITE_TESTE = 100_000

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
    0: "Não",
    1: "Sim",
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
    "Q023",
]


def transformar_participantes(df: pd.DataFrame) -> pd.DataFrame:

    df = df[COLUNAS_PARTICIPANTES].copy()

    df["TP_FAIXA_ETARIA"] = df["TP_FAIXA_ETARIA"].map(MAP_FAIXA_ETARIA)
    df["TP_SEXO"] = df["TP_SEXO"].map(MAP_SEXO)
    df["TP_COR_RACA"] = df["TP_COR_RACA"].map(MAP_COR_RACA)
    df["TP_ST_CONCLUSAO"] = df["TP_ST_CONCLUSAO"].map(
        MAP_SITUACAO_CONCLUSAO
    )
    df["IN_TREINEIRO"] = df["IN_TREINEIRO"].map(MAP_TREINEIRO)
    df["Q007"] = df["Q007"].map(MAP_RENDA)
    df["Q023"] = df["Q023"].map(MAP_TIPO_ESCOLA_EM)

    df["REGIAO_PROVA"] = df["SG_UF_PROVA"].map(MAP_REGIAO)

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
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "NU_NOTA_REDACAO",
]


def transformar_resultados(df: pd.DataFrame) -> pd.DataFrame:

    df = df[COLUNAS_RESULTADOS].copy()

    df["REGIAO_ESCOLA"] = df["SG_UF_ESC"].map(MAP_REGIAO)

    df["TP_DEPENDENCIA_ADM_ESC"] = df["TP_DEPENDENCIA_ADM_ESC"].map(MAP_DEPENDENCIA_ESCOLA)

    df["TP_LOCALIZACAO_ESC"] = df[
        "TP_LOCALIZACAO_ESC"
    ].map(MAP_LOCALIZACAO_ESCOLA)

    for coluna in [
        "TP_PRESENCA_CN",
        "TP_PRESENCA_CH",
        "TP_PRESENCA_LC",
        "TP_PRESENCA_MT",
    ]:
        df[coluna] = df[coluna].map(MAP_PRESENCA)

    colunas_notas = [
        "NU_NOTA_CN",
        "NU_NOTA_CH",
        "NU_NOTA_LC",
        "NU_NOTA_MT",
    ]

    df["NOTA_MEDIA_OBJETIVAS"] = df[colunas_notas].mean(
        axis=1,
    )

    df["PRESENTE_COMPLETO"] = (
        (df["TP_PRESENCA_CN"] == "Presente na prova")
        & (df["TP_PRESENCA_CH"] == "Presente na prova")
        & (df["TP_PRESENCA_LC"] == "Presente na prova")
        & (df["TP_PRESENCA_MT"] == "Presente na prova")
    )

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
            "NU_NOTA_CN": "nota_cn",
            "NU_NOTA_CH": "nota_ch",
            "NU_NOTA_LC": "nota_lc",
            "NU_NOTA_MT": "nota_mt",
            "NU_NOTA_REDACAO": "nota_redacao",
            "NOTA_MEDIA_OBJETIVAS": "nota_media_objetivas",
            "PRESENTE_COMPLETO": "presente_completo",
        }
    )

    return df