from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
VOLUMES_PADRAO = [100_000, 500_000, 1_000_000, 3_000_000]
SEED_PADRAO = 20241027
RESULTADOS = [
    BASE_DIR
    / "data"
    / "benchmark"
    / dataset
    / "resultados"
    / f"{dataset}_{arquitetura}.csv"
    for dataset in ("enem", "tse")
    for arquitetura in ("etl", "elt")
]


def preparar_resultados(limpar: bool) -> None:
    existentes = [c for c in RESULTADOS if c.exists() and c.stat().st_size > 0]
    if existentes and not limpar:
        lista = "\n".join(f"- {c}" for c in existentes)
        raise SystemExit(
            "A campanha deve comecar sem resultados anteriores:\n"
            f"{lista}\nUse --limpar-resultados para remove-los."
        )
    for caminho in existentes:
        caminho.unlink()


def validar_git_limpo() -> None:
    resultado = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0 or resultado.stdout.strip():
        raise SystemExit(
            "A campanha oficial exige uma arvore Git limpa. "
            "Registre as alteracoes antes de executar."
        )


def comando(
    dataset: str,
    arquitetura: str,
    volume: int,
    modo: str,
    rodada: int | None,
) -> list[str]:
    argumentos = [
        sys.executable,
        str(BASE_DIR / "src" / dataset / f"{arquitetura}.py"),
        "--limite",
        str(volume),
        "--modo",
        modo,
    ]
    if rodada is not None:
        argumentos.extend(["--rodada", str(rodada)])
    return argumentos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orquestra a campanha global e randomizada de ENEM e TSE."
    )
    parser.add_argument("--volumes", nargs="+", type=int, default=VOLUMES_PADRAO)
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id", default="oficial_01")
    parser.add_argument("--limpar-resultados", action="store_true")
    args = parser.parse_args()

    if args.rodadas < 1 or any(volume < 1 for volume in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    if not args.run_id.strip():
        parser.error("--run-id nao pode ser vazio.")

    ausentes = [
        BASE_DIR
        / "data"
        / "benchmark"
        / "tse"
        / "subconjuntos"
        / f"chaves_{volume}.csv"
        for volume in args.volumes
        if not (
            BASE_DIR
            / "data"
            / "benchmark"
            / "tse"
            / "subconjuntos"
            / f"chaves_{volume}.csv"
        ).is_file()
    ]
    if ausentes:
        parser.error("Manifestos TSE ausentes:\n" + "\n".join(map(str, ausentes)))

    validar_git_limpo()
    preparar_resultados(args.limpar_resultados)

    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = args.run_id.strip()
    ambiente["PYTHONIOENCODING"] = "utf-8"
    rng = random.Random(args.seed)
    cenarios = [
        (dataset, volume, arquitetura)
        for dataset in ("enem", "tse")
        for volume in args.volumes
        for arquitetura in ("etl", "elt")
    ]
    fases = [
        ("aquecimento", None),
        *[("medir", rodada) for rodada in range(1, args.rodadas + 1)],
    ]

    print(f"Campanha: {args.run_id}")
    print(f"Seed: {args.seed}")
    total = len(cenarios) * len(fases)
    indice = 0
    for modo, rodada in fases:
        ordem = cenarios.copy()
        rng.shuffle(ordem)
        for dataset, volume, arquitetura in ordem:
            indice += 1
            print(
                f"\n=== {indice}/{total} | {modo} | {dataset.upper()} | "
                f"{volume} | {arquitetura.upper()} ==="
            )
            subprocess.run(
                comando(dataset, arquitetura, volume, modo, rodada),
                cwd=BASE_DIR,
                env=ambiente,
                check=True,
            )


if __name__ == "__main__":
    main()
