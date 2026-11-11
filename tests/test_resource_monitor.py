from __future__ import annotations

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
        pai: ProcessoFalso | None = None,
        uss: int | BaseException = 4096,
    ) -> None:
        self.pid = pid
        self._nome = nome
        self._criado = float(criado if criado is not None else pid)
        self._cpu = list(cpu or [0.0])
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
            rm.threading, "Thread", ThreadFalsa
        ):
            monitor = rm.MonitorRecursos(relogio=lambda: 1.0)
            monitor.iniciar()

        self.assertEqual(python.chamadas_cpu, [None])
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
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "Acesso negado"):
            rm.MonitorRecursos._ler_ram_postgres(processo)

    def test_uss_postgres_indisponivel_gera_erro_explicito(self) -> None:
        processo = ProcessoFalso(20, uss=AttributeError())
        with self.assertRaisesRegex(rm.ErroMonitoramentoRecursos, "USS"):
            rm.MonitorRecursos._ler_ram_postgres(processo)

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

    def test_media_e_pico_incluem_amostras_pre_e_pos_conexao(self) -> None:
        python = ProcessoFalso(10, nome="python.exe")
        with mock.patch.object(rm.psutil, "Process", return_value=python):
            monitor = rm.MonitorRecursos()
        monitor._amostras = [
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 10.0,
                "cpu_postgres": 0.0, "cpu_postgres_convencional": True,
                "cpu_total": 10.0,
                "ram_python": 100.0, "ram_postgres": 0.0, "ram_total": 100.0,
            },
            {
                "duracao_cpu_python": 1.0, "duracao_cpu_postgres": 1.0,
                "duracao_cpu_total": 1.0, "cpu_python": 20.0,
                "cpu_postgres": 30.0, "cpu_postgres_convencional": False,
                "cpu_total": 50.0,
                "ram_python": 300.0, "ram_postgres": 400.0, "ram_total": 700.0,
            },
        ]

        resultado = monitor._consolidar()

        self.assertEqual(resultado["cpu_media_python"], 15.0)
        self.assertEqual(resultado["cpu_media_postgres"], 15.0)
        self.assertEqual(resultado["cpu_media_total"], 30.0)
        self.assertEqual(resultado["cpu_pico_total"], 50.0)
        self.assertAlmostEqual(resultado["ram_media_postgres_mb"], 200 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_postgres_mb"], 400 / 1024**2)
        self.assertAlmostEqual(resultado["ram_media_total_mb"], 400 / 1024**2)
        self.assertAlmostEqual(resultado["ram_pico_total_mb"], 700 / 1024**2)

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
