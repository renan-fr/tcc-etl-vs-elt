from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
import os
from pathlib import Path
import threading
import time
from typing import Any

import pandas as pd
import psutil
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

from comum import (
    COLUNAS_CHAVE_ORIGEM,
    filtrar_fonte_por_chaves,
    ler_manifesto_chaves,
    salvar_manifesto_chaves,
    selecionar_secoes,
)
from contrato import CHAVE_FINAL, CONTRATO_FINAL


PASTA_TSE = BASE_DIR / "data" / "raw" / "tse"
PASTA_MUNZONA = PASTA_TSE / "detalhe_votacao_munzona_2024"
PASTA_SECAO = PASTA_TSE / "detalhe_votacao_secao_2024"
PASTA_CANDIDATO = PASTA_TSE / "votacao_candidato_munzona_2024"

TABELA_FINAL = "resultado_municipio_cargo"

COLUNAS_MUNZONA = [
    *COLUNAS_CHAVE_ORIGEM,
    "SG_UF",
    "NM_MUNICIPIO",
    "DS_CARGO",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "QT_TOTAL_VOTOS_VALIDOS",
    "QT_VOTOS_NOMINAIS_VALIDOS",
    "QT_TOTAL_VOTOS_LEG_VALIDOS",
    "QT_VOTOS_BRANCOS",
    "QT_TOTAL_VOTOS_NULOS",
    "QT_TOTAL_VOTOS_ANULADOS",
]

COLUNAS_SECAO = [
    *COLUNAS_CHAVE_ORIGEM,
    "SG_UF",
    "NR_SECAO",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "QT_VOTOS_NOMINAIS",
    "QT_VOTOS_BRANCOS",
    "QT_VOTOS_NULOS",
    "QT_VOTOS_LEGENDA",
]

COLUNAS_CANDIDATO = [
    *COLUNAS_CHAVE_ORIGEM,
    "SG_UF",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_CANDIDATO",
    "SG_PARTIDO",
    "QT_VOTOS_NOMINAIS_VALIDOS",
]

@dataclass(frozen=True)
class FontesTSE:
    munzona: pd.DataFrame
    secao: pd.DataFrame
    candidato: pd.DataFrame
    chaves: pd.DataFrame


@dataclass(frozen=True)
class ResultadoValidacao:
    tabela: str
    erros: list[str]
    alertas: list[str]

    @property
    def valido(self) -> bool:
        return not self.erros


@dataclass(frozen=True)
class ResultadoBenchmark:
    dataset: str
    volume_configurado: int | None
    arquitetura: str
    rodada: int | None
    tempo_leitura: float
    tempo_transformacao: float
    tempo_carga: float
    tempo_total: float
    throughput: float
    cpu_media_python: float
    cpu_pico_python: float
    ram_media_python_mb: float
    ram_pico_python_mb: float
    cpu_media_postgres: float
    cpu_pico_postgres: float
    ram_media_postgres_mb: float
    ram_pico_postgres_mb: float
    cpu_media_total: float
    cpu_pico_total: float
    ram_media_total_mb: float
    ram_pico_total_mb: float
    quantidade_registros: int
    linhas_munzona: int
    linhas_secao: int
    linhas_candidato: int
    linhas_processadas: int
    timestamp: str


ConexaoPostgres = str | dict[str, Any]


def extrair_fontes(
    limite: int | None,
    manifesto_chaves: Path | None = None,
) -> FontesTSE:
    if manifesto_chaves and manifesto_chaves.exists():
        chaves = ler_manifesto_chaves(manifesto_chaves)
        secao = filtrar_fonte_por_chaves(PASTA_SECAO, COLUNAS_SECAO, chaves)
    else:
        secao, chaves = selecionar_secoes(PASTA_SECAO, COLUNAS_SECAO, limite)
        if manifesto_chaves:
            salvar_manifesto_chaves(chaves, manifesto_chaves)

    munzona = filtrar_fonte_por_chaves(PASTA_MUNZONA, COLUNAS_MUNZONA, chaves)
    candidato = filtrar_fonte_por_chaves(
        PASTA_CANDIDATO,
        COLUNAS_CANDIDATO,
        chaves,
    )
    return FontesTSE(munzona, secao, candidato, chaves)


