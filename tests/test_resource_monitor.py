from __future__ import annotations

import math
from types import SimpleNamespace
import unittest
from unittest import mock

import psutil

from src import resource_monitor as rm


class ProcessoFalso:
    def __init__(
        self,
        pid: int,
        *,
        nome: str = "postgres.exe",
        criado: float | None = None,
        cpu: list[float | BaseException] | None = None,
        cpu_times: list[tuple[float, float] | BaseException] | None = None,
        pai: ProcessoFalso | None = None,
        uss: int | BaseException = 4096,
    ) -> None:
        self.pid = pid
        self._nome = nome
        self._criado = float(criado if criado is not None else pid)
        self._cpu = list(cpu or [0.0])
        self._cpu_times = list(cpu_times or [(0.0, 0.0)])
        self._ultimo_cpu_times = self._cpu_times[-1]
        self._pai = pai
        self._uss = uss
        self.filhos: list[ProcessoFalso] = []
        self.chamadas_cpu: list[object] = []
        self.info = {"name": nome}

    def name(self) -> str:
        return self._nome

    def create_time(self) -> float:
        return self._criado

    def parent(self):
        return self._pai

    def children(self, recursive: bool = False):
        return list(self.filhos)

    def cpu_percent(self, interval=None) -> float:
        self.chamadas_cpu.append(interval)
        valor = self._cpu.pop(0)
        if isinstance(valor, BaseException):
            raise valor
        return valor

    def cpu_times(self):
        valor = self._cpu_times.pop(0) if self._cpu_times else self._ultimo_cpu_times
        if isinstance(valor, BaseException):
            raise valor
        self._ultimo_cpu_times = valor
        return SimpleNamespace(user=valor[0], system=valor[1])

    def memory_info(self):
        return SimpleNamespace(rss=1024, private=2048)

    def memory_full_info(self):
        if isinstance(self._uss, BaseException):
            raise self._uss
        return SimpleNamespace(uss=self._uss)


class ThreadFalsa:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self.iniciada = False

    def start(self) -> None:
        self.iniciada = True

    def join(self) -> None:
        pass


