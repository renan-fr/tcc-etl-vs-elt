from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterator

import psutil
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

from contrato import CHAVE_FINAL, CONTRATO_FINAL


PASTA_TSE = BASE_DIR / "data" / "raw" / "tse"
PASTA_MUNZONA = PASTA_TSE / "detalhe_votacao_munzona_2024"
PASTA_SECAO = PASTA_TSE / "detalhe_votacao_secao_2024"
PASTA_CANDIDATO = PASTA_TSE / "votacao_candidato_munzona_2024"

COLUNAS_CHAVE_ORIGEM = [
    "ANO_ELEICAO",
    "CD_ELEICAO",
    "NR_TURNO",
    "CD_MUNICIPIO",
    "NR_ZONA",
    "CD_CARGO",
]

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


SCHEMA_RAW = "tse_elt_raw"
SCHEMA_STAGING = "tse_elt_staging"
SCHEMA_FINAL = "tse_elt_final"

TABELA_RAW_MUNZONA = "detalhe_votacao_munzona"
TABELA_RAW_SECAO = "detalhe_votacao_secao"
TABELA_RAW_CANDIDATO = "votacao_candidato_munzona"
TABELA_STAGING_MUNZONA = "munzona"
TABELA_STAGING_SECAO = "secao"
TABELA_STAGING_CANDIDATO = "candidato"
TABELA_FINAL = "resultado_municipio_cargo"


@dataclass(frozen=True)
class SelecaoManifesto:
    chaves: frozenset[tuple[str, ...]]
    ufs: frozenset[str]


@dataclass(frozen=True)
class ResultadoCargaRaw:
    linhas_munzona: int
    linhas_secao: int
    linhas_candidato: int
    tempo_leitura: float
    tempo_carga: float


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
    aquecimento: bool
    tempo_leitura: float
    tempo_transformacao: float
    tempo_validacao: float | None
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
    validacao_executada: bool
    timestamp: str


ConexaoPostgres = str | dict[str, Any]


def _normalizar_chave(linha: dict[str, str]) -> tuple[str, ...]:
    valores = []
    for coluna in COLUNAS_CHAVE_ORIGEM:
        valor = (linha.get(coluna) or "").strip()
        if coluna == "CD_MUNICIPIO":
            valor = valor.zfill(5)
        valores.append(valor)
    return tuple(valores)


def ler_selecao_manifesto(caminho: Path) -> SelecaoManifesto:
    if not caminho.is_file():
        raise ValueError(f"Manifesto de chaves nao encontrado: {caminho}")

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        colunas = set(leitor.fieldnames or [])
        obrigatorias = {"SG_UF", *COLUNAS_CHAVE_ORIGEM}
        faltantes = sorted(obrigatorias - colunas)
        if faltantes:
            raise ValueError(
                "Manifesto sem colunas obrigatorias: " + ", ".join(faltantes)
            )

        chaves: set[tuple[str, ...]] = set()
        ufs: set[str] = set()
        for linha in leitor:
            chaves.add(_normalizar_chave(linha))
            uf = (linha.get("SG_UF") or "").strip()
            if uf:
                ufs.add(uf)

    if not chaves:
        raise ValueError(f"Manifesto de chaves vazio: {caminho}")
    return SelecaoManifesto(frozenset(chaves), frozenset(ufs))


def _arquivos_estaduais(
    pasta: Path,
    ufs: frozenset[str] | None,
) -> list[Path]:
    arquivos = [
        caminho
        for caminho in pasta.glob("*.csv")
        if not caminho.stem.upper().endswith("_BRASIL")
        and (ufs is None or caminho.stem.rsplit("_", 1)[-1] in ufs)
    ]
    if not arquivos:
        raise ValueError(f"Nenhum CSV estadual encontrado em {pasta}.")
    return sorted(arquivos, key=lambda caminho: caminho.name)


