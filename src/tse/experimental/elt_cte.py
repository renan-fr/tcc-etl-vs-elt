from __future__ import annotations

import argparse
import csv
from datetime import datetime
import os
from pathlib import Path
import sys
import time

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
try:
    from src.benchmark_paths import diretorio_saida_obrigatorio
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from benchmark_paths import diretorio_saida_obrigatorio


BASE_DIR = Path(__file__).resolve().parents[3]
TSE_DIR = BASE_DIR / "src" / "tse"
if str(TSE_DIR) not in sys.path:
    sys.path.insert(0, str(TSE_DIR))

import elt as oficial  # noqa: E402
from contrato import CHAVE_FINAL, CONTRATO_FINAL  # noqa: E402


SCHEMA_RAW = "tse_elt_cte_raw_exp"
SCHEMA_FINAL = "tse_elt_cte_final_exp"
TABELA_FINAL = oficial.TABELA_FINAL


def ctes_transformacao(schema_raw: str) -> sql.Composed:
    """CTEs equivalentes as tres tabelas STAGING do ELT oficial."""
    return sql.SQL(
        """
        WITH munzona AS (
            SELECT
                "ANO_ELEICAO"::integer AS ano_eleicao,
                "CD_ELEICAO"::integer AS cd_eleicao,
                "NR_TURNO"::integer AS nr_turno,
                "SG_UF" AS sg_uf,
                LPAD(TRIM("CD_MUNICIPIO"), 5, '0') AS cd_municipio,
                "NM_MUNICIPIO" AS nm_municipio,
                "NR_ZONA"::integer AS nr_zona,
                "CD_CARGO"::integer AS cd_cargo,
                "DS_CARGO" AS ds_cargo,
                "QT_APTOS"::bigint AS qt_aptos,
                "QT_COMPARECIMENTO"::bigint AS qt_comparecimento,
                "QT_ABSTENCOES"::bigint AS qt_abstencoes,
                "QT_TOTAL_VOTOS_VALIDOS"::bigint AS qt_total_votos_validos,
                "QT_VOTOS_NOMINAIS_VALIDOS"::bigint AS qt_votos_nominais_validos,
                "QT_TOTAL_VOTOS_LEG_VALIDOS"::bigint AS qt_total_votos_leg_validos,
                "QT_VOTOS_BRANCOS"::bigint AS qt_votos_brancos,
                "QT_TOTAL_VOTOS_NULOS"::bigint AS qt_total_votos_nulos,
                "QT_TOTAL_VOTOS_ANULADOS"::bigint AS qt_total_votos_anulados
            FROM {raw}.detalhe_votacao_munzona
        ), secao AS (
            SELECT
                "ANO_ELEICAO"::integer AS ano_eleicao,
                "CD_ELEICAO"::integer AS cd_eleicao,
                "NR_TURNO"::integer AS nr_turno,
                LPAD(TRIM("CD_MUNICIPIO"), 5, '0') AS cd_municipio,
                "NR_ZONA"::integer AS nr_zona,
                "CD_CARGO"::integer AS cd_cargo,
                COUNT(DISTINCT "NR_SECAO"::bigint)::bigint AS qt_secoes_processadas,
                SUM("QT_COMPARECIMENTO"::bigint)::bigint AS qt_comparecimento_secao,
                SUM("QT_ABSTENCOES"::bigint)::bigint AS qt_abstencoes_secao,
                SUM("QT_VOTOS_NOMINAIS"::bigint)::bigint AS qt_votos_nominais_secao,
                SUM("QT_VOTOS_BRANCOS"::bigint)::bigint AS qt_votos_brancos_secao,
                SUM("QT_VOTOS_NULOS"::bigint)::bigint AS qt_votos_nulos_secao,
                SUM("QT_VOTOS_LEGENDA"::bigint)::bigint AS qt_votos_legenda_secao
            FROM {raw}.detalhe_votacao_secao
            GROUP BY 1, 2, 3, 4, 5, 6
        ), candidato_tipado AS (
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
        ), candidato_totais AS (
            SELECT
                ano_eleicao, cd_eleicao, nr_turno, cd_municipio,
                nr_zona, cd_cargo,
                COUNT(DISTINCT sq_candidato)::bigint AS qt_candidatos,
                SUM(votos)::bigint AS qt_votos_candidatos
            FROM candidato_tipado
            GROUP BY 1, 2, 3, 4, 5, 6
        ), candidato_ranking AS (
            SELECT
                candidato_tipado.*,
                ROW_NUMBER() OVER (
                    PARTITION BY ano_eleicao, cd_eleicao, nr_turno,
                                 cd_municipio, nr_zona, cd_cargo
                    ORDER BY votos DESC, sq_candidato ASC
                ) AS posicao
            FROM candidato_tipado
        ), candidato AS (
            SELECT
                t.ano_eleicao, t.cd_eleicao, t.nr_turno, t.cd_municipio,
                t.nr_zona, t.cd_cargo, t.qt_candidatos, t.qt_votos_candidatos,
                r.nr_candidato AS nr_candidato_mais_votado,
                r.nm_candidato AS nm_candidato_mais_votado,
                r.sg_partido AS sg_partido_candidato_mais_votado,
                r.votos AS qt_votos_candidato_mais_votado
            FROM candidato_totais t
            JOIN candidato_ranking r
              ON r.ano_eleicao = t.ano_eleicao
             AND r.cd_eleicao = t.cd_eleicao
             AND r.nr_turno = t.nr_turno
             AND r.cd_municipio = t.cd_municipio
             AND r.nr_zona = t.nr_zona
             AND r.cd_cargo = t.cd_cargo
             AND r.posicao = 1
        )
        """
    ).format(raw=sql.Identifier(schema_raw))