class MonitorRecursosTest(unittest.TestCase):
    def tearDown(self) -> None:
        rm._monitor_ativo = None

    @staticmethod
    def _conexao(pid: int = 20, host: str = "localhost"):
        return SimpleNamespace(
            info=SimpleNamespace(host=host),
            get_backend_pid=lambda: pid,
        )

    def test_iniciar_faz_priming_do_python_antes_da_thread(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0])
        with mock.patch.object(rm.psutil, "Process", return_value=python), mock.patch.object(
            rm.psutil,
            "virtual_memory",
            return_value=SimpleNamespace(available=123),
        ), mock.patch.object(rm.threading, "Thread", ThreadFalsa):
            monitor = rm.MonitorRecursos(relogio=lambda: 1.0)
            monitor.iniciar()

        self.assertEqual(python.chamadas_cpu, [None])
        self.assertEqual(monitor._memoria_disponivel_inicial, 123)
        self.assertTrue(monitor._thread.iniciada)
        monitor._desregistrar()

    def test_pre_conexao_usa_uss_python_e_zero_postgres_por_convencao(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 5.0], uss=123)
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos(relogio=mock.Mock(return_value=1.0))
        python.cpu_percent(interval=None)
        monitor._ultimo_instante = 0.0

        monitor._registrar_amostra()

        amostra = monitor._amostras[-1]
        self.assertFalse(monitor._postgres_vinculado)
        self.assertEqual(amostra["cpu_python"], 5.0)
        self.assertEqual(amostra["cpu_postgres"], 0.0)
        self.assertTrue(amostra["cpu_postgres_convencional"])
        self.assertEqual(amostra["cpu_total"], 5.0)
        self.assertEqual(amostra["duracao_cpu_postgres"], 1.0)
        self.assertEqual(amostra["duracao_cpu_total"], 1.0)
        self.assertEqual(amostra["ram_python"], 123.0)
        self.assertEqual(amostra["ram_postgres"], 0.0)
        self.assertTrue(amostra["ram_postgres_convencional"])
        self.assertEqual(amostra["ram_total"], 123.0)

    def test_vinculo_prima_postgres_e_novo_processo_sem_contar_primeira_leitura(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu=[0.0, 10.0, 0.0, 20.0, 30.0]
        )
        raiz = ProcessoFalso(20, cpu=[0.0, 30.0, 40.0])
        novo = ProcessoFalso(21, cpu=[0.0, 50.0], pai=raiz)
        raiz.filhos = []
        relogio = mock.Mock(side_effect=[1.0, 1.0, 2.0, 3.0])
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz]), mock.patch.object(
            rm.psutil, "process_iter", return_value=[]
        ):
            monitor = rm.MonitorRecursos(relogio=relogio)
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            raiz.filhos = [novo, novo]
            monitor._registrar_amostra()
            monitor._registrar_amostra()

        self.assertEqual(raiz.chamadas_cpu[0], None)
        self.assertEqual(novo.chamadas_cpu[0], None)
        self.assertEqual(monitor._amostras[-2]["cpu_postgres"], 30.0)
        self.assertEqual(monitor._amostras[-1]["cpu_postgres"], 90.0)
        self.assertFalse(monitor._amostras[-1]["cpu_postgres_convencional"])
        self.assertEqual(len(monitor._processos_postgres), 2)

    def test_processo_encerrado_e_invalido_nao_vira_zero(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 5.0, 0.0, 6.0])
        raiz = ProcessoFalso(
            20, cpu=[0.0, psutil.NoSuchProcess(20)]
        )
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz]), mock.patch.object(
            rm.psutil, "process_iter", return_value=[]
        ):
            monitor = rm.MonitorRecursos(
                relogio=mock.Mock(side_effect=[1.0, 1.0, 2.0])
            )
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            monitor._registrar_amostra()

        self.assertIsNone(monitor._amostras[-1]["cpu_postgres"])
        self.assertFalse(monitor._amostras[-1]["cpu_postgres_convencional"])
        self.assertIsNone(monitor._amostras[-1]["cpu_total"])
        self.assertEqual(monitor._amostras[-1]["ram_postgres"], 0.0)
        self.assertEqual(monitor._amostras[-1]["ram_total"], 4096.0)
        self.assertEqual(monitor._processos_postgres, {})
        with self.assertRaises(rm.ErroMonitoramentoRecursos):
            monitor._consolidar()

    def test_processo_encerrado_durante_uss_invalida_ram_sem_zero_ficticio(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 5.0, 0.0, 6.0])
        raiz = ProcessoFalso(
            20,
            cpu=[0.0, 3.0],
            uss=psutil.NoSuchProcess(20),
        )
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz]), mock.patch.object(
            rm.psutil, "process_iter", return_value=[]
        ):
            monitor = rm.MonitorRecursos(
                relogio=mock.Mock(side_effect=[1.0, 1.0, 2.0])
            )
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            monitor._registrar_amostra()

        self.assertIsNone(monitor._amostras[-1]["ram_postgres"])
        self.assertIsNone(monitor._amostras[-1]["ram_total"])
        self.assertEqual(monitor._processos_postgres, {})

    def test_acesso_negado_na_uss_postgres_gera_erro_explicito(self) -> None:
        processo = ProcessoFalso(20, uss=psutil.AccessDenied(20))
        atual = ProcessoFalso(20, criado=20.0, uss=psutil.AccessDenied(20))
        with mock.patch.object(rm.psutil, "Process", return_value=atual):
            with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "Acesso negado"):
                rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

    def test_uss_postgres_indisponivel_gera_erro_explicito(self) -> None:
        processo = ProcessoFalso(20, uss=AttributeError())
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "USS"):
            rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

    def test_acesso_negado_seguido_de_desaparecimento_retorna_none(self) -> None:
        processo = ProcessoFalso(20, uss=psutil.AccessDenied(20))
        with mock.patch.object(
            rm.psutil, "Process", side_effect=psutil.NoSuchProcess(20)
        ):
            valor = rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

        self.assertIsNone(valor)

    def test_acesso_negado_com_pid_reutilizado_retorna_none(self) -> None:
        processo = ProcessoFalso(20, criado=20.0, uss=psutil.AccessDenied(20))
        reutilizado = ProcessoFalso(20, criado=30.0, uss=999)
        reutilizado.memory_full_info = mock.Mock(
            side_effect=AssertionError("nao deve ler USS de PID reutilizado")
        )
        with mock.patch.object(rm.psutil, "Process", return_value=reutilizado):
            valor = rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

        self.assertIsNone(valor)
        reutilizado.memory_full_info.assert_not_called()

    def test_acesso_negado_transitorio_aceita_segunda_leitura(self) -> None:
        processo = ProcessoFalso(20, criado=20.0, uss=psutil.AccessDenied(20))
        atual = ProcessoFalso(20, criado=20.0, uss=321)
        with mock.patch.object(rm.psutil, "Process", return_value=atual):
            valor = rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

        self.assertEqual(valor, 321)

    def test_acesso_negado_na_revalidacao_permanece_falha(self) -> None:
        processo = ProcessoFalso(20, uss=psutil.AccessDenied(20))
        with mock.patch.object(
            rm.psutil, "Process", side_effect=psutil.AccessDenied(20)
        ):
            with self.assertRaisesRegex(
                rm.ErroMonitoramentoRecursos, "revalidar a identidade"
            ):
                rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

    def test_erro_inesperado_na_revalidacao_permanece_falha(self) -> None:
        processo = ProcessoFalso(20, uss=psutil.AccessDenied(20))
        with mock.patch.object(
            rm.psutil, "Process", side_effect=OSError("falha inesperada")
        ):
            with self.assertRaisesRegex(
                rm.ErroMonitoramentoRecursos, "Falha ao revalidar"
            ):
                rm.MonitorRecursos._ler_ram_postgres(processo, (20, 20.0))

    def test_encerramento_entre_cpu_e_uss_invalida_amostra_ram(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[4.0], uss=100)
        postgres = ProcessoFalso(
            20, criado=20.0, cpu=[3.0], uss=psutil.AccessDenied(20)
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos(relogio=mock.Mock(return_value=1.0))
        monitor._postgres_vinculado = True
        monitor._raiz_postgres = postgres
        monitor._identidade_raiz = (20, 20.0)
        monitor._processos_postgres[(20, 20.0)] = postgres
        monitor._ultimo_instante = 0.0
        monitor._ultimo_instante_postgres = 0.0

        with mock.patch.object(
            rm.psutil, "Process", side_effect=psutil.NoSuchProcess(20)
        ):
            monitor._registrar_amostra()

        amostra = monitor._amostras[-1]
        self.assertEqual(amostra["cpu_postgres"], 3.0)
        self.assertIsNone(amostra["ram_postgres"])
        self.assertIsNone(amostra["ram_total"])
        self.assertNotEqual(amostra["ram_postgres"], 0.0)
        self.assertNotIn((20, 20.0), monitor._processos_postgres)

    def test_processo_novo_encerrado_antes_da_uss_remove_so_sua_identidade(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[4.0], uss=100)
        raiz = ProcessoFalso(20, criado=20.0, cpu=[5.0], uss=10)
        novo = ProcessoFalso(
            21,
            criado=21.0,
            cpu=[0.0],
            pai=raiz,
            uss=psutil.AccessDenied(21),
        )
        raiz.filhos = [novo]
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos(relogio=mock.Mock(return_value=1.0))
        monitor._postgres_vinculado = True
        monitor._raiz_postgres = raiz
        monitor._identidade_raiz = (20, 20.0)
        monitor._processos_postgres[(20, 20.0)] = raiz
        monitor._ultimo_instante = 0.0
        monitor._ultimo_instante_postgres = 0.0

        with mock.patch.object(
            rm.psutil, "Process", side_effect=psutil.NoSuchProcess(21)
        ):
            monitor._registrar_amostra()

        amostra = monitor._amostras[-1]
        self.assertEqual(novo.chamadas_cpu, [None])
        self.assertIn((20, 20.0), monitor._processos_postgres)
        self.assertNotIn((21, 21.0), monitor._processos_postgres)
        self.assertIsNone(amostra["ram_postgres"])
        self.assertIsNone(amostra["ram_total"])

    def test_encerramento_na_amostra_final_nao_contabiliza_zero(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[4.0], uss=100)
        postgres = ProcessoFalso(
            20, criado=20.0, cpu=[3.0], uss=psutil.AccessDenied(20)
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos(relogio=mock.Mock(return_value=1.0))
        monitor._postgres_vinculado = True
        monitor._raiz_postgres = postgres
        monitor._identidade_raiz = (20, 20.0)
        monitor._processos_postgres[(20, 20.0)] = postgres
        monitor._ultimo_instante = 0.0
        monitor._ultimo_instante_postgres = 0.0
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0,
                "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0,
                "cpu_python": 2.0,
                "cpu_postgres": 3.0,
                "cpu_postgres_convencional": False,
                "cpu_total": 5.0,
                "ram_python": 100.0,
                "ram_postgres": 200.0,
                "ram_total": 300.0,
            }
        ]
        rm._monitor_ativo = monitor

        with mock.patch.object(
            rm.psutil, "Process", side_effect=psutil.NoSuchProcess(20)
        ):
            resultado = monitor.parar()

        self.assertIsNone(monitor._amostras[-1]["ram_postgres"])
        self.assertIsNone(monitor._amostras[-1]["ram_total"])
        self.assertAlmostEqual(resultado["ram_media_postgres_mb"], 200 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_total_mb"], 300 / 1024**2)
        self.assertEqual(monitor._processos_postgres, {})
        self.assertIsNone(rm._monitor_ativo)

    def test_pid_reutilizado_nao_reaproveita_processo_antigo(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 1.0])
        antigo = ProcessoFalso(20, criado=20.0, cpu=[0.0])
        novo = ProcessoFalso(20, criado=30.0, cpu=[0.0])
        with mock.patch.object(
            rm.psutil, "Process", side_effect=[python, antigo]
        ):
            monitor = rm.MonitorRecursos()
            monitor._raiz_postgres = antigo
            monitor._identidade_raiz = (20, 20.0)
            monitor._processos_postgres[(20, 20.0)] = antigo
            with mock.patch.object(antigo, "children", return_value=[novo]):
                novos = monitor._descobrir_e_inicializar_processos()

        self.assertEqual(novos, {(20, 30.0)})
        self.assertNotIn((20, 20.0), monitor._processos_postgres)
        self.assertIs(monitor._processos_postgres[(20, 30.0)], novo)

    def test_ram_usa_exclusivamente_uss_e_arvore_vinculada(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 1.0, 0.0, 1.0], uss=7)
        raiz = ProcessoFalso(20, cpu=[0.0, 2.0, 3.0], uss=11)
        outro = ProcessoFalso(99, uss=1000)
        with mock.patch.object(
            rm.psutil, "Process", side_effect=[python, raiz]
        ), mock.patch.object(rm.psutil, "process_iter", return_value=[outro]) as iterar:
            monitor = rm.MonitorRecursos(relogio=mock.Mock(side_effect=[1.0, 1.0, 2.0]))
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            monitor._registrar_amostra()

        amostra = monitor._amostras[-1]
        self.assertEqual(amostra["ram_python"], 7.0)
        self.assertEqual(amostra["ram_postgres"], 11.0)
        self.assertEqual(amostra["ram_total"], 18.0)
        self.assertTrue(monitor._postgres_vinculado)
        self.assertEqual(monitor._amostras[-2]["ram_postgres"], 0.0)
        self.assertEqual(monitor._amostras[-2]["ram_total"], 7.0)
        iterar.assert_not_called()

    def test_participacao_postgres_permanece_entre_conexoes_da_mesma_instancia(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
        raiz = ProcessoFalso(20, cpu=[0.0, 2.0, 3.0, 4.0], uss=11)
        relogio = mock.Mock(side_effect=[1.0, 1.0, 2.0, 3.0])
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz, raiz]), mock.patch.object(
            rm.psutil, "process_iter", return_value=[]
        ):
            monitor = rm.MonitorRecursos(relogio=relogio)
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            monitor._registrar_amostra()
            monitor.vincular_conexao_postgres(self._conexao())
            monitor._registrar_amostra()

        self.assertTrue(monitor._postgres_vinculado)
        self.assertEqual(monitor._amostras[-1]["ram_postgres"], 11.0)
        self.assertEqual(monitor._amostras[-1]["ram_total"], 4107.0)

    def test_uss_indisponivel_invalida_medicao_explicitamente(self) -> None:
        processo = ProcessoFalso(10, nome="python.exe", uss=AttributeError())
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "USS"):
            rm.MonitorRecursos._ler_ram_python(processo)

    def test_acesso_negado_na_uss_gera_erro_explicito(self) -> None:
        processo = ProcessoFalso(10, nome="python.exe", uss=psutil.AccessDenied(10))
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "Acesso negado"):
            rm.MonitorRecursos._ler_ram_python(processo)

    def test_acesso_negado_na_cpu_nao_e_substituido_por_zero(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[0.0, 5.0, 0.0, 6.0])
        raiz = ProcessoFalso(20, cpu=[0.0, psutil.AccessDenied(20)])
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz]), mock.patch.object(
            rm.psutil, "process_iter", return_value=[]
        ):
            monitor = rm.MonitorRecursos(
                relogio=mock.Mock(side_effect=[1.0, 1.0, 2.0])
            )
            python.cpu_percent(interval=None)
            monitor._ultimo_instante = 0.0
            monitor.vincular_conexao_postgres(self._conexao())
            with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "Acesso negado"):
                monitor._registrar_amostra()

    def test_media_cpu_e_ponderada_pelo_tempo_e_pico_e_maximo(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 120.0, "cpu_total": 130.0,
                "ram_python": 100.0, "ram_postgres": 200.0, "ram_total": 300.0,
            },
            {
                "duracao_cpu_python": 3.0, "duracao_cpu_postgres": 3.0,
                "duracao_cpu_total": 3.0, "cpu_python": 30.0,
                "cpu_postgres": 240.0, "cpu_total": 270.0,
                "ram_python": 300.0, "ram_postgres": 400.0, "ram_total": 700.0,
            },
        ]

        resultado = monitor._consolidar()

        self.assertEqual(resultado["cpu_media_python"], 25.0)
        self.assertEqual(resultado["cpu_pico_python"], 30.0)
        self.assertEqual(resultado["cpu_media_postgres"], 210.0)
        self.assertEqual(resultado["cpu_pico_postgres"], 240.0)
        self.assertEqual(resultado["cpu_pico_total"], 270.0)
        self.assertAlmostEqual(resultado["ram_media_python_mb"], 200 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_total_mb"], 500 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_total_mb"], 700 / 1024**2)

    def test_memoria_disponivel_registra_inicial_e_maior_reducao(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[5.0, 6.0])
        mb = 1024 * 1024
        relogio = mock.Mock(side_effect=[1.0, 2.0])
        with mock.patch.object(rm.psutil, "Process", return_value=python), mock.patch.object(
            rm.psutil,
            "virtual_memory",
            side_effect=[SimpleNamespace(available=120 * mb), SimpleNamespace(available=80 * mb)],
        ):
            monitor = rm.MonitorRecursos(relogio=relogio)
            monitor._memoria_disponivel_inicial = 100 * mb
            monitor._ultimo_instante = 0.0
            monitor._registrar_amostra()
            monitor._registrar_amostra()

        for amostra in monitor._amostras:
            amostra["cpu_postgres_convencional"] = False
            amostra["ram_postgres_convencional"] = False

        self.assertEqual(monitor._amostras[-1]["memoria_disponivel"], 80 * mb)
        resultado = monitor._consolidar()
        self.assertEqual(resultado["memoria_disponivel_inicial_mb"], 100.0)
        self.assertEqual(resultado["memoria_disponivel_reducao_maxima_mb"], 20.0)

    def test_reducao_de_memoria_disponivel_e_zero_quando_nao_ha_reducao(self) -> None:
        python = ProcessoFalso(10, nome="python.exe", cpu=[5.0])
        mb = 1024 * 1024
        with mock.patch.object(rm.psutil, "Process", return_value=python), mock.patch.object(
            rm.psutil,
            "virtual_memory",
            return_value=SimpleNamespace(available=120 * mb),
        ):
            monitor = rm.MonitorRecursos()
            monitor._memoria_disponivel_inicial = 100 * mb
            monitor._ultimo_instante = 0.0
            monitor._registrar_amostra()

        monitor._amostras[-1]["cpu_postgres_convencional"] = False
        monitor._amostras[-1]["ram_postgres_convencional"] = False

        resultado = monitor._consolidar()
        self.assertEqual(resultado["memoria_disponivel_reducao_maxima_mb"], 0.0)

    def test_consolidacao_ignora_amostras_de_ram_incompletas(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 20.0, "cpu_total": 30.0,
                "ram_python": 100.0, "ram_postgres": None, "ram_total": None,
            },
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 20.0, "cpu_total": 30.0,
                "ram_python": 300.0, "ram_postgres": 400.0, "ram_total": 700.0,
            },
        ]

        resultado = monitor._consolidar()

        self.assertAlmostEqual(resultado["ram_media_python_mb"], 200 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_postgres_mb"], 400 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_total_mb"], 700 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_total_mb"], 700 / 1024**2)

    def test_media_postgres_exclui_zero_convencional_mas_preserva_zero_real(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 0.0, "cpu_postgres_convencional": True,
                "cpu_total": 10.0,
                "ram_python": 100.0, "ram_postgres": 0.0,
                "ram_postgres_convencional": True, "ram_total": 100.0,
            },
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 20.0,
                "cpu_postgres": 30.0, "cpu_postgres_convencional": False,
                "cpu_total": 50.0,
                "ram_python": 300.0, "ram_postgres": 0.0,
                "ram_postgres_convencional": False, "ram_total": 300.0,
            },
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 20.0,
                "cpu_postgres": 30.0, "cpu_postgres_convencional": False,
                "cpu_total": 50.0,
                "ram_python": 300.0, "ram_postgres": 400.0,
                "ram_postgres_convencional": False, "ram_total": 700.0,
            },
        ]

        resultado = monitor._consolidar()

        self.assertAlmostEqual(resultado["cpu_media_python"], 50 / 3)
        self.assertEqual(resultado["cpu_media_postgres"], 20.0)
        self.assertAlmostEqual(resultado["cpu_media_total"], 110 / 3)
        self.assertEqual(resultado["cpu_pico_total"], 50.0)
        self.assertAlmostEqual(resultado["ram_media_postgres_mb"], 200 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_postgres_mb"], 400 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_total_mb"], 1100 / 3 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_total_mb"], 700 / 1024**2)

    def test_media_postgres_falha_explicitamente_sem_leitura_real(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 0.0, "cpu_postgres_convencional": False,
                "cpu_total": 10.0, "ram_python": 100.0,
                "ram_postgres": 0.0, "ram_postgres_convencional": True,
                "ram_total": 100.0,
            }
        ]

        with self.assertRaisesRegex(
            rm.ErroMonitoramentoRecursos, "Nenhuma leitura valida.*ram_postgres"
        ):
            monitor._consolidar()

    def test_conexao_no_final_preserva_cpu_python_no_agregado(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 0.5, "duracao_cpu_postgres": 0.5,
                "duracao_cpu_total": 0.5, "cpu_python": cpu_python,
                "cpu_postgres": 0.0, "cpu_postgres_convencional": True,
                "cpu_total": cpu_python, "ram_python": 100.0,
                "ram_postgres": 0.0, "ram_total": 100.0,
            }
            for cpu_python in (100.0, 80.0, 60.0)
        ]
        monitor._amostras.append(
            {
                "duracao_cpu_python": 0.5, "duracao_cpu_postgres": 0.5,
                "duracao_cpu_total": 0.5, "cpu_python": 0.0,
                "cpu_postgres": 0.0, "cpu_postgres_convencional": False,
                "cpu_total": 0.0, "ram_python": 100.0,
                "ram_postgres": 40.0, "ram_total": 140.0,
            }
        )

        resultado = monitor._consolidar()

        self.assertEqual(resultado["cpu_media_python"], 60.0)
        self.assertEqual(resultado["cpu_media_postgres"], 0.0)
        self.assertEqual(resultado["cpu_media_total"], 60.0)
        self.assertEqual(resultado["cpu_pico_total"], 100.0)

    def test_excecao_da_thread_e_capturada_e_comunicada_no_parar(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._registrar_amostra = mock.Mock(side_effect=ValueError("falha interna"))
        monitor._parar.wait = mock.Mock(return_value=False)

        monitor._coletar()

        self.assertIsInstance(monitor._erro_thread, ValueError)
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "thread") as contexto:
            monitor.parar()
        self.assertIsInstance(contexto.exception.__cause__, ValueError)

    def test_cpu_times_acumula_deltas_de_python_e_multiplos_postgres(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[(1.0, 1.0), (1.6, 1.2), (2.0, 1.5)]
        )
        postgres_a = ProcessoFalso(
            20, cpu_times=[(2.0, 1.0), (2.4, 1.1), (3.0, 1.4)]
        )
        postgres_b = ProcessoFalso(
            21, cpu_times=[(5.0, 1.0), (5.2, 1.5), (5.5, 1.6)]
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()

        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        monitor._processos_postgres = {(20, 20.0): postgres_a, (21, 21.0): postgres_b}
        monitor._cpu_times_postgres_anteriores = {
            (20, 20.0): monitor._ler_cpu_times(postgres_a, "PostgreSQL"),
            (21, 21.0): monitor._ler_cpu_times(postgres_b, "PostgreSQL"),
        }
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertAlmostEqual(resultado["cpu_times_python_s"], 1.5)
        self.assertAlmostEqual(resultado["cpu_times_postgres_s"], 2.5)
        self.assertEqual(resultado["cpu_times_leituras_validas"], 6)
        self.assertEqual(resultado["cpu_times_status"], "valida")

    def test_cpu_times_processo_novo_comeca_na_fronteira_e_encerramento_e_incompleto(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]
        )
        postgres = ProcessoFalso(
            20,
            cpu_times=[(10.0, 2.0), (10.5, 2.1), psutil.NoSuchProcess(20)],
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()

        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        identidade = (20, 20.0)
        monitor._processos_postgres[identidade] = postgres
        monitor._inicializar_cpu_times_postgres(identidade, postgres)
        monitor._registrar_cpu_times_amostra({identidade})
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertAlmostEqual(resultado["cpu_times_postgres_s"], 0.6)
        self.assertEqual(resultado["cpu_times_processos_novos"], 1)
        self.assertEqual(resultado["cpu_times_processos_encerrados"], 1)
        self.assertEqual(resultado["cpu_times_processos_incompletos"], 1)
        self.assertEqual(resultado["cpu_times_status"], "parcial_ha_processos_incompletos")

    def test_cpu_times_reutilizacao_de_pid_descarta_contador_da_identidade_antiga(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        raiz = ProcessoFalso(20, criado=20.0, cpu_times=[(1.0, 1.0)])
        novo = ProcessoFalso(20, criado=30.0, cpu_times=[(100.0, 1.0)])
        with mock.patch.object(rm.psutil, "Process", side_effect=[python, raiz]):
            monitor = rm.MonitorRecursos()
            monitor._raiz_postgres = raiz
            monitor._identidade_raiz = (20, 20.0)
            monitor._processos_postgres[(20, 20.0)] = raiz
            monitor._cpu_times_postgres_anteriores[(20, 20.0)] = (8.0, 2.0)
            with mock.patch.object(raiz, "children", return_value=[novo]):
                monitor._descobrir_e_inicializar_processos()

        self.assertNotIn((20, 20.0), monitor._cpu_times_postgres_anteriores)
        self.assertEqual(monitor._cpu_times_postgres_anteriores[(20, 30.0)], (100.0, 1.0))
        self.assertEqual(monitor._cpu_times_processos_encerrados, 1)

    def test_cpu_times_sem_leituras_validas_e_coerencia_aproximada_com_cpu_percent(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[psutil.AccessDenied(10), psutil.AccessDenied(10)]
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "cpu_python": 50.0, "cpu_postgres": 20.0,
                "cpu_postgres_convencional": False,
            },
            {
                "duracao_cpu_python": 2.0, "duracao_cpu_postgres": 2.0,
                "cpu_python": 25.0, "cpu_postgres": 10.0,
                "cpu_postgres_convencional": False,
            },
        ]
        monitor._registrar_cpu_times_amostra(set())
        sem_leitura = monitor.consolidar_cpu_times_experimental()
        self.assertIsNone(sem_leitura["cpu_times_total_s"])
        self.assertEqual(sem_leitura["cpu_times_status"], "parcial_ha_processos_incompletos")

        monitor._cpu_times_acumulado_python = 0.98
        monitor._cpu_times_acumulado_postgres = 0.39
        monitor._cpu_times_leituras_validas = 2
        monitor._cpu_times_leituras_validas_python = 1
        monitor._cpu_times_leituras_validas_postgres = 1
        resultado = monitor.consolidar_cpu_times_experimental()
        self.assertAlmostEqual(
            resultado["cpu_times_python_s"],
            resultado["cpu_times_integrado_percent_python_s"],
            delta=0.3,
        )
        self.assertAlmostEqual(
            resultado["cpu_times_postgres_s"],
            resultado["cpu_times_integrado_percent_postgres_s"],
            delta=0.3,
        )

    def test_cpu_times_regressao_individual_de_user_descarta_delta_e_marca_parcial(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[(10.0, 4.0), (9.0, 5.0), (10.0, 6.0)]
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertAlmostEqual(resultado["cpu_times_python_s"], 2.0)
        self.assertEqual(resultado["cpu_times_leituras_validas"], 1)
        self.assertEqual(resultado["cpu_times_status"], "parcial_ha_processos_incompletos")

    def test_cpu_times_regressao_individual_de_system_descarta_delta_e_marca_parcial(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[(10.0, 4.0), (11.0, 3.0), (12.0, 4.0)]
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertAlmostEqual(resultado["cpu_times_python_s"], 2.0)
        self.assertEqual(resultado["cpu_times_leituras_validas"], 1)
        self.assertEqual(resultado["cpu_times_status"], "parcial_ha_processos_incompletos")

    def test_cpu_times_falha_inicial_postgres_recupera_sem_apagar_incompletude(self) -> None:
        python = ProcessoFalso(
            10, nome="python.exe", cpu_times=[(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]
        )
        postgres = ProcessoFalso(
            20,
            cpu_times=[
                psutil.AccessDenied(20),
                (5.0, 2.0),
                (5.5, 2.2),
            ],
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        identidade = (20, 20.0)
        monitor._processos_postgres[identidade] = postgres
        monitor._inicializar_cpu_times_postgres(identidade, postgres)

        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertAlmostEqual(resultado["cpu_times_postgres_s"], 0.7)
        self.assertEqual(resultado["cpu_times_leituras_validas_postgres"], 1)
        self.assertEqual(resultado["cpu_times_processos_incompletos"], 1)
        self.assertEqual(resultado["cpu_times_status"], "parcial_ha_processos_incompletos")

    def test_cpu_times_rejeita_nan_infinito_e_delta_negativo(self) -> None:
        python = ProcessoFalso(
            10,
            nome="python.exe",
            cpu_times=[(1.0, 1.0), (math.nan, 2.0), (math.inf, 3.0), (0.5, 4.0)],
        )
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._cpu_times_python_anterior = monitor._ler_cpu_times(python, "Python")
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())
        monitor._registrar_cpu_times_amostra(set())

        resultado = monitor.consolidar_cpu_times_experimental()

        self.assertIsNone(resultado["cpu_times_python_s"])
        self.assertEqual(resultado["cpu_times_leituras_validas"], 0)
        self.assertEqual(resultado["cpu_times_processos_incompletos"], 1)
        self.assertEqual(resultado["cpu_times_status"], "parcial_ha_processos_incompletos")
    def test_instancia_remota_e_rejeitada_explicitamente(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "remota"):
            monitor.vincular_conexao_postgres(
                self._conexao(host="postgres.exemplo.interno")
            )


if __name__ == "__main__":
    unittest.main()
