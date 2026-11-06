from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import time
from typing import Callable, Sequence


BASE_DIR = Path(__file__).resolve().parents[2]
RESULTADOS_BASE = BASE_DIR / "data" / "experimentos" / "overhead_monitor"
DATASETS = ("enem", "tse")
ARQUITETURAS = ("etl", "elt")
CONDICOES = ("desligado", "monitor_0_5s", "monitor_0_3s")
INTERVALOS = {"desligado": None, "monitor_0_5s": 0.5, "monitor_0_3s": 0.3}
RUN_ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
VAR_AMOSTRAS = "OVERHEAD_MONITOR_AMOSTRAS_OUTPUT"
VAR_DIAGNOSTICO = "OVERHEAD_MONITOR_DIAGNOSTICO_OUTPUT"
COLUNAS_RESULTADO = (
    "dataset", "arquitetura", "volume", "condicao", "intervalo_segundos",
    "numero_amostras", "modo", "rodada", "ordem_condicao", "ordem", "seed",
    "status", "tempo_total", "duracao_subprocesso", "inicio", "fim",
    "resultado_bruto",
)


@dataclass(frozen=True)
class Execucao:
    dataset: str
    arquitetura: str
    volume: int
    condicao: str
    intervalo_segundos: float | None
    modo: str
    rodada: int | None
    ordem_condicao: int
    ordem: int


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalizar_volumes(volumes: int | Sequence[int]) -> tuple[int, ...]:
    return (volumes,) if isinstance(volumes, int) else tuple(volumes)


def criar_plano(
    volumes: int | Sequence[int], rodadas: int, seed: int
) -> list[Execucao]:
    rng = random.Random(seed)
    cenarios = [
        (volume, dataset, arquitetura)
        for volume in _normalizar_volumes(volumes)
        for dataset in DATASETS
        for arquitetura in ARQUITETURAS
    ]
    plano: list[Execucao] = []
    fases = [("aquecimento", None), *[("medir", n) for n in range(1, rodadas + 1)]]
    for modo, rodada in fases:
        ordem_cenarios = cenarios.copy()
        rng.shuffle(ordem_cenarios)
        for volume, dataset, arquitetura in ordem_cenarios:
            ordem_condicoes = list(CONDICOES)
            rng.shuffle(ordem_condicoes)
            for posicao, condicao in enumerate(ordem_condicoes, start=1):
                plano.append(Execucao(
                    dataset, arquitetura, volume, condicao, INTERVALOS[condicao],
                    modo, rodada, posicao, len(plano) + 1,
                ))
    return plano


def comando(execucao: Execucao, resultado_bruto: Path | None) -> list[str]:
    argumentos = [
        sys.executable,
        str(BASE_DIR / "src" / execucao.dataset / f"{execucao.arquitetura}.py"),
        "--limite", str(execucao.volume), "--modo", execucao.modo,
    ]
    if execucao.rodada is not None:
        argumentos.extend(("--rodada", str(execucao.rodada)))
    if execucao.intervalo_segundos is None:
        argumentos.append("--sem-monitoramento")
    else:
        argumentos.extend(("--intervalo-monitoramento", str(execucao.intervalo_segundos)))
    if resultado_bruto is not None:
        argumentos.extend(("--benchmark-output", str(resultado_bruto)))
    return argumentos


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _commit_git() -> str | None:
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=BASE_DIR,
        capture_output=True, text=True, check=False,
    )
    return resultado.stdout.strip() if resultado.returncode == 0 else None


def _salvar_json(caminho: Path, conteudo: dict[str, object]) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporario.replace(caminho)


def _registrar(caminho: Path, linha: dict[str, object]) -> None:
    existe = caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_RESULTADO)
        if not existe:
            escritor.writeheader()
        escritor.writerow(linha)


def _ler_resultado_bruto(caminho: Path) -> dict[str, str]:
    if not caminho.is_file():
        raise RuntimeError(f"Pipeline nao gerou o resultado esperado: {caminho}")
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo, delimiter=";"))
    if len(linhas) != 1 or not linhas[0].get("tempo_total"):
        raise RuntimeError(f"Resultado bruto invalido: {caminho}")
    return linhas[0]


