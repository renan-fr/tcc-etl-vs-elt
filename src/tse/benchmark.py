from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
import re
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

ETL_SCRIPT = BASE_DIR / "src" / "tse" / "etl.py"
ELT_SCRIPT = BASE_DIR / "src" / "tse" / "elt.py"
EQUIVALENCIA_SCRIPT = BASE_DIR / "src" / "tse" / "equivalencia.py"
MANIFESTOS_DIR = BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos"
RESULTADOS = [
    BASE_DIR / "data" / "benchmark" / "tse" / "resultados" / nome
    for nome in ("tse_etl.csv", "tse_elt.csv")
]
SEED_PADRAO = 20241027
COMPARACOES_SECAO = (
    "comparecimento",
    "abstencoes",
    "votos nominais",
    "votos brancos",
    "votos nulos",
    "votos de legenda",
)


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
) -> dict[str, str]:
    marcador = modo if rodada is None else f"rodada_{rodada}"
    print(f"\n=== TSE | volume={volume} | {marcador} ===")

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
    saidas = {}
    for nome, comando in comandos:
        saidas[nome.lower()] = executar(comando, ambiente, capturar)

    if modo == "certificar":
        saidas["equivalencia"] = executar(
            [sys.executable, str(EQUIVALENCIA_SCRIPT)], ambiente, capturar
        )
    return saidas


def _salvar_alertas(run_id: str, linhas: list[dict[str, object]]) -> Path:
    pasta = BASE_DIR / "data" / "benchmark" / "tse" / "certificacoes"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"alertas_munzona_secao_{run_id}.csv"
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=[
                "run_id",
                "volume_configurado",
                "arquitetura",
                "comparacao",
                "quantidade_chaves",
            ],
            delimiter=";",
        )
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


def _alertas_saida(
    run_id: str,
    volume: int,
    arquitetura: str,
    saida: str,
) -> list[dict[str, object]]:
    encontrados = {
        nome: int(quantidade)
        for quantidade, nome in re.findall(
            r"(\d+) chaves possuem diferenca em (.+?) entre munzona e secoes\.",
            saida,
        )
    }
    return [
        {
            "run_id": run_id,
            "volume_configurado": volume,
            "arquitetura": arquitetura,
            "comparacao": nome,
            "quantidade_chaves": encontrados.get(nome, 0),
        }
        for nome in COMPARACOES_SECAO
    ]


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(
        description="Executa o benchmark ETL x ELT do TSE."
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

    ausentes = [
        MANIFESTOS_DIR / f"chaves_{volume}.csv"
        for volume in args.volumes
        if not (MANIFESTOS_DIR / f"chaves_{volume}.csv").is_file()
    ]
    if ausentes:
        lista = "\n".join(f"- {caminho}" for caminho in ausentes)
        parser.error(
            "Manifestos ausentes:\n"
            f"{lista}\n"
            "Prepare-os antes com src/tse/preparar_subconjuntos.py."
        )

    if args.certificar:
        identidade = criar_identidade(BASE_DIR, args.run_id)
        ambiente = ambiente_com_identidade(identidade)
        alertas: list[dict[str, object]] = []
        log = ""
        for volume in args.volumes:
            saidas = executar_cenario(
                volume, "certificar", ambiente=ambiente, capturar=True
            )
            log += f"\n=== TSE | volume={volume} | certificar ===\n"
            log += "".join(saidas.values())
            for arquitetura in ("etl", "elt"):
                alertas.extend(
                    _alertas_saida(
                        identidade["run_id"], volume, arquitetura, saidas[arquitetura]
                    )
                )
        caminho = _salvar_alertas(identidade["run_id"], alertas)
        caminho_log = caminho.parent / f"certificacao_{identidade['run_id']}.log"
        caminho_log.write_text(log, encoding="utf-8")
        print(f"Alertas de qualidade salvos em: {caminho}")
        print(f"Log da certificacao salvo em: {caminho_log}")
        return

    preparar_resultados(RESULTADOS, args.limpar_resultados)
    identidade = criar_identidade(BASE_DIR, args.run_id)
    ambiente = ambiente_com_identidade(identidade)
    rng = random.Random(args.seed)
    cenarios = [
        (volume, arquitetura)
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
            "dataset": "tse",
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
