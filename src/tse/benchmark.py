from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys

try:
    from src.benchmark_paths import (
        criar_diretorio_campanha,
        criar_diretorios_modalidades,
        diretorio_campanha,
        validar_run_id,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from benchmark_paths import (
        criar_diretorio_campanha,
        criar_diretorios_modalidades,
        diretorio_campanha,
        validar_run_id,
    )


BASE_DIR = Path(__file__).resolve().parents[2]
ETL_SCRIPT = BASE_DIR / "src" / "tse" / "etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "tse" / "elt.py"
EQUIVALENCIA_SCRIPT = BASE_DIR / "src" / "tse" / "equivalencia.py"
MANIFESTOS_DIR = BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos"
SEED_PADRAO = 20241027
MODALIDADES = ("desempenho", "recursos")


def executar(comando: list[str], ambiente: dict[str, str] | None = None) -> None:
    print("\n$", " ".join(comando))
    subprocess.run(comando, cwd=BASE_DIR, env=ambiente, check=True)


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

    run_id = validar_run_id(args.run_id)
    autorizado_pelo_orquestrador = (
        os.environ.get("BENCHMARK_ORCHESTRATOR_RUN_ID") == run_id
    )
    if autorizado_pelo_orquestrador:
        campanha_dir = diretorio_campanha(run_id).resolve()
        caminho_informado = os.environ.get("BENCHMARK_OUTPUT_DIR")
        if (
            not caminho_informado
            or Path(caminho_informado).resolve() != campanha_dir
            or not campanha_dir.is_dir()
        ):
            parser.error("Ambiente do orquestrador inconsistente com a campanha.")
    else:
        try:
            campanha_dir = criar_diretorio_campanha(run_id)
        except FileExistsError as erro:
            parser.error(str(erro))
    criar_diretorios_modalidades(campanha_dir)
    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = run_id
    ambiente["BENCHMARK_OUTPUT_DIR"] = str(campanha_dir)
    ambiente["PYTHONIOENCODING"] = "utf-8"
    rng = random.Random(args.seed)
    cenarios = [
        (modalidade, volume, arquitetura)
        for modalidade in MODALIDADES
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
        for modalidade, volume, arquitetura in ordem:
            argumentos = ["--limite", str(volume), "--modo", modo]
            if rodada is not None:
                argumentos.extend(["--rodada", str(rodada)])
            if modalidade == "desempenho":
                argumentos.append("--sem-monitoramento")
            executar(
                [sys.executable, str(scripts[arquitetura]), *argumentos],
                ambiente,
            )


if __name__ == "__main__":
    main()
