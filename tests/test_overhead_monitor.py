from __future__ import annotations

import csv
from dataclasses import fields
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src.experimentos import overhead_monitor as experimento


def _modulos_pipeline():
    caminho_tse = str(experimento.BASE_DIR / "src" / "tse")
    sys.path.insert(0, caminho_tse)
    try:
        from src.enem import elt as enem_elt, etl as enem_etl
        from src.tse import elt as tse_elt, etl as tse_etl
        return enem_etl, enem_elt, tse_etl, tse_elt
    finally:
        sys.path.remove(caminho_tse)


def _execucao(condicao: str, ordem: int = 1) -> experimento.Execucao:
    return experimento.Execucao(
        dataset="enem", arquitetura="etl", volume=100_000,
        condicao=condicao, intervalo_segundos=experimento.INTERVALOS[condicao],
        modo="medir", rodada=1, ordem_condicao=1, ordem=ordem,
    )


class OverheadMonitorTest(unittest.TestCase):
    def test_diagnostico_mede_periodicas_e_final_nos_quatro_monitores(self) -> None:
        amostra = {
            "cpu_python": 1.0, "ram_python": 2.0,
            "cpu_postgres": 3.0, "ram_postgres": 4.0,
            "cpu_total": 4.0, "ram_total": 6.0,
        }
        relogio = [
            1_100_000_000, 1_120_000_000,
            1_230_000_000, 1_260_000_000,
            1_300_000_000, 1_340_000_000,
        ]
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                caminho = Path(temporario) / "diagnostico.csv"
                with mock.patch.dict(
                    os.environ, {experimento.VAR_DIAGNOSTICO: str(caminho)}
                ):
                    os.environ.pop(experimento.VAR_AMOSTRAS, None)
                    monitor = modulo.MonitorRecursos(intervalo_segundos=0.1)
                    registrar = mock.Mock(
                        side_effect=lambda: monitor._amostras.append(amostra.copy())
                    )
                    with mock.patch.object(
                        monitor, "_registrar_amostra", registrar
                    ), mock.patch.object(
                        modulo.time, "perf_counter_ns", side_effect=relogio.copy()
                    ):
                        monitor._registrar_amostra_diagnosticada(
                            "periodica", 1_000_000_000, 1_100_000_000,
                            100_000_000,
                        )
                        monitor._registrar_amostra_diagnosticada(
                            "periodica", 1_120_000_000, 1_220_000_000,
                            100_000_000,
                        )
                        self.assertFalse(caminho.exists())
                        monitor.parar()

                with caminho.open(encoding="utf-8", newline="") as arquivo:
                    linhas = list(csv.DictReader(arquivo))
                self.assertEqual(
                    [linha["origem"] for linha in linhas],
                    ["periodica", "periodica", "final"],
                )
                self.assertEqual(
                    [float(linha["duracao_coleta_ms"]) for linha in linhas],
                    [20.0, 30.0, 40.0],
                )
                self.assertEqual(linhas[0]["intervalo_efetivo_ms"], "")
                self.assertEqual(float(linhas[1]["intervalo_efetivo_ms"]), 130.0)
                self.assertEqual(linhas[2]["intervalo_efetivo_ms"], "")
                self.assertEqual(float(linhas[0]["espera_efetiva_ms"]), 100.0)
                self.assertEqual(float(linhas[1]["atraso_agendamento_ms"]), 10.0)
                self.assertEqual(linhas[2]["atraso_agendamento_ms"], "")

    def test_diagnostico_fica_desligado_por_padrao(self) -> None:
        amostra = {
            "cpu_python": 1.0, "ram_python": 2.0,
            "cpu_postgres": 3.0, "ram_postgres": 4.0,
            "cpu_total": 4.0, "ram_total": 6.0,
        }
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__), mock.patch.dict(
                os.environ, {}, clear=False
            ):
                os.environ.pop(experimento.VAR_DIAGNOSTICO, None)
                os.environ.pop(experimento.VAR_AMOSTRAS, None)
                monitor = modulo.MonitorRecursos(intervalo_segundos=0.1)
                monitor._parar = mock.Mock()
                monitor._parar.wait.side_effect = [False, True]
                registrar = mock.Mock(
                    side_effect=lambda: monitor._amostras.append(amostra.copy())
                )
                with mock.patch.object(
                    monitor, "_registrar_amostra", registrar
                ), mock.patch.object(
                    modulo.time, "perf_counter_ns",
                    side_effect=AssertionError("relogio diagnostico foi consultado"),
                ):
                    monitor._coletar()
                registrar.assert_called_once_with()
                self.assertIsNone(monitor._diagnostico_coletas)

    def test_desligado_nao_instancia_monitor_nos_quatro_pipelines(self) -> None:
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__):
                with mock.patch.object(modulo, "MonitorRecursos") as monitor:
                    self.assertIsNone(modulo._iniciar_monitoramento(True, False, 0.1))
                    monitor.assert_not_called()

    def test_padrao_continua_em_meio_segundo_nos_quatro_pipelines(self) -> None:
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__):
                with mock.patch.object(modulo, "MonitorRecursos") as monitor:
                    criado = modulo._iniciar_monitoramento(True)
                    self.assertIs(criado, monitor.return_value)
                    monitor.assert_called_once_with(intervalo_segundos=0.5)
                    monitor.return_value.iniciar.assert_called_once_with()

    def test_intervalo_de_um_decimo_chega_aos_quatro_monitores(self) -> None:
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__):
                with mock.patch.object(modulo, "MonitorRecursos") as monitor:
                    modulo._iniciar_monitoramento(True, True, 0.1)
                    monitor.assert_called_once_with(intervalo_segundos=0.1)

    def test_contagem_real_de_amostras_e_gravada_pelo_monitor(self) -> None:
        for modulo in _modulos_pipeline():
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                caminho = Path(temporario) / "amostras.txt"
                with mock.patch.dict(os.environ, {experimento.VAR_AMOSTRAS: str(caminho)}):
                    modulo._salvar_numero_amostras([{}, {}, {}])
                self.assertEqual(caminho.read_text(encoding="utf-8"), "3")

    def test_sem_monitoramento_salva_recursos_em_branco_nao_zero(self) -> None:
        for modulo in _modulos_pipeline():
            valores = {}
            for campo in fields(modulo.ResultadoBenchmark):
                if campo.name in modulo.CAMPOS_RECURSOS:
                    valores[campo.name] = None
                elif campo.name == "dataset":
                    valores[campo.name] = "teste"
                elif campo.name == "arquitetura":
                    valores[campo.name] = "etl"
                elif campo.name == "timestamp":
                    valores[campo.name] = "2026-11-05T00:00:00"
                elif campo.name.startswith("tempo_") or campo.name == "throughput":
                    valores[campo.name] = 1.0
                else:
                    valores[campo.name] = 1
            resultado = modulo.ResultadoBenchmark(**valores)
            salvar = (
                getattr(modulo, "_salvar_resultado_benchmark", None)
                or getattr(modulo, "salvar_benchmark", None)
                or getattr(modulo, "_salvar_benchmark")
            )
            with self.subTest(modulo=modulo.__name__), tempfile.TemporaryDirectory() as temporario:
                caminho = Path(temporario) / "resultado.csv"
                with mock.patch.dict(os.environ, {"BENCHMARK_RUN_ID": "teste"}):
                    salvar(resultado, caminho)
                with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
                    linha = next(csv.DictReader(arquivo, delimiter=";"))
                for campo in modulo.CAMPOS_RECURSOS:
                    self.assertEqual(linha[campo], "")
                self.assertNotIn("numero_amostras", linha)

    def test_plano_oficial_tem_72_execucoes_reprodutiveis_e_pareadas(self) -> None:
        plano = experimento.criar_plano([100_000], 5, 42)
        self.assertEqual(plano, experimento.criar_plano([100_000], 5, 42))
        self.assertEqual(len(plano), 72)
        self.assertEqual(sum(item.modo == "aquecimento" for item in plano), 12)
        self.assertEqual(sum(item.modo == "medir" for item in plano), 60)
        self.assertEqual([item.ordem for item in plano], list(range(1, 73)))
        for indice in range(0, len(plano), 3):
            grupo = plano[indice:indice + 3]
            identidades = {
                (item.dataset, item.arquitetura, item.volume, item.modo, item.rodada)
                for item in grupo
            }
            self.assertEqual(len(identidades), 1)
            self.assertEqual({item.condicao for item in grupo}, set(experimento.CONDICOES))
            self.assertEqual({item.ordem_condicao for item in grupo}, {1, 2, 3})

    def test_condicoes_mudam_somente_configuracao_do_monitor(self) -> None:
        comandos = {
            condicao: experimento.comando(_execucao(condicao), Path("x.csv"))
            for condicao in experimento.CONDICOES
        }

        def sem_configuracao_monitor(argumentos: list[str]) -> list[str]:
            argumentos = argumentos.copy()
            if "--sem-monitoramento" in argumentos:
                argumentos.remove("--sem-monitoramento")
            if "--intervalo-monitoramento" in argumentos:
                indice = argumentos.index("--intervalo-monitoramento")
                del argumentos[indice:indice + 2]
            return argumentos

        bases = [sem_configuracao_monitor(valor) for valor in comandos.values()]
        self.assertTrue(all(base == bases[0] for base in bases))
        self.assertIn("--sem-monitoramento", comandos["desligado"])
        self.assertIn("0.5", comandos["monitor_0_5s"])
        self.assertIn("0.3", comandos["monitor_0_3s"])

    def test_orquestrador_simulado_gera_72_resultados_e_metadados(self) -> None:
        chamadas: list[list[str]] = []

        def runner(comando, **kwargs):
            chamadas.append(comando)
            self.assertNotIn(experimento.VAR_DIAGNOSTICO, kwargs["env"])
            if "--benchmark-output" in comando:
                caminho = Path(comando[comando.index("--benchmark-output") + 1])
                caminho.write_text("tempo_total;cpu_media_total\n1,25;\n", encoding="utf-8")
            caminho_amostras = kwargs["env"].get(experimento.VAR_AMOSTRAS)
            if caminho_amostras:
                Path(caminho_amostras).write_text("7", encoding="utf-8")
            return subprocess.CompletedProcess(comando, 0)

        with tempfile.TemporaryDirectory() as temporario:
            saida = experimento.executar_experimento(
                [100_000], 5, 77, "teste_01", runner=runner,
                resultados_base=Path(temporario),
            )
            with (saida / "resultados.csv").open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo))
            metadados = json.loads((saida / "metadados.json").read_text(encoding="utf-8"))

            self.assertEqual(len(chamadas), 72)
            self.assertEqual(len(linhas), 72)
            self.assertEqual(
                {
                    (linha["condicao"], linha["intervalo_segundos"])
                    for linha in linhas
                },
                {("desligado", ""), ("monitor_0_5s", "0.5"),
                 ("monitor_0_3s", "0.3")},
            )
            self.assertEqual(sum(linha["modo"] == "medir" for linha in linhas), 60)
            self.assertEqual(sum(linha["modo"] == "aquecimento" for linha in linhas), 12)
            desligadas = [linha for linha in linhas if linha["condicao"] == "desligado"]
            monitoradas = [linha for linha in linhas if linha["condicao"] != "desligado"]
            self.assertTrue(all(linha["numero_amostras"] == "" for linha in desligadas))
            self.assertTrue(all(linha["intervalo_segundos"] == "" for linha in desligadas))
            self.assertTrue(all(linha["numero_amostras"] == "7" for linha in monitoradas))
            self.assertTrue(all(linha["seed"] == "77" for linha in linhas))
            self.assertTrue(all(linha["tempo_total"] == "1.25" for linha in linhas if linha["modo"] == "medir"))
            self.assertTrue(all(linha["tempo_total"] == "" for linha in linhas if linha["modo"] == "aquecimento"))
            self.assertEqual(metadados["status"], "concluido")
            self.assertEqual(metadados["medicoes_validas"], 60)
            self.assertEqual(metadados["aquecimentos"], 12)
            self.assertEqual(metadados["execucoes_previstas"], 72)
            self.assertEqual(
                metadados["condicoes"],
                [
                    {"nome": "desligado", "intervalo_segundos": None},
                    {"nome": "monitor_0_5s", "intervalo_segundos": 0.5},
                    {"nome": "monitor_0_3s", "intervalo_segundos": 0.3},
                ],
            )
            self.assertIn("sha256", metadados["manifestos_tse"][0])

    def test_diagnostico_reduzido_prepara_quatro_execucoes(self) -> None:
        chamadas: list[list[str]] = []

        def runner(comando, **kwargs):
            chamadas.append(comando)
            ambiente = kwargs["env"]
            bruto = Path(comando[comando.index("--benchmark-output") + 1])
            bruto.write_text("tempo_total;cpu_media_total\n1,25;10\n", encoding="utf-8")
            Path(ambiente[experimento.VAR_AMOSTRAS]).write_text("2", encoding="utf-8")
            Path(ambiente[experimento.VAR_DIAGNOSTICO]).write_text(
                "origem,inicio_perf_counter_ns,duracao_coleta_ms,"
                "intervalo_efetivo_ms,intervalo_configurado_ms,"
                "espera_efetiva_ms,atraso_agendamento_ms\n"
                "periodica,1,10,,100,100,0\n"
                "final,2,20,,,,\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(comando, 0)

        with tempfile.TemporaryDirectory() as temporario:
            saida = experimento.executar_diagnostico_coletas(
                100_000, "diagnostico_teste", runner=runner,
                resultados_base=Path(temporario),
            )
            metadados = json.loads((saida / "metadados.json").read_text(encoding="utf-8"))

        self.assertEqual(len(chamadas), 4)
        self.assertTrue(all("--intervalo-monitoramento" in chamada for chamada in chamadas))
        self.assertTrue(all("0.1" in chamada for chamada in chamadas))
        self.assertEqual(metadados["status"], "concluido")
        self.assertEqual(metadados["execucoes_medidas_concluidas"], 4)
        self.assertEqual(len(metadados["arquivos"]), 4)

    def test_run_id_existente_e_travessia_sao_protegidos(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            (raiz / "repetido").mkdir()
            with self.assertRaises(FileExistsError):
                experimento.executar_experimento(
                    100_000, 1, 1, "repetido", runner=lambda *a, **k: None,
                    resultados_base=raiz,
                )
            with self.assertRaises(ValueError):
                experimento.executar_experimento(
                    100_000, 1, 1, "../fora", runner=lambda *a, **k: None,
                    resultados_base=raiz,
                )

    def test_quatro_pipelines_aceitam_intervalo_sem_executar_pipeline(self) -> None:
        for dataset in experimento.DATASETS:
            for arquitetura in experimento.ARQUITETURAS:
                processo = subprocess.run(
                    [sys.executable, str(experimento.BASE_DIR / "src" / dataset / f"{arquitetura}.py"),
                     "--limite", "0", "--modo", "medir", "--rodada", "1",
                     "--intervalo-monitoramento", "0.1"],
                    cwd=experimento.BASE_DIR, capture_output=True, text=True,
                )
                saida = processo.stdout + processo.stderr
                self.assertNotEqual(processo.returncode, 0)
                self.assertNotIn("unrecognized arguments", saida)
                self.assertIn("maior", saida)


if __name__ == "__main__":
    unittest.main()