def _renomear_chaves(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "ANO_ELEICAO": "ano_eleicao",
            "CD_ELEICAO": "cd_eleicao",
            "NR_TURNO": "nr_turno",
            "CD_MUNICIPIO": "cd_municipio",
            "NR_ZONA": "nr_zona",
            "CD_CARGO": "cd_cargo",
        }
    )


def _converter_inteiros(df: pd.DataFrame, colunas: list[str]) -> None:
    for coluna in colunas:
        try:
            df[coluna] = pd.to_numeric(df[coluna], errors="raise").astype("int64")
        except (TypeError, ValueError) as erro:
            raise ValueError(f"Falha ao converter {coluna} para inteiro.") from erro


def transformar_munzona(df: pd.DataFrame) -> pd.DataFrame:
    resultado = _renomear_chaves(df.copy()).rename(
        columns={
            "SG_UF": "sg_uf",
            "NM_MUNICIPIO": "nm_municipio",
            "DS_CARGO": "ds_cargo",
            "QT_APTOS": "qt_aptos",
            "QT_COMPARECIMENTO": "qt_comparecimento",
            "QT_ABSTENCOES": "qt_abstencoes",
            "QT_TOTAL_VOTOS_VALIDOS": "qt_total_votos_validos",
            "QT_VOTOS_NOMINAIS_VALIDOS": "qt_votos_nominais_validos",
            "QT_TOTAL_VOTOS_LEG_VALIDOS": "qt_total_votos_leg_validos",
            "QT_VOTOS_BRANCOS": "qt_votos_brancos",
            "QT_TOTAL_VOTOS_NULOS": "qt_total_votos_nulos",
            "QT_TOTAL_VOTOS_ANULADOS": "qt_total_votos_anulados",
        }
    )
    numericas = [
        "ano_eleicao",
        "cd_eleicao",
        "nr_turno",
        "nr_zona",
        "cd_cargo",
        "qt_aptos",
        "qt_comparecimento",
        "qt_abstencoes",
        "qt_total_votos_validos",
        "qt_votos_nominais_validos",
        "qt_total_votos_leg_validos",
        "qt_votos_brancos",
        "qt_total_votos_nulos",
        "qt_total_votos_anulados",
    ]
    _converter_inteiros(resultado, numericas)
    return resultado


def agregar_secoes(df: pd.DataFrame) -> pd.DataFrame:
    resultado = _renomear_chaves(df.copy()).rename(
        columns={
            "NR_SECAO": "nr_secao",
            "QT_COMPARECIMENTO": "qt_comparecimento_secao",
            "QT_ABSTENCOES": "qt_abstencoes_secao",
            "QT_VOTOS_NOMINAIS": "qt_votos_nominais_secao",
            "QT_VOTOS_BRANCOS": "qt_votos_brancos_secao",
            "QT_VOTOS_NULOS": "qt_votos_nulos_secao",
            "QT_VOTOS_LEGENDA": "qt_votos_legenda_secao",
        }
    )
    numericas = [
        "ano_eleicao",
        "cd_eleicao",
        "nr_turno",
        "nr_zona",
        "cd_cargo",
        "nr_secao",
        "qt_comparecimento_secao",
        "qt_abstencoes_secao",
        "qt_votos_nominais_secao",
        "qt_votos_brancos_secao",
        "qt_votos_nulos_secao",
        "qt_votos_legenda_secao",
    ]
    _converter_inteiros(resultado, numericas)
    return resultado.groupby(CHAVE_FINAL, as_index=False, dropna=False).agg(
        qt_secoes_processadas=("nr_secao", "nunique"),
        qt_comparecimento_secao=("qt_comparecimento_secao", "sum"),
        qt_abstencoes_secao=("qt_abstencoes_secao", "sum"),
        qt_votos_nominais_secao=("qt_votos_nominais_secao", "sum"),
        qt_votos_brancos_secao=("qt_votos_brancos_secao", "sum"),
        qt_votos_nulos_secao=("qt_votos_nulos_secao", "sum"),
        qt_votos_legenda_secao=("qt_votos_legenda_secao", "sum"),
    )


