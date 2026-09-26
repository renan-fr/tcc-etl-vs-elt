from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from io import TextIOWrapper
import os
from pathlib import Path
import tempfile
import threading
import time

import psycopg2
import psutil
from psycopg2 import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
PASTA_ENEM = BASE_DIR / "data" / "raw" / "enem" / "microdados_enem_2024" / "DADOS"
CAMINHO_PARTICIPANTES = PASTA_ENEM / "PARTICIPANTES_2024.csv"
CAMINHO_RESULTADOS = PASTA_ENEM / "RESULTADOS_2024.csv"

SCHEMA_RAW = "raw"
SCHEMA_FINAL = "elt"
TABELA_RAW_PARTICIPANTES = "enem_participantes"
TABELA_RAW_RESULTADOS = "enem_resultados"
TABELA_FINAL_PARTICIPANTES = "enem_participantes"
TABELA_FINAL_RESULTADOS = "enem_resultados"

COLUNAS_PARTICIPANTES = [
    "NU_INSCRICAO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_COR_RACA",
    "TP_ST_CONCLUSAO", "IN_TREINEIRO", "NO_MUNICIPIO_PROVA", "SG_UF_PROVA",
    "Q007", "Q020", "Q023",
]

COLUNAS_RESULTADOS = [
    "NU_SEQUENCIAL", "NO_MUNICIPIO_ESC", "SG_UF_ESC", "TP_DEPENDENCIA_ADM_ESC",
    "TP_LOCALIZACAO_ESC", "TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC",
    "TP_PRESENCA_MT", "TP_STATUS_REDACAO", "NU_NOTA_CN", "NU_NOTA_CH",
    "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO",
]


@dataclass(frozen=True)
class TemposELT:
    leitura: float
    carga_raw: float
    transformacao_sql: float
    validacao: float
    total: float
    linhas_participantes: int
    linhas_resultados: int


@dataclass(frozen=True)
class ResultadoBenchmark:
    dataset: str
    volume_configurado: int | None
    arquitetura: str
    rodada: int | None
    aquecimento: bool
    tempo_leitura: float
    tempo_transformacao: float
    tempo_validacao: float
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
    linhas_participantes: int
    linhas_resultados: int
    timestamp: str


class MonitorRecursos:
    def __init__(self, intervalo_segundos: float = 0.5) -> None:
        self._processo_python = psutil.Process()
        self._intervalo = intervalo_segundos
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
        chaves = ("cpu_python", "ram_python", "cpu_postgres", "ram_postgres", "cpu_total", "ram_total")
        if not self._amostras:
            valores = {chave: [0.0] for chave in chaves}
        else:
            valores = {chave: [amostra[chave] for amostra in self._amostras] for chave in chaves}
        return {
            "cpu_media_python": sum(valores["cpu_python"]) / len(valores["cpu_python"]),
            "cpu_pico_python": max(valores["cpu_python"]),
            "ram_media_python_mb": sum(valores["ram_python"]) / len(valores["ram_python"]) / (1024 * 1024),
            "ram_pico_python_mb": max(valores["ram_python"]) / (1024 * 1024),
            "cpu_media_postgres": sum(valores["cpu_postgres"]) / len(valores["cpu_postgres"]),
            "cpu_pico_postgres": max(valores["cpu_postgres"]),
            "ram_media_postgres_mb": sum(valores["ram_postgres"]) / len(valores["ram_postgres"]) / (1024 * 1024),
            "ram_pico_postgres_mb": max(valores["ram_postgres"]) / (1024 * 1024),
            "cpu_media_total": sum(valores["cpu_total"]) / len(valores["cpu_total"]),
            "cpu_pico_total": max(valores["cpu_total"]),
            "ram_media_total_mb": sum(valores["ram_total"]) / len(valores["ram_total"]) / (1024 * 1024),
            "ram_pico_total_mb": max(valores["ram_total"]) / (1024 * 1024),
        }

    def _coletar(self) -> None:
        while not self._parar.wait(self._intervalo):
            self._registrar_amostra()

    def _registrar_amostra(self) -> None:
        processos = []
        for processo in psutil.process_iter(["name"]):
            try:
                if "postgres" in (processo.info["name"] or "").lower():
                    processos.append(processo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        cpu_python = _cpu(self._processo_python)
        ram_python = _ram(self._processo_python)
        cpu_postgres = sum(_cpu(processo) for processo in processos)
        ram_postgres = sum(_ram(processo) for processo in processos)
        self._amostras.append({
            "cpu_python": cpu_python,
            "ram_python": float(ram_python),
            "cpu_postgres": cpu_postgres,
            "ram_postgres": float(ram_postgres),
            "cpu_total": cpu_python + cpu_postgres,
            "ram_total": float(ram_python + ram_postgres),
        })


def _cpu(processo: psutil.Process) -> float:
    try:
        return processo.cpu_percent(interval=None)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def _ram(processo: psutil.Process) -> int:
    try:
        return processo.memory_info().rss
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def obter_conexao(database_url: str | None = None):
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def ler_cabecalho(caminho: Path) -> list[str]:
    with caminho.open("r", encoding="latin-1", newline="") as arquivo:
        return next(csv.reader(arquivo, delimiter=";"))


def criar_tabela_raw(cursor, schema: str, tabela: str, colunas: list[str]) -> None:
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema)))
    cursor.execute(
        sql.SQL("DROP TABLE IF EXISTS {}.{};").format(
            sql.Identifier(schema), sql.Identifier(tabela)
        )
    )
    definicoes = [
        sql.SQL("{} TEXT").format(sql.Identifier(coluna)) for coluna in colunas
    ]
    cursor.execute(
        sql.SQL("CREATE TABLE {}.{} ({});").format(
            sql.Identifier(schema), sql.Identifier(tabela), sql.SQL(", ").join(definicoes)
        )
    )


