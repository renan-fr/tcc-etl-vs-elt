"""Diagnóstico não invasivo de USS no Windows para o TCC ETL x ELT.
Uso: python diagnostico_uss.py [--pg-root PID] [--samples 12] [--interval 0.5]
"""
import argparse
import platform
import sys
import time
import statistics

try:
    import psutil
except ImportError:
    sys.exit('psutil não instalado. Execute: python -m pip install psutil')

MB = 1024 ** 2


def uss_bytes(proc):
    # psutil 8 substituiu memory_full_info() por memory_footprint().
    if hasattr(proc, 'memory_footprint'):
        return proc.memory_footprint().uss
    return proc.memory_full_info().uss


def pg_candidates():
    found = []
    for p in psutil.process_iter(['pid', 'name', 'ppid']):
        try:
            if (p.info['name'] or '').lower() in ('postgres.exe', 'postgres'):
                found.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(found, key=lambda p: p.pid)


def get_tracked(root_pid):
    if root_pid is None:
        return []
    root = psutil.Process(root_pid)
    return [root] + root.children(recursive=True)


def main():
    ap = argparse.ArgumentParser(description='Verifica disponibilidade, latência e cobertura USS.')
    ap.add_argument('--pg-root', type=int, help='PID do processo raiz da instância PostgreSQL')
    ap.add_argument('--samples', type=int, default=12)
    ap.add_argument('--interval', type=float, default=0.5)
    args = ap.parse_args()
    if args.samples < 2 or args.interval <= 0:
        ap.error('Use pelo menos 2 amostras e intervalo positivo.')
    print('SO:', platform.platform(), '| Python:', platform.python_version(), '| psutil:', psutil.__version__)
    me = psutil.Process()
    print('\nProcesso Python (PID %d)' % me.pid)
    try:
        print('  RSS: %.2f MiB | USS: %.2f MiB' % (me.memory_info().rss / MB, uss_bytes(me) / MB))
    except (psutil.AccessDenied, AttributeError, NotImplementedError) as exc:
        sys.exit('USS do Python indisponível: %s' % exc)
    print('\nProcessos PostgreSQL encontrados (não presumir que todos pertencem ao benchmark):')
    found = pg_candidates()
    for p in found:
        try:
            print('  PID %d | PPID %d | RSS %.1f MiB | USS %.1f MiB' % (
                p.pid, p.ppid(), p.memory_info().rss / MB, uss_bytes(p) / MB))
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError, NotImplementedError) as exc:
            print('  PID %d | erro: %s' % (p.pid, exc))
    if not found:
        print('  Nenhum postgres.exe encontrado.')
    print('\nAVISO: a lista acima é apenas descoberta. Não somar instâncias distintas.')
    if args.pg_root is None:
        print('Para testar o agrupamento da instância, rode novamente com --pg-root PID,')
        print('após identificar qual PID é o processo raiz da instância de teste.')
    else:
        print('Raiz PostgreSQL selecionada:', args.pg_root)
        try:
            procs = get_tracked(args.pg_root)
            print('PIDs rastreados inicialmente:', [p.pid for p in procs])
            if not any(p.pid == args.pg_root for p in found):
                print('ATENÇÃO: o PID indicado não apareceu na lista de processos PostgreSQL.')
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            sys.exit('Raiz não acessível: %s' % exc)
    print('\nAmostragem (sem executar o pipeline):')
    costs = []
    interval_actual = []
    errors = 0
    prev = None
    start = time.perf_counter()
    for i in range(args.samples):
        target = start + i * args.interval
        time.sleep(max(0, target - time.perf_counter()))
        ts = time.perf_counter()
        if prev is not None:
            interval_actual.append(ts - prev)
        prev = ts
        stage = time.perf_counter()
        try:
            py_uss = uss_bytes(me)
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError, NotImplementedError):
            py_uss = None
            errors += 1
        pg_uss = 0
        count = 0
        if args.pg_root is not None:
            try:
                procs = get_tracked(args.pg_root)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                procs = []
                errors += 1
            for proc in procs:
                try:
                    pg_uss += uss_bytes(proc)
                    count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, NotImplementedError):
                    errors += 1
        cost = time.perf_counter() - stage
        costs.append(cost)
        print('  %02d | Python USS: %s | PostgreSQL: %s | PIDs PG: %d | coleta: %.1f ms' % (
            i+1, ('%.1f MiB' % (py_uss/MB)) if py_uss is not None else 'ERRO',
            ('%.1f MiB' % (pg_uss/MB)) if args.pg_root is not None else 'não selecionado',
            count, cost*1000))
    print('\nRESUMO')
    print('  Duração média da coleta: %.1f ms | máxima: %.1f ms' % (statistics.mean(costs)*1000, max(costs)*1000))
    if interval_actual:
        print('  Intervalo real médio: %.3f s | máximo: %.3f s' % (statistics.mean(interval_actual), max(interval_actual)))
    print('  Erros de acesso/leitura:', errors)
    if max(costs) >= args.interval:
        print('  ALERTA: coleta tão lenta quanto o intervalo planejado; rever amostragem.')
    print('  NOTA: ausência de erros não prova cobertura completa do PostgreSQL; validar árvore de processos.')
    print('  NOTA: este teste parado não valida comportamento sob carga. É apenas o primeiro diagnóstico.')


if __name__ == '__main__':
    main()