class FluxoCSVFiltrado:
    """Produz CSV em blocos sem materializar a fonte inteira em memoria."""

    def __init__(
        self,
        pasta: Path,
        colunas: list[str],
        selecao: SelecaoManifesto | None,
        linhas_por_bloco: int = 4_096,
    ) -> None:
        self._pasta = pasta
        self._colunas = colunas
        self._selecao = selecao
        self._linhas_por_bloco = linhas_por_bloco
        self._blocos = self._gerar_blocos()
        self._pendente = ""
        self.linhas = 0
        self.tempo_leitura = 0.0

    def read(self, tamanho: int = -1) -> str:
        if tamanho is None or tamanho < 0:
            tamanho = 64 * 1024
        while len(self._pendente) < tamanho:
            try:
                self._pendente += next(self._blocos)
            except StopIteration:
                break
        resultado = self._pendente[:tamanho]
        self._pendente = self._pendente[tamanho:]
        return resultado

    def _iterar_linhas(self) -> Iterator[list[str]]:
        ufs = self._selecao.ufs if self._selecao else None
        for caminho in _arquivos_estaduais(self._pasta, ufs):
            with caminho.open("r", encoding="latin-1", newline="") as arquivo:
                leitor = csv.DictReader(arquivo, delimiter=";")
                presentes = set(leitor.fieldnames or [])
                faltantes = sorted(set(self._colunas) - presentes)
                if faltantes:
                    raise ValueError(
                        f"{caminho.name} sem colunas obrigatorias: "
                        + ", ".join(faltantes)
                    )

                for linha in leitor:
                    chave = _normalizar_chave(linha)
                    if self._selecao and chave not in self._selecao.chaves:
                        continue
                    valores = []
                    for coluna in self._colunas:
                        valor = linha.get(coluna) or ""
                        if coluna in COLUNAS_CHAVE_ORIGEM:
                            valor = valor.strip()
                            if coluna == "CD_MUNICIPIO":
                                valor = valor.zfill(5)
                        valores.append(valor)
                    yield valores

    def _gerar_blocos(self) -> Iterator[str]:
        cabecalho = StringIO()
        csv.writer(cabecalho, lineterminator="\n").writerow(self._colunas)
        yield cabecalho.getvalue()

        linhas = self._iterar_linhas()
        finalizado = False
        while not finalizado:
            inicio = time.perf_counter()
            buffer = StringIO()
            escritor = csv.writer(buffer, lineterminator="\n")
            quantidade = 0
            for _ in range(self._linhas_por_bloco):
                try:
                    escritor.writerow(next(linhas))
                    quantidade += 1
                except StopIteration:
                    finalizado = True
                    break
            self.tempo_leitura += time.perf_counter() - inicio
            if quantidade:
                self.linhas += quantidade
                yield buffer.getvalue()


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


def _criar_tabela_texto(cursor, schema: str, tabela: str, colunas: list[str]) -> None:
    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
    )
    cursor.execute(
        sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(schema), sql.Identifier(tabela)
        )
    )
    definicoes = [
        sql.SQL("{} TEXT").format(sql.Identifier(coluna)) for coluna in colunas
    ]
    cursor.execute(
        sql.SQL("CREATE TABLE {}.{} ({})").format(
            sql.Identifier(schema),
            sql.Identifier(tabela),
            sql.SQL(", ").join(definicoes),
        )
    )


def _carregar_fonte_raw(
    cursor,
    schema: str,
    tabela: str,
    pasta: Path,
    colunas: list[str],
    selecao: SelecaoManifesto | None,
) -> tuple[int, float, float]:
    inicio_total = time.perf_counter()
    _criar_tabela_texto(cursor, schema, tabela, colunas)
    fluxo = FluxoCSVFiltrado(pasta, colunas, selecao)
    comando = sql.SQL(
        "COPY {}.{} ({}) FROM STDIN WITH "
        "(FORMAT CSV, HEADER TRUE, NULL '')"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(tabela),
        sql.SQL(", ").join(sql.Identifier(coluna) for coluna in colunas),
    )
    cursor.copy_expert(comando.as_string(cursor), fluxo)
    tempo_total = time.perf_counter() - inicio_total
    tempo_carga = max(0.0, tempo_total - fluxo.tempo_leitura)
    return fluxo.linhas, fluxo.tempo_leitura, tempo_carga


def carregar_raw(
    cursor,
    schema_raw: str,
    selecao: SelecaoManifesto | None,
) -> ResultadoCargaRaw:
    tabelas = (
        (TABELA_RAW_MUNZONA, PASTA_MUNZONA, COLUNAS_MUNZONA),
        (TABELA_RAW_SECAO, PASTA_SECAO, COLUNAS_SECAO),
        (TABELA_RAW_CANDIDATO, PASTA_CANDIDATO, COLUNAS_CANDIDATO),
    )
    resultados = []
    for tabela, pasta, colunas in tabelas:
        resultados.append(
            _carregar_fonte_raw(cursor, schema_raw, tabela, pasta, colunas, selecao)
        )
    return ResultadoCargaRaw(
        linhas_munzona=resultados[0][0],
        linhas_secao=resultados[1][0],
        linhas_candidato=resultados[2][0],
        tempo_leitura=sum(resultado[1] for resultado in resultados),
        tempo_carga=sum(resultado[2] for resultado in resultados),
    )