def carregar_csv_raw(
    cursor,
    caminho: Path,
    schema: str,
    tabela: str,
    limite: int | None = None,
) -> tuple[int, float, float]:
    if limite is not None and limite < 0:
        raise ValueError("limite deve ser maior ou igual a zero.")

    inicio_leitura = time.perf_counter()
    colunas = ler_cabecalho(caminho)
    if limite is None:
        arquivo = caminho.open("r", encoding="latin-1", newline="")
        arquivo_temporario = None
    else:
        arquivo_temporario = tempfile.NamedTemporaryFile(
            mode="w+", encoding="utf-8", newline="", suffix=".csv"
        )
        escritor = csv.writer(arquivo_temporario, delimiter=";", lineterminator="\n")
        with caminho.open("r", encoding="latin-1", newline="") as origem:
            leitor = csv.reader(origem, delimiter=";")
            escritor.writerow(next(leitor))
            for numero, linha in enumerate(leitor):
                if numero >= limite:
                    break
                escritor.writerow(linha)
        arquivo_temporario.flush()
        arquivo_temporario.seek(0)
        arquivo = arquivo_temporario
    tempo_leitura = time.perf_counter() - inicio_leitura

    inicio_carga = time.perf_counter()
    try:
        cursor.copy_expert(
            sql.SQL("COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '')").format(
                sql.Identifier(schema),
                sql.Identifier(tabela),
                sql.SQL(", ").join(sql.Identifier(coluna) for coluna in colunas),
            ).as_string(cursor),
            arquivo,
        )
    finally:
        arquivo.close()
        if arquivo_temporario is not None:
            arquivo_temporario.close()

    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{};").format(
            sql.Identifier(schema), sql.Identifier(tabela)
        )
    )
    quantidade = int(cursor.fetchone()[0])
    return quantidade, tempo_leitura, time.perf_counter() - inicio_carga


def _case(coluna: str, mapa: dict[str, str], desconhecido: str = "Não informado") -> str:
    partes = [f"WHEN {coluna} = '{origem}' THEN '{destino}'" for origem, destino in mapa.items()]
    return "CASE " + " ".join(partes) + f" ELSE '{desconhecido}' END"