def agregar_candidatos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                *CHAVE_FINAL,
                "qt_candidatos",
                "qt_votos_candidatos",
                "nr_candidato_mais_votado",
                "nm_candidato_mais_votado",
                "sg_partido_candidato_mais_votado",
                "qt_votos_candidato_mais_votado",
            ]
        )

    resultado = _renomear_chaves(df.copy()).rename(
        columns={
            "SQ_CANDIDATO": "sq_candidato",
            "NR_CANDIDATO": "nr_candidato",
            "NM_CANDIDATO": "nm_candidato",
            "SG_PARTIDO": "sg_partido",
            "QT_VOTOS_NOMINAIS_VALIDOS": "qt_votos_nominais_validos",
        }
    )
    _converter_inteiros(
        resultado,
        [
            "ano_eleicao",
            "cd_eleicao",
            "nr_turno",
            "nr_zona",
            "cd_cargo",
            "sq_candidato",
            "qt_votos_nominais_validos",
        ],
    )

    totais = resultado.groupby(CHAVE_FINAL, as_index=False, dropna=False).agg(
        qt_candidatos=("sq_candidato", "nunique"),
        qt_votos_candidatos=("qt_votos_nominais_validos", "sum"),
    )
    ordenado = resultado.sort_values(
        [*CHAVE_FINAL, "qt_votos_nominais_validos", "sq_candidato"],
        ascending=[True] * len(CHAVE_FINAL) + [False, True],
        kind="mergesort",
    )
    mais_votados = ordenado.drop_duplicates(CHAVE_FINAL, keep="first").rename(
        columns={
            "nr_candidato": "nr_candidato_mais_votado",
            "nm_candidato": "nm_candidato_mais_votado",
            "sg_partido": "sg_partido_candidato_mais_votado",
            "qt_votos_nominais_validos": "qt_votos_candidato_mais_votado",
        }
    )
    colunas_topo = [
        *CHAVE_FINAL,
        "nr_candidato_mais_votado",
        "nm_candidato_mais_votado",
        "sg_partido_candidato_mais_votado",
        "qt_votos_candidato_mais_votado",
    ]
    return totais.merge(
        mais_votados[colunas_topo],
        on=CHAVE_FINAL,
        how="left",
        validate="one_to_one",
    )


def _percentual(numerador: object, denominador: object) -> Decimal | None:
    if pd.isna(numerador) or pd.isna(denominador) or int(denominador) == 0:
        return None
    return (Decimal(int(numerador)) / Decimal(int(denominador))).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def construir_produto(
    munzona: pd.DataFrame,
    secoes: pd.DataFrame,
    candidatos: pd.DataFrame,
) -> pd.DataFrame:
    if munzona.duplicated(CHAVE_FINAL).any():
        quantidade = int(munzona.duplicated(CHAVE_FINAL, keep=False).sum())
        raise ValueError(
            f"munzona possui {quantidade} linhas em chaves logicas duplicadas."
        )
    if secoes.duplicated(CHAVE_FINAL).any():
        raise ValueError("Agregacao de secoes produziu chaves duplicadas.")
    if candidatos.duplicated(CHAVE_FINAL).any():
        raise ValueError("Agregacao de candidatos produziu chaves duplicadas.")

    quantidade_base = len(munzona)
    produto = munzona.merge(
        secoes,
        on=CHAVE_FINAL,
        how="left",
        validate="one_to_one",
    ).merge(
        candidatos,
        on=CHAVE_FINAL,
        how="left",
        validate="one_to_one",
    )
    if len(produto) != quantidade_base:
        raise ValueError("Os joins alteraram a quantidade de linhas de munzona.")

    agregadas_zero = [
        "qt_secoes_processadas",
        "qt_comparecimento_secao",
        "qt_abstencoes_secao",
        "qt_votos_nominais_secao",
        "qt_votos_brancos_secao",
        "qt_votos_nulos_secao",
        "qt_votos_legenda_secao",
        "qt_candidatos",
        "qt_votos_candidatos",
    ]
    for coluna in agregadas_zero:
        produto[coluna] = produto[coluna].fillna(0).astype("int64")

    produto["nr_candidato_mais_votado"] = produto[
        "nr_candidato_mais_votado"
    ].astype("string")
    produto["qt_votos_candidato_mais_votado"] = pd.to_numeric(
        produto["qt_votos_candidato_mais_votado"],
        errors="raise",
    ).astype("Int64")
    produto["pct_comparecimento"] = [
        _percentual(numerador, denominador)
        for numerador, denominador in zip(
            produto["qt_comparecimento"],
            produto["qt_aptos"],
        )
    ]
    produto["pct_abstencao"] = [
        _percentual(numerador, denominador)
        for numerador, denominador in zip(
            produto["qt_abstencoes"],
            produto["qt_aptos"],
        )
    ]
    produto["pct_votos_candidato_mais_votado"] = [
        _percentual(numerador, denominador)
        for numerador, denominador in zip(
            produto["qt_votos_candidato_mais_votado"],
            produto["qt_votos_candidatos"],
        )
    ]
    return produto[[coluna for coluna, _ in CONTRATO_FINAL]]