def construir_staging(
    cursor,
    schema_raw: str,
    schema_staging: str,
) -> None:
    numericas_obrigatorias = {
        TABELA_RAW_MUNZONA: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
            "QT_TOTAL_VOTOS_VALIDOS", "QT_VOTOS_NOMINAIS_VALIDOS",
            "QT_TOTAL_VOTOS_LEG_VALIDOS", "QT_VOTOS_BRANCOS",
            "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_ANULADOS",
        ],
        TABELA_RAW_SECAO: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "NR_SECAO", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
            "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS",
            "QT_VOTOS_LEGENDA",
        ],
        TABELA_RAW_CANDIDATO: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "SQ_CANDIDATO", "QT_VOTOS_NOMINAIS_VALIDOS",
        ],
    }
    for tabela, colunas in numericas_obrigatorias.items():
        condicao = sql.SQL(" OR ").join(
            sql.SQL("{} IS NULL").format(sql.Identifier(coluna))
            for coluna in colunas
        )
        cursor.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.{} WHERE {}").format(
                sql.Identifier(schema_raw), sql.Identifier(tabela), condicao
            )
        )
        nulas = int(cursor.fetchone()[0])
        if nulas:
            raise ValueError(
                f"{schema_raw}.{tabela} possui {nulas} linhas com valores "
                "numericos obrigatorios ausentes."
            )

    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            sql.Identifier(schema_staging)
        )
    )
    cursor.execute(
        sql.SQL(
            """
            DROP TABLE IF EXISTS {staging}.munzona;
            CREATE TABLE {staging}.munzona (
                ano_eleicao INTEGER NOT NULL,
                cd_eleicao INTEGER NOT NULL,
                nr_turno INTEGER NOT NULL,
                sg_uf TEXT NOT NULL,
                cd_municipio TEXT NOT NULL,
                nm_municipio TEXT NOT NULL,
                nr_zona INTEGER NOT NULL,
                cd_cargo INTEGER NOT NULL,
                ds_cargo TEXT NOT NULL,
                qt_aptos BIGINT NOT NULL,
                qt_comparecimento BIGINT NOT NULL,
                qt_abstencoes BIGINT NOT NULL,
                qt_total_votos_validos BIGINT NOT NULL,
                qt_votos_nominais_validos BIGINT NOT NULL,
                qt_total_votos_leg_validos BIGINT NOT NULL,
                qt_votos_brancos BIGINT NOT NULL,
                qt_total_votos_nulos BIGINT NOT NULL,
                qt_total_votos_anulados BIGINT NOT NULL
            );
            INSERT INTO {staging}.munzona
            SELECT
                "ANO_ELEICAO"::integer,
                "CD_ELEICAO"::integer,
                "NR_TURNO"::integer,
                "SG_UF",
                LPAD(TRIM("CD_MUNICIPIO"), 5, '0'),
                "NM_MUNICIPIO",
                "NR_ZONA"::integer,
                "CD_CARGO"::integer,
                "DS_CARGO",
                "QT_APTOS"::bigint,
                "QT_COMPARECIMENTO"::bigint,
                "QT_ABSTENCOES"::bigint,
                "QT_TOTAL_VOTOS_VALIDOS"::bigint,
                "QT_VOTOS_NOMINAIS_VALIDOS"::bigint,
                "QT_TOTAL_VOTOS_LEG_VALIDOS"::bigint,
                "QT_VOTOS_BRANCOS"::bigint,
                "QT_TOTAL_VOTOS_NULOS"::bigint,
                "QT_TOTAL_VOTOS_ANULADOS"::bigint
            FROM {raw}.detalhe_votacao_munzona;

            DROP TABLE IF EXISTS {staging}.secao;
            CREATE TABLE {staging}.secao (
                ano_eleicao INTEGER NOT NULL,
                cd_eleicao INTEGER NOT NULL,
                nr_turno INTEGER NOT NULL,
                cd_municipio TEXT NOT NULL,
                nr_zona INTEGER NOT NULL,
                cd_cargo INTEGER NOT NULL,
                qt_secoes_processadas BIGINT NOT NULL,
                qt_comparecimento_secao BIGINT NOT NULL,
                qt_abstencoes_secao BIGINT NOT NULL,
                qt_votos_nominais_secao BIGINT NOT NULL,
                qt_votos_brancos_secao BIGINT NOT NULL,
                qt_votos_nulos_secao BIGINT NOT NULL,
                qt_votos_legenda_secao BIGINT NOT NULL
            );
            INSERT INTO {staging}.secao
            SELECT
                "ANO_ELEICAO"::integer,
                "CD_ELEICAO"::integer,
                "NR_TURNO"::integer,
                LPAD(TRIM("CD_MUNICIPIO"), 5, '0'),
                "NR_ZONA"::integer,
                "CD_CARGO"::integer,
                COUNT(DISTINCT "NR_SECAO"::bigint)::bigint,
                SUM("QT_COMPARECIMENTO"::bigint)::bigint,
                SUM("QT_ABSTENCOES"::bigint)::bigint,
                SUM("QT_VOTOS_NOMINAIS"::bigint)::bigint,
                SUM("QT_VOTOS_BRANCOS"::bigint)::bigint,
                SUM("QT_VOTOS_NULOS"::bigint)::bigint,
                SUM("QT_VOTOS_LEGENDA"::bigint)::bigint
            FROM {raw}.detalhe_votacao_secao
            GROUP BY 1, 2, 3, 4, 5, 6;

            DROP TABLE IF EXISTS {staging}.candidato;
            CREATE TABLE {staging}.candidato (
                ano_eleicao INTEGER NOT NULL,
                cd_eleicao INTEGER NOT NULL,
                nr_turno INTEGER NOT NULL,
                cd_municipio TEXT NOT NULL,
                nr_zona INTEGER NOT NULL,
                cd_cargo INTEGER NOT NULL,
                qt_candidatos BIGINT NOT NULL,
                qt_votos_candidatos BIGINT NOT NULL,
                nr_candidato_mais_votado TEXT,
                nm_candidato_mais_votado TEXT,
                sg_partido_candidato_mais_votado TEXT,
                qt_votos_candidato_mais_votado BIGINT
            );
            WITH tipado AS (
                SELECT
                    "ANO_ELEICAO"::integer AS ano_eleicao,
                    "CD_ELEICAO"::integer AS cd_eleicao,
                    "NR_TURNO"::integer AS nr_turno,
                    LPAD(TRIM("CD_MUNICIPIO"), 5, '0') AS cd_municipio,
                    "NR_ZONA"::integer AS nr_zona,
                    "CD_CARGO"::integer AS cd_cargo,
                    "SQ_CANDIDATO"::bigint AS sq_candidato,
                    "NR_CANDIDATO" AS nr_candidato,
                    "NM_CANDIDATO" AS nm_candidato,
                    "SG_PARTIDO" AS sg_partido,
                    "QT_VOTOS_NOMINAIS_VALIDOS"::bigint AS votos
                FROM {raw}.votacao_candidato_munzona
            ), totais AS (
                SELECT
                    ano_eleicao, cd_eleicao, nr_turno, cd_municipio,
                    nr_zona, cd_cargo,
                    COUNT(DISTINCT sq_candidato)::bigint AS qt_candidatos,
                    SUM(votos)::bigint AS qt_votos_candidatos
                FROM tipado
                GROUP BY 1, 2, 3, 4, 5, 6
            ), ranking AS (
                SELECT
                    tipado.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY ano_eleicao, cd_eleicao, nr_turno,
                                     cd_municipio, nr_zona, cd_cargo
                        ORDER BY votos DESC, sq_candidato ASC
                    ) AS posicao
                FROM tipado
            )
            INSERT INTO {staging}.candidato
            SELECT
                t.ano_eleicao, t.cd_eleicao, t.nr_turno, t.cd_municipio,
                t.nr_zona, t.cd_cargo, t.qt_candidatos, t.qt_votos_candidatos,
                r.nr_candidato, r.nm_candidato, r.sg_partido, r.votos
            FROM totais t
            JOIN ranking r
              ON r.ano_eleicao = t.ano_eleicao
             AND r.cd_eleicao = t.cd_eleicao
             AND r.nr_turno = t.nr_turno
             AND r.cd_municipio = t.cd_municipio
             AND r.nr_zona = t.nr_zona
             AND r.cd_cargo = t.cd_cargo
             AND r.posicao = 1;
            """
        ).format(
            raw=sql.Identifier(schema_raw),
            staging=sql.Identifier(schema_staging),
        )
    )


