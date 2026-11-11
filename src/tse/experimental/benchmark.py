from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import random
import subprocess
import sys

try:
    from src.benchmark_paths import criar_diretorio_campanha, validar_run_id
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from benchmark_paths import criar_diretorio_campanha, validar_run_id


BASE_DIR = Path(__file__).resolve().parents[3]
EXP_DIR = BASE_DIR / "src" / "tse" / "experimental"
SCRIPTS = {
    "elt_staging": EXP_DIR / "elt_staging.py",
    "elt_cte": EXP_DIR / "elt_cte.py",
}
EQUIVALENCIA = EXP_DIR / "equivalencia.py"
RESULTADOS = {
    "elt_staging": Path(),
    "elt_cte": Path(),
}
SEQUENCIA = Path()
VALIDACOES = Path()
SEED_PADRAO = 20261102


def executar(comando: list[str], ambiente: dict[str, str]) -> None:
    print("\n$", " ".join(comando), flush=True)
    subprocess.run(comando, cwd=BASE_DIR, env=ambiente, check=True)


def preparar_saidas(saida_dir: Path) -> None:
    saida_dir.mkdir(parents=True, exist_ok=True)


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
    args = parser.parse_args()
    if args.rodadas < 1 or any(v < 1 for v in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    run_id = validar_run_id(args.run_id)
    try:
        campanha_dir = criar_diretorio_campanha(run_id)
    except FileExistsError as erro:
        parser.error(str(erro))
    saida_dir = campanha_dir / "experimental_cte"
    saida_dir.mkdir()
    for nome in ("elt_staging", "elt_cte"):
        RESULTADOS[nome] = saida_dir / f"tse_{nome}.csv"
    global SEQUENCIA, VALIDACOES
    SEQUENCIA = saida_dir / "sequencia.csv"
    VALIDACOES = saida_dir / "validacoes.csv"
    preparar_saidas(saida_dir)
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = run_id
    ambiente["BENCHMARK_OUTPUT_DIR"] = str(campanha_dir)
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
