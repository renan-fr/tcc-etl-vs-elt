from __future__ import annotations

import csv
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, fields, replace
import importlib.util
import inspect
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
from types import SimpleNamespace


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src" / "enem"))
sys.path.insert(0, str(BASE_DIR / "src" / "tse"))

if importlib.util.find_spec("matplotlib") is None:
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.use = lambda *_args, **_kwargs: None
    pyplot = types.ModuleType("matplotlib.pyplot")
    matplotlib.pyplot = pyplot
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

from graficos import gerar_graficos
from src import benchmark, benchmark_paths
from src.benchmark_output import (
    finalizar_monitoramento_recursos,
    linhas_resultado_benchmark,
)
from src.enem import benchmark as benchmark_enem
from src.tse import benchmark as benchmark_tse


def carregar_pipeline(nome: str, caminho: Path):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PIPELINES = (
    carregar_pipeline("teste_enem_etl", BASE_DIR / "src" / "enem" / "etl.py"),
    carregar_pipeline("teste_enem_elt", BASE_DIR / "src" / "enem" / "elt.py"),
    carregar_pipeline("teste_tse_etl", BASE_DIR / "src" / "tse" / "etl.py"),
    carregar_pipeline("teste_tse_elt", BASE_DIR / "src" / "tse" / "elt.py"),
)


def resultado_sem_recursos(modulo):
    valores: dict[str, object] = {}
    for campo in fields(modulo.ResultadoBenchmark):
        if campo.name in modulo.CAMPOS_RECURSOS:
            valores[campo.name] = None
        elif campo.name == "dataset":
            valores[campo.name] = "enem" if "enem" in modulo.__name__ else "tse"
        elif campo.name == "arquitetura":
            valores[campo.name] = "etl" if modulo.__name__.endswith("etl") else "elt"
        elif campo.name == "modalidade":
            valores[campo.name] = "desempenho"
        elif campo.name == "monitoramento_ativo":
            valores[campo.name] = False
        elif campo.name == "intervalo_monitoramento_s":
            valores[campo.name] = None
        elif campo.name == "timestamp":
            valores[campo.name] = "2026-11-05T00:00:00"
        elif campo.name.startswith("tempo_") or campo.name == "throughput":
            valores[campo.name] = 1.0
        else:
            valores[campo.name] = 1
    return modulo.ResultadoBenchmark(**valores)