def _contar_duplicadas(cursor, schema: str, tabela: str) -> int:
    chaves = sql.SQL(", ").join(sql.Identifier(coluna) for coluna in CHAVE_FINAL)
    cursor.execute(
        sql.SQL(
            "SELECT COALESCE(SUM(quantidade), 0) FROM "
            "(SELECT COUNT(*) AS quantidade FROM {}.{} "
            "GROUP BY {} HAVING COUNT(*) > 1) duplicadas"
        ).format(sql.Identifier(schema), sql.Identifier(tabela), chaves)
    )
    return int(cursor.fetchone()[0])


def construir_produto(
    cursor,
    schema_staging: str,
    schema_final: str,
) -> int:
    for tabela in (
        TABELA_STAGING_MUNZONA,
        TABELA_STAGING_SECAO,
        TABELA_STAGING_CANDIDATO,
    ):
        duplicadas = _contar_duplicadas(cursor, schema_staging, tabela)
        if duplicadas:
            raise ValueError(
                f"{schema_staging}.{tabela} possui {duplicadas} linhas em "
                "chaves logicas duplicadas."
            )

    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_final))
    )
    cursor.execute(
        sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(schema_final), sql.Identifier(TABELA_FINAL)
        )
    )
    definicoes = [
        sql.SQL("{} {}").format(sql.Identifier(nome), sql.SQL(tipo))
        for nome, tipo in CONTRATO_FINAL
    ]
    cursor.execute(
        sql.SQL("CREATE TABLE {}.{} ({})").format(
            sql.Identifier(schema_final),
            sql.Identifier(TABELA_FINAL),
            sql.SQL(", ").join(definicoes),
        )
    )
    cursor.execute(
        sql.SQL(
            """
            INSERT INTO {final}.resultado_municipio_cargo
            SELECT
                m.ano_eleicao,
                m.cd_eleicao,
                m.nr_turno,
                m.sg_uf,
                m.cd_municipio,
                m.nm_municipio,
                m.nr_zona,
                m.cd_cargo,
                m.ds_cargo,
                m.qt_aptos,
                m.qt_comparecimento,
                m.qt_abstencoes,
                m.qt_total_votos_validos,
                m.qt_votos_nominais_validos,
                m.qt_total_votos_leg_validos,
                m.qt_votos_brancos,
                m.qt_total_votos_nulos,
                m.qt_total_votos_anulados,
                COALESCE(s.qt_secoes_processadas, 0),
                COALESCE(s.qt_comparecimento_secao, 0),
                COALESCE(s.qt_abstencoes_secao, 0),
                COALESCE(s.qt_votos_nominais_secao, 0),
                COALESCE(s.qt_votos_brancos_secao, 0),
                COALESCE(s.qt_votos_nulos_secao, 0),
                COALESCE(s.qt_votos_legenda_secao, 0),
                COALESCE(c.qt_candidatos, 0),
                COALESCE(c.qt_votos_candidatos, 0),
                c.nr_candidato_mais_votado,
                c.nm_candidato_mais_votado,
                c.sg_partido_candidato_mais_votado,
                c.qt_votos_candidato_mais_votado,
                ROUND(
                    m.qt_comparecimento::numeric / NULLIF(m.qt_aptos, 0), 6
                )::numeric(9,6),
                ROUND(
                    m.qt_abstencoes::numeric / NULLIF(m.qt_aptos, 0), 6
                )::numeric(9,6),
                ROUND(
                    c.qt_votos_candidato_mais_votado::numeric
                    / NULLIF(c.qt_votos_candidatos, 0), 6
                )::numeric(9,6)
            FROM {staging}.munzona m
            LEFT JOIN {staging}.secao s
              USING (ano_eleicao, cd_eleicao, nr_turno, cd_municipio,
                     nr_zona, cd_cargo)
            LEFT JOIN {staging}.candidato c
              USING (ano_eleicao, cd_eleicao, nr_turno, cd_municipio,
                     nr_zona, cd_cargo);
            """
        ).format(
            staging=sql.Identifier(schema_staging),
            final=sql.Identifier(schema_final),
        )
    )
    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema_staging), sql.Identifier(TABELA_STAGING_MUNZONA)
        )
    )
    linhas_base = int(cursor.fetchone()[0])
    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema_final), sql.Identifier(TABELA_FINAL)
        )
    )
    linhas_produto = int(cursor.fetchone()[0])
    if linhas_produto != linhas_base:
        raise ValueError(
            f"Os joins alteraram a quantidade de linhas: "
            f"munzona={linhas_base}, final={linhas_produto}."
        )
    return linhas_produto