def _ler_numero_amostras(caminho: Path) -> int:
    if not caminho.is_file():
        raise RuntimeError(f"Pipeline nao registrou a contagem de amostras: {caminho}")
    try:
        quantidade = int(caminho.read_text(encoding="utf-8").strip())
    except ValueError as erro:
        raise RuntimeError(f"Contagem de amostras invalida: {caminho}") from erro
    if quantidade < 1:
        raise RuntimeError(f"Contagem de amostras deve ser positiva: {caminho}")
    return quantidade


def _validar_diagnostico_coletas(caminho: Path) -> int:
    if not caminho.is_file():
        raise RuntimeError(f"Pipeline nao gerou o diagnostico esperado: {caminho}")
    with caminho.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        campos_necessarios = {
            "origem", "inicio_perf_counter_ns", "duracao_coleta_ms",
            "intervalo_efetivo_ms", "intervalo_configurado_ms",
            "espera_efetiva_ms", "atraso_agendamento_ms",
        }
        if not campos_necessarios.issubset(leitor.fieldnames or []):
            raise RuntimeError(f"Colunas ausentes no diagnostico: {caminho}")
        linhas = list(leitor)
    if not linhas:
        raise RuntimeError(f"Diagnostico de coletas vazio: {caminho}")
    origens = [linha.get("origem") for linha in linhas]
    if origens.count("final") != 1 or "periodica" not in origens:
        raise RuntimeError(
            f"Diagnostico deve conter coletas periodicas e uma final: {caminho}"
        )
    return len(linhas)


def _validar_entradas(
    volumes: int | Sequence[int], rodadas: int, run_id: str
) -> dict[int, Path]:
    volumes_normalizados = _normalizar_volumes(volumes)
    if not volumes_normalizados or any(volume < 1 for volume in volumes_normalizados):
        raise ValueError("Volumes devem ser maiores que zero.")
    if len(set(volumes_normalizados)) != len(volumes_normalizados):
        raise ValueError("Volumes nao podem ser repetidos.")
    if rodadas < 1:
        raise ValueError("Rodadas devem ser maiores que zero.")
    if not RUN_ID_VALIDO.fullmatch(run_id):
        raise ValueError("run_id deve conter apenas letras, numeros, '.', '_' ou '-'.")
    manifestos = {
        volume: BASE_DIR / "data" / "benchmark" / "tse" / "subconjuntos" / f"chaves_{volume}.csv"
        for volume in volumes_normalizados
    }
    for manifesto in manifestos.values():
        if not manifesto.is_file():
            raise ValueError(f"Manifesto TSE ausente: {manifesto}")
    return manifestos


