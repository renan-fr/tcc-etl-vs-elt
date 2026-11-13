"""Monitoramento compartilhado de CPU e RAM para os benchmarks.

CPU e expressa em percentual de um nucleo logico. Portanto, a soma de
processos pode legitimamente ultrapassar 100%; nenhuma normalizacao pelo
numero de CPUs e aplicada.
"""

from __future__ import annotations

import ipaddress
import math
import socket
import threading
import time
from typing import Any, Callable

import psutil


class ErroMonitoramentoRecursos(RuntimeError):
    """Falha que torna uma medicao de recursos invalida."""


_monitor_ativo: MonitorRecursos | None = None
_monitor_ativo_lock = threading.Lock()


def _nome_postgres(processo: psutil.Process) -> bool:
    return "postgres" in processo.name().lower()


def _conexao_e_local(conexao: Any) -> bool:
    info = getattr(conexao, "info", None)
    host = getattr(info, "host", None)
    if not host:
        return True
    host = str(host).strip().lower().rstrip(".")
    if host in {"localhost", socket.gethostname().lower(), socket.getfqdn().lower()}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def vincular_conexao_postgres(conexao: Any) -> None:
    """Vincula a conexao ao monitor ativo sem executar uma consulta SQL."""
    with _monitor_ativo_lock:
        monitor = _monitor_ativo
    if monitor is not None:
        try:
            monitor.vincular_conexao_postgres(conexao)
        except BaseException:
            monitor._abortar()
            try:
                conexao.close()
            except BaseException:
                pass
            raise


