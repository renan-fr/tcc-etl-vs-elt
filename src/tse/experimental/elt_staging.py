"""Invocador isolado da implementacao ELT oficial para o experimento."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

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


SCHEMA_RAW = "tse_elt_staging_raw_exp"
SCHEMA_STAGING = "tse_elt_staging_exp"
SCHEMA_FINAL = "tse_elt_staging_final_exp"


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(description="ELT TSE oficial em schemas experimentais")
    parser.add_argument("--limite", type=int, required=True)
    parser.add_argument(
        "--modo", choices=["certificar", "aquecimento", "medir"], required=True
    )
    parser.add_argument("--rodada", type=int)
    parser.add_argument("--schema-raw", default=SCHEMA_RAW)
    parser.add_argument("--schema-staging", default=SCHEMA_STAGING)
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
            diretorio_saida_obrigatorio() / "experimental_cte" / "tse_elt_staging.csv"
        )
    if args.modo != "medir":
        args.benchmark_output = None
    oficial.executar(args)


if __name__ == "__main__":
    main()