def validar_produto(
    produto: pd.DataFrame,
    linhas_base: int,
    secoes: pd.DataFrame | None = None,
    candidatos: pd.DataFrame | None = None,
) -> ResultadoValidacao:
    erros: list[str] = []
    alertas: list[str] = []
    esperadas = [coluna for coluna, _ in CONTRATO_FINAL]
    if list(produto.columns) != esperadas:
        erros.append("Estrutura ou ordem das colunas diverge do contrato final.")
        return ResultadoValidacao(TABELA_FINAL, erros, alertas)

    if len(produto) != linhas_base:
        erros.append(
            f"Quantidade final divergente: munzona={linhas_base}, final={len(produto)}."
        )
    nulos_chave = int(produto[CHAVE_FINAL].isna().any(axis=1).sum())
    duplicadas = int(produto.duplicated(CHAVE_FINAL).sum())
    if nulos_chave:
        erros.append(f"A chave final possui {nulos_chave} linhas com valores nulos.")
    if duplicadas:
        erros.append(f"A chave final possui {duplicadas} duplicidades.")

    indice_base = pd.MultiIndex.from_frame(produto[CHAVE_FINAL].drop_duplicates())
    for nome, agregado in (("secao", secoes), ("candidato", candidatos)):
        if agregado is None or agregado.empty:
            continue
        indice_agregado = pd.MultiIndex.from_frame(
            agregado[CHAVE_FINAL].drop_duplicates()
        )
        orfas = len(indice_agregado.difference(indice_base))
        if orfas:
            alertas.append(
                f"{orfas} chaves de {nome} nao possuem correspondencia em munzona."
            )

    descricoes = ["sg_uf", "nm_municipio", "ds_cargo"]
    nulos_descricoes = int(produto[descricoes].isna().any(axis=1).sum())
    if nulos_descricoes:
        erros.append(
            f"Identificacoes descritivas possuem {nulos_descricoes} linhas nulas."
        )

    quantidades = [
        coluna
        for coluna, tipo in CONTRATO_FINAL
        if tipo.startswith("BIGINT")
    ]
    for coluna in quantidades:
        negativos = int((produto[coluna].dropna() < 0).sum())
        if negativos:
            erros.append(f"{coluna} possui {negativos} valores negativos.")

    sem_candidatos = int((produto["qt_candidatos"] == 0).sum())
    if sem_candidatos:
        alertas.append(f"{sem_candidatos} chaves nao possuem candidatos.")

    colunas_candidato = [
        "nr_candidato_mais_votado",
        "nm_candidato_mais_votado",
        "sg_partido_candidato_mais_votado",
        "qt_votos_candidato_mais_votado",
    ]
    candidato_ausente_com_dados = (
        (produto["qt_candidatos"] == 0)
        & produto[colunas_candidato].notna().any(axis=1)
    )
    candidato_presente_incompleto = (
        (produto["qt_candidatos"] > 0)
        & produto[colunas_candidato].isna().any(axis=1)
    )
    if candidato_ausente_com_dados.any() or candidato_presente_incompleto.any():
        erros.append("Campos do candidato mais votado possuem nulos inconsistentes.")

    divergencia_eleitores = int(
        (
            produto["qt_comparecimento"] + produto["qt_abstencoes"]
            != produto["qt_aptos"]
        ).sum()
    )
    if divergencia_eleitores:
        alertas.append(
            f"{divergencia_eleitores} chaves possuem comparecimento + abstencoes "
            "diferente de aptos."
        )

    divergencia_votos_candidatos = int(
        (
            produto["qt_votos_candidatos"]
            != produto["qt_votos_nominais_validos"]
        ).sum()
    )
    if divergencia_votos_candidatos:
        alertas.append(
            f"{divergencia_votos_candidatos} chaves possuem diferenca entre "
            "votos validos de candidatos e votos nominais validos de munzona."
        )

    percentuais_esperados = {
        "pct_comparecimento": ("qt_comparecimento", "qt_aptos"),
        "pct_abstencao": ("qt_abstencoes", "qt_aptos"),
        "pct_votos_candidato_mais_votado": (
            "qt_votos_candidato_mais_votado",
            "qt_votos_candidatos",
        ),
    }
    for percentual, (numerador, denominador) in percentuais_esperados.items():
        esperado = [
            _percentual(num, den)
            for num, den in zip(produto[numerador], produto[denominador])
        ]
        divergentes = sum(
            1
            for atual, correto in zip(produto[percentual], esperado)
            if not (
                (pd.isna(atual) and correto is None)
                or atual == correto
            )
        )
        if divergentes:
            erros.append(
                f"{percentual} possui {divergentes} valores inconsistentes."
            )

    comparacoes_secao = {
        "comparecimento": ("qt_comparecimento", "qt_comparecimento_secao"),
        "abstencoes": ("qt_abstencoes", "qt_abstencoes_secao"),
        "votos nominais": (
            "qt_votos_nominais_validos",
            "qt_votos_nominais_secao",
        ),
        "votos brancos": ("qt_votos_brancos", "qt_votos_brancos_secao"),
        "votos nulos": ("qt_total_votos_nulos", "qt_votos_nulos_secao"),
        "votos de legenda": (
            "qt_total_votos_leg_validos",
            "qt_votos_legenda_secao",
        ),
    }
    for nome, (municipal, secao) in comparacoes_secao.items():
        divergentes = int((produto[municipal] != produto[secao]).sum())
        if divergentes:
            alertas.append(
                f"{divergentes} chaves possuem diferenca em {nome} entre "
                "munzona e secoes."
            )

    return ResultadoValidacao(TABELA_FINAL, erros, alertas)


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
        nome
        for nome, valor in {
            "POSTGRES_DB": conexao["dbname"],
            "POSTGRES_USER": conexao["user"],
            "POSTGRES_PASSWORD": conexao["password"],
        }.items()
        if not valor
    ]
    if faltantes:
        raise ValueError("Variaveis de conexao ausentes: " + ", ".join(faltantes))
    return conexao


