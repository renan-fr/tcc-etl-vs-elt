from __future__ import annotations

import argparse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

from comum import (
    COLUNAS_MANIFESTO,
    salvar_manifesto_chaves,
    selecionar_secoes,
)


PASTA_SECAO = (
    BASE_DIR
    / "data"
    / "raw"
    / "tse"
    / "detalhe_votacao_secao_2024"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepara os manifestos de chaves compartilhados por ETL e ELT."
    )
    parser.add_argument(
        "--volumes",
        nargs="+",
        type=int,
        default=[100_000, 500_000, 1_000_000, 3_000_000],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos",
    )
    parser.add_argument("--sobrescrever", action="store_true")
    args = parser.parse_args()

    if any(volume < 1 for volume in args.volumes):
        parser.error("Todos os volumes devem ser maiores que zero.")

    for volume in args.volumes:
        destino = args.output_dir / f"chaves_{volume}.csv"
        if destino.exists() and not args.sobrescrever:
            print(f"Mantido: {destino}")
            continue
        secoes, chaves = selecionar_secoes(
            PASTA_SECAO,
            COLUNAS_MANIFESTO,
            volume,
        )
        salvar_manifesto_chaves(chaves, destino)
        print(
            f"Criado: {destino} | volume_nominal={volume} | "
            f"linhas_secao={len(secoes)} | chaves={len(chaves)}"
        )


if __name__ == "__main__":
    main()
