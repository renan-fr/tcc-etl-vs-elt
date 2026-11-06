from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import fields
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
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

        def executar(comando, **_kwargs):
            comandos.append(list(comando))
            return mock.Mock(returncode=0)

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
            benchmark.subprocess, "run", side_effect=executar
        ):
            benchmark.main()
        return comandos, json.loads((campanha / "campanha.json").read_text(encoding="utf-8"))

    def test_integracao_simulada_quantidades_flags_metadados_e_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            comandos_1, metadados = self._executar_orquestrador_simulado(raiz, 7)
            comandos_2, _ = self._executar_orquestrador_simulado(raiz, 7)
            comandos_3, _ = self._executar_orquestrador_simulado(raiz, 8)

        self.assertEqual(comandos_1, comandos_2)
        self.assertNotEqual(comandos_1, comandos_3)
        self.assertEqual(len(comandos_1), 16)
        self.assertEqual(sum("--sem-monitoramento" in c for c in comandos_1), 8)
        self.assertEqual(metadados["combinacoes"], 8)
        self.assertEqual(metadados["cenarios_processamento"], 4)
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
                benchmark.subprocess, "run",
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


class AmbienteCampanhaTest(unittest.TestCase):
    def _executar_com_erro_controlado(
        self,
        erro: BaseException,
        ambiente=None,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporario:
            campanha = Path(temporario) / "campanha"
            campanha.mkdir()
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
                benchmark.subprocess, "run", side_effect=erro
            ), mock.patch.object(
                benchmark, "coletar_ambiente",
                return_value=ambiente if ambiente is not None else {
                    "status": "capturado_no_host_da_campanha",
                    "declarado_para_campanha_oficial": {},
                    "capturado_automaticamente": {},
                },
            ):
                with self.assertRaises(type(erro)):
                    benchmark.main()
            return json.loads(
                (campanha / "campanha.json").read_text(encoding="utf-8")
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
                benchmark.subprocess, "run",
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
        metadados = self._executar_com_erro_controlado(erro)

        self.assertEqual(metadados["status"], "falhou")
        registro_erro = metadados["erro"]
        self.assertEqual(registro_erro["tipo"], "RuntimeError")
        self.assertEqual(registro_erro["contexto"], "execucao_pipeline")
        self.assertNotIn("senha-ficticia", json.dumps(metadados))
        self.assertNotIn("senha-url", json.dumps(metadados))
        self.assertNotIn("postgresql://", registro_erro["mensagem"])

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
    def test_resumo_enem_etl_preserva_numeros_e_indica_recurso_ausente(self) -> None:
        modulo = PIPELINES[0]
        resultado = resultado_sem_recursos(modulo)

        linhas = modulo._linhas_resumo_benchmark(resultado)

        self.assertIn("CPU media total: não monitorado", linhas)
        self.assertIn("CPU pico total: não monitorado", linhas)
        self.assertIn("RAM media total: não monitorado", linhas)
        self.assertIn("RAM pico total: não monitorado", linhas)
        self.assertNotIn("0.00", "\n".join(linhas))

        valores = {campo: 12.345 for campo in modulo.CAMPOS_RECURSOS}
        monitorado = modulo.ResultadoBenchmark(
            **{
                campo.name: valores.get(campo.name, getattr(resultado, campo.name))
                for campo in fields(modulo.ResultadoBenchmark)
            }
        )
        linhas_monitorado = modulo._linhas_resumo_benchmark(monitorado)
        self.assertIn("CPU media total: 12.35%", linhas_monitorado)
        self.assertIn("RAM media total: 12.35 MB", linhas_monitorado)

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


class EquivalenciaFluxoTest(unittest.TestCase):
    @staticmethod
    def _monitor(modulo):
        monitor = mock.Mock()
        monitor.parar.return_value = {campo: 1.0 for campo in modulo.CAMPOS_RECURSOS}
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