class MatrizEOrquestradorTest(unittest.TestCase):
    def test_matriz_completa_tem_32_unidades_e_192_execucoes(self) -> None:
        unidades = [
            (modalidade, dataset, volume, arquitetura)
            for modalidade in benchmark.MODALIDADES
            for dataset in ("enem", "tse")
            for volume in benchmark.VOLUMES_PADRAO
            for arquitetura in ("etl", "elt")
        ]
        self.assertEqual(len(unidades), 32)
        self.assertEqual(len(set(unidades)), 32)
        self.assertEqual(len(unidades) * 5, 160)
        self.assertEqual(len(unidades) * 6, 192)

    def _executar_orquestrador_simulado(self, raiz: Path, seed: int):
        campanha = raiz / f"campanha_{seed}"
        campanha.mkdir(exist_ok=True)
        comandos: list[list[str]] = []

        def executar(comando, **kwargs):
            comandos.append(list(comando))
            arquivo_log = kwargs["arquivo_log"]
            arquivo_log.write("Mensagem simulada do pipeline\n")
            arquivo_log.write(
                'RAM_AMOSTRAS_JSON={"total":1,"validas":1,"incompletas":0}\n'
            )

        argumentos = [
            "benchmark.py", "--run-id", f"teste_{seed}",
            "--volumes", "100000", "--rodadas", "1", "--seed", str(seed),
        ]
        with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
            benchmark, "validar_git_limpo"
        ), mock.patch.object(
            benchmark, "criar_diretorio_campanha", return_value=campanha
        ), mock.patch.object(
            benchmark, "obter_commit_git", return_value="abc123"
        ), mock.patch.object(
            benchmark, "executar_pipeline", side_effect=executar
        ):
            benchmark.main()
        return (
            comandos,
            json.loads((campanha / "campanha.json").read_text(encoding="utf-8")),
            (campanha / "campanha.log").read_text(encoding="utf-8"),
        )

    def test_integracao_simulada_quantidades_flags_metadados_e_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            comandos_1, metadados, log = self._executar_orquestrador_simulado(raiz, 7)
            comandos_2, _, _ = self._executar_orquestrador_simulado(raiz, 7)
            comandos_3, _, _ = self._executar_orquestrador_simulado(raiz, 8)

        self.assertEqual(comandos_1, comandos_2)
        self.assertNotEqual(comandos_1, comandos_3)
        self.assertEqual(len(comandos_1), 16)
        self.assertEqual(sum("--sem-monitoramento" in c for c in comandos_1), 8)
        self.assertEqual(metadados["combinacoes"], 8)
        self.assertEqual(metadados["cenarios_processamento"], 4)
        self.assertEqual(metadados["datasets"], list(benchmark.DATASETS))
        self.assertEqual(metadados["volumes"], [100000])
        self.assertEqual(metadados["rodadas"], 1)
        self.assertEqual(metadados["run_id"], "teste_7")
        self.assertEqual(metadados["aquecimentos"], 8)
        self.assertEqual(metadados["medicoes_validas"], 8)
        self.assertEqual(metadados["execucoes_previstas"], 16)
        self.assertEqual(metadados["execucoes_concluidas"], 16)
        self.assertEqual(metadados["status"], "concluida")
        self.assertIn("ambiente", metadados)
        self.assertIn("capturado_automaticamente", metadados["ambiente"])
        self.assertEqual(
            metadados["modalidades"]["recursos"]["intervalo_monitoramento_s"],
            0.5,
        )
        self.assertIn(
            "tempo_total",
            metadados["modalidades"]["recursos"]["metricas_diagnosticas"],
        )
        self.assertEqual(
            metadados["modalidades"]["recursos"]["metricas_experimentais"],
            [
                "cpu_times_python_s",
                "cpu_times_postgres_s",
                "cpu_times_total_s",
                "cpu_times_status",
            ],
        )
        self.assertIn(
            "cpu_times_processos_incompletos",
            metadados["modalidades"]["recursos"]["diagnosticos_cpu_times"],
        )
        self.assertIn("Campanha: teste_7", log)
        self.assertIn("Seed: 7", log)
        self.assertEqual(log.count("=== "), 16)
        self.assertEqual(log.count("Mensagem simulada do pipeline"), 16)
        self.assertEqual(log.count("RAM_AMOSTRAS_JSON="), 16)

    def test_execucao_replica_stdout_e_stderr_sem_duplicar(self) -> None:
        codigo = (
            "import sys; "
            "print('mensagem stdout'); "
            "print('RAM_AMOSTRAS_JSON={\\\"total\\\":1}', flush=True); "
            "print('diagnostico USS stderr', file=sys.stderr, flush=True)"
        )
        saida = StringIO()
        erros = StringIO()
        with tempfile.TemporaryDirectory() as temporario:
            caminho_log = Path(temporario) / "campanha.log"
            with caminho_log.open("w", encoding="utf-8", buffering=1) as arquivo_log:
                with redirect_stdout(saida), redirect_stderr(erros):
                    benchmark.executar_pipeline(
                        [sys.executable, "-u", "-c", codigo],
                        ambiente=os.environ.copy(),
                        arquivo_log=arquivo_log,
                    )
            log = caminho_log.read_text(encoding="utf-8")

        self.assertIn("mensagem stdout", saida.getvalue())
        self.assertIn("RAM_AMOSTRAS_JSON=", saida.getvalue())
        self.assertIn("diagnostico USS stderr", erros.getvalue())
        for mensagem in (
            "mensagem stdout",
            "RAM_AMOSTRAS_JSON=",
            "diagnostico USS stderr",
        ):
            self.assertEqual(log.count(mensagem), 1)

    def test_execucao_sanitiza_credenciais_em_stdout_stderr_e_log(self) -> None:
        url = "postgresql://usuario:senha-url@localhost:5432/tcc"
        senha_parametro = "senha-parametro-ficticia"
        segredo_ambiente = "segredo-conhecido-ficticio"
        linha_ram = 'RAM_AMOSTRAS_JSON={"total":1,"validas":1}'
        codigo = (
            "import sys; "
            f"print({'conexao: ' + url!r}); "
            f"print({'valor isolado: ' + segredo_ambiente!r}); "
            f"print({'password=' + senha_parametro!r}, file=sys.stderr); "
            f"print({linha_ram!r})"
        )
        ambiente = os.environ.copy()
        ambiente["DATABASE_URL"] = url
        ambiente["POSTGRES_PASSWORD"] = segredo_ambiente
        saida = StringIO()
        erros = StringIO()
        arquivo_log = StringIO()

        with redirect_stdout(saida), redirect_stderr(erros):
            benchmark.executar_pipeline(
                [sys.executable, "-u", "-c", codigo],
                ambiente=ambiente,
                arquivo_log=arquivo_log,
            )

        destinos = (saida.getvalue(), erros.getvalue(), arquivo_log.getvalue())
        for destino in destinos:
            self.assertNotIn(url, destino)
            self.assertNotIn("usuario", destino)
            self.assertNotIn("senha-url", destino)
            self.assertNotIn(senha_parametro, destino)
            self.assertNotIn(segredo_ambiente, destino)
        self.assertIn("<url_postgresql_redigida>", saida.getvalue())
        self.assertIn("password=<valor_redigido>", erros.getvalue())
        self.assertIn("valor isolado: <valor_redigido>", saida.getvalue())
        self.assertIn(linha_ram + "\n", saida.getvalue())
        self.assertIn(linha_ram + "\n", arquivo_log.getvalue())

    def test_falha_na_sanitizacao_omite_mensagem_sem_expor_original(self) -> None:
        segredo = "segredo-que-nao-pode-vazar"
        saida = StringIO()
        arquivo_log = StringIO()
        with mock.patch.object(
            benchmark,
            "_sanitizar_texto",
            side_effect=RuntimeError("sanitizador indisponivel"),
        ), redirect_stdout(saida):
            benchmark.executar_pipeline(
                [sys.executable, "-u", "-c", f"print({segredo!r})"],
                ambiente=os.environ.copy(),
                arquivo_log=arquivo_log,
            )

        self.assertNotIn(segredo, saida.getvalue())
        self.assertNotIn(segredo, arquivo_log.getvalue())
        self.assertEqual(
            saida.getvalue(),
            benchmark.MENSAGEM_SANITIZACAO_INDISPONIVEL + "\n",
        )
        self.assertEqual(saida.getvalue(), arquivo_log.getvalue())

    def test_senhas_curtas_sao_redigidas_apenas_em_contexto_de_credencial(self) -> None:
        linha_ram = (
            'RAM_AMOSTRAS_JSON={"total":10,"validas":1,"incompletas":0}\n'
        )
        for senha in ("0", "1", "segredo-conhecido-longo"):
            with self.subTest(senha=senha):
                self.assertEqual(
                    benchmark._sanitizar_texto_seguro(linha_ram, (senha,)),
                    linha_ram,
                )

        mensagens = (
            "password=1",
            'diagnostico {"password":"0"}',
            'RAM_AMOSTRAS_JSON={"password":"1"}',
            "postgresql://usuario:1@localhost/tcc",
        )
        for mensagem in mensagens:
            with self.subTest(mensagem=mensagem):
                sanitizada = benchmark._sanitizar_texto_seguro(
                    mensagem,
                    ("0", "1"),
                )
                self.assertNotIn(mensagem, sanitizada)
                self.assertIn("redigid", sanitizada)

        mensagem_longa = "falha usando segredo-conhecido-longo"
        self.assertNotIn(
            "segredo-conhecido-longo",
            benchmark._sanitizar_texto_seguro(
                mensagem_longa,
                ("segredo-conhecido-longo",),
            ),
        )

    def test_falha_de_escrita_no_log_encerra_subprocesso_ativo(self) -> None:
        class LogComFalha(StringIO):
            def write(self, _texto: str) -> int:
                raise OSError("disco indisponivel")

        codigo = "import time; print('antes da falha', flush=True); time.sleep(30)"
        inicio = time.monotonic()
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            with self.assertRaises(benchmark.ErroCapturaFluxo) as contexto:
                benchmark.executar_pipeline(
                    [sys.executable, "-u", "-c", codigo],
                    ambiente=os.environ.copy(),
                    arquivo_log=LogComFalha(),
                )

        self.assertLess(time.monotonic() - inicio, 5)
        self.assertIsInstance(contexto.exception.__cause__, OSError)
        self.assertIn("stdout", str(contexto.exception))
        self.assertIn("disco indisponivel", str(contexto.exception))

    def test_falha_de_leitura_encerra_processo_e_finaliza_as_threads(self) -> None:
        class FluxoControlado:
            def __init__(
                self, finalizado: threading.Event, *, falhar: bool = False
            ) -> None:
                self.finalizado = finalizado
                self.falhar = falhar
                self.fechado = threading.Event()

            def readline(self) -> str:
                if self.falhar:
                    self.falhar = False
                    raise OSError("pipe ilegivel")
                self.finalizado.wait()
                return ""

            def close(self) -> None:
                self.fechado.set()

        class ProcessoAtivo:
            def __init__(self, fluxo_com_falha: str) -> None:
                self.finalizado = threading.Event()
                self.stdout = FluxoControlado(
                    self.finalizado, falhar=fluxo_com_falha == "stdout"
                )
                self.stderr = FluxoControlado(
                    self.finalizado, falhar=fluxo_com_falha == "stderr"
                )
                self.returncode = None
                self.terminado = False

            def poll(self):
                return self.returncode

            def terminate(self) -> None:
                self.terminado = True
                self.returncode = -15
                self.finalizado.set()

            def wait(self, timeout=None):
                if not self.finalizado.wait(timeout):
                    raise subprocess.TimeoutExpired(["pipeline"], timeout)
                return self.returncode

            def kill(self) -> None:
                self.returncode = -9
                self.finalizado.set()

        for nome_fluxo in ("stdout", "stderr"):
            with self.subTest(nome_fluxo=nome_fluxo):
                processo = ProcessoAtivo(nome_fluxo)
                with mock.patch.object(
                    benchmark.subprocess, "Popen", return_value=processo
                ):
                    with self.assertRaises(benchmark.ErroCapturaFluxo) as contexto:
                        benchmark.executar_pipeline(
                            ["pipeline"],
                            ambiente={},
                            arquivo_log=StringIO(),
                        )

                self.assertTrue(processo.terminado)
                self.assertTrue(processo.stdout.fechado.is_set())
                self.assertTrue(processo.stderr.fechado.is_set())
                self.assertIn(nome_fluxo, str(contexto.exception))
                self.assertIsInstance(contexto.exception.__cause__, OSError)

    def test_falhas_de_terminate_e_kill_nao_bloqueiam_join(self) -> None:
        class Fluxo:
            def __init__(
                self, finalizado: threading.Event, *, falhar: bool = False
            ) -> None:
                self.finalizado = finalizado
                self.falhar = falhar
                self.fechado = threading.Event()

            def readline(self) -> str:
                if self.falhar:
                    self.falhar = False
                    raise OSError("falha de leitura")
                self.finalizado.wait()
                return ""

            def close(self) -> None:
                self.fechado.set()

        class ProcessoIncontrolavel:
            def __init__(self) -> None:
                self.finalizado = threading.Event()
                self.stdout = Fluxo(self.finalizado, falhar=True)
                self.stderr = Fluxo(self.finalizado)
                self.returncode = None

            def poll(self):
                return self.returncode

            def terminate(self) -> None:
                raise OSError("terminate recusado")

            def kill(self) -> None:
                raise OSError("kill recusado")

            def wait(self, timeout=None):
                raise subprocess.TimeoutExpired(["pipeline"], timeout)

        processo = ProcessoIncontrolavel()
        inicio = time.monotonic()
        with mock.patch.object(
            benchmark.subprocess, "Popen", return_value=processo
        ), mock.patch.object(benchmark, "TEMPO_LIMITE_THREAD_S", 0.01):
            with self.assertRaises(benchmark.ErroCapturaFluxo) as contexto:
                benchmark.executar_pipeline(
                    ["pipeline"],
                    ambiente={},
                    arquivo_log=StringIO(),
                )

        self.assertLess(time.monotonic() - inicio, 1)
        notas = "\n".join(getattr(contexto.exception, "__notes__", ()))
        self.assertIn("Não foi possível confirmar o encerramento", notas)
        self.assertIn("permanecerão daemon", notas)
        threads_ativas = [
            thread
            for thread in threading.enumerate()
            if thread.name in {"benchmark-stdout", "benchmark-stderr"}
        ]
        self.assertTrue(threads_ativas)
        self.assertTrue(all(thread.daemon for thread in threads_ativas))

        processo.finalizado.set()
        self.assertTrue(processo.stderr.fechado.wait(1))

    def test_codigo_de_saida_diferente_de_zero_continua_sendo_propagado(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError) as contexto:
            benchmark.executar_pipeline(
                [sys.executable, "-u", "-c", "raise SystemExit(7)"],
                ambiente=os.environ.copy(),
                arquivo_log=StringIO(),
            )

        self.assertEqual(contexto.exception.returncode, 7)

    def test_campanha_interrompida_preserva_log_e_metadados(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()

            def interromper(_comando, **kwargs):
                kwargs["arquivo_log"].write("saida antes da interrupcao\n")
                raise KeyboardInterrupt()

            argumentos = [
                "benchmark.py", "--run-id", "interrompida",
                "--volumes", "100000", "--rodadas", "1",
            ]
            with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark, "executar_pipeline", side_effect=interromper
            ):
                with self.assertRaises(KeyboardInterrupt):
                    benchmark.main()

            metadados = json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
            )
            log = (campanha / "campanha.log").read_text(encoding="utf-8")

        self.assertEqual(metadados["status"], "interrompida")
        self.assertEqual(metadados["execucoes_concluidas"], 0)
        self.assertIn("=== 1/16 | aquecimento |", log)
        self.assertIn("saida antes da interrupcao", log)
        self.assertIn("KeyboardInterrupt", log)

    def test_falha_de_captura_marca_campanha_como_falhou(self) -> None:
        def falhar_com_log_indisponivel(_comando, **kwargs) -> None:
            kwargs["arquivo_log"].close()
            raise benchmark.ErroCapturaFluxo(
                "Falha ao capturar stdout do subprocesso: disco indisponivel"
            )

        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
            erro_terminal = StringIO()
            argumentos = [
                "benchmark.py", "--run-id", "captura_falhou",
                "--volumes", "100000", "--rodadas", "1",
            ]
            with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark,
                "executar_pipeline",
                side_effect=falhar_com_log_indisponivel,
            ), redirect_stderr(erro_terminal):
                with self.assertRaises(benchmark.ErroCapturaFluxo):
                    benchmark.main()

            metadados = json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
            )
            log = (campanha / "campanha.log").read_text(encoding="utf-8")

        self.assertEqual(metadados["status"], "falhou")
        self.assertEqual(metadados["execucoes_concluidas"], 0)
        self.assertEqual(metadados["erro"]["tipo"], "ErroCapturaFluxo")
        self.assertIn("disco indisponivel", metadados["erro"]["mensagem"])
        self.assertIn("disco indisponivel", erro_terminal.getvalue())
        self.assertIn("disco indisponivel", log)

    def test_falha_antes_da_campanha_e_comunicada_uma_vez_pela_cli(self) -> None:
        erro_terminal = StringIO()
        erro = RuntimeError("falha inicial password=segredo-ficticio")
        argumentos = [
            "benchmark.py", "--run-id", "falha_pre_campanha",
            "--volumes", "100000", "--rodadas", "1",
        ]
        with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
            benchmark, "validar_git_limpo", side_effect=erro
        ), mock.patch.object(
            benchmark, "criar_diretorio_campanha"
        ) as criar, redirect_stderr(erro_terminal):
            with self.assertRaises(SystemExit) as contexto:
                benchmark._executar_cli()

        criar.assert_not_called()
        self.assertEqual(contexto.exception.code, 1)
        self.assertNotIn("segredo-ficticio", erro_terminal.getvalue())
        self.assertIn("RuntimeError", erro_terminal.getvalue())
        self.assertEqual(erro_terminal.getvalue().count("RuntimeError"), 1)

    def test_keyboard_interrupt_antes_da_campanha_preserva_codigo_130(self) -> None:
        erro_terminal = StringIO()
        with mock.patch.object(
            benchmark, "main", side_effect=KeyboardInterrupt
        ), redirect_stderr(erro_terminal):
            with self.assertRaises(SystemExit) as contexto:
                benchmark._executar_cli()

        self.assertEqual(contexto.exception.code, 130)
        self.assertIn("KeyboardInterrupt", erro_terminal.getvalue())

    def test_falha_na_inicializacao_persiste_json_e_log_quando_disponiveis(
        self,
    ) -> None:
        salvar_original = benchmark.salvar_metadados
        chamadas = 0

        def falhar_na_primeira_gravacao(caminho, metadados) -> None:
            nonlocal chamadas
            chamadas += 1
            if chamadas == 1:
                raise OSError("falha inicial password=segredo-inicializacao")
            salvar_original(caminho, metadados)

        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
            erro_terminal = StringIO()
            argumentos = [
                "benchmark.py", "--run-id", "falha_inicializacao",
                "--volumes", "100000", "--rodadas", "1",
            ]
            with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark, "salvar_metadados", side_effect=falhar_na_primeira_gravacao
            ), mock.patch.object(
                benchmark, "executar_pipeline"
            ) as executar, redirect_stderr(erro_terminal):
                with self.assertRaises(OSError):
                    benchmark.main()

            metadados = json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
            )
            log = (campanha / "campanha.log").read_text(encoding="utf-8")

        executar.assert_not_called()
        self.assertEqual(metadados["status"], "falhou")
        self.assertEqual(metadados["erro"]["contexto"], "inicializacao_campanha")
        for destino in (json.dumps(metadados), log, erro_terminal.getvalue()):
            self.assertNotIn("segredo-inicializacao", destino)
            self.assertIn("OSError", destino)

    def test_campanha_completa_simulada_tem_um_aquecimento_e_cinco_rodadas(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
            comandos: list[list[str]] = []
            with mock.patch.object(
                sys, "argv", ["benchmark.py", "--run-id", "completa"]
            ), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark, "executar_pipeline",
                side_effect=lambda comando, **_: comandos.append(list(comando)),
            ), mock.patch("builtins.print"):
                benchmark.main()

            metadados = json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
            )

        aquecimentos: dict[tuple[str, str, str, str], int] = defaultdict(int)
        rodadas: dict[tuple[str, str, str, str], set[int]] = defaultdict(set)
        for comando in comandos:
            modalidade = (
                "desempenho" if "--sem-monitoramento" in comando else "recursos"
            )
            script = Path(comando[1])
            dataset, arquitetura = script.parent.name, script.stem
            volume = comando[comando.index("--limite") + 1]
            identidade = (modalidade, dataset, arquitetura, volume)
            modo = comando[comando.index("--modo") + 1]
            if modo == "aquecimento":
                aquecimentos[identidade] += 1
            else:
                rodadas[identidade].add(int(comando[comando.index("--rodada") + 1]))

        self.assertEqual(len(comandos), 192)
        self.assertEqual(len(aquecimentos), 32)
        self.assertTrue(all(quantidade == 1 for quantidade in aquecimentos.values()))
        self.assertEqual(len(rodadas), 32)
        self.assertTrue(all(valores == set(range(1, 6)) for valores in rodadas.values()))
        self.assertEqual(metadados["aquecimentos"], 32)
        self.assertEqual(metadados["medicoes_validas"], 160)
        self.assertEqual(metadados["execucoes_previstas"], 192)
        self.assertEqual(metadados["datasets"], list(benchmark.DATASETS))
        self.assertEqual(metadados["volumes"], [100000, 250000, 500000, 1000000])
        self.assertEqual(metadados["rodadas"], 5)
        self.assertEqual(metadados["run_id"], "completa")