def transformar_participantes_sql(cursor, schema_raw: str, schema_final: str) -> None:
    raw = f'"{schema_raw}"."{TABELA_RAW_PARTICIPANTES}"'
    final = f'"{schema_final}"."{TABELA_FINAL_PARTICIPANTES}"'
    faixa_etaria = {
        str(i): nome for i, nome in enumerate([
            "Menor de 17 anos", "17 anos", "18 anos", "19 anos", "20 anos",
            "21 anos", "22 anos", "23 anos", "24 anos", "25 anos",
            "Entre 26 e 30 anos", "Entre 31 e 35 anos", "Entre 36 e 40 anos",
            "Entre 41 e 45 anos", "Entre 46 e 50 anos", "Entre 51 e 55 anos",
            "Entre 56 e 60 anos", "Entre 61 e 65 anos", "Entre 66 e 70 anos",
            "Maior de 70 anos",
        ], 1)
    }
    faixa_etaria_sql = _case('"TP_FAIXA_ETARIA"', faixa_etaria)
    sql_texto = f"""
    DROP TABLE IF EXISTS {final};
    CREATE SCHEMA IF NOT EXISTS "{schema_final}";
    CREATE TABLE {final} AS
    SELECT
        "NU_INSCRICAO"::text AS id_participante,
        {faixa_etaria_sql} AS faixa_etaria,
        CASE "TP_SEXO" WHEN 'M' THEN 'Masculino' WHEN 'F' THEN 'Feminino' ELSE 'Não informado' END AS sexo,
        CASE "TP_COR_RACA" WHEN '0' THEN 'Não declarado' WHEN '1' THEN 'Branca' WHEN '2' THEN 'Preta' WHEN '3' THEN 'Parda' WHEN '4' THEN 'Amarela' WHEN '5' THEN 'Indígena' WHEN '6' THEN 'Não dispõe da informação' ELSE 'Não informado' END AS cor_raca,
        CASE "TP_ST_CONCLUSAO" WHEN '1' THEN 'Já concluí o Ensino Médio' WHEN '2' THEN 'Estou cursando e concluirei o Ensino Médio em 2024' WHEN '3' THEN 'Estou cursando e concluirei o Ensino Médio após 2024' WHEN '4' THEN 'Não concluí e não estou cursando o Ensino Médio' ELSE 'Não informado' END AS situacao_conclusao,
        CASE "IN_TREINEIRO" WHEN '0' THEN FALSE WHEN '1' THEN TRUE ELSE NULL END AS treineiro,
        COALESCE(NULLIF("NO_MUNICIPIO_PROVA", ''), 'Não informado') AS municipio_prova,
        COALESCE(NULLIF("SG_UF_PROVA", ''), 'Não informado') AS uf_prova,
        CASE "Q007" WHEN 'A' THEN 'Nenhuma Renda' WHEN 'B' THEN 'Até R$ 1.412,00' WHEN 'C' THEN 'De R$ 1.412,01 até R$ 2.118,00' WHEN 'D' THEN 'De R$ 2.118,01 até R$ 2.824,00' WHEN 'E' THEN 'De R$ 2.824,01 até R$ 3.530,00' WHEN 'F' THEN 'De R$ 3.530,01 até R$ 4.236,00' WHEN 'G' THEN 'De R$ 4.236,01 até R$ 5.648,00' WHEN 'H' THEN 'De R$ 5.648,01 até R$ 7.060,00' WHEN 'I' THEN 'De R$ 7.060,01 até R$ 8.472,00' WHEN 'J' THEN 'De R$ 8.472,01 até R$ 9.884,00' WHEN 'K' THEN 'De R$ 9.884,01 até R$ 11.296,00' WHEN 'L' THEN 'De R$ 11.296,01 até R$ 12.708,00' WHEN 'M' THEN 'De R$ 12.708,01 até R$ 14.120,00' WHEN 'N' THEN 'De R$ 14.120,01 até R$ 16.944,00' WHEN 'O' THEN 'De R$ 16.944,01 até R$ 21.180,00' WHEN 'P' THEN 'De R$ 21.180,01 até R$ 28.240,00' WHEN 'Q' THEN 'Acima de R$ 28.240,00' ELSE 'Não informado' END AS faixa_renda,
        CASE "Q020" WHEN 'A' THEN FALSE WHEN 'B' THEN TRUE ELSE NULL END AS possui_internet,
        CASE "Q023" WHEN 'A' THEN 'Somente em escola pública' WHEN 'B' THEN 'Parte em escola pública e parte em escola privada sem bolsa integral'
             WHEN 'C' THEN 'Parte em escola pública e parte em escola privada com bolsa integral' WHEN 'D' THEN 'Somente em escola privada sem bolsa integral'
             WHEN 'E' THEN 'Somente em escola privada com bolsa integral' WHEN 'F' THEN 'Não frequentei escola de Ensino Médio' ELSE 'Não informado' END AS tipo_escola_em,
        CASE "SG_UF_PROVA" WHEN 'AC' THEN 'Norte' WHEN 'AP' THEN 'Norte' WHEN 'AM' THEN 'Norte' WHEN 'PA' THEN 'Norte' WHEN 'RO' THEN 'Norte' WHEN 'RR' THEN 'Norte' WHEN 'TO' THEN 'Norte'
             WHEN 'AL' THEN 'Nordeste' WHEN 'BA' THEN 'Nordeste' WHEN 'CE' THEN 'Nordeste' WHEN 'MA' THEN 'Nordeste' WHEN 'PB' THEN 'Nordeste' WHEN 'PE' THEN 'Nordeste' WHEN 'PI' THEN 'Nordeste' WHEN 'RN' THEN 'Nordeste' WHEN 'SE' THEN 'Nordeste'
             WHEN 'DF' THEN 'Centro-Oeste' WHEN 'GO' THEN 'Centro-Oeste' WHEN 'MT' THEN 'Centro-Oeste' WHEN 'MS' THEN 'Centro-Oeste'
             WHEN 'ES' THEN 'Sudeste' WHEN 'MG' THEN 'Sudeste' WHEN 'RJ' THEN 'Sudeste' WHEN 'SP' THEN 'Sudeste'
             WHEN 'PR' THEN 'Sul' WHEN 'RS' THEN 'Sul' WHEN 'SC' THEN 'Sul' ELSE 'Não informado' END AS regiao_prova
    FROM {raw};
    """
    cursor.execute(sql_texto)


