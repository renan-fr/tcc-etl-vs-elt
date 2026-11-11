"""Diagnóstico não oficial da coleta USS sob carga (Windows, psutil).

Exemplo (PowerShell como administrador, na raiz do repositório):
python tests/diagnostico_uss_carga.py --pg-root 6660 --output uss_carga.csv -- python src/enem/benchmark.py --certificar --volumes 100000

NÃO altera a instrumentação oficial. Executa o comando informado; portanto,
confira antes se o comando é seguro e não aponta para a campanha oficial.
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

import psutil

MIB = 1024 * 1024
ERRS = (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, AttributeError, NotImplementedError)


def uss(proc: psutil.Process) -> int:
    if hasattr(proc, "memory_footprint"):
        return proc.memory_footprint().uss
    return proc.memory_full_info().uss


def process_tree(root: psutil.Process) -> list[psutil.Process]:
    # Reavaliar a árvore a cada amostra para incluir processos criados durante a execução.
    return [root, *root.children(recursive=True)]


def collect(procs: list[psutil.Process]) -> tuple[int | None, int, list[str]]:
    total = 0
    good = 0
    errors = []
    for proc in procs:
        try:
            total += uss(proc)
            good += 1
        except ERRS as exc:
            errors.append(f"{proc.pid}:{type(exc).__name__}")
    return (total if good else None), good, errors


def mib(value: int | None) -> str:
    return f"{value / MIB:.1f}" if value is not None else "indisponível"


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa USS do processo de teste e PostgreSQL enquanto há carga real.")
    parser.add_argument("--pg-root", type=int, required=True, help="PID raiz confirmado da instância PostgreSQL")
    parser.add_argument("--interval", type=float, default=0.5, help="Intervalo alvo entre amostras, em segundos")
    parser.add_argument("--output", default="uss_carga.csv", help="Arquivo CSV de diagnóstico; não é resultado oficial")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Comando a executar, precedido de --")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval deve ser positivo")
    cmd = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not cmd:
        parser.error("informe o comando após --")
    # Recusa explícita de uma invocação potencialmente oficial; para testar,
    # use um wrapper de certificação/piloto conscientemente escolhido.
    if any(token.replace("\\", "/").lower().endswith("src/benchmark.py") for token in cmd):
        parser.error("não use o orquestrador global aqui; escolha um comando de teste/certificação não oficial")

    try:
        pg_root = psutil.Process(args.pg_root)
        if pg_root.name().lower() not in ("postgres.exe", "postgres"):
            parser.error(f"PID {args.pg_root} não é postgres.exe")
        _ = uss(pg_root)  # falha cedo se não houver acesso
    except ERRS as exc:
        parser.error(f"não foi possível acessar a raiz PostgreSQL/USS: {exc}. Use PowerShell administrador")

    output = Path(args.output)
    if output.exists():
        parser.error(f"arquivo já existe: {output}. Escolha outro --output para evitar sobrescrever")
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"PostgreSQL raiz: {pg_root.pid} | comando de teste: {cmd}", flush=True)
    print("Atenção: memória do PostgreSQL inclui processos da instância que podem estar ociosos; USS não inclui memória compartilhada.", flush=True)
    print("Este diagnóstico não mede o overhead causal da instrumentação e não produz resultados oficiais.", flush=True)

    # A coleta inicia logo após criar o processo: atividades muito curtas podem
    # terminar entre amostras e não terem seus picos capturados.
    proc = subprocess.Popen(cmd, cwd=os.getcwd())
    py_root = psutil.Process(proc.pid)
    print(f"PID Python do comando: {py_root.pid}", flush=True)
    cols = ["amostra", "segundos_desde_inicio", "python_uss_mib", "postgres_uss_mib", "soma_uss_mib", "pids_python", "pids_postgres", "erros", "custo_coleta_ms", "intervalo_real_s"]
    costs: list[float] = []
    gaps: list[float] = []
    rows = 0
    errors_total = 0
    prev = None
    start = time.perf_counter()
    next_sample = start

    try:
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=cols, delimiter=";")
            writer.writeheader()
            while True:
                time.sleep(max(0, next_sample - time.perf_counter()))
                now = time.perf_counter()
                gap = None if prev is None else now - prev
                prev = now
                if gap is not None:
                    gaps.append(gap)
                t0 = time.perf_counter()
                issues = []
                try:
                    py_procs = process_tree(py_root)
                    py_total, py_count, py_errors = collect(py_procs)
                    issues.extend(f"python:{x}" for x in py_errors)
                except ERRS as exc:
                    py_total, py_count = None, 0
                    issues.append(f"python_root:{type(exc).__name__}")
                try:
                    pg_procs = process_tree(pg_root)
                    pg_total, pg_count, pg_errors = collect(pg_procs)
                    issues.extend(f"postgres:{x}" for x in pg_errors)
                except ERRS as exc:
                    pg_total, pg_count = None, 0
                    issues.append(f"postgres_root:{type(exc).__name__}")
                elapsed_collect = time.perf_counter() - t0
                costs.append(elapsed_collect)
                errors_total += len(issues)
                combined = py_total + pg_total if py_total is not None and pg_total is not None and not issues else None
                rows += 1
                writer.writerow({
                    "amostra": rows,
                    "segundos_desde_inicio": f"{now - start:.6f}",
                    "python_uss_mib": "" if py_total is None else f"{py_total / MIB:.3f}",
                    "postgres_uss_mib": "" if pg_total is None else f"{pg_total / MIB:.3f}",
                    "soma_uss_mib": "" if combined is None else f"{combined / MIB:.3f}",
                    "pids_python": py_count,
                    "pids_postgres": pg_count,
                    "erros": "|".join(issues),
                    "custo_coleta_ms": f"{elapsed_collect * 1000:.3f}",
                    "intervalo_real_s": "" if gap is None else f"{gap:.6f}",
                })
                if rows <= 5 or rows % 10 == 0 or issues:
                    print(f"{rows:03d} | Python {mib(py_total)} MiB ({py_count} PIDs) | PG {mib(pg_total)} MiB ({pg_count} PIDs) | coleta {elapsed_collect*1000:.1f} ms | erros {len(issues)}", flush=True)
                if proc.poll() is not None:
                    break
                next_sample += args.interval
                if next_sample < time.perf_counter():
                    # Não acumular atraso caso a coleta demore demais.
                    next_sample = time.perf_counter()
    except KeyboardInterrupt:
        print("Interrompido pelo usuário; encerrando somente o processo de teste iniciado.", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Processo ainda ativo; interrompa-o manualmente, se necessário.", flush=True)
        return 130
    rc = proc.wait()
    print("\nRESUMO (diagnóstico, não campanha)")
    print(f"Comando terminou com código: {rc}")
    print(f"Amostras: {rows} | Erros de leitura: {errors_total}")
    print(f"Custo da coleta: média {statistics.mean(costs)*1000:.1f} ms | máximo {max(costs)*1000:.1f} ms")
    if gaps:
        print(f"Intervalo real: média {statistics.mean(gaps):.3f} s | máximo {max(gaps):.3f} s")
    if max(costs) >= args.interval:
        print("ALERTA: houve coleta igual ou mais lenta que o intervalo configurado.")
    print(f"CSV diagnóstico: {output}")
    print("Observação: o Python observado é o processo iniciado e seus descendentes; confirme se o comando realmente executou o pipeline esperado.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