class AmbienteCampanhaTest(unittest.TestCase):
    def _executar_com_erro_controlado(
        self,
        erro: BaseException,
        ambiente=None,
    ) -> tuple[dict[str, object], str, str]:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
            erro_terminal = StringIO()
            argumentos = [
                "benchmark.py", "--run-id", "erro_controlado",
                "--volumes", "100000", "--rodadas", "1",
            ]
            with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark, "executar_pipeline", side_effect=erro
            ), mock.patch.object(
                benchmark, "coletar_ambiente",
                return_value=ambiente if ambiente is not None else {
                    "status": "capturado_no_host_da_campanha",
                    "declarado_para_campanha_oficial": {},
                    "capturado_automaticamente": {},
                },
            ), redirect_stderr(erro_terminal):
                with self.assertRaises(type(erro)):
                    benchmark.main()
            return (
                json.loads(
                    (campanha / "campanha.json").read_text(encoding="utf-8")
                ),
                (campanha / "campanha.log").read_text(encoding="utf-8"),
                erro_terminal.getvalue(),
            )

    def test_falha_inesperada_na_coleta_nao_interrompe_campanha(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
            comandos: list[list[str]] = []
            argumentos = [
                "benchmark.py", "--run-id", "coleta_falha",
                "--volumes", "100000", "--rodadas", "1",
            ]
            with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                benchmark, "validar_git_limpo"
            ), mock.patch.object(
                benchmark, "criar_diretorio_campanha", return_value=campanha
            ), mock.patch.object(
                benchmark, "obter_commit_git", return_value="abc123"
            ), mock.patch.object(
                benchmark, "coletar_ambiente",
                side_effect=RuntimeError(
                    "falha interna password=nao-gravar "
                    "postgresql://usuario:nao-gravar@localhost/tcc"
                ),
            ), mock.patch.object(
                benchmark, "executar_pipeline",
                side_effect=lambda comando, **_: comandos.append(list(comando)),
            ):
                benchmark.main()
            metadados = json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
            )

        self.assertEqual(len(comandos), 16)
        self.assertEqual(metadados["status"], "concluida")
        self.assertEqual(metadados["ambiente"]["status"], "falha_na_coleta")
        self.assertEqual(
            metadados["ambiente"]["erro"],
            {"tipo": "RuntimeError", "contexto": "coleta_ambiente"},
        )
        self.assertIsNone(metadados["ambiente"]["capturado_automaticamente"])
        self.assertNotIn("nao-gravar", json.dumps(metadados))

    def test_erro_persistido_redige_senha_e_url_postgresql(self) -> None:
        erro = RuntimeError(
            "password=senha-ficticia "
            "postgresql://usuario:senha-url@localhost:5432/tcc"
        )
        metadados, log, erro_terminal = self._executar_com_erro_controlado(erro)

        self.assertEqual(metadados["status"], "falhou")
        registro_erro = metadados["erro"]
        self.assertEqual(registro_erro["tipo"], "RuntimeError")
        self.assertEqual(registro_erro["contexto"], "execucao_pipeline")
        self.assertNotIn("senha-ficticia", json.dumps(metadados))
        self.assertNotIn("senha-url", json.dumps(metadados))
        self.assertNotIn("postgresql://", registro_erro["mensagem"])
        self.assertIn("Campanha: erro_controlado", log)
        self.assertIn("RuntimeError", log)
        for destino in (log, erro_terminal):
            self.assertNotIn("senha-ficticia", destino)
            self.assertNotIn("senha-url", destino)
            self.assertNotIn("postgresql://", destino)
            self.assertIn("RuntimeError", destino)

    def test_traceback_redige_valor_sensivel_conhecido_do_ambiente(self) -> None:
        segredo = "segredo-isolado-do-ambiente"
        with mock.patch.dict(os.environ, {"POSTGRES_PASSWORD": segredo}):
            metadados, log, erro_terminal = self._executar_com_erro_controlado(
                RuntimeError(f"falha usando {segredo}")
            )

        self.assertEqual(metadados["status"], "falhou")
        for destino in (json.dumps(metadados), log, erro_terminal):
            self.assertNotIn(segredo, destino)
            self.assertIn("<valor_redigido>", destino)

    def test_coleta_ambiente_preserva_origem_e_nao_expoe_credenciais(self) -> None:
        with mock.patch.object(
            benchmark,
            "_configuracao_postgres",
            return_value=(None, {}, {"host": "localhost", "porta": 5432, "banco": "tcc"}),
        ), mock.patch.object(
            benchmark,
            "_consultar_postgres_ambiente",
            return_value={
                "versao_servidor": "PostgreSQL observado",
                "configuracoes": {"work_mem": "4MB"},
                "status": "consultado",
                "origem": "teste",
            },
        ), mock.patch.object(
            benchmark,
            "_versoes_dependencias",
            return_value={"pandas": "observado", "psutil": "observado"},
        ):
            ambiente = benchmark.coletar_ambiente()

        self.assertEqual(
            ambiente["status"], "capturado_no_host_da_campanha"
        )
        self.assertEqual(
            ambiente["declarado_para_campanha_oficial"]["sistema_operacional"],
            "Windows 11",
        )
        capturado = ambiente["capturado_automaticamente"]
        self.assertIn("sistema_operacional", capturado)
        self.assertIn("python", capturado)
        self.assertIn("dependencias", capturado)
        self.assertIn("postgresql", capturado)
        self.assertIn("hardware", capturado)
        texto = json.dumps(ambiente)
        self.assertNotIn("password", texto.lower())
        self.assertNotIn("database_url", texto.lower())
        self.assertNotIn("senha", texto.lower())

    def test_consulta_postgres_usa_somente_select_e_show_e_fecha_recursos(self) -> None:
        cursor = mock.MagicMock()
        cursor.fetchone.side_effect = [
            ("PostgreSQL 18 observado",),
            *[(f"valor_{parametro}",) for parametro in benchmark.PARAMETROS_POSTGRES],
        ]
        conexao = mock.MagicMock()
        conexao.cursor.return_value = cursor
        with mock.patch.object(benchmark.psycopg2, "connect", return_value=conexao):
            resultado = benchmark._consultar_postgres_ambiente(
                None,
                {
                    "dbname": "tcc",
                    "user": "usuario",
                    "password": "segredo",
                },
            )

        self.assertEqual(resultado["status"], "consultado")
        self.assertEqual(resultado["versao_servidor"], "PostgreSQL 18 observado")
        self.assertEqual(cursor.execute.call_count, 1 + len(benchmark.PARAMETROS_POSTGRES))
        self.assertTrue(all(
            chamada.args[0].startswith(("SELECT version()", "SHOW "))
            for chamada in cursor.execute.call_args_list
        ))
        cursor.close.assert_called_once_with()
        conexao.close.assert_called_once_with()

    def test_consulta_postgres_indisponivel_nao_inventa_valores(self) -> None:
        resultado = benchmark._consultar_postgres_ambiente(
            None,
            {"dbname": None, "user": None, "password": None},
        )

        self.assertEqual(resultado["status"], "nao_consultado_configuracao_incompleta")
        self.assertIsNone(resultado["versao_servidor"])
        self.assertTrue(all(
            valor is None for valor in resultado["configuracoes"].values()
        ))

    def test_wrappers_executam_as_duas_modalidades(self) -> None:
        for modulo in (benchmark_enem, benchmark_tse):
            comandos: list[list[str]] = []
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                campanha = Path(temporario) / "campanha"
                campanha.mkdir()
                argumentos = [
                    "benchmark.py", "--run-id", "teste", "--volumes", "100000",
                    "--rodadas", "1", "--seed", "7",
                ]
                with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
                    modulo, "criar_diretorio_campanha", return_value=campanha
                ), mock.patch.object(
                    modulo, "executar", side_effect=lambda comando, *_: comandos.append(comando)
                ):
                    modulo.main()
            self.assertEqual(len(comandos), 8)
            self.assertEqual(sum("--sem-monitoramento" in c for c in comandos), 4)


