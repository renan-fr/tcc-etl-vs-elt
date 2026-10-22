from __future__ import annotations

import argparse
import random
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv

from benchmark_comum import (
    ambiente_com_identidade,
    criar_identidade,
    preparar_resultados,
    salvar_campanha,
)


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
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(
        description="Orquestra a campanha global e randomizada de ENEM e TSE."
    )
    parser.add_argument("--volumes", nargs="+", type=int, default=VOLUMES_PADRAO)
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id")
    parser.add_argument("--limpar-resultados", action="store_true")
    parser.add_argument("--permitir-worktree-sujo", action="store_true")
    args = parser.parse_args()

    if args.rodadas < 1 or any(volume < 1 for volume in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")

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

    identidade = criar_identidade(BASE_DIR, args.run_id)
    if (
        identidade["git_worktree_limpo"] != "true"
        and not args.permitir_worktree_sujo
    ):
        raise SystemExit(
            "A campanha oficial exige uma arvore Git limpa. "
            "Revise e registre as alteracoes antes de executar."
        )
    preparar_resultados(RESULTADOS, args.limpar_resultados)
    ambiente = ambiente_com_identidade(identidade)
    rng = random.Random(args.seed)
    cenarios = [
        (dataset, volume, arquitetura)
        for dataset in ("enem", "tse")
        for volume in args.volumes
        for arquitetura in ("etl", "elt")
    ]
    plano: list[dict[str, object]] = []
    fases = [
        ("aquecimento", None),
        *[("medir", rodada) for rodada in range(1, args.rodadas + 1)],
    ]
    for modo, rodada in fases:
        ordem = cenarios.copy()
        rng.shuffle(ordem)
        for dataset, volume, arquitetura in ordem:
            plano.append(
                {
                    "modo": modo,
                    "rodada": rodada,
                    "dataset": dataset,
                    "volume": volume,
                    "arquitetura": arquitetura,
                }
            )

    manifesto = salvar_campanha(
        BASE_DIR,
        identidade,
        {
            "seed": args.seed,
            "volumes": args.volumes,
            "rodadas": args.rodadas,
            "plano": plano,
        },
    )
    print(f"Campanha: {identidade['run_id']}")
    print(f"Manifesto: {manifesto}")
    for indice, item in enumerate(plano, start=1):
        print(
            f"\n=== {indice}/{len(plano)} | {item['modo']} | "
            f"{str(item['dataset']).upper()} | {item['volume']} | "
            f"{str(item['arquitetura']).upper()} ==="
        )
        subprocess.run(
            comando(
                str(item["dataset"]),
                str(item["arquitetura"]),
                int(item["volume"]),
                str(item["modo"]),
                int(item["rodada"]) if item["rodada"] is not None else None,
            ),
            cwd=BASE_DIR,
            env=ambiente,
            check=True,
        )


if __name__ == "__main__":
    main()
