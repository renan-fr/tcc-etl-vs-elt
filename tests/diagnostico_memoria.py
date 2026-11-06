"""Diagnóstico independente das métricas de memória expostas pelo psutil.

Este script não importa os pipelines, não acessa bancos e não altera processos.
Ele mede o processo Python atual, processos cujo nome contém ``postgres`` e o
custo agregado de enumerar/coletar esses processos.
"""

from __future__ import annotations

from dataclasses import dataclass
import platform
import statistics
import sys
import time
from typing import Callable, Iterable

import psutil


REPETICOES = 20
PADRAO_POSTGRES = "postgres"


@dataclass(frozen=True)
class ResultadoChamada:
    status: str
    valor: int | None = None
    detalhe: str | None = None


@dataclass(frozen=True)
class EstatisticasTempo:
    media_ms: float
    mediana_ms: float
    minimo_ms: float
    maximo_ms: float


def classificar_excecao(erro: BaseException) -> tuple[str, str]:
    if isinstance(erro, (psutil.NoSuchProcess, psutil.ZombieProcess)):
        return "encerrado", str(erro) or type(erro).__name__
    if isinstance(erro, psutil.AccessDenied):
        return "permissao", str(erro) or type(erro).__name__
    if isinstance(erro, AttributeError):
        return "indisponivel", str(erro) or type(erro).__name__
    if isinstance(erro, psutil.Error):
        return "erro_psutil", str(erro) or type(erro).__name__
    return "erro", f"{type(erro).__name__}: {erro}"


def medir_chamada(
    chamada: Callable[[], int],
) -> tuple[ResultadoChamada, float]:
    inicio = time.perf_counter()
    try:
        resultado = ResultadoChamada(status="ok", valor=chamada())
    except BaseException as erro:  # preserva a classificação sem zerar falhas
        status, detalhe = classificar_excecao(erro)
        resultado = ResultadoChamada(status=status, detalhe=detalhe)
    duracao = (time.perf_counter() - inicio) * 1000
    return resultado, duracao


def estatisticas(duracoes_ms: Iterable[float]) -> EstatisticasTempo:
    valores = list(duracoes_ms)
    return EstatisticasTempo(
        media_ms=statistics.fmean(valores),
        mediana_ms=statistics.median(valores),
        minimo_ms=min(valores),
        maximo_ms=max(valores),
    )


def formatar_estatisticas(valor: EstatisticasTempo) -> str:
    return (
        f"media={valor.media_ms:.3f} ms, "
        f"mediana={valor.mediana_ms:.3f} ms, "
        f"min={valor.minimo_ms:.3f} ms, "
        f"max={valor.maximo_ms:.3f} ms"
    )


def obter_memoria_info(processo: psutil.Process) -> object:
    return processo.memory_info()


def obter_rss(processo: psutil.Process) -> int:
    return processo.memory_info().rss


def obter_private(processo: psutil.Process) -> int:
    memoria = processo.memory_info()
    return getattr(memoria, "private")


def obter_uss(processo: psutil.Process) -> int:
    memoria = processo.memory_full_info()
    return memoria.uss


def medir_metrica(
    processo: psutil.Process,
    nome: str,
    chamada: Callable[[psutil.Process], int],
) -> tuple[ResultadoChamada, EstatisticasTempo]:
    resultados: list[ResultadoChamada] = []
    duracoes: list[float] = []
    for _ in range(REPETICOES):
        resultado, duracao = medir_chamada(lambda: chamada(processo))
        resultados.append(resultado)
        duracoes.append(duracao)

    status = {item.status for item in resultados}
    if status == {"ok"}:
        resumo = f"ok; amostra={resultados[-1].valor} bytes"
    elif len(status) == 1:
        detalhe = next((item.detalhe for item in resultados if item.detalhe), "")
        resumo = f"{next(iter(status))}; detalhe={detalhe}"
    else:
        resumo = f"status_variados={','.join(sorted(status))}"
    print(f"    {nome:<8} {resumo}")
    return resultados[-1], estatisticas(duracoes)