class MonitorESerializacaoTest(unittest.TestCase):
    def test_resumo_compartilhado_preserva_valores_e_indica_ausentes(self) -> None:
        for modulo in PIPELINES:
            resultado = resultado_sem_recursos(modulo)
            antes = asdict(resultado)

            linhas = linhas_resultado_benchmark(resultado)

            with self.subTest(modulo=modulo.__name__):
                self.assertEqual(asdict(resultado), antes)
                self.assertEqual("\n".join(linhas).count("não monitorado"), 16)
                self.assertIn("Tempo total: 1.000s", linhas)
                self.assertIn("Throughput: 1.00 registros/s", linhas)

    def test_resumo_exibe_valores_consolidados_sem_recalculo(self) -> None:
        modulo = PIPELINES[0]
        base = resultado_sem_recursos(modulo)
        valores = {campo: 12.345 for campo in modulo.CAMPOS_RECURSOS}
        valores["cpu_times_status"] = "valida"
        for campo in modulo.CAMPOS_RECURSOS:
            if campo.startswith("cpu_times_leituras_") or campo.startswith(
                "cpu_times_processos_"
            ):
                valores[campo] = 1
        monitorado = modulo.ResultadoBenchmark(
            **{
                campo.name: (
                    True
                    if campo.name == "monitoramento_ativo"
                    else valores.get(campo.name, getattr(base, campo.name))
                )
                for campo in fields(modulo.ResultadoBenchmark)
            }
        )

        linhas = modulo._linhas_resumo_benchmark(monitorado)

        self.assertIn(
            "Agregado | CPU média: 12.35% | CPU pico: 12.35% | "
            "RAM USS média: 12.35 MB | RAM USS pico: 12.35 MB",
            linhas,
        )
        self.assertIn(
            "Tempo acumulado de CPU (cpu_times) | Python: 12.35s | "
            "PostgreSQL: 12.35s | Total: 12.35s | Status: valida",
            linhas,
        )

        desativado = replace(monitorado, monitoramento_ativo=False)
        self.assertEqual(
            "\n".join(linhas_resultado_benchmark(desativado)).count(
                "não monitorado"
            ),
            16,
        )

        sem_cpu_python = replace(monitorado, cpu_media_python=None)
        self.assertIn(
            "Python | CPU média: não monitorado | CPU pico: 12.35% | "
            "RAM USS média: 12.35 MB | RAM USS pico: 12.35 MB",
            linhas_resultado_benchmark(sem_cpu_python),
        )

    def test_desempenho_nao_instancia_monitor_e_recursos_usa_meio_segundo(self) -> None:
        for modulo in PIPELINES:
            with self.subTest(modulo=modulo.__name__), mock.patch.object(
                modulo, "MonitorRecursos"
            ) as monitor:
                self.assertIsNone(modulo._iniciar_monitoramento(True, False))
                monitor.assert_not_called()

                criado = modulo._iniciar_monitoramento(True, True)
                self.assertIs(criado, monitor.return_value)
                monitor.assert_called_once_with(intervalo_segundos=0.5)
                monitor.return_value.iniciar.assert_called_once_with()

    def test_certificacao_tambem_nao_instancia_monitor(self) -> None:
        for modulo in PIPELINES:
            with self.subTest(modulo=modulo.__name__), mock.patch.object(
                modulo, "MonitorRecursos"
            ) as monitor:
                self.assertIsNone(modulo._iniciar_monitoramento(False, True))
                monitor.assert_not_called()

    def test_recursos_ausentes_sao_vazios_e_identidade_duplicada_e_recusada(self) -> None:
        for modulo in PIPELINES:
            salvar = (
                getattr(modulo, "_salvar_resultado_benchmark", None)
                or getattr(modulo, "salvar_benchmark", None)
                or getattr(modulo, "_salvar_benchmark")
            )
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                caminho = Path(temporario) / "desempenho" / "resultado.csv"
                with mock.patch.dict(os.environ, {"BENCHMARK_RUN_ID": "teste"}):
                    salvar(resultado_sem_recursos(modulo), caminho)
                    with self.assertRaisesRegex(ValueError, "Execucao duplicada"):
                        salvar(resultado_sem_recursos(modulo), caminho)
                with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
                    linha = next(csv.DictReader(arquivo, delimiter=";"))
                self.assertEqual(linha["modalidade"], "desempenho")
                self.assertEqual(linha["monitoramento_ativo"].lower(), "false")
                self.assertEqual(linha["intervalo_monitoramento_s"], "")
                for campo in modulo.CAMPOS_RECURSOS:
                    self.assertEqual(linha[campo], "")

    def test_cpu_times_validos_e_parciais_sao_serializados_nos_quatro_pipelines(self) -> None:
        campos_oficiais_anteriores = (
            "cpu_media_python", "cpu_pico_python", "ram_media_python_mb",
            "ram_pico_python_mb", "cpu_media_postgres", "cpu_pico_postgres",
            "ram_media_postgres_mb", "ram_pico_postgres_mb", "cpu_media_total",
            "cpu_pico_total", "ram_media_total_mb", "ram_pico_total_mb",
            "memoria_disponivel_inicial_mb",
            "memoria_disponivel_reducao_maxima_mb",
        )
        for modulo in PIPELINES:
            salvar = (
                getattr(modulo, "_salvar_resultado_benchmark", None)
                or getattr(modulo, "salvar_benchmark", None)
                or getattr(modulo, "_salvar_benchmark")
            )
            base = resultado_sem_recursos(modulo)
            diagnosticos = {
                "cpu_times_leituras_validas": 20,
                "cpu_times_leituras_validas_python": 10,
                "cpu_times_leituras_validas_postgres": 10,
                "cpu_times_processos_novos": 3,
                "cpu_times_processos_encerrados": 0,
                "cpu_times_processos_incompletos": 0,
            }
            valido = replace(
                base,
                modalidade="recursos",
                monitoramento_ativo=True,
                intervalo_monitoramento_s=0.5,
                cpu_times_python_s=1.25,
                cpu_times_postgres_s=2.5,
                cpu_times_total_s=3.75,
                cpu_times_status="valida",
                **diagnosticos,
            )
            parcial = replace(
                valido,
                rodada=2,
                cpu_times_postgres_s=None,
                cpu_times_total_s=None,
                cpu_times_status="parcial_ha_componentes_sem_deltas",
                cpu_times_leituras_validas_postgres=0,
            )
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                caminho = Path(temporario) / "recursos" / "resultado.csv"
                with mock.patch.dict(os.environ, {"BENCHMARK_RUN_ID": "teste"}):
                    salvar(valido, caminho)
                    salvar(parcial, caminho)
                with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
                    linhas = list(csv.DictReader(arquivo, delimiter=";"))
                self.assertEqual(
                    modulo.CAMPOS_RECURSOS[: len(campos_oficiais_anteriores)],
                    campos_oficiais_anteriores,
                )
                self.assertEqual(linhas[0]["cpu_times_status"], "valida")
                self.assertEqual(linhas[0]["cpu_times_total_s"].replace(",", "."), "3.75")
                self.assertEqual(
                    linhas[1]["cpu_times_status"],
                    "parcial_ha_componentes_sem_deltas",
                )
                self.assertEqual(linhas[1]["cpu_times_postgres_s"], "")
                self.assertEqual(linhas[1]["cpu_times_total_s"], "")
                self.assertEqual(
                    linhas[1]["cpu_times_leituras_validas_postgres"], "0"
                )


