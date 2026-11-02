from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from psycopg2 import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
TSE_DIR = BASE_DIR / "src" / "tse"
if str(TSE_DIR) not in sys.path:
    sys.path.insert(0, str(TSE_DIR))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import elt as oficial  # noqa: E402
from elt_cte import ctes_transformacao, selecao_final  # noqa: E402


SAIDA_PADRAO = BASE_DIR / "data" / "benchmark" / "tse" / "experimental_cte" / "planos"


def explicar(cursor, consulta: sql.Composed) -> str:
    cursor.execute(
        sql.SQL("EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT) ") + consulta
    )
    return "\n".join(linha[0] for linha in cursor.fetchall()) + "\n"


def consulta_staging(schema_staging: str) -> sql.Composed:
    # Os aliases tornam reutilizavel exatamente a mesma projecao/juncao final.
    return (
        sql.SQL(
            "WITH munzona AS (SELECT * FROM {}.munzona), "
            "secao AS (SELECT * FROM {}.secao), "
            "candidato AS (SELECT * FROM {}.candidato) "
        ).format(
            sql.Identifier(schema_staging),
            sql.Identifier(schema_staging),
            sql.Identifier(schema_staging),
        )
        + selecao_final()
    )


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(description="Planos SQL do experimento TSE")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--schema-staging", default="tse_elt_staging_exp")
    parser.add_argument("--schema-raw-cte", default="tse_elt_cte_raw_exp")
    parser.add_argument("--output-dir", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()
    conexao_postgres = oficial.obter_conexao_postgres(args.database_url)
    with oficial._conectar_postgres(conexao_postgres) as conexao:
        with conexao.cursor() as cursor:
            plano_staging = explicar(cursor, consulta_staging(args.schema_staging))
            plano_cte = explicar(
                cursor,
                ctes_transformacao(args.schema_raw_cte) + selecao_final(),
            )
        conexao.rollback()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "elt_staging_final.txt").write_text(
        plano_staging, encoding="utf-8"
    )
    (args.output_dir / "elt_cte_completo.txt").write_text(plano_cte, encoding="utf-8")
    print(f"Planos salvos em: {args.output_dir}")
    print(
        "Observacao: o plano STAGING cobre a juncao final; a materializacao das "
        "tres tabelas ocorre em comandos anteriores e nao esta nesse plano unico."
    )


if __name__ == "__main__":
    main()