def selecao_final() -> sql.SQL:
    return sql.SQL(
        """
        SELECT
            m.ano_eleicao, m.cd_eleicao, m.nr_turno, m.sg_uf,
            m.cd_municipio, m.nm_municipio, m.nr_zona, m.cd_cargo,
            m.ds_cargo, m.qt_aptos, m.qt_comparecimento, m.qt_abstencoes,
            m.qt_total_votos_validos, m.qt_votos_nominais_validos,
            m.qt_total_votos_leg_validos, m.qt_votos_brancos,
            m.qt_total_votos_nulos, m.qt_total_votos_anulados,
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
            ROUND(m.qt_comparecimento::numeric / NULLIF(m.qt_aptos, 0), 6)::numeric(9,6),
            ROUND(m.qt_abstencoes::numeric / NULLIF(m.qt_aptos, 0), 6)::numeric(9,6),
            ROUND(
                c.qt_votos_candidato_mais_votado::numeric
                / NULLIF(c.qt_votos_candidatos, 0), 6
            )::numeric(9,6)
        FROM munzona m
        LEFT JOIN secao s
          USING (ano_eleicao, cd_eleicao, nr_turno, cd_municipio, nr_zona, cd_cargo)
        LEFT JOIN candidato c
          USING (ano_eleicao, cd_eleicao, nr_turno, cd_municipio, nr_zona, cd_cargo)
        """
    )


def _validar_numericas_raw(cursor, schema_raw: str) -> None:
    tabelas = {
        oficial.TABELA_RAW_MUNZONA: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
            "QT_TOTAL_VOTOS_VALIDOS", "QT_VOTOS_NOMINAIS_VALIDOS",
            "QT_TOTAL_VOTOS_LEG_VALIDOS", "QT_VOTOS_BRANCOS",
            "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_ANULADOS",
        ],
        oficial.TABELA_RAW_SECAO: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "NR_SECAO", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
            "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS",
            "QT_VOTOS_LEGENDA",
        ],
        oficial.TABELA_RAW_CANDIDATO: [
            "ANO_ELEICAO", "CD_ELEICAO", "NR_TURNO", "NR_ZONA", "CD_CARGO",
            "SQ_CANDIDATO", "QT_VOTOS_NOMINAIS_VALIDOS",
        ],
    }
    for tabela, colunas in tabelas.items():
        condicao = sql.SQL(" OR ").join(
            sql.SQL("{} IS NULL").format(sql.Identifier(coluna)) for coluna in colunas
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


def _validar_unicidade_ctes(cursor, schema_raw: str) -> None:
    chaves = sql.SQL(", ").join(sql.Identifier(coluna) for coluna in CHAVE_FINAL)
    subconsultas = []
    for tabela in ("munzona", "secao", "candidato"):
        subconsultas.append(
            sql.SQL(
                "(SELECT COALESCE(SUM(quantidade), 0) FROM "
                "(SELECT COUNT(*) AS quantidade FROM {} GROUP BY {} "
                "HAVING COUNT(*) > 1) d)"
            ).format(sql.Identifier(tabela), chaves)
        )
    cursor.execute(
        ctes_transformacao(schema_raw)
        + sql.SQL(" SELECT {}, {}, {}").format(*subconsultas)
    )
    for tabela, duplicadas in zip(
        ("munzona", "secao", "candidato"), cursor.fetchone(), strict=True
    ):
        if duplicadas:
            raise ValueError(
                f"CTE {tabela} possui {int(duplicadas)} linhas em chaves logicas duplicadas."
            )


def construir_produto(cursor, schema_raw: str, schema_final: str) -> int:
    _validar_numericas_raw(cursor, schema_raw)
    _validar_unicidade_ctes(cursor, schema_raw)
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
    destino = sql.SQL("{}.{}").format(
        sql.Identifier(schema_final), sql.Identifier(TABELA_FINAL)
    )
    cursor.execute(
        ctes_transformacao(schema_raw)
        + sql.SQL(" INSERT INTO {} ").format(destino)
        + selecao_final()
    )
    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema_raw), sql.Identifier(oficial.TABELA_RAW_MUNZONA)
        )
    )
    linhas_base = int(cursor.fetchone()[0])
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(destino))
    linhas_produto = int(cursor.fetchone()[0])
    if linhas_produto != linhas_base:
        raise ValueError(
            "Os joins alteraram a quantidade de linhas: "
            f"munzona={linhas_base}, final={linhas_produto}."
        )
    return linhas_produto