def medir_processo(processo: psutil.Process, rotulo: str) -> None:
    try:
        nome = processo.name()
    except BaseException as erro:
        status, detalhe = classificar_excecao(erro)
        nome = f"<indisponivel: {status}; {detalhe}>"

    print(f"  {rotulo}: pid={processo.pid}, nome={nome}")
    metricas = (
        ("rss", obter_rss),
        ("private", obter_private),
        ("uss", obter_uss),
    )
    for nome_metrica, chamada in metricas:
        _, tempos = medir_metrica(processo, nome_metrica, chamada)
        print(f"      custo {nome_metrica:<7} {formatar_estatisticas(tempos)}")


def encontrar_postgres(
    *, exibir_falhas: bool = True, falhas: list[str] | None = None
) -> list[psutil.Process]:
    encontrados: list[psutil.Process] = []
    try:
        processos = psutil.process_iter(["name"])
        for processo in processos:
            nome = (processo.info.get("name") or "").lower()
            if PADRAO_POSTGRES in nome:
                encontrados.append(processo)
    except BaseException as erro:
        status, detalhe = classificar_excecao(erro)
        if falhas is not None:
            falhas.append(status)
        if exibir_falhas:
            print(
                f"  falha durante enumeração de processos: "
                f"status={status}; detalhe={detalhe}"
            )
    return encontrados


def coletar_agregado_postgres() -> tuple[int, list[int], dict[str, int | str]]:
    falhas_enumeracao: list[str] = []
    processos = encontrar_postgres(
        exibir_falhas=False, falhas=falhas_enumeracao
    )
    contagens = {"ok": 0, "indisponivel": 0, "permissao": 0, "encerrado": 0, "erro": 0}
    contagens["enumeracao"] = falhas_enumeracao[0] if falhas_enumeracao else "ok"
    for processo in processos:
        for chamada in (obter_rss, obter_private, obter_uss):
            try:
                chamada(processo)
                contagens["ok"] += 1
            except BaseException as erro:
                status, _ = classificar_excecao(erro)
                contagens[status] = contagens.get(status, 0) + 1
    return len(processos), [processo.pid for processo in processos], contagens


def medir_agregado_postgres() -> None:
    duracoes: list[float] = []
    quantidades: list[int] = []
    pids_ultima: list[int] = []
    contagens_ultima: dict[str, int | str] = {}
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        quantidade, pids, contagens = coletar_agregado_postgres()
        duracoes.append((time.perf_counter() - inicio) * 1000)
        quantidades.append(quantidade)
        pids_ultima = pids
        contagens_ultima = contagens

    print("  custo agregado enumeração + coleta PostgreSQL:")
    print(f"    {formatar_estatisticas(estatisticas(duracoes))}")
    print(
        f"    processos por repetição: min={min(quantidades)}, "
        f"max={max(quantidades)}, última={quantidades[-1]}"
    )
    print(f"    PIDs da última repetição: {pids_ultima or 'nenhum'}")
    print(f"    estados das chamadas da última repetição: {contagens_ultima}")


def main() -> None:
    print("Diagnóstico de memória psutil")
    print(f"psutil: {psutil.__version__}")
    print(f"sistema: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"repetições por medição: {REPETICOES}")
    print()

    processo_atual = psutil.Process()
    print("Processo Python atual")
    medir_processo(processo_atual, "Python")
    print()

    processos_postgres = encontrar_postgres()
    print(f"Processos PostgreSQL identificados por nome contendo '{PADRAO_POSTGRES}':")
    print(f"  quantidade: {len(processos_postgres)}")
    print(f"  PIDs: {[processo.pid for processo in processos_postgres] or 'nenhum'}")
    for indice, processo in enumerate(processos_postgres, start=1):
        medir_processo(processo, f"PostgreSQL #{indice}")
    if not processos_postgres:
        print("  nenhum processo disponível para medições individuais")
    print()

    medir_agregado_postgres()
    print()
    print("Observação: valores do ambiente atual são diagnósticos, não resultados oficiais do TCC.")


if __name__ == "__main__":
    main()
