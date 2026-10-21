from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


TABELA = "resultado_municipio_cargo"


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


def obter_estrutura(cursor, schema: str) -> list[tuple[str, str, str, int | None, int | None]]:
    cursor.execute(
        """
        SELECT
            column_name,
            data_type,
            is_nullable,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, TABELA),
    )
    return cursor.fetchall()


def contar_linhas(cursor, schema: str) -> int:
    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema), sql.Identifier(TABELA)
        )
    )
    return int(cursor.fetchone()[0])


def contar_diferencas(cursor, schema_a: str, schema_b: str) -> tuple[int, int]:
    tabela_a = sql.SQL("{}.{}").format(
        sql.Identifier(schema_a), sql.Identifier(TABELA)
    )
    tabela_b = sql.SQL("{}.{}").format(
        sql.Identifier(schema_b), sql.Identifier(TABELA)
    )
    cursor.execute(
        sql.SQL(
            "SELECT COUNT(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d"
        ).format(tabela_a, tabela_b)
    )
    apenas_a = int(cursor.fetchone()[0])
    cursor.execute(
        sql.SQL(
            "SELECT COUNT(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d"
        ).format(tabela_b, tabela_a)
    )
    apenas_b = int(cursor.fetchone()[0])
    return apenas_a, apenas_b


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Compara os produtos finais ETL e ELT do TSE."
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument(
        "--schema-etl",
        default=os.getenv("POSTGRES_SCHEMA_TSE_ETL_FINAL", "tse_etl_final"),
    )
    parser.add_argument(
        "--schema-elt",
        default=os.getenv("POSTGRES_SCHEMA_TSE_ELT_FINAL", "tse_elt_final"),
    )
    args = parser.parse_args()

    try:
        with obter_conexao(args.database_url) as conexao:
            with conexao.cursor() as cursor:
                estrutura_etl = obter_estrutura(cursor, args.schema_etl)
                estrutura_elt = obter_estrutura(cursor, args.schema_elt)
                if not estrutura_etl or not estrutura_elt:
                    raise SystemExit(
                        "Uma ou ambas as tabelas finais nao existem nos schemas informados."
                    )

                estrutura_igual = estrutura_etl == estrutura_elt
                linhas_etl = contar_linhas(cursor, args.schema_etl)
                linhas_elt = contar_linhas(cursor, args.schema_elt)
                apenas_etl, apenas_elt = contar_diferencas(
                    cursor, args.schema_etl, args.schema_elt
                )
    except psycopg2.Error as erro:
        raise SystemExit(f"Falha ao comparar ETL e ELT: {erro}") from erro

    equivalente = (
        estrutura_igual
        and linhas_etl == linhas_elt
        and apenas_etl == 0
        and apenas_elt == 0
    )
    print(f"Estrutura e tipos: {'OK' if estrutura_igual else 'DIVERGENTE'}")
    print(f"Linhas ETL: {linhas_etl}")
    print(f"Linhas ELT: {linhas_elt}")
    print(f"Linhas apenas no ETL: {apenas_etl}")
    print(f"Linhas apenas no ELT: {apenas_elt}")
    print("Equivalencia: OK" if equivalente else "Equivalencia: FALHA")
    raise SystemExit(0 if equivalente else 1)


if __name__ == "__main__":
    main()
