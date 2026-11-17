"""Apresentacao compartilhada dos resultados dos pipelines oficiais."""

from __future__ import annotations

from typing import Any


def _formatar_recurso(
    resultado: Any,
    campo: str,
    unidade: str,
) -> str:
    if not resultado.monitoramento_ativo:
        return "não monitorado"
    valor = getattr(resultado, campo)
    if valor is None:
        return "não monitorado"
    return f"{valor:.2f}{unidade}"


def linhas_resultado_benchmark(resultado: Any) -> list[str]:
    """Formata somente as metricas ja consolidadas no objeto de resultado."""
    volume = (
        "todos"
        if resultado.volume_configurado is None
        else str(resultado.volume_configurado)
    )
    linhas = [
        f"Benchmark {resultado.dataset.upper()} {resultado.arquitetura.upper()}:",
        f"Volume configurado: {volume}",
        f"Quantidade de registros: {resultado.quantidade_registros}",
        f"Tempo de leitura: {resultado.tempo_leitura:.3f}s",
        f"Tempo de transformação: {resultado.tempo_transformacao:.3f}s",
        f"Tempo de carga: {resultado.tempo_carga:.3f}s",
        f"Tempo total: {resultado.tempo_total:.3f}s",
        f"Throughput: {resultado.throughput:.2f} registros/s",
    ]
    for rotulo, sufixo in (
        ("Python", "python"),
        ("PostgreSQL", "postgres"),
        ("Agregado", "total"),
    ):
        linhas.append(
            f"{rotulo} | "
            f"CPU média: {_formatar_recurso(resultado, f'cpu_media_{sufixo}', '%')} | "
            f"CPU pico: {_formatar_recurso(resultado, f'cpu_pico_{sufixo}', '%')} | "
            f"RAM USS média: "
            f"{_formatar_recurso(resultado, f'ram_media_{sufixo}_mb', ' MB')} | "
            f"RAM USS pico: "
            f"{_formatar_recurso(resultado, f'ram_pico_{sufixo}_mb', ' MB')}"
        )
    status_cpu_times = (
        resultado.cpu_times_status
        if resultado.monitoramento_ativo and resultado.cpu_times_status
        else "não monitorado"
    )
    linhas.append(
        "Tempo acumulado de CPU (cpu_times) | "
        f"Python: {_formatar_recurso(resultado, 'cpu_times_python_s', 's')} | "
        f"PostgreSQL: "
        f"{_formatar_recurso(resultado, 'cpu_times_postgres_s', 's')} | "
        f"Total: {_formatar_recurso(resultado, 'cpu_times_total_s', 's')} | "
        f"Status: {status_cpu_times}"
    )
    return linhas


def imprimir_resultado_benchmark(resultado: Any) -> None:
    """Exibe o resumo padronizado sem modificar ou recalcular metricas."""
    for linha in linhas_resultado_benchmark(resultado):
        print(linha)