def executar_experimento(
    volumes: int | Sequence[int],
    rodadas: int,
    seed: int,
    run_id: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    resultados_base: Path = RESULTADOS_BASE,
) -> Path:
    volumes_normalizados = _normalizar_volumes(volumes)
    manifestos = _validar_entradas(volumes_normalizados, rodadas, run_id)
    diretorio = resultados_base / run_id
    diretorio.mkdir(parents=True, exist_ok=False)
    brutos = diretorio / "brutos"
    amostras = diretorio / "amostras"
    brutos.mkdir()
    amostras.mkdir()
    resultados_csv = diretorio / "resultados.csv"
    plano = criar_plano(volumes_normalizados, rodadas, seed)
    numero_cenarios = len(volumes_normalizados) * len(DATASETS) * len(ARQUITETURAS)
    metadados: dict[str, object] = {
        "run_id": run_id, "status": "em_andamento", "inicio": agora_iso(),
        "fim": None, "volumes": list(volumes_normalizados), "rodadas": rodadas,
        "seed": seed,
        "condicoes": [
            {"nome": condicao, "intervalo_segundos": INTERVALOS[condicao]}
            for condicao in CONDICOES
        ],
        "datasets": list(DATASETS), "arquiteturas": list(ARQUITETURAS),
        "aquecimentos": numero_cenarios * len(CONDICOES),
        "medicoes_validas": numero_cenarios * len(CONDICOES) * rodadas,
        "execucoes_previstas": len(plano), "execucoes_concluidas": 0,
        "python": sys.version, "plataforma": platform.platform(),
        "commit_git": _commit_git(),
        "manifestos_tse": [
            {"volume": volume, "caminho": str(caminho), "sha256": _sha256(caminho)}
            for volume, caminho in manifestos.items()
        ],
        "controle_dados": (
            "Dentro de cada volume, as tres condicoes usam o mesmo entrypoint, "
            "dados e manifesto; variam apenas monitoramento e intervalo."
        ),
        "plano": [asdict(item) for item in plano],
    }
    metadados_path = diretorio / "metadados.json"
    _salvar_json(metadados_path, metadados)
    ambiente_base = os.environ.copy()
    ambiente_base["BENCHMARK_RUN_ID"] = run_id
    ambiente_base["PYTHONIOENCODING"] = "utf-8"
    ambiente_base.pop(VAR_AMOSTRAS, None)
    ambiente_base.pop(VAR_DIAGNOSTICO, None)

    try:
        for item in plano:
            nome = (
                f"{item.ordem:03d}_{item.dataset}_{item.arquitetura}_"
                f"v{item.volume}_{item.condicao}"
            )
            bruto = brutos / f"{nome}.csv" if item.modo == "medir" else None
            contagem = amostras / f"{nome}.txt" if item.intervalo_segundos is not None else None
            ambiente = ambiente_base.copy()
            if contagem is not None:
                ambiente[VAR_AMOSTRAS] = str(contagem)
            inicio_iso = agora_iso()
            inicio = time.perf_counter()
            status = "sucesso"
            tempo_total: float | str = ""
            numero_amostras: int | str = ""
            try:
                runner(comando(item, bruto), cwd=BASE_DIR, env=ambiente, check=True)
                if bruto is not None:
                    linha_bruta = _ler_resultado_bruto(bruto)
                    tempo_total = float(linha_bruta["tempo_total"].replace(",", "."))
                if contagem is not None:
                    numero_amostras = _ler_numero_amostras(contagem)
            except BaseException:
                status = "falhou"
                raise
            finally:
                _registrar(resultados_csv, {
                    "dataset": item.dataset, "arquitetura": item.arquitetura,
                    "volume": item.volume, "condicao": item.condicao,
                    "intervalo_segundos": item.intervalo_segundos
                    if item.intervalo_segundos is not None else "",
                    "numero_amostras": numero_amostras, "modo": item.modo,
                    "rodada": item.rodada or "", "ordem_condicao": item.ordem_condicao,
                    "ordem": item.ordem, "seed": seed, "status": status,
                    "tempo_total": tempo_total,
                    "duracao_subprocesso": round(time.perf_counter() - inicio, 6),
                    "inicio": inicio_iso, "fim": agora_iso(),
                    "resultado_bruto": str(bruto.relative_to(diretorio)) if bruto else "",
                })
            metadados["execucoes_concluidas"] = item.ordem
            _salvar_json(metadados_path, metadados)
    except BaseException as erro:
        metadados["status"] = "falhou"
        metadados["fim"] = agora_iso()
        metadados["erro"] = f"{type(erro).__name__}: {erro}"
        _salvar_json(metadados_path, metadados)
        raise

    metadados["status"] = "concluido"
    metadados["fim"] = agora_iso()
    _salvar_json(metadados_path, metadados)
    return diretorio