def _escalar(cursor, consulta: sql.Composed) -> int:
    cursor.execute(consulta)
    return int(cursor.fetchone()[0])


def validar_produto(
    cursor,
    schema_staging: str,
    schema_final: str,
) -> ResultadoValidacao:
    erros: list[str] = []
    alertas: list[str] = []
    final = sql.SQL("{}.{}").format(
        sql.Identifier(schema_final), sql.Identifier(TABELA_FINAL)
    )
    staging = sql.Identifier(schema_staging)

    cursor.execute(
        """
        SELECT
            atributo.attname,
            pg_catalog.format_type(atributo.atttypid, atributo.atttypmod),
            atributo.attnotnull
        FROM pg_catalog.pg_attribute atributo
        JOIN pg_catalog.pg_class tabela
          ON tabela.oid = atributo.attrelid
        JOIN pg_catalog.pg_namespace schema
          ON schema.oid = tabela.relnamespace
        WHERE schema.nspname = %s
          AND tabela.relname = %s
          AND atributo.attnum > 0
          AND NOT atributo.attisdropped
        ORDER BY atributo.attnum
        """,
        (schema_final, TABELA_FINAL),
    )
    estrutura = cursor.fetchall()
    estrutura_esperada = [
        (
            nome,
            tipo.replace(" NOT NULL", "").lower(),
            tipo.endswith(" NOT NULL"),
        )
        for nome, tipo in CONTRATO_FINAL
    ]
    if estrutura != estrutura_esperada:
        erros.append(
            "Estrutura, ordem, tipos ou nulabilidade divergem do contrato final."
        )
        return ResultadoValidacao(TABELA_FINAL, erros, alertas)

    chaves = sql.SQL(", ").join(sql.Identifier(coluna) for coluna in CHAVE_FINAL)
    nulos_chave = _escalar(
        cursor,
        sql.SQL("SELECT COUNT(*) FROM {} WHERE {} ").format(
            final,
            sql.SQL(" OR ").join(
                sql.SQL("{} IS NULL").format(sql.Identifier(coluna))
                for coluna in CHAVE_FINAL
            ),
        ),
    )
    if nulos_chave:
        erros.append(f"A chave final possui {nulos_chave} linhas com valores nulos.")
    duplicadas = _contar_duplicadas(cursor, schema_final, TABELA_FINAL)
    if duplicadas:
        erros.append(f"A chave final possui {duplicadas} linhas duplicadas.")

    nulos_descricoes = _escalar(
        cursor,
        sql.SQL(
            "SELECT COUNT(*) FROM {} WHERE sg_uf IS NULL "
            "OR nm_municipio IS NULL OR ds_cargo IS NULL"
        ).format(final),
    )
    if nulos_descricoes:
        erros.append(
            f"Identificacoes descritivas possuem {nulos_descricoes} linhas nulas."
        )

    quantidades = [
        coluna for coluna, tipo in CONTRATO_FINAL if tipo.startswith("BIGINT")
    ]
    for coluna in quantidades:
        negativos = _escalar(
            cursor,
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} < 0").format(
                final, sql.Identifier(coluna)
            ),
        )
        if negativos:
            erros.append(f"{coluna} possui {negativos} valores negativos.")

    sem_candidatos = _escalar(
        cursor, sql.SQL("SELECT COUNT(*) FROM {} WHERE qt_candidatos = 0").format(final)
    )
    if sem_candidatos:
        alertas.append(f"{sem_candidatos} chaves nao possuem candidatos.")

    inconsistencias_candidato = _escalar(
        cursor,
        sql.SQL(
            """
            SELECT COUNT(*) FROM {}
            WHERE (qt_candidatos = 0 AND (
                       nr_candidato_mais_votado IS NOT NULL
                    OR nm_candidato_mais_votado IS NOT NULL
                    OR sg_partido_candidato_mais_votado IS NOT NULL
                    OR qt_votos_candidato_mais_votado IS NOT NULL))
               OR (qt_candidatos > 0 AND (
                       nr_candidato_mais_votado IS NULL
                    OR nm_candidato_mais_votado IS NULL
                    OR sg_partido_candidato_mais_votado IS NULL
                    OR qt_votos_candidato_mais_votado IS NULL))
            """
        ).format(final),
    )
    if inconsistencias_candidato:
        erros.append("Campos do candidato mais votado possuem nulos inconsistentes.")

    verificacoes_alerta = (
        (
            "comparecimento + abstencoes diferente de aptos",
            "qt_comparecimento + qt_abstencoes <> qt_aptos",
        ),
        (
            "diferenca entre votos validos de candidatos e votos nominais validos de munzona",
            "qt_votos_candidatos <> qt_votos_nominais_validos",
        ),
    )
    for mensagem, condicao in verificacoes_alerta:
        quantidade = _escalar(
            cursor,
            sql.SQL("SELECT COUNT(*) FROM {} WHERE " + condicao).format(final),
        )
        if quantidade:
            alertas.append(f"{quantidade} chaves possuem {mensagem}.")

    percentuais = (
        ("pct_comparecimento", "qt_comparecimento", "qt_aptos"),
        ("pct_abstencao", "qt_abstencoes", "qt_aptos"),
        (
            "pct_votos_candidato_mais_votado",
            "qt_votos_candidato_mais_votado",
            "qt_votos_candidatos",
        ),
    )
    for percentual, numerador, denominador in percentuais:
        divergentes = _escalar(
            cursor,
            sql.SQL(
                "SELECT COUNT(*) FROM {} WHERE {} IS DISTINCT FROM "
                "ROUND({}::numeric / NULLIF({}, 0), 6)::numeric(9,6)"
            ).format(
                final,
                sql.Identifier(percentual),
                sql.Identifier(numerador),
                sql.Identifier(denominador),
            ),
        )
        if divergentes:
            erros.append(f"{percentual} possui {divergentes} valores inconsistentes.")

    comparacoes_secao = (
        ("comparecimento", "qt_comparecimento", "qt_comparecimento_secao"),
        ("abstencoes", "qt_abstencoes", "qt_abstencoes_secao"),
        ("votos nominais", "qt_votos_nominais_validos", "qt_votos_nominais_secao"),
        ("votos brancos", "qt_votos_brancos", "qt_votos_brancos_secao"),
        ("votos nulos", "qt_total_votos_nulos", "qt_votos_nulos_secao"),
        ("votos de legenda", "qt_total_votos_leg_validos", "qt_votos_legenda_secao"),
    )
    for nome, municipal, secao in comparacoes_secao:
        divergentes = _escalar(
            cursor,
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} <> {}").format(
                final, sql.Identifier(municipal), sql.Identifier(secao)
            ),
        )
        if divergentes:
            alertas.append(
                f"{divergentes} chaves possuem diferenca em {nome} entre "
                "munzona e secoes."
            )

    for nome, tabela in (("secao", "secao"), ("candidato", "candidato")):
        condicoes = sql.SQL(" AND ").join(
            sql.SQL("b.{} = a.{}").format(
                sql.Identifier(coluna), sql.Identifier(coluna)
            )
            for coluna in CHAVE_FINAL
        )
        orfas = _escalar(
            cursor,
            sql.SQL(
                "SELECT COUNT(*) FROM {}.{} a WHERE NOT EXISTS "
                "(SELECT 1 FROM {}.munzona b WHERE {})"
            ).format(staging, sql.Identifier(tabela), staging, condicoes),
        )
        if orfas:
            alertas.append(
                f"{orfas} chaves de {nome} nao possuem correspondencia em munzona."
            )

    return ResultadoValidacao(TABELA_FINAL, erros, alertas)


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
    campos = list(resultado.__dataclass_fields__)
    linha: dict[str, object] = {}
    for campo in campos:
        valor = getattr(resultado, campo)
        if isinstance(valor, float):
            casas = 3 if campo.startswith("tempo_") else 2
            valor = str(round(valor, casas)).replace(".", ",")
        linha[campo] = valor
    with caminho.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        if not existe:
            escritor.writeheader()
        escritor.writerow(linha)


