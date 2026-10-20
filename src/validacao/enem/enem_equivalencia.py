from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


TABELAS = {
    "participantes": "id_participante",
    "resultados": "id_resultado",
}


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


def _tabela(schema: str, tabela: str):
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(tabela))


def obter_estrutura(
    cursor,
    schema: str,
    tabela: str,
) -> list[tuple[str, str, str, int | None, int | None, int | None]]:
    cursor.execute(
        """
        SELECT
            column_name,
            data_type,
            is_nullable,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, tabela),
    )
    return cursor.fetchall()


def contar_linhas(cursor, schema: str, tabela: str) -> int:
    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}").format(_tabela(schema, tabela))
    )
    return int(cursor.fetchone()[0])


def contar_diferencas(
    cursor,
    schema_etl: str,
    schema_elt: str,
    tabela: str,
) -> tuple[int, int]:
    tabela_etl = _tabela(schema_etl, tabela)
    tabela_elt = _tabela(schema_elt, tabela)
    cursor.execute(
        sql.SQL(
            "SELECT COUNT(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d"
        ).format(tabela_etl, tabela_elt)
    )
    apenas_etl = int(cursor.fetchone()[0])
    cursor.execute(
        sql.SQL(
            "SELECT COUNT(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d"
        ).format(tabela_elt, tabela_etl)
    )
    apenas_elt = int(cursor.fetchone()[0])
    return apenas_etl, apenas_elt


def divergencias_por_coluna(
    cursor,
    schema_etl: str,
    schema_elt: str,
    tabela: str,
    colunas: list[str],
) -> list[tuple[str, int]]:
    chave = TABELAS[tabela]
    divergencias: list[tuple[str, int]] = []
    for coluna in colunas:
        cursor.execute(
            sql.SQL(
                "SELECT COUNT(*) FROM {} etl "
                "JOIN {} elt USING ({}) "
                "WHERE etl.{} IS DISTINCT FROM elt.{}"
            ).format(
                _tabela(schema_etl, tabela),
                _tabela(schema_elt, tabela),
                sql.Identifier(chave),
                sql.Identifier(coluna),
                sql.Identifier(coluna),
            )
        )
        quantidade = int(cursor.fetchone()[0])
        if quantidade:
            divergencias.append((coluna, quantidade))
    return divergencias


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Compara os produtos finais ETL e ELT do ENEM."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL"),
    )
    parser.add_argument(
        "--schema-etl",
        "--schema-a",
        dest="schema_etl",
        default=os.getenv("POSTGRES_SCHEMA_ENEM_ETL_FINAL", "enem_etl_final"),
        help="Schema final produzido pelo ETL.",
    )
    parser.add_argument(
        "--schema-elt",
        "--schema-b",
        dest="schema_elt",
        default=os.getenv("POSTGRES_SCHEMA_ENEM_ELT_FINAL", "enem_elt_final"),
        help="Schema final produzido pelo ELT.",
    )
    args = parser.parse_args()

    equivalente = True
    try:
        with obter_conexao(args.database_url) as conexao:
            with conexao.cursor() as cursor:
                for tabela in TABELAS:
                    estrutura_etl = obter_estrutura(cursor, args.schema_etl, tabela)
                    estrutura_elt = obter_estrutura(cursor, args.schema_elt, tabela)
                    tabelas_existem = bool(estrutura_etl) and bool(estrutura_elt)
                    estrutura_igual = tabelas_existem and estrutura_etl == estrutura_elt

                    if not tabelas_existem:
                        print(f"{tabela}: DIVERGENTE")
                        print(
                            "  tabela_etl=" + ("OK" if estrutura_etl else "AUSENTE")
                        )
                        print(
                            "  tabela_elt=" + ("OK" if estrutura_elt else "AUSENTE")
                        )
                        equivalente = False
                        continue

                    linhas_etl = contar_linhas(cursor, args.schema_etl, tabela)
                    linhas_elt = contar_linhas(cursor, args.schema_elt, tabela)
                    apenas_etl = apenas_elt = -1
                    divergencias: list[tuple[str, int]] = []
                    if estrutura_igual:
                        apenas_etl, apenas_elt = contar_diferencas(
                            cursor, args.schema_etl, args.schema_elt, tabela
                        )
                        if apenas_etl or apenas_elt:
                            colunas = [coluna[0] for coluna in estrutura_etl]
                            divergencias = divergencias_por_coluna(
                                cursor,
                                args.schema_etl,
                                args.schema_elt,
                                tabela,
                                colunas,
                            )

                    tabela_equivalente = (
                        estrutura_igual
                        and linhas_etl == linhas_elt
                        and apenas_etl == 0
                        and apenas_elt == 0
                    )
                    equivalente = equivalente and tabela_equivalente
                    print(
                        f"{tabela}: "
                        + ("OK" if tabela_equivalente else "DIVERGENTE")
                    )
                    print(
                        "  estrutura_e_tipos="
                        + ("OK" if estrutura_igual else "DIVERGENTE")
                    )
                    print(f"  linhas_etl={linhas_etl}")
                    print(f"  linhas_elt={linhas_elt}")
                    if estrutura_igual:
                        print(f"  apenas_etl={apenas_etl}")
                        print(f"  apenas_elt={apenas_elt}")
                        for coluna, quantidade in divergencias:
                            print(f"  divergencia_{coluna}={quantidade}")
                    else:
                        print(f"  estrutura_etl={estrutura_etl}")
                        print(f"  estrutura_elt={estrutura_elt}")
    except psycopg2.Error as erro:
        raise SystemExit(f"Falha ao comparar ETL e ELT do ENEM: {erro}") from erro

    print("Equivalencia: OK" if equivalente else "Equivalencia: FALHA")
    raise SystemExit(0 if equivalente else 1)


if __name__ == "__main__":
    main()