class EquivalenciaFluxoTest(unittest.TestCase):
    @staticmethod
    def _monitor(modulo):
        monitor = mock.Mock()
        valores = {campo: 1.0 for campo in modulo.CAMPOS_RECURSOS}
        valores["cpu_times_status"] = "valida"
        monitor.parar_com_cpu_times.return_value = valores
        monitor.diagnostico_ram_amostras.return_value = {
            "total": 4,
            "validas": 3,
            "incompletas": 1,
            "percentual_incompletas": 25.0,
        }
        return monitor

    def _fluxo_enem_etl(self, monitorar: bool) -> list[str]:
        modulo = PIPELINES[0]
        eventos: list[str] = []
        dataframe = modulo.pd.DataFrame({"id": [1]})
        with mock.patch.object(
            modulo, "_iniciar_monitoramento",
            return_value=self._monitor(modulo) if monitorar else None,
        ), mock.patch.object(
            modulo, "extrair_participantes",
            side_effect=lambda *_: eventos.append("extrair_participantes") or dataframe,
        ), mock.patch.object(
            modulo, "extrair_resultados",
            side_effect=lambda *_: eventos.append("extrair_resultados") or dataframe,
        ), mock.patch.object(
            modulo, "transformar_participantes",
            side_effect=lambda valor: eventos.append("transformar_participantes") or valor,
        ), mock.patch.object(
            modulo, "transformar_resultados",
            side_effect=lambda valor: eventos.append("transformar_resultados") or valor,
        ), mock.patch.object(
            modulo, "relatorio_valores_desconhecidos",
            return_value=modulo.pd.DataFrame(),
        ), mock.patch.object(
            modulo, "obter_conexao_postgres", return_value=object()
        ), mock.patch.object(
            modulo, "carregar_enem",
            side_effect=lambda *_args, **_kwargs: eventos.append("carregar_enem"),
        ):
            modulo.main(
                1, None, "schema", "replace", benchmark=True,
                benchmark_output=None, rodada=1, validar=False,
                monitorar_recursos=monitorar,
                modalidade="recursos" if monitorar else "desempenho",
            )
        return eventos

    def _fluxo_enem_elt(self, monitorar: bool):
        modulo = PIPELINES[1]
        tempos = modulo.TemposELT(1.0, 1.0, 1.0, None, 3.0, 1, 1)
        argumentos = ["elt.py", "--limite", "1", "--modo", "aquecimento"]
        if not monitorar:
            argumentos.append("--sem-monitoramento")
        with mock.patch.object(sys, "argv", argumentos), mock.patch.object(
            modulo, "_iniciar_monitoramento",
            return_value=self._monitor(modulo) if monitorar else None,
        ), mock.patch.object(
            modulo, "executar_elt", return_value=tempos
        ) as executar:
            modulo.main()
        return executar.call_args

    def _fluxo_tse_etl(self, monitorar: bool) -> list[str]:
        modulo = PIPELINES[2]
        eventos: list[str] = []
        dataframe = modulo.pd.DataFrame({"id": [1]})
        fontes = modulo.FontesTSE(dataframe, dataframe, dataframe, dataframe)
        args = SimpleNamespace(
            benchmark=True, monitorar_recursos=monitorar, limite=1,
            manifesto_chaves=Path("manifesto.csv"), sem_validacao=True,
            database_url=None, schema="schema", rodada=1,
            modalidade="recursos" if monitorar else "desempenho",
            benchmark_output=None,
        )
        with mock.patch.object(
            modulo, "_iniciar_monitoramento",
            return_value=self._monitor(modulo) if monitorar else None,
        ), mock.patch.object(
            modulo, "extrair_fontes",
            side_effect=lambda *_: eventos.append("extrair_fontes") or fontes,
        ), mock.patch.object(
            modulo, "transformar_munzona",
            side_effect=lambda valor: eventos.append("transformar_munzona") or valor,
        ), mock.patch.object(
            modulo, "agregar_secoes",
            side_effect=lambda valor: eventos.append("agregar_secoes") or valor,
        ), mock.patch.object(
            modulo, "agregar_candidatos",
            side_effect=lambda valor: eventos.append("agregar_candidatos") or valor,
        ), mock.patch.object(
            modulo, "construir_produto",
            side_effect=lambda *_: eventos.append("construir_produto") or dataframe,
        ), mock.patch.object(
            modulo, "obter_conexao_postgres", return_value=object()
        ), mock.patch.object(
            modulo, "carregar_produto",
            side_effect=lambda *_: eventos.append("carregar_produto"),
        ):
            modulo.executar(args)
        return eventos

    def _fluxo_tse_elt(self, monitorar: bool) -> list[str]:
        modulo = PIPELINES[3]
        eventos: list[str] = []
        args = SimpleNamespace(
            benchmark=True, monitorar_recursos=monitorar, limite=1,
            manifesto_chaves=Path("manifesto.csv"), sem_validacao=True,
            database_url=None, schema_raw="raw", schema_staging="staging",
            schema_final="final", rodada=1,
            modalidade="recursos" if monitorar else "desempenho",
            benchmark_output=None,
        )
        carga = modulo.ResultadoCargaRaw(1, 1, 1, 1.0, 1.0)
        conexao = mock.MagicMock()
        cursor = mock.MagicMock()
        conexao.__enter__.return_value = conexao
        conexao.cursor.return_value.__enter__.return_value = cursor
        with mock.patch.object(
            modulo, "_iniciar_monitoramento",
            return_value=self._monitor(modulo) if monitorar else None,
        ), mock.patch.object(
            modulo, "ler_selecao_manifesto",
            side_effect=lambda *_: eventos.append("ler_manifesto") or object(),
        ), mock.patch.object(
            modulo, "obter_conexao_postgres", return_value=object()
        ), mock.patch.object(
            modulo, "_conectar_postgres", return_value=conexao
        ), mock.patch.object(
            modulo, "carregar_raw",
            side_effect=lambda *_: eventos.append("carregar_raw") or carga,
        ), mock.patch.object(
            modulo, "construir_staging",
            side_effect=lambda *_: eventos.append("construir_staging"),
        ), mock.patch.object(
            modulo, "construir_produto",
            side_effect=lambda *_: eventos.append("construir_produto") or 1,
        ):
            modulo.executar(args)
        return eventos

    def test_fluxo_de_processamento_e_identico_entre_modalidades(self) -> None:
        self.assertEqual(self._fluxo_enem_etl(False), self._fluxo_enem_etl(True))
        self.assertEqual(self._fluxo_enem_elt(False), self._fluxo_enem_elt(True))
        self.assertEqual(self._fluxo_tse_etl(False), self._fluxo_tse_etl(True))
        self.assertEqual(self._fluxo_tse_elt(False), self._fluxo_tse_elt(True))

    def test_diagnostico_ram_e_emitido_uma_vez_nos_quatro_pipelines(self) -> None:
        prefixo = "RAM_AMOSTRAS_JSON="
        esperado = {
            "total": 4,
            "validas": 3,
            "incompletas": 1,
            "percentual_incompletas": 25.0,
        }
        for fluxo in (
            self._fluxo_enem_etl,
            self._fluxo_enem_elt,
            self._fluxo_tse_etl,
            self._fluxo_tse_elt,
        ):
            with self.subTest(fluxo=fluxo.__name__):
                saida = StringIO()
                with redirect_stdout(saida):
                    fluxo(True)
                linhas = [
                    linha for linha in saida.getvalue().splitlines()
                    if linha.startswith(prefixo)
                ]
                self.assertEqual(len(linhas), 1)
                self.assertEqual(json.loads(linhas[0][len(prefixo):]), esperado)

    def test_diagnostico_ram_nao_e_emitido_sem_monitoramento(self) -> None:
        for fluxo in (
            self._fluxo_enem_etl,
            self._fluxo_enem_elt,
            self._fluxo_tse_etl,
            self._fluxo_tse_elt,
        ):
            with self.subTest(fluxo=fluxo.__name__):
                saida = StringIO()
                with redirect_stdout(saida):
                    fluxo(False)
                self.assertNotIn("RAM_AMOSTRAS_JSON=", saida.getvalue())

    def test_diagnostico_ram_nao_altera_formato_dos_resultados(self) -> None:
        campos_diagnostico = {
            "total", "validas", "incompletas", "percentual_incompletas"
        }
        for modulo in PIPELINES:
            with self.subTest(modulo=modulo.__name__):
                campos_resultado = {campo.name for campo in fields(modulo.ResultadoBenchmark)}
                self.assertTrue(campos_diagnostico.isdisjoint(campos_resultado))
                self.assertTrue(campos_diagnostico.isdisjoint(modulo.CAMPOS_RECURSOS))

    def test_falha_ao_finalizar_monitor_nao_e_mascarada(self) -> None:
        class FalhaMonitor(RuntimeError):
            pass

        monitor = mock.Mock()
        falha = FalhaMonitor("falha original")
        monitor.parar_com_cpu_times.side_effect = falha
        saida = StringIO()

        with redirect_stdout(saida), self.assertRaises(FalhaMonitor) as capturada:
            finalizar_monitoramento_recursos(monitor)

        self.assertIs(capturada.exception, falha)
        monitor.diagnostico_ram_amostras.assert_not_called()
        self.assertNotIn("RAM_AMOSTRAS_JSON=", saida.getvalue())