def transformar_resultados_sql(cursor, schema_raw: str, schema_final: str) -> None:
    raw = f'"{schema_raw}"."{TABELA_RAW_RESULTADOS}"'
    final = f'"{schema_final}"."{TABELA_FINAL_RESULTADOS}"'
    sql_texto = f"""
    DROP TABLE IF EXISTS {final};
    CREATE SCHEMA IF NOT EXISTS "{schema_final}";
    CREATE TABLE {final} AS
    SELECT
        "NU_SEQUENCIAL"::text AS id_resultado,
        COALESCE(NULLIF("NO_MUNICIPIO_ESC", ''), 'Não informado') AS municipio_escola,
        COALESCE(NULLIF("SG_UF_ESC", ''), 'Não informado') AS uf_escola,
        CASE "TP_DEPENDENCIA_ADM_ESC" WHEN '1' THEN 'Federal' WHEN '2' THEN 'Estadual' WHEN '3' THEN 'Municipal' WHEN '4' THEN 'Privada' ELSE 'Não informado' END AS dependencia_escola,
        CASE "TP_LOCALIZACAO_ESC" WHEN '1' THEN 'Urbana' WHEN '2' THEN 'Rural' ELSE 'Não informado' END AS localizacao_escola,
        CASE "TP_PRESENCA_CN" WHEN '0' THEN 'Faltou à prova' WHEN '1' THEN 'Presente na prova' WHEN '2' THEN 'Eliminado na prova' ELSE 'Não informado' END AS presenca_cn,
        CASE "TP_PRESENCA_CH" WHEN '0' THEN 'Faltou à prova' WHEN '1' THEN 'Presente na prova' WHEN '2' THEN 'Eliminado na prova' ELSE 'Não informado' END AS presenca_ch,
        CASE "TP_PRESENCA_LC" WHEN '0' THEN 'Faltou à prova' WHEN '1' THEN 'Presente na prova' WHEN '2' THEN 'Eliminado na prova' ELSE 'Não informado' END AS presenca_lc,
        CASE "TP_PRESENCA_MT" WHEN '0' THEN 'Faltou à prova' WHEN '1' THEN 'Presente na prova' WHEN '2' THEN 'Eliminado na prova' ELSE 'Não informado' END AS presenca_mt,
        CASE WHEN "TP_STATUS_REDACAO" IS NOT NULL THEN 'Presente na prova' ELSE 'Faltou à prova' END AS presenca_redacao,
        NULLIF("NU_NOTA_CN", '')::numeric AS nota_cn,
        NULLIF("NU_NOTA_CH", '')::numeric AS nota_ch,
        NULLIF("NU_NOTA_LC", '')::numeric AS nota_lc,
        NULLIF("NU_NOTA_MT", '')::numeric AS nota_mt,
        NULLIF("NU_NOTA_REDACAO", '')::numeric AS nota_redacao,
        CASE WHEN "SG_UF_ESC" IN ('AC','AP','AM','PA','RO','RR','TO') THEN 'Norte'
             WHEN "SG_UF_ESC" IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
             WHEN "SG_UF_ESC" IN ('DF','GO','MT','MS') THEN 'Centro-Oeste'
             WHEN "SG_UF_ESC" IN ('ES','MG','RJ','SP') THEN 'Sudeste'
             WHEN "SG_UF_ESC" IN ('PR','RS','SC') THEN 'Sul' ELSE 'Não informado' END AS regiao_escola,
        CASE WHEN media_objetiva_bruta IS NULL THEN NULL ELSE
             (
                 CASE
                     WHEN media_objetiva_bruta * 100 - TRUNC(media_objetiva_bruta * 100) < 0.5
                         THEN TRUNC(media_objetiva_bruta * 100)
                     WHEN media_objetiva_bruta * 100 - TRUNC(media_objetiva_bruta * 100) > 0.5
                         THEN TRUNC(media_objetiva_bruta * 100) + 1
                     WHEN MOD(TRUNC(media_objetiva_bruta * 100), 2) = 0
                         THEN TRUNC(media_objetiva_bruta * 100)
                     ELSE TRUNC(media_objetiva_bruta * 100) + 1
                 END
             ) / 100
        END AS nota_media_objetivas,
        ("TP_PRESENCA_CN" = '1' AND "TP_PRESENCA_CH" = '1' AND "TP_PRESENCA_LC" = '1' AND "TP_PRESENCA_MT" = '1' AND "TP_STATUS_REDACAO" IS NOT NULL) AS presente_completo
    FROM (
        SELECT r.*,
               CASE
                   WHEN NULLIF("NU_NOTA_CN", '') IS NOT NULL
                    AND NULLIF("NU_NOTA_CH", '') IS NOT NULL
                    AND NULLIF("NU_NOTA_LC", '') IS NOT NULL
                    AND NULLIF("NU_NOTA_MT", '') IS NOT NULL
                   THEN (
                       NULLIF("NU_NOTA_CN", '')::numeric
                       + NULLIF("NU_NOTA_CH", '')::numeric
                       + NULLIF("NU_NOTA_LC", '')::numeric
                       + NULLIF("NU_NOTA_MT", '')::numeric
                   ) / 4
               END AS media_objetiva_bruta
        FROM {raw} r
    ) origem;
    """
    cursor.execute(sql_texto)


