from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[2]
ETL_SCRIPT = BASE_DIR / "src" / "enem" / "etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "enem" / "elt.py"
EQUIVALENCIA_SCRIPT = BASE_DIR / "src" / "enem" / "equivalencia.py"


def executar(comando: list[str]) -> None:
    print("\n$", " ".join(comando))
    subprocess.run(comando, cwd=BASE_DIR, check=True)


def executar_cenario(
    volume: int,
    modo: str,
    rodada: int | None = None,
    inverter_ordem: bool = False,
) -> None:
    marcador = modo if rodada is None else f"rodada_{rodada}"
    print(f"\n=== ENEM | volume={volume} | {marcador} ===")

    argumentos = ["--limite", str(volume), "--modo", modo]
    if rodada is not None:
        argumentos.extend(["--rodada", str(rodada)])

    comandos = [
        ("ETL", [sys.executable, str(ETL_SCRIPT), *argumentos]),
        ("ELT", [sys.executable, str(ELT_SCRIPT), *argumentos]),
    ]
    if inverter_ordem:
        comandos.reverse()

    print("Ordem:", " -> ".join(nome for nome, _ in comandos))
    for _, comando in comandos:
        executar(comando)

    if modo == "certificar":
        executar([sys.executable, str(EQUIVALENCIA_SCRIPT)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa o benchmark ETL x ELT do ENEM."
    )
    parser.add_argument(
        "--volumes",
        nargs="+",
        type=int,
        default=[100_000, 500_000, 1_000_000, 3_000_000],
    )
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--certificar", action="store_true")
    args = parser.parse_args()

    if args.rodadas < 1:
        parser.error("--rodadas deve ser maior ou igual a 1.")
    if any(volume < 1 for volume in args.volumes):
        parser.error("Todos os volumes devem ser maiores que zero.")

    if args.certificar:
        for volume in args.volumes:
            executar_cenario(volume, "certificar")
        return

    indice_cenario = 0
    for volume in args.volumes:
        executar_cenario(
            volume,
            "aquecimento",
            inverter_ordem=indice_cenario % 2 == 1,
        )
        indice_cenario += 1
        for rodada in range(1, args.rodadas + 1):
            executar_cenario(
                volume,
                "medir",
                rodada,
                inverter_ordem=indice_cenario % 2 == 1,
            )
            indice_cenario += 1


if __name__ == "__main__":
    main()