class MonitorRecursos:
    """Amostra recursos do Python e da instancia PostgreSQL conectada."""

    def __init__(
        self,
        intervalo_segundos: float = 0.5,
        *,
        relogio: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.intervalo_segundos = intervalo_segundos
        self._relogio = relogio
        self._processo_python = psutil.Process()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._amostras: list[dict[str, float | bool | None]] = []
        self._processos_postgres: dict[tuple[int, float], psutil.Process] = {}
        self._raiz_postgres: psutil.Process | None = None
        self._identidade_raiz: tuple[int, float] | None = None
        self._postgres_vinculado = False
        self._ultimo_instante: float | None = None
        self._ultimo_instante_postgres: float | None = None
        self._erro_thread: BaseException | None = None
        self._lock = threading.RLock()
        self._resultado: dict[str, float | None] | None = None
        self._memoria_disponivel_inicial: int | None = None
        # Medicao experimental: nao participa de _consolidar() nem dos CSVs.
        self._cpu_times_python_anterior: tuple[float, float] | None = None
        self._cpu_times_postgres_anteriores: dict[
            tuple[int, float], tuple[float, float] | None
        ] = {}
        self._cpu_times_acumulado_python = 0.0
        self._cpu_times_acumulado_postgres = 0.0
        self._cpu_times_leituras_validas = 0
        self._cpu_times_leituras_validas_python = 0
        self._cpu_times_leituras_validas_postgres = 0
        self._cpu_times_python_incompleto = False
        self._cpu_times_processos_incompletos: set[tuple[int, float]] = set()
        self._cpu_times_processos_ja_encerrados: set[tuple[int, float]] = set()
        self._cpu_times_processos_novos = 0
        self._cpu_times_processos_encerrados = 0

    def iniciar(self) -> None:
        global _monitor_ativo
        with _monitor_ativo_lock:
            if _monitor_ativo is not None and _monitor_ativo is not self:
                raise ErroMonitoramentoRecursos("Ja existe um monitor de recursos ativo.")
            _monitor_ativo = self
        try:
            self._parar.clear()
            self._memoria_disponivel_inicial = self._ler_memoria_disponivel()
            self._processo_python.cpu_percent(interval=None)
            self._cpu_times_python_anterior = self._ler_cpu_times(
                self._processo_python, "Python"
            )
            self._ultimo_instante = self._relogio()
            self._thread = threading.Thread(target=self._coletar, daemon=True)
            self._thread.start()
        except BaseException:
            self._desregistrar()
            raise

    def vincular_conexao_postgres(self, conexao: Any) -> None:
        if not _conexao_e_local(conexao):
            raise ErroMonitoramentoRecursos(
                "Nao e possivel identificar com seguranca os processos de uma "
                "instancia PostgreSQL remota."
            )
        try:
            pid_backend = int(conexao.get_backend_pid())
            backend = psutil.Process(pid_backend)
            if not _nome_postgres(backend):
                raise ErroMonitoramentoRecursos(
                    f"O PID de backend {pid_backend} nao pertence a um processo PostgreSQL."
                )
            raiz = backend
            while True:
                pai = raiz.parent()
                if pai is None or not _nome_postgres(pai):
                    break
                raiz = pai
        except ErroMonitoramentoRecursos:
            raise
        except (psutil.NoSuchProcess, psutil.ZombieProcess) as erro:
            raise ErroMonitoramentoRecursos(
                "O backend PostgreSQL encerrou durante sua identificacao."
            ) from erro
        except psutil.AccessDenied as erro:
            raise ErroMonitoramentoRecursos(
                "Acesso negado ao identificar a instancia PostgreSQL conectada."
            ) from erro
        except (AttributeError, TypeError, ValueError) as erro:
            raise ErroMonitoramentoRecursos(
                "A conexao nao expoe um PID de backend PostgreSQL valido."
            ) from erro

        with self._lock:
            primeira_vinculacao = self._raiz_postgres is None
            if primeira_vinculacao and self._ultimo_instante is not None:
                # Fecha o intervalo Python anterior a conexao. Em seguida,
                # Python e PostgreSQL passam a compartilhar a mesma fronteira
                # logica, sem descartar o trabalho feito antes da conexao.
                self._registrar_amostra()
            if self._raiz_postgres is not None:
                try:
                    identidade_atual = self._identidade(self._raiz_postgres)
                    identidade_nova = self._identidade(raiz)
                except (psutil.NoSuchProcess, psutil.ZombieProcess) as erro:
                    raise ErroMonitoramentoRecursos(
                        "A raiz da instancia PostgreSQL encerrou durante a medicao."
                    ) from erro
                except psutil.AccessDenied as erro:
                    raise ErroMonitoramentoRecursos(
                        "Acesso negado ao confirmar a instancia PostgreSQL."
                    ) from erro
                if identidade_atual != identidade_nova:
                    raise ErroMonitoramentoRecursos(
                        "Foram detectadas conexoes com instancias PostgreSQL locais diferentes."
                    )
            self._raiz_postgres = raiz
            self._identidade_raiz = self._identidade(raiz)
            self._descobrir_e_inicializar_processos()
            self._postgres_vinculado = True
            if primeira_vinculacao:
                self._processo_python.cpu_percent(interval=None)
                fronteira = self._relogio()
                self._ultimo_instante = fronteira
                self._ultimo_instante_postgres = fronteira

    def parar(self) -> dict[str, float | None]:
        if self._resultado is not None:
            return dict(self._resultado)
        self._parar.set()
        if self._thread is not None:
            self._thread.join()
        try:
            if self._erro_thread is not None:
                raise ErroMonitoramentoRecursos(
                    "Falha na thread de monitoramento de recursos."
                ) from self._erro_thread
            self._registrar_amostra()
            self._resultado = self._consolidar()
            return dict(self._resultado)
        finally:
            self._desregistrar()

    def _desregistrar(self) -> None:
        global _monitor_ativo
        with _monitor_ativo_lock:
            if _monitor_ativo is self:
                _monitor_ativo = None

    def _abortar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join()
        self._desregistrar()

    def _coletar(self) -> None:
        try:
            proxima_coleta = self._relogio() + self.intervalo_segundos

            while not self._parar.is_set():
                espera = max(0.0, proxima_coleta - self._relogio())

                if self._parar.wait(espera):
                    break

                self._registrar_amostra()

                proxima_coleta += self.intervalo_segundos

                # Se uma coleta ultrapassar o prazo, pula os
                # horarios perdidos sem executar coletas sobrepostas.
                agora = self._relogio()
                if proxima_coleta <= agora:
                    intervalos_perdidos = (
                        int((agora - proxima_coleta) // self.intervalo_segundos) + 1
                    )
                    proxima_coleta += (
                        intervalos_perdidos * self.intervalo_segundos
                    )

        except BaseException as erro:
            self._erro_thread = erro
            self._parar.set()

    @staticmethod
    def _identidade(processo: psutil.Process) -> tuple[int, float]:
        return processo.pid, processo.create_time()

    def _descobrir_e_inicializar_processos(self) -> set[tuple[int, float]]:
        raiz = self._raiz_postgres
        if raiz is None:
            return set()
        try:
            if self._identidade(raiz) != self._identidade_raiz:
                raise ErroMonitoramentoRecursos(
                    "A raiz da instancia PostgreSQL mudou de PID ou foi substituida."
                )
            candidatos = [raiz, *raiz.children(recursive=True)]
        except ErroMonitoramentoRecursos:
            raise
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return set()
        except psutil.AccessDenied as erro:
            raise ErroMonitoramentoRecursos(
                "Acesso negado ao enumerar processos da instancia PostgreSQL."
            ) from erro

        novos: set[tuple[int, float]] = set()
        for processo in candidatos:
            try:
                identidade = self._identidade(processo)
                if identidade in self._processos_postgres:
                    continue
                if not _nome_postgres(processo):
                    continue
                processo.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied as erro:
                raise ErroMonitoramentoRecursos(
                    f"Acesso negado ao inicializar CPU do processo PostgreSQL {processo.pid}."
                ) from erro
            for identidade_antiga in list(self._processos_postgres):
                if (
                    identidade_antiga[0] == identidade[0]
                    and identidade_antiga != identidade
                ):
                    self._processos_postgres.pop(identidade_antiga)
                    self._cpu_times_postgres_anteriores.pop(identidade_antiga, None)
                    self._cpu_times_processos_incompletos.add(identidade_antiga)
                    self._cpu_times_processos_encerrados += 1
            self._processos_postgres[identidade] = processo
            self._inicializar_cpu_times_postgres(identidade, processo)
            novos.add(identidade)
        return novos

    @staticmethod
    def _ler_cpu(processo: psutil.Process, rotulo: str) -> float | None:
        try:
            return float(processo.cpu_percent(interval=None))
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return None
        except psutil.AccessDenied as erro:
            raise ErroMonitoramentoRecursos(
                f"Acesso negado ao ler CPU de {rotulo} (PID {processo.pid})."
            ) from erro

    @staticmethod
    def _ler_cpu_times(
        processo: psutil.Process, rotulo: str
    ) -> tuple[float, float] | None:
        """Le user/system sem tornar a medicao oficial dependente do experimento."""
        try:
            tempos = processo.cpu_times()
            user = float(tempos.user)
            system = float(tempos.system)
            if not math.isfinite(user) or not math.isfinite(system):
                return None
            return user, system
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            return None
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _delta_cpu_times(
        anterior: tuple[float, float] | None,
        atual: tuple[float, float] | None,
    ) -> float | None:
        if anterior is None or atual is None:
            return None
        delta_user = atual[0] - anterior[0]
        delta_system = atual[1] - anterior[1]
        if (
            not math.isfinite(delta_user)
            or not math.isfinite(delta_system)
            or delta_user < 0
            or delta_system < 0
        ):
            return None
        delta = delta_user + delta_system
        return delta if math.isfinite(delta) else None

    def _inicializar_cpu_times_postgres(
        self,
        identidade: tuple[int, float],
        processo: psutil.Process,
    ) -> None:
        """Estabelece a fronteira do processo novo sem contar CPU anterior."""
        atual = self._ler_cpu_times(processo, "PostgreSQL")
        self._cpu_times_postgres_anteriores[identidade] = atual
        self._cpu_times_processos_novos += 1
        if atual is None:
            self._cpu_times_processos_incompletos.add(identidade)

    def _registrar_cpu_times_amostra(
        self,
        novos: set[tuple[int, float]],
    ) -> None:
        """Acumula deltas uma vez por amostra, mantendo identidades PID/create_time."""
        atual_python = self._ler_cpu_times(self._processo_python, "Python")
        delta_python = self._delta_cpu_times(
            self._cpu_times_python_anterior, atual_python
        )
        if delta_python is not None:
            self._cpu_times_acumulado_python += delta_python
            self._cpu_times_leituras_validas += 1
            self._cpu_times_leituras_validas_python += 1
        elif delta_python is None:
            self._cpu_times_python_incompleto = True
        self._cpu_times_python_anterior = atual_python

        for identidade, processo in list(self._processos_postgres.items()):
            if identidade in novos or identidade in self._cpu_times_processos_ja_encerrados:
                continue
            atual = self._ler_cpu_times(processo, "PostgreSQL")
            anterior = self._cpu_times_postgres_anteriores.get(identidade)
            delta = self._delta_cpu_times(anterior, atual)
            if delta is not None:
                self._cpu_times_acumulado_postgres += delta
                self._cpu_times_leituras_validas += 1
                self._cpu_times_leituras_validas_postgres += 1
            else:
                self._cpu_times_processos_incompletos.add(identidade)
                if atual is None:
                    self._cpu_times_processos_encerrados += 1
                    self._cpu_times_postgres_anteriores.pop(identidade, None)
                    self._cpu_times_processos_ja_encerrados.add(identidade)
                    continue
            self._cpu_times_postgres_anteriores[identidade] = atual

    def consolidar_cpu_times_experimental(
        self,
    ) -> dict[str, float | int | None | str]:
        """Retorna a medicao experimental sem alterar o resultado oficial.

        ``None`` nos acumulados indica que nao houve delta valido. Processos
        novos sao contabilizados a partir da primeira fronteira observada;
        processos encerrados antes da ultima leitura podem ter consumo final
        desconhecido e aparecem em ``processos_incompletos``.
        """
        with self._lock:
            python = (
                self._cpu_times_acumulado_python
                if self._cpu_times_leituras_validas_python
                else None
            )
            postgres = (
                self._cpu_times_acumulado_postgres
                if self._cpu_times_leituras_validas_postgres
                else None
            )
            total = (
                python + postgres
                if python is not None and postgres is not None
                else None
            )
            integrados = self._integrar_cpu_percent_experimental()
            return {
                "cpu_times_python_s": python,
                "cpu_times_postgres_s": postgres,
                "cpu_times_total_s": total,
                "cpu_times_integrado_percent_python_s": integrados[0],
                "cpu_times_integrado_percent_postgres_s": integrados[1],
                "cpu_times_integrado_percent_total_s": integrados[2],
                "cpu_times_leituras_validas": self._cpu_times_leituras_validas,
                "cpu_times_leituras_validas_python": (
                    self._cpu_times_leituras_validas_python
                ),
                "cpu_times_leituras_validas_postgres": (
                    self._cpu_times_leituras_validas_postgres
                ),
                "cpu_times_processos_novos": self._cpu_times_processos_novos,
                "cpu_times_processos_encerrados": self._cpu_times_processos_encerrados,
                "cpu_times_processos_incompletos": len(
                    self._cpu_times_processos_incompletos
                ) + int(self._cpu_times_python_incompleto),
                "cpu_times_status": (
                    "parcial_ha_processos_incompletos"
                    if self._cpu_times_processos_incompletos
                    or self._cpu_times_python_incompleto
                    else "sem_leituras_validas"
                    if self._cpu_times_leituras_validas == 0
                    else "valida"
                ),
            }

    def _integrar_cpu_percent_experimental(self) -> tuple[float, float, float]:
        python = 0.0
        postgres = 0.0
        for amostra in self._amostras:
            duracao_python = amostra.get("duracao_cpu_python")
            valor_python = amostra.get("cpu_python")
            if duracao_python is not None and valor_python is not None:
                python += float(valor_python) / 100.0 * float(duracao_python)
            if amostra.get("cpu_postgres_convencional", False):
                continue
            duracao_postgres = amostra.get("duracao_cpu_postgres")
            valor_postgres = amostra.get("cpu_postgres")
            if duracao_postgres is not None and valor_postgres is not None:
                postgres += float(valor_postgres) / 100.0 * float(duracao_postgres)
        return python, postgres, python + postgres

    @staticmethod
    def _ler_ram_python(processo: psutil.Process) -> int | None:
        try:
            memoria = processo.memory_full_info()
            return int(memoria.uss)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            # O processo pode terminar entre a descoberta e a leitura. Isso
            # invalida esta amostra, mas nao e uma falha do monitor.
            return None
        except psutil.AccessDenied as erro:
            raise ErroMonitoramentoRecursos(
                f"Acesso negado ao ler USS de Python (PID {processo.pid})."
            ) from erro
        except AttributeError as erro:
            raise ErroMonitoramentoRecursos(
                "USS nao esta disponivel para o processo Python."
            ) from erro

    @staticmethod
    def _ler_memoria_disponivel() -> int:
        try:
            return int(psutil.virtual_memory().available)
        except (AttributeError, psutil.Error) as erro:
            raise ErroMonitoramentoRecursos(
                "Memoria disponivel do sistema nao esta disponivel."
            ) from erro

    @staticmethod
    def _ler_ram_postgres(
        processo: psutil.Process,
        identidade_esperada: tuple[int, float],
    ) -> int | None:
        try:
            memoria = processo.memory_full_info()
            return int(memoria.uss)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return None
        except psutil.AccessDenied as erro_inicial:
            try:
                processo_atual = psutil.Process(processo.pid)
                identidade_atual = (
                    processo_atual.pid,
                    processo_atual.create_time(),
                )
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                return None
            except psutil.AccessDenied as erro:
                raise ErroMonitoramentoRecursos(
                    "Acesso negado ao revalidar a identidade do processo "
                    f"PostgreSQL (PID {processo.pid})."
                ) from erro
            except Exception as erro:
                raise ErroMonitoramentoRecursos(
                    "Falha ao revalidar a identidade do processo PostgreSQL "
                    f"(PID {processo.pid})."
                ) from erro

            if identidade_atual != identidade_esperada:
                return None

            try:
                memoria = processo_atual.memory_full_info()
                return int(memoria.uss)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                return None
            except psutil.AccessDenied as erro:
                raise ErroMonitoramentoRecursos(
                    f"Acesso negado ao ler USS de PostgreSQL (PID {processo.pid})."
                ) from erro
            except AttributeError as erro:
                raise ErroMonitoramentoRecursos(
                    "USS nao esta disponivel para um processo PostgreSQL."
                ) from erro
        except AttributeError as erro:
            raise ErroMonitoramentoRecursos(
                "USS nao esta disponivel para um processo PostgreSQL."
            ) from erro

    def _registrar_amostra(self) -> None:
        with self._lock:
            agora = self._relogio()
            if self._ultimo_instante is None:
                self._ultimo_instante = agora
                return
            if self._memoria_disponivel_inicial is None:
                self._memoria_disponivel_inicial = self._ler_memoria_disponivel()
            duracao = agora - self._ultimo_instante
            if duracao <= 0:
                raise ErroMonitoramentoRecursos("Intervalo de amostragem de CPU invalido.")

            novos = self._descobrir_e_inicializar_processos()
            self._registrar_cpu_times_amostra(novos)
            memoria_disponivel = self._ler_memoria_disponivel()
            cpu_python = self._ler_cpu(self._processo_python, "Python")
            ram_python = self._ler_ram_python(self._processo_python)

            cpu_postgres_convencional = not self._postgres_vinculado
            if cpu_postgres_convencional:
                cpu_postgres = 0.0
                duracao_postgres = duracao
            else:
                cpu_postgres_validas: list[float] = []
                encerrados: list[tuple[int, float]] = []
                for identidade, processo in list(self._processos_postgres.items()):
                    if identidade in novos:
                        continue
                    valor = self._ler_cpu(processo, "PostgreSQL")
                    if valor is None:
                        encerrados.append(identidade)
                    else:
                        cpu_postgres_validas.append(valor)
                for identidade in encerrados:
                    self._processos_postgres.pop(identidade, None)

                cpu_postgres = (
                    sum(cpu_postgres_validas) if cpu_postgres_validas else None
                )
                duracao_postgres = (
                    agora - self._ultimo_instante_postgres
                    if self._ultimo_instante_postgres is not None
                    else None
                )
            intervalos_compativeis = (
                duracao_postgres is not None
                and abs(duracao - duracao_postgres) <= 1e-9
            )
            cpu_total = (
                cpu_python + cpu_postgres
                if (
                    cpu_python is not None
                    and cpu_postgres is not None
                    and intervalos_compativeis
                )
                else None
            )
            # Antes da primeira vinculacao, PostgreSQL participa por
            # convencao: zero nao e uma leitura de USS. Depois da
            # vinculacao, a soma vem exclusivamente das leituras USS da
            # arvore da instancia. Um processo encerrado durante USS
            # invalida a amostra, nunca e convertido em zero.
            ram_postgres: int | None = 0
            ram_postgres_convencional = not self._postgres_vinculado
            ram_postgres_incompleta = False
            if self._postgres_vinculado:
                for identidade, processo in list(self._processos_postgres.items()):
                    valor = self._ler_ram_postgres(processo, identidade)
                    if valor is None:
                        ram_postgres_incompleta = True
                        self._processos_postgres.pop(identidade, None)
                    else:
                        ram_postgres += valor
            if ram_postgres_incompleta:
                ram_postgres = None
            ram_total = (
                ram_python + ram_postgres
                if ram_python is not None and ram_postgres is not None
                else None
            )
            self._amostras.append(
                {
                    "duracao_cpu_python": duracao,
                    "duracao_cpu_postgres": duracao_postgres,
                    "duracao_cpu_total": duracao if cpu_total is not None else None,
                    "cpu_python": cpu_python,
                    "ram_python": (
                        float(ram_python) if ram_python is not None else None
                    ),
                    "cpu_postgres": cpu_postgres,
                    "cpu_postgres_convencional": cpu_postgres_convencional,
                    "ram_postgres": (
                        float(ram_postgres) if ram_postgres is not None else None
                    ),
                    "ram_postgres_convencional": ram_postgres_convencional,
                    "cpu_total": cpu_total,
                    "ram_total": float(ram_total) if ram_total is not None else None,
                    "memoria_disponivel": float(memoria_disponivel),
                }
            )
            self._ultimo_instante = agora
            if self._ultimo_instante_postgres is not None:
                self._ultimo_instante_postgres = agora

    def _consolidar(self) -> dict[str, float | None]:
        def cpu(chave: str, pico: bool = False) -> float:
            chave_duracao = f"duracao_{chave}"
            if chave in {"cpu_postgres", "cpu_total"} and not any(
                amostra[chave] is not None
                and not amostra.get("cpu_postgres_convencional", False)
                for amostra in self._amostras
            ):
                raise ErroMonitoramentoRecursos(
                    f"Nenhuma leitura valida foi obtida para {chave}."
                )
            valores = [
                (float(amostra[chave]), float(amostra[chave_duracao]))
                for amostra in self._amostras
                if (
                    amostra[chave] is not None
                    and amostra[chave_duracao] is not None
                )
            ]
            if not valores:
                raise ErroMonitoramentoRecursos(
                    f"Nenhuma leitura valida foi obtida para {chave}."
                )
            if pico:
                return max(valor for valor, _ in valores)
            tempo = sum(duracao for _, duracao in valores)
            return sum(valor * duracao for valor, duracao in valores) / tempo

        def ram(
            chave: str,
            pico: bool = False,
            *,
            somente_leituras_reais: bool = False,
        ) -> float:
            valores = [
                float(amostra[chave])
                for amostra in self._amostras
                if (
                    amostra[chave] is not None
                    and (
                        not somente_leituras_reais
                        or not amostra.get("ram_postgres_convencional", False)
                    )
                )
            ]
            if not valores:
                raise ErroMonitoramentoRecursos(
                    f"Nenhuma leitura valida foi obtida para {chave}."
                )
            return max(valores) if pico else sum(valores) / len(valores)

        mb = 1024 * 1024
        memoria_disponivel = [
            float(amostra["memoria_disponivel"])
            for amostra in self._amostras
            if amostra.get("memoria_disponivel") is not None
        ]
        reducao_memoria_disponivel_mb = None
        memoria_disponivel_inicial_mb = None
        if self._memoria_disponivel_inicial is not None and memoria_disponivel:
            memoria_disponivel_inicial_mb = self._memoria_disponivel_inicial / mb
            reducao_memoria_disponivel_mb = max(
                0.0,
                max(
                    self._memoria_disponivel_inicial - valor
                    for valor in memoria_disponivel
                ) / mb,
            )
        return {
            "cpu_media_python": cpu("cpu_python"),
            "cpu_pico_python": cpu("cpu_python", pico=True),
            "ram_media_python_mb": ram("ram_python") / mb,
            "ram_pico_python_mb": ram("ram_python", pico=True) / mb,
            "cpu_media_postgres": cpu("cpu_postgres"),
            "cpu_pico_postgres": cpu("cpu_postgres", pico=True),
            "ram_media_postgres_mb": ram(
                "ram_postgres", somente_leituras_reais=True
            ) / mb,
            "ram_pico_postgres_mb": ram("ram_postgres", pico=True) / mb,
            "cpu_media_total": cpu("cpu_total"),
            "cpu_pico_total": cpu("cpu_total", pico=True),
            "ram_media_total_mb": ram("ram_total") / mb,
            "ram_pico_total_mb": ram("ram_total", pico=True) / mb,
            "memoria_disponivel_inicial_mb": memoria_disponivel_inicial_mb,
            "memoria_disponivel_reducao_maxima_mb": reducao_memoria_disponivel_mb,
        }