def _escalar(cursor, consulta: sql.Composed) -> int:
    cursor.execute(consulta)
    return int(cursor.fetchone()[0])


def validar_produto(cursor, schema_raw: str, schema_final: str) -> oficial.ResultadoValidacao:
    """Replica as validacoes oficiais, consultando as relacoes derivadas via CTE."""
    erros: list[str] = []
    alertas: list[str] = []
    final = sql.SQL("{}.{}").format(
        sql.Identifier(schema_final), sql.Identifier(TABELA_FINAL)
    )
    cursor.execute(
        """
        SELECT atributo.attname,
               pg_catalog.format_type(atributo.atttypid, atributo.atttypmod),
               atributo.attnotnull
        FROM pg_catalog.pg_attribute atributo
        JOIN pg_catalog.pg_class tabela ON tabela.oid = atributo.attrelid
        JOIN pg_catalog.pg_namespace schema ON schema.oid = tabela.relnamespace
        WHERE schema.nspname = %s AND tabela.relname = %s
          AND atributo.attnum > 0 AND NOT atributo.attisdropped
        ORDER BY atributo.attnum
        """,
        (schema_final, TABELA_FINAL),
    )
    esperada = [
        (nome, tipo.replace(" NOT NULL", "").lower(), tipo.endswith(" NOT NULL"))
        for nome, tipo in CONTRATO_FINAL
    ]
    if cursor.fetchall() != esperada:
        erros.append("Estrutura, ordem, tipos ou nulabilidade divergem do contrato final.")
        return oficial.ResultadoValidacao(TABELA_FINAL, erros, alertas)

    condicao_nula = sql.SQL(" OR ").join(
        sql.SQL("{} IS NULL").format(sql.Identifier(c)) for c in CHAVE_FINAL
    )
    nulos = _escalar(
        cursor, sql.SQL("SELECT COUNT(*) FROM {} WHERE {}").format(final, condicao_nula)
    )
    if nulos:
        erros.append(f"A chave final possui {nulos} linhas com valores nulos.")
    duplicadas = oficial._contar_duplicadas(cursor, schema_final, TABELA_FINAL)
    if duplicadas:
        erros.append(f"A chave final possui {duplicadas} linhas duplicadas.")

    nulos_descricoes = _escalar(
        cursor,
        sql.SQL(
            "SELECT COUNT(*) FROM {} WHERE sg_uf IS NULL OR nm_municipio IS NULL "
            "OR ds_cargo IS NULL"
        ).format(final),
    )
    if nulos_descricoes:
        erros.append(f"Identificacoes descritivas possuem {nulos_descricoes} linhas nulas.")
    for coluna, tipo in CONTRATO_FINAL:
        if not tipo.startswith("BIGINT"):
            continue
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
    inconsistencias = _escalar(
        cursor,
        sql.SQL(
            """SELECT COUNT(*) FROM {}
            WHERE (qt_candidatos = 0 AND (
                       nr_candidato_mais_votado IS NOT NULL
                    OR nm_candidato_mais_votado IS NOT NULL
                    OR sg_partido_candidato_mais_votado IS NOT NULL
                    OR qt_votos_candidato_mais_votado IS NOT NULL))
               OR (qt_candidatos > 0 AND (
                       nr_candidato_mais_votado IS NULL
                    OR nm_candidato_mais_votado IS NULL
                    OR sg_partido_candidato_mais_votado IS NULL
                    OR qt_votos_candidato_mais_votado IS NULL))"""
        ).format(final),
    )
    if inconsistencias:
        erros.append("Campos do candidato mais votado possuem nulos inconsistentes.")

    for mensagem, condicao in (
        ("comparecimento + abstencoes diferente de aptos", "qt_comparecimento + qt_abstencoes <> qt_aptos"),
        ("diferenca entre votos validos de candidatos e votos nominais validos de munzona", "qt_votos_candidatos <> qt_votos_nominais_validos"),
    ):
        quantidade = _escalar(
            cursor, sql.SQL("SELECT COUNT(*) FROM {} WHERE " + condicao).format(final)
        )
        if quantidade:
            alertas.append(f"{quantidade} chaves possuem {mensagem}.")

    for percentual, numerador, denominador in (
        ("pct_comparecimento", "qt_comparecimento", "qt_aptos"),
        ("pct_abstencao", "qt_abstencoes", "qt_aptos"),
        ("pct_votos_candidato_mais_votado", "qt_votos_candidato_mais_votado", "qt_votos_candidatos"),
    ):
        divergentes = _escalar(
            cursor,
            sql.SQL(
                "SELECT COUNT(*) FROM {} WHERE {} IS DISTINCT FROM "
                "ROUND({}::numeric / NULLIF({}, 0), 6)::numeric(9,6)"
            ).format(
                final, sql.Identifier(percentual), sql.Identifier(numerador),
                sql.Identifier(denominador)
            ),
        )
        if divergentes:
            erros.append(f"{percentual} possui {divergentes} valores inconsistentes.")

    for nome, municipal, secao in (
        ("comparecimento", "qt_comparecimento", "qt_comparecimento_secao"),
        ("abstencoes", "qt_abstencoes", "qt_abstencoes_secao"),
        ("votos nominais", "qt_votos_nominais_validos", "qt_votos_nominais_secao"),
        ("votos brancos", "qt_votos_brancos", "qt_votos_brancos_secao"),
        ("votos nulos", "qt_total_votos_nulos", "qt_votos_nulos_secao"),
        ("votos de legenda", "qt_total_votos_leg_validos", "qt_votos_legenda_secao"),
    ):
        divergentes = _escalar(
            cursor,
            sql.SQL("SELECT COUNT(*) FROM {} WHERE {} <> {}").format(
                final, sql.Identifier(municipal), sql.Identifier(secao)
            ),
        )
        if divergentes:
            alertas.append(
                f"{divergentes} chaves possuem diferenca em {nome} entre munzona e secoes."
            )

    condicoes = sql.SQL(" AND ").join(
        sql.SQL("m.{} = a.{}").format(sql.Identifier(c), sql.Identifier(c))
        for c in CHAVE_FINAL
    )
    cursor.execute(
        ctes_transformacao(schema_raw)
        + sql.SQL(
            " SELECT "
            "(SELECT COUNT(*) FROM secao a WHERE NOT EXISTS "
            " (SELECT 1 FROM munzona m WHERE {})), "
            "(SELECT COUNT(*) FROM candidato a WHERE NOT EXISTS "
            " (SELECT 1 FROM munzona m WHERE {}))"
        ).format(condicoes, condicoes)
    )
    for nome, orfas in zip(("secao", "candidato"), cursor.fetchone(), strict=True):
        if orfas:
            alertas.append(
                f"{int(orfas)} chaves de {nome} nao possuem correspondencia em munzona."
            )
    return oficial.ResultadoValidacao(TABELA_FINAL, erros, alertas)