def executar_elt(
    database_url: str | None,
    limite: int | None,
    schema_raw: str = SCHEMA_RAW,
    schema_final: str = SCHEMA_FINAL,
) -> TemposELT:
    inicio_total = time.perf_counter()
    with obter_conexao(database_url) as conexao:
        with conexao.cursor() as cursor:
            inicio_carga_raw = time.perf_counter()
            inicio = time.perf_counter()
            criar_tabela_raw(cursor, schema_raw, TABELA_RAW_PARTICIPANTES, ler_cabecalho(CAMINHO_PARTICIPANTES))
            criar_tabela_raw(cursor, schema_raw, TABELA_RAW_RESULTADOS, ler_cabecalho(CAMINHO_RESULTADOS))
            _, leitura_participantes, _ = carregar_csv_raw(
                cursor, CAMINHO_PARTICIPANTES, schema_raw,
                TABELA_RAW_PARTICIPANTES, limite,
            )
            _, leitura_resultados, _ = carregar_csv_raw(
                cursor, CAMINHO_RESULTADOS, schema_raw,
                TABELA_RAW_RESULTADOS, limite,
            )
            conexao.commit()
            tempo_leitura = leitura_participantes + leitura_resultados
            tempo_raw = time.perf_counter() - inicio_carga_raw

            inicio = time.perf_counter()
            transformar_participantes_sql(cursor, schema_raw, schema_final)
            transformar_resultados_sql(cursor, schema_raw, schema_final)
            conexao.commit()
            tempo_sql = time.perf_counter() - inicio

            inicio = time.perf_counter()
            cursor.execute(f'SELECT COUNT(*) FROM "{schema_final}"."{TABELA_FINAL_PARTICIPANTES}"')
            linhas_participantes = int(cursor.fetchone()[0])
            cursor.execute(f'SELECT COUNT(*) FROM "{schema_final}"."{TABELA_FINAL_RESULTADOS}"')
            linhas_resultados = int(cursor.fetchone()[0])
            conexao.commit()
            tempo_validacao = time.perf_counter() - inicio

    return TemposELT(
        tempo_leitura, tempo_raw, tempo_sql, tempo_validacao, time.perf_counter() - inicio_total,
        linhas_participantes, linhas_resultados,
    )