class FronteirasTempoTest(unittest.TestCase):
    def test_enem_elt_reutiliza_o_total_interno_no_csv_e_no_throughput(self) -> None:
        modulo = PIPELINES[1]
        tempos = modulo.TemposELT(1.0, 2.0, 3.0, None, 7.5, 3, 2)
        with tempfile.TemporaryDirectory() as temporario, mock.patch.object(
            modulo, "salvar_benchmark"
        ) as salvar:
            modulo.finalizar_benchmark(
                None,
                tempos,
                1,
                1,
                Path(temporario) / "enem_elt.csv",
                "desempenho",
            )

        resultado = salvar.call_args.args[0]
        self.assertEqual(resultado.tempo_total, tempos.total)
        self.assertEqual(resultado.throughput, 5 / tempos.total)

    def test_totais_dos_etls_sao_capturados_antes_dos_resumos(self) -> None:
        for modulo, marcador in (
            (PIPELINES[0], "Carga concluída:"),
            (PIPELINES[2], "Carga concluida:"),
        ):
            with self.subTest(modulo=modulo.__name__):
                fonte = inspect.getsource(modulo.main if modulo is PIPELINES[0] else modulo.executar)
                self.assertLess(
                    fonte.index("tempo_total = time.perf_counter() - inicio_total"),
                    fonte.index(marcador),
                )

    def test_tse_elt_mantem_carga_e_commit_antes_do_total(self) -> None:
        fonte = inspect.getsource(PIPELINES[3].executar)
        self.assertLess(fonte.index("construir_produto("), fonte.index("tempo_total = time.perf_counter()"))
        self.assertLess(fonte.index("conexao.commit()"), fonte.index("tempo_total = time.perf_counter()"))

    def test_limpeza_auxiliar_do_enem_etl_precede_o_cronometro(self) -> None:
        fonte = inspect.getsource(PIPELINES[0].main)
        self.assertLess(fonte.index("limpar_relatorio_valores_desconhecidos()"), fonte.index("inicio_total = time.perf_counter()"))

    def test_formula_de_throughput_e_protegida_nos_quatro_pipelines(self) -> None:
        expressao = "if tempo_total else 0.0"
        for modulo in PIPELINES:
            with self.subTest(modulo=modulo.__name__):
                self.assertIn(expressao, inspect.getsource(modulo))