def executar(args: argparse.Namespace) -> None:
    inicio_total = time.perf_counter()
    monitor = oficial.MonitorRecursos()
    if args.benchmark:
        monitor.iniciar()
    inicio_manifesto = time.perf_counter()
    try:
        selecao = oficial.ler_selecao_manifesto(args.manifesto_chaves)
    except (OSError, ValueError, csv.Error) as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(str(erro)) from erro
    tempo_manifesto = time.perf_counter() - inicio_manifesto
    try:
        conexao_postgres = oficial.obter_conexao_postgres(args.database_url)
        with oficial._conectar_postgres(conexao_postgres) as conexao:
            with conexao.cursor() as cursor:
                carga_raw = oficial.carregar_raw(cursor, args.schema_raw, selecao)
                inicio_commit = time.perf_counter()
                conexao.commit()
                tempo_commit = time.perf_counter() - inicio_commit
                inicio_sql = time.perf_counter()
                linhas_processadas = construir_produto(
                    cursor, args.schema_raw, args.schema_final
                )
                conexao.commit()
                tempo_transformacao = time.perf_counter() - inicio_sql
                validacao = None
                tempo_validacao = None
                if not args.sem_validacao:
                    inicio_validacao = time.perf_counter()
                    validacao = validar_produto(cursor, args.schema_raw, args.schema_final)
                    tempo_validacao = time.perf_counter() - inicio_validacao
    except (psycopg2.Error, UnicodeError, ValueError, OSError, csv.Error) as erro:
        if args.benchmark:
            monitor.parar()
        raise SystemExit(f"Falha no ELT experimental com CTEs: {erro}") from erro

    if validacao is not None:
        oficial._imprimir_validacao(validacao)
        if not validacao.valido:
            if args.benchmark:
                monitor.parar()
            raise SystemExit("Pipeline interrompido por erros criticos de validacao.")
    else:
        print("Validacao interna ignorada no modo de desempenho.")
    tempo_leitura = tempo_manifesto + carga_raw.tempo_leitura
    tempo_carga = carga_raw.tempo_carga + tempo_commit
    tempo_total = time.perf_counter() - inicio_total
    print(f"Munzona: {carga_raw.linhas_munzona} linhas")
    print(f"Secao: {carga_raw.linhas_secao} linhas")
    print(f"Candidato: {carga_raw.linhas_candidato} linhas")
    print(f"Produto final: {linhas_processadas} linhas")
    print(f"Carga RAW: {tempo_carga:.3f}s")
    print(f"Transformacao SQL: {tempo_transformacao:.3f}s")
    print("Validacao: nao executada" if tempo_validacao is None else f"Validacao: {tempo_validacao:.3f}s")
    print(f"Total: {tempo_total:.3f}s")
    if not args.benchmark:
        return

    recursos = monitor.parar()
    quantidade = (
        carga_raw.linhas_munzona + carga_raw.linhas_secao + carga_raw.linhas_candidato
    )
    resultado = oficial.ResultadoBenchmark(
        dataset="tse",
        volume_configurado=args.limite,
        arquitetura="elt_cte",
        rodada=args.rodada,
        tempo_leitura=tempo_leitura,
        tempo_transformacao=tempo_transformacao,
        tempo_carga=tempo_carga,
        tempo_total=tempo_total,
        throughput=quantidade / tempo_total if tempo_total else 0.0,
        quantidade_registros=quantidade,
        linhas_munzona=carga_raw.linhas_munzona,
        linhas_secao=carga_raw.linhas_secao,
        linhas_candidato=carga_raw.linhas_candidato,
        linhas_processadas=linhas_processadas,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        **recursos,
    )
    print(
        f"Benchmark ELT CTE | volume={args.limite} | total={tempo_total:.3f}s | "
        f"registros={quantidade} | throughput={resultado.throughput:.2f} registros/s"
    )
    if args.benchmark_output:
        oficial._salvar_benchmark(resultado, args.benchmark_output)
        print(f"Resultado salvo em: {args.benchmark_output}")


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(description="ELT TSE experimental com CTEs")
    parser.add_argument("--limite", type=int, required=True)
    parser.add_argument(
        "--modo", choices=["certificar", "aquecimento", "medir"], required=True
    )
    parser.add_argument("--rodada", type=int)
    parser.add_argument("--schema-raw", default=SCHEMA_RAW)
    parser.add_argument("--schema-final", default=SCHEMA_FINAL)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--benchmark-output", type=Path, default=None)
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite deve ser maior que zero.")
    if args.modo == "medir" and args.rodada is None:
        parser.error("--rodada e obrigatoria no modo medir.")
    if args.modo != "medir" and args.rodada is not None:
        parser.error("--rodada so pode ser usada no modo medir.")
    args.manifesto_chaves = (
        BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos"
        / f"chaves_{args.limite}.csv"
    )
    if not args.manifesto_chaves.is_file():
        parser.error(f"Manifesto ausente: {args.manifesto_chaves}")
    args.benchmark = args.modo != "certificar"
    args.sem_validacao = args.modo != "certificar"
    if args.modo == "medir":
        args.benchmark_output = (
            diretorio_saida_obrigatorio() / "experimental_cte" / "tse_elt_cte.csv"
        )
    if args.modo != "medir":
        args.benchmark_output = None
    executar(args)


if __name__ == "__main__":
    main()