def salvar_benchmark(resultado: ResultadoBenchmark, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = list(resultado.__dataclass_fields__)
    existe = caminho.exists()
    with caminho.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        if not existe:
            escritor.writeheader()
        escritor.writerow({campo: getattr(resultado, campo) for campo in campos})


def finalizar_benchmark(monitor, inicio_total, tempos, limite, rodada, aquecimento, caminho_csv, caminho_resumo) -> None:
    recursos = monitor.parar()
    quantidade = tempos.linhas_participantes + tempos.linhas_resultados
    tempo_total = time.perf_counter() - inicio_total
    resultado = ResultadoBenchmark(
        dataset="enem", volume_configurado=limite, arquitetura="elt",
        rodada=rodada, aquecimento=aquecimento, tempo_leitura=tempos.leitura,
        tempo_transformacao=tempos.transformacao_sql, tempo_validacao=tempos.validacao,
        tempo_carga=tempos.carga_raw, tempo_total=tempo_total,
        throughput=quantidade / tempo_total if tempo_total else 0.0,
        quantidade_registros=quantidade, linhas_participantes=tempos.linhas_participantes,
        linhas_resultados=tempos.linhas_resultados,
        timestamp=datetime.now().isoformat(timespec="seconds"), **recursos,
    )
    salvar_benchmark(resultado, caminho_csv)
    caminho_resumo.parent.mkdir(parents=True, exist_ok=True)
    with caminho_resumo.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"Benchmark ELT ENEM | volume={limite or 'todos'} | total={tempo_total:.3f}s | registros={quantidade} | throughput={resultado.throughput:.2f}\n")
    print(f"Resultado do benchmark salvo em: {caminho_csv}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Esboço do pipeline ELT do ENEM 2024")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL"))
    parser.add_argument("--schema-raw", default=os.getenv("POSTGRES_SCHEMA_RAW", SCHEMA_RAW))
    parser.add_argument("--schema-final", default=os.getenv("POSTGRES_SCHEMA_ELT", SCHEMA_FINAL))
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--benchmark-output", type=Path, default=BASE_DIR / "data" / "benchmark" / "enem_elt_resultados.csv")
    parser.add_argument("--benchmark-summary-output", type=Path, default=BASE_DIR / "data" / "benchmark" / "enem_elt_resumo.txt")
    parser.add_argument("--rodada", type=int, default=None)
    parser.add_argument("--aquecimento", action="store_true")
    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="Quantidade máxima de linhas lidas de cada arquivo; use 0 para todas.",
    )
    args = parser.parse_args()
    inicio_total = time.perf_counter()
    monitor = MonitorRecursos()
    if args.benchmark:
        monitor.iniciar()
    limite = None if args.limite == 0 else args.limite
    tempos = executar_elt(args.database_url, limite, args.schema_raw, args.schema_final)
    print(f"Leitura/preparacao: {tempos.leitura:.3f}s")
    print(f"Carga RAW: {tempos.carga_raw:.3f}s")
    print(f"Transformação SQL: {tempos.transformacao_sql:.3f}s")
    print(f"Validação: {tempos.validacao:.3f}s")
    print(f"Total: {tempos.total:.3f}s")
    if args.benchmark:
        finalizar_benchmark(
            monitor, inicio_total, tempos, limite, args.rodada, args.aquecimento,
            args.benchmark_output, args.benchmark_summary_output,
        )


if __name__ == "__main__":
    main()
