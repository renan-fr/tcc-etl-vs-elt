from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[2]
ETL_SCRIPT = BASE_DIR / "src" / "tse" / "etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "tse" / "elt.py"
EQUIVALENCIA_SCRIPT = BASE_DIR / "src" / "tse" / "equivalencia.py"
MANIFESTOS_DIR = BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos"
RESULTADOS = [
    BASE_DIR / "data" / "benchmark" / "tse" / "resultados" / nome
    for nome in ("tse_etl.csv", "tse_elt.csv")
]
SEED_PADRAO = 20241027


def executar(comando: list[str], ambiente: dict[str, str] | None = None) -> None:
    print("\n$", " ".join(comando))
    subprocess.run(comando, cwd=BASE_DIR, env=ambiente, check=True)


def preparar_resultados(limpar: bool) -> None:
    existentes = [c for c in RESULTADOS if c.exists() and c.stat().st_size > 0]
    if existentes and not limpar:
        raise SystemExit(
            "Resultados anteriores encontrados. Use --limpar-resultados "
            "para iniciar outra campanha."
        )
    for caminho in existentes:
        caminho.unlink()


def certificar(volumes: list[int]) -> None:
    for volume in volumes:
        print(f"\n=== TSE | volume={volume} | certificar ===")
        argumentos = ["--limite", str(volume), "--modo", "certificar"]
        executar([sys.executable, str(ETL_SCRIPT), *argumentos])
        executar([sys.executable, str(ELT_SCRIPT), *argumentos])
        executar([sys.executable, str(EQUIVALENCIA_SCRIPT)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa o benchmark ETL x ELT do TSE."
    )
    parser.add_argument(
        "--volumes",
        nargs="+",
        type=int,
        default=[100_000, 250_000, 500_000, 1_000_000],
    )
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--certificar", action="store_true")
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id", default="teste_tecnico")
    parser.add_argument("--limpar-resultados", action="store_true")
    args = parser.parse_args()

    if args.rodadas < 1 or any(volume < 1 for volume in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    ausentes = [
        MANIFESTOS_DIR / f"chaves_{volume}.csv"
        for volume in args.volumes
        if not (MANIFESTOS_DIR / f"chaves_{volume}.csv").is_file()
    ]
    if ausentes:
        parser.error("Manifestos TSE ausentes:\n" + "\n".join(map(str, ausentes)))
    if args.certificar:
        certificar(args.volumes)
        return
    if not args.run_id.strip():
        parser.error("--run-id nao pode ser vazio.")

    preparar_resultados(args.limpar_resultados)
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = args.run_id.strip()
    ambiente["PYTHONIOENCODING"] = "utf-8"
    rng = random.Random(args.seed)
    cenarios = [
        (volume, arquitetura)
        for volume in args.volumes
        for arquitetura in ("etl", "elt")
    ]
    scripts = {"etl": ETL_SCRIPT, "elt": ELT_SCRIPT}
    fases = [
        ("aquecimento", None),
        *[("medir", rodada) for rodada in range(1, args.rodadas + 1)],
    ]
    print(f"Campanha: {args.run_id}")
    for modo, rodada in fases:
        ordem = cenarios.copy()
        rng.shuffle(ordem)
        for volume, arquitetura in ordem:
            argumentos = ["--limite", str(volume), "--modo", modo]
            if rodada is not None:
                argumentos.extend(["--rodada", str(rodada)])
            executar(
                [sys.executable, str(scripts[arquitetura]), *argumentos],
                ambiente,
            )


if __name__ == "__main__":
    main()
