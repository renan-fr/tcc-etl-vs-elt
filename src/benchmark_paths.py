"""Paths compartilhados para resultados isolados por campanha."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parents[1]
CAMPANHAS_DIR = BASE_DIR / "data" / "benchmark" / "campanhas"
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
MODALIDADES = ("desempenho", "recursos")
CAMPOS_IDENTIDADE = (
    "run_id",
    "modalidade",
    "dataset",
    "arquitetura",
    "volume_configurado",
    "rodada",
)


def validar_run_id(run_id: str) -> str:
    valor = run_id.strip()
    if not valor or not _RUN_ID_RE.fullmatch(valor):
        raise ValueError(
            "run_id deve conter apenas letras, números, ponto, hífen ou sublinhado."
        )
    return valor


def diretorio_campanha(run_id: str) -> Path:
    return CAMPANHAS_DIR / validar_run_id(run_id)


def criar_diretorio_campanha(run_id: str) -> Path:
    caminho = diretorio_campanha(run_id)
    try:
        caminho.mkdir(parents=True)
    except FileExistsError as erro:
        raise FileExistsError(
            f"A campanha '{run_id}' já existe em {caminho}; escolha outro run_id."
        ) from erro
    return caminho


def criar_diretorios_modalidades(campanha_dir: Path) -> None:
    for modalidade in MODALIDADES:
        (campanha_dir / modalidade).mkdir(exist_ok=True)


def diretorio_saida_obrigatorio() -> Path:
    valor = os.environ.get("BENCHMARK_OUTPUT_DIR")
    if not valor:
        raise RuntimeError(
            "BENCHMARK_OUTPUT_DIR não definido; execute pelo orquestrador "
            "ou informe o diretório da campanha."
        )
    caminho = Path(valor).resolve()
    try:
        caminho.relative_to(CAMPANHAS_DIR.resolve())
    except ValueError as erro:
        raise RuntimeError(
            f"Diretório de resultados fora de {CAMPANHAS_DIR}: {caminho}"
        ) from erro
    return caminho


def diretorio_modalidade_obrigatorio(modalidade: str) -> Path:
    if modalidade not in MODALIDADES:
        raise ValueError(f"Modalidade invalida: {modalidade!r}.")
    return diretorio_saida_obrigatorio() / modalidade


def validar_execucao_inedita(
    caminho: Path,
    linha: dict[str, object],
) -> None:
    """Recusa uma segunda linha com a mesma identidade experimental."""
    if not caminho.is_file() or caminho.stat().st_size == 0:
        return
    identidade = tuple(str(linha[campo]) for campo in CAMPOS_IDENTIDADE)
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        ausentes = set(CAMPOS_IDENTIDADE) - set(leitor.fieldnames or ())
        if ausentes:
            raise ValueError(
                f"{caminho}: colunas de identidade ausentes: {sorted(ausentes)}"
            )
        for existente in leitor:
            if tuple(existente[campo] for campo in CAMPOS_IDENTIDADE) == identidade:
                raise ValueError(
                    "Execucao duplicada para "
                    + ", ".join(
                        f"{campo}={linha[campo]!r}" for campo in CAMPOS_IDENTIDADE
                    )
                )
