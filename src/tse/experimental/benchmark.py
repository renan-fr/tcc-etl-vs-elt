from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import random
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[3]
EXP_DIR = BASE_DIR / "src" / "tse" / "experimental"
SAIDA_DIR = BASE_DIR / "data" / "benchmark" / "tse" / "experimental_cte"
SCRIPTS = {
    "elt_staging": EXP_DIR / "elt_staging.py",
    "elt_cte": EXP_DIR / "elt_cte.py",
}
EQUIVALENCIA = EXP_DIR / "equivalencia.py"
RESULTADOS = {
    "elt_staging": SAIDA_DIR / "tse_elt_staging.csv",
    "elt_cte": SAIDA_DIR / "tse_elt_cte.csv",
}
SEQUENCIA = SAIDA_DIR / "sequencia.csv"
VALIDACOES = SAIDA_DIR / "validacoes.csv"
SEED_PADRAO = 20261102


def executar(comando: list[str], ambiente: dict[str, str]) -> None:
    print("\n$", " ".join(comando), flush=True)
    subprocess.run(comando, cwd=BASE_DIR, env=ambiente, check=True)


def preparar_saidas(limpar: bool) -> None:
    caminhos = [*RESULTADOS.values(), SEQUENCIA, VALIDACOES]
    existentes = [c for c in caminhos if c.exists() and c.stat().st_size > 0]
    if existentes and not limpar:
        raise SystemExit(
            "Resultados experimentais anteriores encontrados; use "
            "--limpar-resultados-experimentais para substitui-los."
        )
    for caminho in existentes:
        caminho.unlink()
    SAIDA_DIR.mkdir(parents=True, exist_ok=True)


def registrar(ordem: int, fase: str, rodada: int | None, volume: int, arquitetura: str) -> None:
    existe = SEQUENCIA.exists() and SEQUENCIA.stat().st_size > 0
    with SEQUENCIA.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=["ordem", "fase", "rodada", "volume", "arquitetura"],
            delimiter=";",
        )
        if not existe:
            escritor.writeheader()
        escritor.writerow(
            {
                "ordem": ordem,
                "fase": fase,
                "rodada": "" if rodada is None else rodada,
                "volume": volume,
                "arquitetura": arquitetura,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark exploratorio ELT STAGING x CTE")
    parser.add_argument("--volumes", nargs="+", type=int, default=[100_000, 500_000])
    parser.add_argument("--rodadas", type=int, default=3)
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id", default="tse_cte_exploratorio_20261102")
    parser.add_argument("--limpar-resultados-experimentais", action="store_true")
    args = parser.parse_args()
    if args.rodadas < 1 or any(v < 1 for v in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    preparar_saidas(args.limpar_resultados_experimentais)
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = args.run_id
    ambiente["PYTHONIOENCODING"] = "utf-8"

    # O benchmark so comeca depois de ambas as implementacoes passarem, por volume.
    for volume in args.volumes:
        for arquitetura in ("elt_staging", "elt_cte"):
            executar(
                [sys.executable, str(SCRIPTS[arquitetura]), "--limite", str(volume),
                 "--modo", "certificar"],
                ambiente,
            )
        executar(
            [
                sys.executable, str(EQUIVALENCIA), "--volume", str(volume),
                "--output", str(VALIDACOES),
            ],
            ambiente,
        )

    rng = random.Random(args.seed)
    cenarios = [(v, a) for v in args.volumes for a in SCRIPTS]
    fases = [("aquecimento", None), *[("medir", r) for r in range(1, args.rodadas + 1)]]
    ordem_global = 0
    for fase, rodada in fases:
        ordem = cenarios.copy()
        rng.shuffle(ordem)
        for volume, arquitetura in ordem:
            ordem_global += 1
            registrar(ordem_global, fase, rodada, volume, arquitetura)
            comando = [
                sys.executable, str(SCRIPTS[arquitetura]),
                "--limite", str(volume), "--modo", fase,
            ]
            if rodada is not None:
                comando.extend(["--rodada", str(rodada)])
            executar(comando, ambiente)


if __name__ == "__main__":
    main()
