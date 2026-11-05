from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import random
import subprocess
import sys

try:
    from src.benchmark_paths import criar_diretorio_campanha, validar_run_id
except ModuleNotFoundError:  # execução direta: python src/benchmark.py
    from benchmark_paths import criar_diretorio_campanha, validar_run_id


BASE_DIR = Path(__file__).resolve().parents[1]
VOLUMES_PADRAO = [100_000, 250_000, 500_000, 1_000_000]
SEED_PADRAO = 20241027
def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def obter_commit_git() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def salvar_metadados(caminho: Path, metadados: dict[str, object]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)


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
    args = parser.parse_args()

    if args.rodadas < 1 or any(volume < 1 for volume in args.volumes):
        parser.error("Volumes e rodadas devem ser maiores que zero.")
    try:
        run_id = validar_run_id(args.run_id)
    except ValueError as erro:
        parser.error(str(erro))

    # Deve ocorrer antes de criar, limpar ou alterar qualquer resultado.
    validar_git_limpo()

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

    try:
        campanha_dir = criar_diretorio_campanha(run_id)
    except FileExistsError as erro:
        parser.error(str(erro))

    metadados_caminho = campanha_dir / "campanha.json"

    ambiente = os.environ.copy()
    ambiente["BENCHMARK_RUN_ID"] = run_id
    ambiente["BENCHMARK_OUTPUT_DIR"] = str(campanha_dir)
    ambiente["BENCHMARK_ORCHESTRATOR_RUN_ID"] = run_id
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

    print(f"Campanha: {run_id}")
    print(f"Seed: {args.seed}")
    total = len(cenarios) * len(fases)
    aquecimentos = len(cenarios)
    medicoes_validas = len(cenarios) * args.rodadas
    metadados: dict[str, object] = {
        "run_id": run_id,
        "status": "em_andamento",
        "inicio": agora_iso(),
        "fim": None,
        "commit_git": obter_commit_git(),
        "seed": args.seed,
        "volumes": args.volumes,
        "rodadas": args.rodadas,
        "combinacoes": len(cenarios),
        "aquecimentos": aquecimentos,
        "medicoes_validas": medicoes_validas,
        "execucoes_previstas": total,
        "execucoes_concluidas": 0,
    }
    salvar_metadados(metadados_caminho, metadados)
    indice = 0
    try:
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
                metadados["execucoes_concluidas"] = indice
                salvar_metadados(metadados_caminho, metadados)
    except BaseException as erro:
        metadados["status"] = (
            "interrompida" if isinstance(erro, KeyboardInterrupt) else "falhou"
        )
        metadados["fim"] = agora_iso()
        metadados["erro"] = f"{type(erro).__name__}: {erro}"
        salvar_metadados(metadados_caminho, metadados)
        raise

    metadados["status"] = "concluida"
    metadados["fim"] = agora_iso()
    salvar_metadados(metadados_caminho, metadados)


if __name__ == "__main__":
    main()
