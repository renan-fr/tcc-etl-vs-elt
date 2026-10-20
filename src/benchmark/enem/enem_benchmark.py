from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[3]
ETL_SCRIPT = BASE_DIR / "src" / "etl" / "enem" / "enem_etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "elt" / "enem" / "enem_elt.py"
EQUIVALENCIA_SCRIPT = (
    BASE_DIR / "src" / "validacao" / "enem" / "enem_equivalencia.py"
)


def executar(comando: list[str]) -> None:
    print("\n$", " ".join(comando))
    subprocess.run(comando, cwd=BASE_DIR, check=True)


def executar_cenario(
    python: str,
    volume: int,
    rodada: int | None,
    aquecimento: bool,
    diretorio_resultados: Path,
    diretorio_resumos: Path,
) -> None:
    marcador = "aquecimento" if aquecimento else f"rodada_{rodada}"
    print(f"\n=== ENEM | volume={volume} | {marcador} ===")

    argumentos_comuns = [
        "--limite", str(volume),
        "--benchmark",
    ]
    if aquecimento:
        argumentos_comuns.append("--aquecimento")
    else:
        argumentos_comuns.extend(["--rodada", str(rodada)])

    executar([
        python, str(ETL_SCRIPT),
        *argumentos_comuns,
        "--benchmark-output",
        str(diretorio_resultados / "enem_etl.csv"),
        "--benchmark-summary-output",
        str(diretorio_resumos / "enem_etl.txt"),
    ])
    executar([
        python, str(ELT_SCRIPT),
        *argumentos_comuns,
        "--benchmark-output",
        str(diretorio_resultados / "enem_elt.csv"),
        "--benchmark-summary-output",
        str(diretorio_resumos / "enem_elt.txt"),
    ])
    executar([python, str(EQUIVALENCIA_SCRIPT)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa aquecimento e rodadas do benchmark ETL x ELT do ENEM."
    )
    parser.add_argument(
        "--volumes",
        nargs="+",
        type=int,
        default=[100_000, 500_000, 1_000_000, 3_000_000],
        help="Volumes por arquivo. Padrão: 100000 500000 1000000 3000000.",
    )
    parser.add_argument(
        "--rodadas",
        type=int,
        default=5,
        help="Quantidade de rodadas válidas por volume.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "data" / "benchmark" / "enem" / "resultados",
        help="Diretório dos CSVs e resumos gerados.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Executável Python usado pelos pipelines.",
    )
    args = parser.parse_args()

    if args.rodadas < 1:
        parser.error("--rodadas deve ser maior ou igual a 1.")
    if any(volume < 1 for volume in args.volumes):
        parser.error("Todos os volumes devem ser maiores que zero.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    diretorio_resumos = args.output_dir.parent / "resumos"
    diretorio_resumos.mkdir(parents=True, exist_ok=True)
    for volume in args.volumes:
        executar_cenario(args.python, volume, None, True, args.output_dir, diretorio_resumos)
        for rodada in range(1, args.rodadas + 1):
            executar_cenario(args.python, volume, rodada, False, args.output_dir, diretorio_resumos)


if __name__ == "__main__":
    main()
