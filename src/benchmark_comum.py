from __future__ import annotations

from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import uuid

import psycopg2


VAR_IDENTIDADE = "BENCHMARK_IDENTIDADE_JSON"
PACOTES = ("pandas", "python-dotenv", "SQLAlchemy", "psycopg2-binary", "psutil")


def _git_commit(base_dir: Path) -> str:
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=base_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return resultado.stdout.strip() if resultado.returncode == 0 else "indisponivel"


def _git_worktree_limpo(base_dir: Path) -> bool:
    resultado = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=base_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return resultado.returncode == 0 and not resultado.stdout.strip()


def _versao_postgres() -> str:
    parametros: dict[str, object]
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if database_url:
        parametros = {"dsn": database_url}
    else:
        parametros = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
        }
    try:
        with psycopg2.connect(**parametros) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SHOW server_version")
                return str(cursor.fetchone()[0])
    except psycopg2.Error:
        return "indisponivel"


def criar_identidade(base_dir: Path, run_id: str | None = None) -> dict[str, str]:
    instante = datetime.now().astimezone()
    identificador = run_id or (
        instante.strftime("%Y%m%dT%H%M%S%z") + "-" + uuid.uuid4().hex[:8]
    )
    dependencias = ",".join(
        f"{pacote}=={importlib.metadata.version(pacote)}" for pacote in PACOTES
    )
    return {
        "run_id": identificador,
        "git_commit": _git_commit(base_dir),
        "git_worktree_limpo": str(_git_worktree_limpo(base_dir)).lower(),
        "python_versao": platform.python_version(),
        "postgresql_versao": _versao_postgres(),
        "dependencias": dependencias,
        "maquina": platform.node() or "indisponivel",
        "sistema": platform.platform(),
        "processador": platform.processor() or "indisponivel",
        "ram_python_metrica": "rss",
        "ram_postgresql_metrica": (
            "private_bytes" if platform.system() == "Windows" else "uss"
        ),
    }


def ambiente_com_identidade(identidade: dict[str, str]) -> dict[str, str]:
    ambiente = os.environ.copy()
    ambiente[VAR_IDENTIDADE] = json.dumps(identidade, ensure_ascii=False)
    ambiente["PYTHONIOENCODING"] = "utf-8"
    return ambiente


def salvar_campanha(
    base_dir: Path,
    identidade: dict[str, str],
    configuracao: dict[str, object],
) -> Path:
    pasta = base_dir / "data" / "benchmark" / "campanhas"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{identidade['run_id']}.json"
    conteudo = {
        **identidade,
        "criada_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        **configuracao,
    }
    caminho.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return caminho


def preparar_resultados(caminhos: list[Path], limpar: bool) -> None:
    existentes = [c for c in caminhos if c.exists() and c.stat().st_size > 0]
    if existentes and not limpar:
        lista = "\n".join(f"- {c}" for c in existentes)
        raise SystemExit(
            "A campanha deve comecar com CSVs vazios. Arquivos encontrados:\n"
            f"{lista}\nUse --limpar-resultados para iniciar uma nova campanha."
        )
    if limpar:
        for caminho in existentes:
            caminho.unlink()