def executar(args: argparse.Namespace) -> None:
    inicio_total = time.perf_counter()
    if args.limite is not None and args.manifesto_chaves is None:
        raise SystemExit(
            "O TSE ELT exige --manifesto-chaves quando --limite e informado. "
            "Prepare o manifesto antes da execucao."
        )

    monitor = MonitorRecursos()
    if args.benchmark:
        monitor.iniciar()

    inicio_manifesto = time.perf_counter()
    try:
        selecao = (
            ler_selecao_manifesto(args.manifesto_chaves)
            if args.manifesto_chaves is not None
            else None
        )
    except (OSError, ValueError, csv.Error) as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(str(erro)) from erro
    tempo_manifesto = time.perf_counter() - inicio_manifesto

    tempo_validacao: float | None = None
    validacao: ResultadoValidacao | None = None
    try:
        conexao_postgres = obter_conexao_postgres(args.database_url)
    except ValueError as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(str(erro)) from erro

    try:
        with _conectar_postgres(conexao_postgres) as conexao:
            with conexao.cursor() as cursor:
                carga_raw = carregar_raw(cursor, args.schema_raw, selecao)
                inicio_commit = time.perf_counter()
                conexao.commit()
                tempo_commit = time.perf_counter() - inicio_commit
                tempo_leitura = tempo_manifesto + carga_raw.tempo_leitura
                tempo_carga = carga_raw.tempo_carga + tempo_commit
                linhas_munzona = carga_raw.linhas_munzona
                linhas_secao = carga_raw.linhas_secao
                linhas_candidato = carga_raw.linhas_candidato

                inicio = time.perf_counter()
                construir_staging(cursor, args.schema_raw, args.schema_staging)
                linhas_processadas = construir_produto(
                    cursor, args.schema_staging, args.schema_final
                )
                conexao.commit()
                tempo_transformacao = time.perf_counter() - inicio

                if not args.sem_validacao:
                    inicio = time.perf_counter()
                    validacao = validar_produto(
                        cursor, args.schema_staging, args.schema_final
                    )
                    tempo_validacao = time.perf_counter() - inicio
    except (psycopg2.Error, UnicodeError, ValueError, OSError, csv.Error) as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(f"Falha no pipeline ELT do TSE: {erro}") from erro

    if validacao is not None:
        _imprimir_validacao(validacao)
        if not validacao.valido:
            if args.benchmark:
                monitor.parar()
            raise SystemExit("Pipeline interrompido por erros criticos de validacao.")
    else:
        print("Validacao interna ignorada (--sem-validacao).")

    tempo_total = time.perf_counter() - inicio_total
    print(f"Munzona: {linhas_munzona} linhas")
    print(f"Secao: {linhas_secao} linhas")
    print(f"Candidato: {linhas_candidato} linhas")
    print(f"Produto final: {linhas_processadas} linhas")
    print(f"Carga RAW: {tempo_carga:.3f}s")
    print(f"Transformacao SQL: {tempo_transformacao:.3f}s")
    if tempo_validacao is None:
        print("Validacao: nao executada")
    else:
        print(f"Validacao: {tempo_validacao:.3f}s")
    print(f"Total: {tempo_total:.3f}s")

    if not args.benchmark:
        return

    recursos = monitor.parar()
    quantidade = linhas_munzona + linhas_secao + linhas_candidato
    resultado = ResultadoBenchmark(
        dataset="tse",
        volume_configurado=args.limite,
        arquitetura="elt",
        rodada=args.rodada,
        aquecimento=args.aquecimento,
        tempo_leitura=tempo_leitura,
        tempo_transformacao=tempo_transformacao,
        tempo_validacao=tempo_validacao,
        tempo_carga=tempo_carga,
        tempo_total=tempo_total,
        throughput=quantidade / tempo_total if tempo_total else 0.0,
        quantidade_registros=quantidade,
        linhas_munzona=linhas_munzona,
        linhas_secao=linhas_secao,
        linhas_candidato=linhas_candidato,
        linhas_processadas=linhas_processadas,
        validacao_executada=tempo_validacao is not None,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        **recursos,
    )
    print(
        f"Benchmark ELT TSE | volume={args.limite or 'todos'} | "
        f"total={tempo_total:.3f}s | registros={quantidade} | "
        f"throughput={resultado.throughput:.2f} registros/s"
    )
    if args.benchmark_output:
        _salvar_benchmark(resultado, args.benchmark_output)
        print(f"Resultado salvo em: {args.benchmark_output}")
    if args.benchmark_summary_output:
        args.benchmark_summary_output.parent.mkdir(parents=True, exist_ok=True)
        with args.benchmark_summary_output.open("a", encoding="utf-8") as arquivo:
            arquivo.write(
                f"Benchmark ELT TSE | volume={args.limite or 'todos'} | "
                f"total={tempo_total:.3f}s | registros={quantidade} | "
                f"processadas={linhas_processadas} | "
                f"throughput={resultado.throughput:.2f}\n"
            )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline ELT do TSE 2024")
    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="Volume nominal de linhas da fonte de secao; use 0 para todas.",
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument(
        "--schema-raw",
        default=os.getenv("POSTGRES_SCHEMA_TSE_ELT_RAW", SCHEMA_RAW),
    )
    parser.add_argument(
        "--schema-staging",
        default=os.getenv("POSTGRES_SCHEMA_TSE_ELT_STAGING", SCHEMA_STAGING),
    )
    parser.add_argument(
        "--schema-final",
        default=os.getenv("POSTGRES_SCHEMA_TSE_ELT_FINAL", SCHEMA_FINAL),
    )
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument(
        "--sem-validacao",
        action="store_true",
        help="Ignora validacoes internas no benchmark previamente certificado.",
    )
    parser.add_argument("--rodada", type=int, default=None)
    parser.add_argument("--aquecimento", action="store_true")
    parser.add_argument("--manifesto-chaves", type=Path, default=None)
    parser.add_argument(
        "--benchmark-output",
        type=Path,
        default=BASE_DIR / "data" / "benchmark" / "tse" / "resultados" / "tse_elt.csv",
    )
    parser.add_argument(
        "--benchmark-summary-output",
        type=Path,
        default=BASE_DIR / "data" / "benchmark" / "tse" / "resumos" / "tse_elt.txt",
    )
    args = parser.parse_args()
    if args.limite < 0:
        parser.error("--limite deve ser maior ou igual a zero.")
    args.limite = None if args.limite == 0 else args.limite
    executar(args)


if __name__ == "__main__":
    main()
