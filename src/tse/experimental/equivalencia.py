from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import sys

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
TSE_DIR = BASE_DIR / "src" / "tse"
if str(TSE_DIR) not in sys.path:
    sys.path.insert(0, str(TSE_DIR))

import equivalencia as oficial  # noqa: E402
from contrato import CHAVE_FINAL  # noqa: E402


TABELA = oficial.TABELA


def tabela_existe(cursor, schema: str) -> bool:
    cursor.execute(
        "SELECT to_regclass(%s) IS NOT NULL", (f'"{schema}"."{TABELA}"',)
    )
    return bool(cursor.fetchone()[0])


def duplicadas(cursor, schema: str) -> int:
    chaves = sql.SQL(", ").join(sql.Identifier(c) for c in CHAVE_FINAL)
    cursor.execute(
        sql.SQL(
            "SELECT COALESCE(SUM(n), 0) FROM (SELECT COUNT(*) AS n FROM {}.{} "
            "GROUP BY {} HAVING COUNT(*) > 1) d"
        ).format(sql.Identifier(schema), sql.Identifier(TABELA), chaves)
    )
    return int(cursor.fetchone()[0])


def comparar(cursor, referencia: str, candidato: str, rotulo: str) -> bool:
    estrutura_ref = oficial.obter_estrutura(cursor, referencia)
    estrutura_cand = oficial.obter_estrutura(cursor, candidato)
    linhas_ref = oficial.contar_linhas(cursor, referencia)
    linhas_cand = oficial.contar_linhas(cursor, candidato)
    apenas_ref, apenas_cand = oficial.contar_diferencas(
        cursor, referencia, candidato
    )
    dup_ref = duplicadas(cursor, referencia)
    dup_cand = duplicadas(cursor, candidato)
    equivalente = (
        estrutura_ref == estrutura_cand
        and linhas_ref == linhas_cand
        and apenas_ref == 0
        and apenas_cand == 0
        and dup_ref == 0
        and dup_cand == 0
    )
    print(f"[{rotulo}] estrutura: {'OK' if estrutura_ref == estrutura_cand else 'FALHA'}")
    print(f"[{rotulo}] linhas: referencia={linhas_ref}, candidato={linhas_cand}")
    print(f"[{rotulo}] apenas referencia={apenas_ref}, apenas candidato={apenas_cand}")
    print(f"[{rotulo}] duplicadas: referencia={dup_ref}, candidato={dup_cand}")
    print(f"[{rotulo}] equivalencia: {'OK' if equivalente else 'FALHA'}")
    return equivalente


def comparar_contrato(cursor, schema_etl: str, schema_cte: str) -> bool:
    """Compara o contrato do ETL sem presumir que sua tabela usa o mesmo manifesto."""
    estrutura_etl = oficial.obter_estrutura(cursor, schema_etl)
    estrutura_cte = oficial.obter_estrutura(cursor, schema_cte)
    igual = estrutura_etl == estrutura_cte
    print(f"[contrato ETL x CTE] estrutura: {'OK' if igual else 'FALHA'}")
    print(
        "[contrato ETL x CTE] valores nao comparados: a tabela ETL existente "
        "pode ter sido produzida com outro volume."
    )
    return igual


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(
        description="Compara diretamente ELT STAGING e ELT CTE experimentais"
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--schema-staging", default="tse_elt_staging_final_exp")
    parser.add_argument("--schema-cte", default="tse_elt_cte_final_exp")
    parser.add_argument(
        "--schema-etl", default=os.getenv("POSTGRES_SCHEMA_TSE_ETL_FINAL", "tse_etl_final")
    )
    parser.add_argument("--volume", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with oficial.obter_conexao(args.database_url) as conexao:
            with conexao.cursor() as cursor:
                if not tabela_existe(cursor, args.schema_staging) or not tabela_existe(
                    cursor, args.schema_cte
                ):
                    raise SystemExit("Uma das tabelas finais experimentais nao existe.")
                ok = comparar(
                    cursor, args.schema_staging, args.schema_cte, "ELT STAGING x CTE"
                )
                estrutura_igual = (
                    oficial.obter_estrutura(cursor, args.schema_staging)
                    == oficial.obter_estrutura(cursor, args.schema_cte)
                )
                linhas_staging = oficial.contar_linhas(cursor, args.schema_staging)
                linhas_cte = oficial.contar_linhas(cursor, args.schema_cte)
                apenas_staging, apenas_cte = oficial.contar_diferencas(
                    cursor, args.schema_staging, args.schema_cte
                )
                duplicadas_staging = duplicadas(cursor, args.schema_staging)
                duplicadas_cte = duplicadas(cursor, args.schema_cte)
                if tabela_existe(cursor, args.schema_etl):
                    ok = comparar_contrato(cursor, args.schema_etl, args.schema_cte) and ok
                else:
                    print("[contrato ETL x CTE] nao executado: tabela ETL ausente.")
    except psycopg2.Error as erro:
        raise SystemExit(f"Falha ao comparar os produtos: {erro}") from erro
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        existe = args.output.exists() and args.output.stat().st_size > 0
        campos = [
            "volume", "estrutura_igual", "linhas_staging", "linhas_cte",
            "apenas_staging", "apenas_cte", "duplicadas_staging",
            "duplicadas_cte", "equivalente",
        ]
        with args.output.open("a", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
            if not existe:
                escritor.writeheader()
            escritor.writerow(
                {
                    "volume": args.volume,
                    "estrutura_igual": estrutura_igual,
                    "linhas_staging": linhas_staging,
                    "linhas_cte": linhas_cte,
                    "apenas_staging": apenas_staging,
                    "apenas_cte": apenas_cte,
                    "duplicadas_staging": duplicadas_staging,
                    "duplicadas_cte": duplicadas_cte,
                    "equivalente": ok,
                }
            )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