def _conectar_postgres(conexao_postgres: ConexaoPostgres):
    if isinstance(conexao_postgres, str):
        return psycopg2.connect(conexao_postgres)
    return psycopg2.connect(**conexao_postgres)


def carregar_produto(
    produto: pd.DataFrame,
    conexao_postgres: ConexaoPostgres,
    schema: str,
) -> None:
    with _conectar_postgres(conexao_postgres) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(schema)
                )
            )
            cursor.execute(
                sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                    sql.Identifier(schema),
                    sql.Identifier(TABELA_FINAL),
                )
            )
            definicoes = [
                sql.SQL("{} {}").format(sql.Identifier(nome), sql.SQL(tipo))
                for nome, tipo in CONTRATO_FINAL
            ]
            cursor.execute(
                sql.SQL("CREATE TABLE {}.{} ({})").format(
                    sql.Identifier(schema),
                    sql.Identifier(TABELA_FINAL),
                    sql.SQL(", ").join(definicoes),
                )
            )

            buffer = StringIO()
            produto.to_csv(buffer, index=False, header=True, na_rep="")
            buffer.seek(0)
            comando = sql.SQL(
                "COPY {}.{} ({}) FROM STDIN WITH "
                "(FORMAT CSV, HEADER TRUE, NULL '')"
            ).format(
                sql.Identifier(schema),
                sql.Identifier(TABELA_FINAL),
                sql.SQL(", ").join(
                    sql.Identifier(coluna) for coluna in produto.columns
                ),
            )
            cursor.copy_expert(comando.as_string(cursor), buffer)