class CaminhosEGraficosTest(unittest.TestCase):
    def test_campanha_existente_nao_e_sobrescrita_e_modalidade_fica_isolada(self) -> None:
        with tempfile.TemporaryDirectory() as temporario, mock.patch.object(
            benchmark_paths, "CAMPANHAS_DIR", Path(temporario)
        ):
            campanha = benchmark_paths.criar_diretorio_campanha("teste")
            benchmark_paths.criar_diretorios_modalidades(campanha)
            self.assertTrue((campanha / "desempenho").is_dir())
            self.assertTrue((campanha / "recursos").is_dir())
            with self.assertRaises(FileExistsError):
                benchmark_paths.criar_diretorio_campanha("teste")
            with mock.patch.dict(
                os.environ, {"BENCHMARK_OUTPUT_DIR": str(campanha)}
            ):
                self.assertEqual(
                    benchmark_paths.diretorio_modalidade_obrigatorio("desempenho").resolve(),
                    (campanha / "desempenho").resolve(),
                )
                self.assertEqual(
                    benchmark_paths.diretorio_modalidade_obrigatorio("recursos").resolve(),
                    (campanha / "recursos").resolve(),
                )
                with self.assertRaises(ValueError):
                    benchmark_paths.diretorio_modalidade_obrigatorio("mista")

    @staticmethod
    def _criar_csvs_graficos(campanha: Path, modalidade: str = "desempenho") -> None:
        destino = campanha / "desempenho"
        destino.mkdir(parents=True)
        campos = [
            "run_id", "modalidade", "monitoramento_ativo",
            "intervalo_monitoramento_s", "dataset", "volume_configurado",
            "arquitetura", "rodada", "tempo_total", "throughput",
        ]
        for dataset in ("enem", "tse"):
            for arquitetura in ("etl", "elt"):
                with (destino / f"{dataset}_{arquitetura}.csv").open(
                    "w", encoding="utf-8", newline=""
                ) as arquivo:
                    escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                    escritor.writeheader()
                    for volume in sorted(gerar_graficos.VOLUMES_ESPERADOS):
                        for rodada in range(1, 6):
                            escritor.writerow({
                                "run_id": "teste",
                                "modalidade": modalidade,
                                "monitoramento_ativo": "false",
                                "intervalo_monitoramento_s": "",
                                "dataset": dataset,
                                "volume_configurado": volume,
                                "arquitetura": arquitetura,
                                "rodada": rodada,
                                "tempo_total": "1,0",
                                "throughput": "100,0",
                            })

    def test_graficos_leem_apenas_desempenho_e_rejeitam_mistura(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario)
            self._criar_csvs_graficos(campanha)
            resultados = gerar_graficos.carregar_resultados(campanha)
            self.assertEqual(len(resultados), 80)
            self.assertEqual(set(resultados["modalidade"]), {"desempenho"})

            caminho = campanha / "desempenho" / "enem_etl.csv"
            texto = caminho.read_text(encoding="utf-8")
            caminho.write_text(texto.replace("desempenho", "recursos", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "modalidades diferentes"):
                gerar_graficos.carregar_resultados(campanha)


if __name__ == "__main__":
    unittest.main()
