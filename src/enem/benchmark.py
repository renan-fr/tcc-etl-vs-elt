from __future__ import annotations

import argparse
import random
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benchmark_comum import (
    ambiente_com_identidade,
    criar_identidade,
    preparar_resultados,
    salvar_campanha,
)

ETL_SCRIPT = BASE_DIR / "src" / "enem" / "etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "enem" / "elt.py"
EQUIVALENCIA_SCRIPT = BASE_DIR / "src" / "enem" / "equivalencia.py"


RESULTADOS = [
    BASE_DIR / "data" / "benchmark" / "enem" / "resultados" / nome
    for nome in ("enem_etl.csv", "enem_elt.csv")
]
SEED_PADRAO = 20241027


def executar(
    comando: list[str],
    ambiente: dict[str, str] | None = None,
    capturar: bool = False,
) -> str:
    print("\n$", " ".join(comando))
    resultado = subprocess.run(
        comando,
        cwd=BASE_DIR,
        env=ambiente,
        check=True,
        capture_output=capturar,
        text=capturar,
        encoding="utf-8" if capturar else None,
        errors="replace" if capturar else None,
    )
    if capturar:
        codificacao_saida = sys.stdout.encoding or "utf-8"
        print(
            resultado.stdout.encode(codificacao_saida, errors="replace").decode(
                codificacao_saida
            ),
            end="",
        )
        if resultado.stderr:
            codificacao_erro = sys.stderr.encoding or "utf-8"
            print(
                resultado.stderr.encode(codificacao_erro, errors="replace").decode(
                    codificacao_erro
                ),
                end="",
                file=sys.stderr,
            )
        return resultado.stdout + resultado.stderr
    return ""


def executar_cenario(
    volume: int,
    modo: str,
    rodada: int | None = None,
    inverter_ordem: bool = False,
    ambiente: dict[str, str] | None = None,
    capturar: bool = False,
) -> str:
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
    saida = ""
    for _, comando in comandos:
        saida += executar(comando, ambiente, capturar)

    if modo == "certificar":
        saida += executar(
            [sys.executable, str(EQUIVALENCIA_SCRIPT)], ambiente, capturar
        )
    return saida


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
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
    parser.add_argument("--seed", type=int, default=SEED_PADRAO)
    parser.add_argument("--run-id")
    parser.add_argument("--limpar-resultados", action="store_true")
    args = parser.parse_args()

    if args.rodadas < 1:
        parser.error("--rodadas deve ser maior ou igual a 1.")
    if any(volume < 1 for volume in args.volumes):
        parser.error("Todos os volumes devem ser maiores que zero.")

    if args.certificar:
        identidade = criar_identidade(BASE_DIR, args.run_id)
        ambiente = ambiente_com_identidade(identidade)
        saida = ""
        for volume in args.volumes:
            saida += f"\n=== ENEM | volume={volume} | certificar ===\n"
            saida += executar_cenario(
                volume, "certificar", ambiente=ambiente, capturar=True
            )
        pasta = BASE_DIR / "data" / "benchmark" / "enem" / "certificacoes"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"certificacao_{identidade['run_id']}.log"
        caminho.write_text(saida, encoding="utf-8")
        print(f"Log da certificacao salvo em: {caminho}")
        return

    preparar_resultados(RESULTADOS, args.limpar_resultados)
    identidade = criar_identidade(BASE_DIR, args.run_id)
    ambiente = ambiente_com_identidade(identidade)
    rng = random.Random(args.seed)
    plano: list[dict[str, object]] = []
    cenarios = [
        (volume, arquitetura)
        for volume in args.volumes
        for arquitetura in ("etl", "elt")
    ]
    fases = [
        ("aquecimento", None),
        *[("medir", rodada) for rodada in range(1, args.rodadas + 1)],
    ]
    for modo, rodada in fases:
        ordem = cenarios.copy()
        rng.shuffle(ordem)
        for volume, arquitetura in ordem:
            plano.append(
                {
                    "modo": modo,
                    "rodada": rodada,
                    "volume": volume,
                    "arquitetura": arquitetura,
                }
            )
    manifesto = salvar_campanha(
        BASE_DIR,
        identidade,
        {
            "dataset": "enem",
            "seed": args.seed,
            "volumes": args.volumes,
            "rodadas": args.rodadas,
            "plano": plano,
        },
    )
    print(f"Campanha: {identidade['run_id']}")
    print(f"Manifesto: {manifesto}")
    scripts = {"etl": ETL_SCRIPT, "elt": ELT_SCRIPT}
    for item in plano:
        argumentos = ["--limite", str(item["volume"]), "--modo", str(item["modo"])]
        if item["rodada"] is not None:
            argumentos.extend(["--rodada", str(item["rodada"])])
        executar(
            [sys.executable, str(scripts[str(item["arquitetura"])]), *argumentos],
            ambiente,
        )


if __name__ == "__main__":
    main()