def executar_diagnostico_coletas(
    volume: int,
    run_id: str,
    *,
    aquecimento: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    resultados_base: Path = RESULTADOS_BASE,
) -> Path:
    _validar_entradas(volume, 1, run_id)
    diretorio = resultados_base / run_id
    diretorio.mkdir(parents=True, exist_ok=False)
    brutos = diretorio / "brutos"
    amostras = diretorio / "amostras"
    diagnosticos = diretorio / "diagnosticos"
    brutos.mkdir()
    amostras.mkdir()
    diagnosticos.mkdir()

    metadados_path = diretorio / "metadados.json"
    metadados: dict[str, object] = {
        "run_id": run_id,
        "tipo": "diagnostico_duracao_coletas",
        "status": "em_andamento",
        "inicio": agora_iso(),
        "fim": None,
        "volume": volume,
        "intervalo_segundos": 0.1,
        "aquecimento_separado": aquecimento,
        "execucoes_medidas_previstas": len(DATASETS) * len(ARQUITETURAS),
        "execucoes_medidas_concluidas": 0,
        "python": sys.version,
        "plataforma": platform.platform(),
        "commit_git": _commit_git(),
        "arquivos": [],
    }
    _salvar_json(metadados_path, metadados)

    ambiente_base = os.environ.copy()
    ambiente_base["BENCHMARK_RUN_ID"] = run_id
    ambiente_base["PYTHONIOENCODING"] = "utf-8"
    ambiente_base.pop(VAR_AMOSTRAS, None)
    ambiente_base.pop(VAR_DIAGNOSTICO, None)

    try:
        ordem = 0
        for dataset in DATASETS:
            for arquitetura in ARQUITETURAS:
                ordem += 1
                if aquecimento:
                    execucao_aquecimento = Execucao(
                        dataset, arquitetura, volume, "monitor_0_1s", 0.1,
                        "aquecimento", None, 1, ordem,
                    )
                    runner(
                        comando(execucao_aquecimento, None),
                        cwd=BASE_DIR, env=ambiente_base.copy(), check=True,
                    )

                nome = f"{dataset}_{arquitetura}_v{volume}_monitor_0_1s"
                bruto = brutos / f"{nome}.csv"
                contagem = amostras / f"{nome}.txt"
                diagnostico = diagnosticos / f"{nome}.csv"
                ambiente = ambiente_base.copy()
                ambiente[VAR_AMOSTRAS] = str(contagem)
                ambiente[VAR_DIAGNOSTICO] = str(diagnostico)
                execucao = Execucao(
                    dataset, arquitetura, volume, "monitor_0_1s", 0.1,
                    "medir", 1, 1, ordem,
                )
                runner(comando(execucao, bruto), cwd=BASE_DIR, env=ambiente, check=True)
                resultado = _ler_resultado_bruto(bruto)
                numero_amostras = _ler_numero_amostras(contagem)
                numero_diagnosticos = _validar_diagnostico_coletas(diagnostico)
                if numero_diagnosticos != numero_amostras:
                    raise RuntimeError(
                        "Diagnostico e monitor registraram quantidades diferentes "
                        f"para {dataset} {arquitetura}: "
                        f"{numero_diagnosticos} != {numero_amostras}"
                    )
                arquivos = metadados["arquivos"]
                assert isinstance(arquivos, list)
                arquivos.append({
                    "dataset": dataset,
                    "arquitetura": arquitetura,
                    "resultado_bruto": str(bruto.relative_to(diretorio)),
                    "diagnostico": str(diagnostico.relative_to(diretorio)),
                    "numero_amostras": numero_amostras,
                    "tempo_total": resultado["tempo_total"],
                })
                metadados["execucoes_medidas_concluidas"] = ordem
                _salvar_json(metadados_path, metadados)
    except BaseException as erro:
        metadados["status"] = "falhou"
        metadados["fim"] = agora_iso()
        metadados["erro"] = f"{type(erro).__name__}: {erro}"
        _salvar_json(metadados_path, metadados)
        raise

    metadados["status"] = "concluido"
    metadados["fim"] = agora_iso()
    _salvar_json(metadados_path, metadados)
    return diretorio


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mede o overhead do monitor de CPU/RAM.")
    parser.add_argument("--volumes", type=int, nargs="+", default=[100_000])
    parser.add_argument("--rodadas", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261105)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--diagnostico-coletas", action="store_true",
        help="Executa somente um diagnostico a 0,1 s dos quatro pipelines.",
    )
    parser.add_argument(
        "--aquecimento-diagnostico", action="store_true",
        help="Executa um aquecimento nao instrumentado antes de cada diagnostico.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = criar_parser()
    args = parser.parse_args(argv)
    try:
        if args.aquecimento_diagnostico and not args.diagnostico_coletas:
            parser.error(
                "--aquecimento-diagnostico exige --diagnostico-coletas."
            )
        if args.diagnostico_coletas:
            if len(args.volumes) != 1:
                parser.error("O diagnostico exige exatamente um volume.")
            diretorio = executar_diagnostico_coletas(
                args.volumes[0], args.run_id,
                aquecimento=args.aquecimento_diagnostico,
            )
        else:
            diretorio = executar_experimento(
                args.volumes, args.rodadas, args.seed, args.run_id
            )
    except (ValueError, FileExistsError) as erro:
        parser.error(str(erro))
    print(f"Experimento concluido: {diretorio}")


if __name__ == "__main__":
    main()