def _imprimir_validacao(resultado: ResultadoValidacao) -> None:
    print(f"Validacao {resultado.tabela}:")
    print("  Erros criticos: nenhum" if resultado.valido else "  Erros criticos:")
    for erro in resultado.erros:
        print(f"  - {erro}")
    print("  Alertas: nenhum" if not resultado.alertas else "  Alertas:")
    for alerta in resultado.alertas:
        print(f"  - {alerta}")


class MonitorRecursos:
    def __init__(self, intervalo_segundos: float = 0.5) -> None:
        self.intervalo_segundos = intervalo_segundos
        self._processo_python = psutil.Process()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._amostras: list[dict[str, float]] = []

    def iniciar(self) -> None:
        self._parar.clear()
        self._processo_python.cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._coletar, daemon=True)
        self._thread.start()

    def parar(self) -> dict[str, float]:
        self._parar.set()
        if self._thread:
            self._thread.join()
        self._registrar_amostra()
        return self._consolidar()

    def _coletar(self) -> None:
        while not self._parar.wait(self.intervalo_segundos):
            self._registrar_amostra()

    def _registrar_amostra(self) -> None:
        processos_postgres = []
        for processo in psutil.process_iter(["name"]):
            try:
                if "postgres" in (processo.info["name"] or "").lower():
                    processos_postgres.append(processo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        def cpu(processo: psutil.Process) -> float:
            try:
                return processo.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return 0.0

        def ram(processo: psutil.Process) -> int:
            try:
                return processo.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return 0

        cpu_python = cpu(self._processo_python)
        ram_python = ram(self._processo_python)
        cpu_postgres = sum(cpu(processo) for processo in processos_postgres)
        ram_postgres = sum(ram(processo) for processo in processos_postgres)
        self._amostras.append(
            {
                "cpu_python": cpu_python,
                "ram_python": float(ram_python),
                "cpu_postgres": cpu_postgres,
                "ram_postgres": float(ram_postgres),
                "cpu_total": cpu_python + cpu_postgres,
                "ram_total": float(ram_python + ram_postgres),
            }
        )

    def _consolidar(self) -> dict[str, float]:
        def media(chave: str) -> float:
            return sum(item[chave] for item in self._amostras) / len(self._amostras)

        def pico(chave: str) -> float:
            return max(item[chave] for item in self._amostras)

        return {
            "cpu_media_python": media("cpu_python"),
            "cpu_pico_python": pico("cpu_python"),
            "ram_media_python_mb": media("ram_python") / (1024 * 1024),
            "ram_pico_python_mb": pico("ram_python") / (1024 * 1024),
            "cpu_media_postgres": media("cpu_postgres"),
            "cpu_pico_postgres": pico("cpu_postgres"),
            "ram_media_postgres_mb": media("ram_postgres") / (1024 * 1024),
            "ram_pico_postgres_mb": pico("ram_postgres") / (1024 * 1024),
            "cpu_media_total": media("cpu_total"),
            "cpu_pico_total": pico("cpu_total"),
            "ram_media_total_mb": media("ram_total") / (1024 * 1024),
            "ram_pico_total_mb": pico("ram_total") / (1024 * 1024),
        }


def _salvar_benchmark(resultado: ResultadoBenchmark, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    existe = caminho.exists() and caminho.stat().st_size > 0
    linha = {}
    for campo, valor in resultado.__dict__.items():
        if isinstance(valor, float):
            valor = round(valor, 3 if campo.startswith("tempo_") else 2)
        linha[campo] = valor
    pd.DataFrame([linha]).to_csv(
        caminho,
        mode="a",
        index=False,
        header=not existe,
        sep=";",
        decimal=",",
        encoding="utf-8",
    )


def executar(args: argparse.Namespace) -> None:
    inicio_total = time.perf_counter()
    monitor = MonitorRecursos()
    if args.benchmark:
        monitor.iniciar()

    inicio = time.perf_counter()
    fontes = extrair_fontes(args.limite, args.manifesto_chaves)
    tempo_leitura = time.perf_counter() - inicio

    inicio = time.perf_counter()
    munzona = transformar_munzona(fontes.munzona)
    secoes = agregar_secoes(fontes.secao)
    candidatos = agregar_candidatos(fontes.candidato)
    produto = construir_produto(munzona, secoes, candidatos)
    tempo_transformacao = time.perf_counter() - inicio

    tempo_validacao: float | None = None
    if not args.sem_validacao:
        inicio = time.perf_counter()
        validacao = validar_produto(produto, len(munzona), secoes, candidatos)
        tempo_validacao = time.perf_counter() - inicio
        _imprimir_validacao(validacao)
        if not validacao.valido:
            if args.benchmark:
                monitor.parar()
            raise SystemExit("Carga interrompida por erros criticos de validacao.")
    else:
        print("Validacao interna ignorada no modo de desempenho.")

    try:
        conexao = obter_conexao_postgres(args.database_url)
    except ValueError as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(str(erro)) from erro
    inicio = time.perf_counter()
    try:
        carregar_produto(produto, conexao, args.schema)
    except (psycopg2.Error, UnicodeError) as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(
            f"Falha ao conectar ou carregar no PostgreSQL: {erro}"
        ) from erro
    tempo_carga = time.perf_counter() - inicio
    print(f"Carga concluida: {args.schema}.{TABELA_FINAL}.")

    print(f"Munzona: {len(fontes.munzona)} linhas")
    print(f"Secao: {len(fontes.secao)} linhas")
    print(f"Candidato: {len(fontes.candidato)} linhas")
    print(f"Produto final: {len(produto)} linhas")

    if not args.benchmark:
        return

    tempo_total = time.perf_counter() - inicio_total
    recursos = monitor.parar()
    quantidade = len(fontes.munzona) + len(fontes.secao) + len(fontes.candidato)
    resultado = ResultadoBenchmark(
        dataset="tse",
        volume_configurado=args.limite,
        arquitetura="etl",
        rodada=args.rodada,
        tempo_leitura=tempo_leitura,
        tempo_transformacao=tempo_transformacao,
        tempo_carga=tempo_carga,
        tempo_total=tempo_total,
        throughput=quantidade / tempo_total if tempo_total else 0.0,
        quantidade_registros=quantidade,
        linhas_munzona=len(fontes.munzona),
        linhas_secao=len(fontes.secao),
        linhas_candidato=len(fontes.candidato),
        linhas_processadas=len(produto),
        timestamp=datetime.now().isoformat(timespec="seconds"),
        **recursos,
    )
    print(
        f"Benchmark ETL TSE | volume={args.limite or 'todos'} | "
        f"total={tempo_total:.3f}s | registros={quantidade} | "
        f"throughput={resultado.throughput:.2f} registros/s"
    )
    if args.benchmark_output:
        _salvar_benchmark(resultado, args.benchmark_output)
        print(f"Resultado salvo em: {args.benchmark_output}")
def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline ETL do TSE 2024")
    parser.add_argument("--limite", type=int, required=True)
    parser.add_argument(
        "--modo",
        choices=["certificar", "aquecimento", "medir"],
        required=True,
    )
    parser.add_argument("--rodada", type=int)
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite deve ser maior que zero.")
    if args.modo == "medir" and args.rodada is None:
        parser.error("--rodada e obrigatoria no modo medir.")
    if args.modo != "medir" and args.rodada is not None:
        parser.error("--rodada so pode ser usada no modo medir.")

    args.manifesto_chaves = (
        BASE_DIR
        / "data"
        / "benchmark"
        / "tse"
        / "subconjuntos"
        / f"chaves_{args.limite}.csv"
    )
    if not args.manifesto_chaves.is_file():
        parser.error(
            f"Manifesto ausente: {args.manifesto_chaves}. "
            "Prepare-o com src/tse/preparar_subconjuntos.py."
        )

    args.database_url = os.getenv("DATABASE_URL")
    args.schema = os.getenv("POSTGRES_SCHEMA_TSE_ETL_FINAL", "tse_etl_final")
    args.benchmark = args.modo != "certificar"
    args.sem_validacao = args.modo != "certificar"
    args.benchmark_output = (
        BASE_DIR / "data" / "benchmark" / "tse" / "resultados" / "tse_etl.csv"
        if args.modo == "medir"
        else None
    )
    executar(args)


if __name__ == "__main__":
    main()
