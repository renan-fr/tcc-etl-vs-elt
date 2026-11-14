import csv
import json
from pathlib import Path
import tempfile
import unittest

from src.analise_estatistica import AnaliseError, analisar_campanha


IDENTITY = ["run_id", "modalidade", "dataset", "volume_configurado", "arquitetura", "rodada"]
RESOURCE = ["cpu_media_total", "cpu_pico_total", "ram_media_total_mb", "ram_pico_total_mb"]
PERFORMANCE = ["tempo_total", "throughput", "tempo_leitura", "tempo_transformacao", "tempo_carga"]
SEPARATED_RESOURCE = ["cpu_media_python", "cpu_pico_python", "ram_media_python_mb", "ram_pico_python_mb", "cpu_media_postgres", "cpu_pico_postgres", "ram_media_postgres_mb", "ram_pico_postgres_mb"]
CPU_TIMES = [
    "cpu_times_python_s", "cpu_times_postgres_s", "cpu_times_total_s",
    "cpu_times_status", "cpu_times_leituras_validas",
    "cpu_times_leituras_validas_python",
    "cpu_times_leituras_validas_postgres", "cpu_times_processos_novos",
    "cpu_times_processos_encerrados", "cpu_times_processos_incompletos",
]


class TestAnaliseEstatistica(unittest.TestCase):
    def _criar_campanha(
        self,
        raiz: Path,
        rodadas=range(1, 6),
        volumes=(100000,),
        separated=False,
        cpu_times_statuses: dict[int, str] | None = None,
    ) -> Path:
        campanha = raiz / "campanha_teste"
        for modalidade in ("desempenho", "recursos"):
            (campanha / modalidade).mkdir(parents=True)
            for dataset in ("enem", "tse"):
                for arquitetura in ("etl", "elt"):
                    campos = IDENTITY + (
                        PERFORMANCE
                        if modalidade == "desempenho"
                        else RESOURCE
                        + (SEPARATED_RESOURCE if separated else [])
                        + (CPU_TIMES if cpu_times_statuses is not None else [])
                    )
                    caminho = campanha / modalidade / f"{dataset}_{arquitetura}.csv"
                    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                        escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                        escritor.writeheader()
                        for volume in volumes:
                          for rodada in rodadas:
                            fator = rodada + volume / 100000 + (0 if arquitetura == "etl" else 1)
                            linha = {"run_id": "campanha_teste", "modalidade": modalidade,
                                     "dataset": dataset, "volume_configurado": str(volume),
                                     "arquitetura": arquitetura, "rodada": rodada}
                            if modalidade == "desempenho":
                                linha.update(tempo_total=str(fator).replace(".", ","), throughput="100", tempo_leitura="1", tempo_transformacao="2", tempo_carga="3")
                            else:
                                linha.update(cpu_media_total="10", cpu_pico_total="20", ram_media_total_mb="30", ram_pico_total_mb="40")
                                if separated:
                                    linha.update(cpu_media_python="1", cpu_pico_python="2", ram_media_python_mb="3", ram_pico_python_mb="4", cpu_media_postgres="5", cpu_pico_postgres="6", ram_media_postgres_mb="7", ram_pico_postgres_mb="8")
                                if cpu_times_statuses is not None:
                                    status = cpu_times_statuses[rodada]
                                    linha.update(
                                        cpu_times_python_s=("1" if status != "sem_leituras_validas" else ""),
                                        cpu_times_postgres_s=("2" if status == "valida" else ""),
                                        cpu_times_total_s=("3" if status == "valida" else ""),
                                        cpu_times_status=status,
                                        cpu_times_leituras_validas=(2 if status == "valida" else 1 if status.startswith("parcial") else 0),
                                        cpu_times_leituras_validas_python=(1 if status != "sem_leituras_validas" else 0),
                                        cpu_times_leituras_validas_postgres=(1 if status == "valida" else 0),
                                        cpu_times_processos_novos=2,
                                        cpu_times_processos_encerrados=0,
                                        cpu_times_processos_incompletos=(1 if status == "parcial_ha_processos_incompletos" else 0),
                                    )
                            escritor.writerow(linha)
        (campanha / "campanha.json").write_text(json.dumps({
            "run_id": "campanha_teste",
            "datasets": ["enem", "tse"],
            "volumes": list(volumes),
        }), encoding="utf-8")
        return campanha

    def test_gera_estatisticas_com_separacao_e_comparacao(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            destino = analisar_campanha("campanha_teste", Path(temporario))
            with (destino / "analise_desempenho.csv").open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo, delimiter=";"))
            etl = next(l for l in linhas if l["arquitetura"] == "etl")
            self.assertEqual(float(etl["tempo_total_media"].replace(",", ".")), 4.0)
            self.assertAlmostEqual(float(etl["tempo_total_desvio_padrao"].replace(",", ".")), 1.5811, places=3)
            self.assertEqual(float(etl["tempo_total_mediana"].replace(",", ".")), 4.0)
            with (destino / "comparacao_etl_elt.csv").open(encoding="utf-8", newline="") as arquivo:
                comparacao = next(csv.DictReader(arquivo, delimiter=";"))
            self.assertAlmostEqual(float(comparacao["variacao_tempo_pct"].replace(",", ".")), 25.0, places=3)
            self.assertTrue((campanha / "desempenho" / "enem_etl.csv").is_file())

    def test_campanha_completa_tem_160_registros_e_resultados_esperados(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario), volumes=(100000, 250000, 500000, 1000000), separated=True)
            originais = {p: p.read_bytes() for p in campanha.glob("*/*.csv")}
            destino = analisar_campanha("campanha_teste", Path(temporario))
            with (destino / "analise_desempenho.csv").open(encoding="utf-8", newline="") as arquivo:
                desempenho = list(csv.DictReader(arquivo, delimiter=";"))
            with (destino / "analise_recursos.csv").open(encoding="utf-8", newline="") as arquivo:
                recursos = list(csv.DictReader(arquivo, delimiter=";"))
            with (destino / "comparacao_etl_elt.csv").open(encoding="utf-8", newline="") as arquivo:
                comparacoes = list(csv.DictReader(arquivo, delimiter=";"))
            quantidade_original = 0
            for p in [*campanha.glob("desempenho/*.csv"), *campanha.glob("recursos/*.csv")]:
                with p.open(encoding="utf-8", newline="") as arquivo:
                    quantidade_original += sum(1 for _ in csv.DictReader(arquivo, delimiter=";"))
            self.assertEqual(quantidade_original, 160)
            self.assertEqual(len(desempenho), 16)
            self.assertEqual(len(recursos), 16)
            self.assertEqual(len(comparacoes), 8)
            etl = next(l for l in desempenho if l["dataset"] == "enem" and l["volume_configurado"] == "250000" and l["arquitetura"] == "etl")
            self.assertAlmostEqual(float(etl["tempo_total_media"].replace(",", ".")), 5.5)
            self.assertAlmostEqual(float(etl["tempo_total_desvio_padrao"].replace(",", ".")), 1.58113883, places=6)
            self.assertAlmostEqual(float(etl["tempo_total_mediana"].replace(",", ".")), 5.5)
            comparacao = next(l for l in comparacoes if l["dataset"] == "enem" and l["volume_configurado"] == "250000")
            self.assertAlmostEqual(float(comparacao["variacao_tempo_pct"].replace(",", ".")), 18.181818, places=5)
            recurso = next(l for l in recursos if l["arquitetura"] == "etl")
            self.assertEqual(recurso["cpu_media_python_media"], "1,0")
            self.assertEqual(recurso["ram_pico_postgres_mb_mediana"], "8,0")
            self.assertEqual({p: p.read_bytes() for p in originais}, originais)

    def test_aquecimento_e_ignorado_mas_rodada_duplicada_falha(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            caminho = campanha / "desempenho" / "enem_etl.csv"
            with caminho.open("a", encoding="utf-8", newline="") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow(["campanha_teste", "desempenho", "enem", "100000", "etl", "aquecimento", "1", "1", "1", "1", "1"])
            analisar_campanha("campanha_teste", Path(temporario))
            with caminho.open("a", encoding="utf-8", newline="") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow(["campanha_teste", "desempenho", "enem", "100000", "etl", "1", "1", "1", "1", "1", "1"])
            with self.assertRaises(AnaliseError):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_rodada_ausente_e_campo_vazio_falham_sem_criar_saida(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario), range(1, 5))
            with self.assertRaises(AnaliseError):
                analisar_campanha("campanha_teste", Path(temporario))
            self.assertFalse((campanha / "analise").exists())

    def test_valor_vazio_nao_numerico_e_run_id_incorreto_falham(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            caminho = campanha / "desempenho" / "enem_etl.csv"
            with caminho.open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo, delimiter=";"))
            fieldnames = list(linhas[0])
            linhas[0]["tempo_total"] = ""
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=fieldnames, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "vazia"):
                analisar_campanha("campanha_teste", Path(temporario))
            linhas[0]["tempo_total"] = "abc"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=fieldnames, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "não numérico"):
                analisar_campanha("campanha_teste", Path(temporario))
            linhas[0]["run_id"] = "outra_campanha"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=fieldnames, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "outro run_id"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_arquitetura_ausente_falha(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            (campanha / "desempenho" / "enem_elt.csv").unlink()
            with self.assertRaisesRegex(AnaliseError, "elt"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_cenario_definido_nos_metadados_mas_ausente_falha(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario), volumes=(100000, 250000, 500000, 1000000))
            for modalidade in ("desempenho", "recursos"):
                for arquitetura in ("etl", "elt"):
                    caminho = campanha / modalidade / f"enem_{arquitetura}.csv"
                    with caminho.open(encoding="utf-8", newline="") as arquivo:
                        leitor = csv.DictReader(arquivo, delimiter=";")
                        campos = leitor.fieldnames
                        linhas = [linha for linha in leitor if linha["volume_configurado"] != "250000"]
                    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                        escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                        escritor.writeheader()
                        escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "cenários esperados ausentes"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_metadados_sem_conjunto_esperado_falham(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            (campanha / "campanha.json").write_text(json.dumps({"run_id": "campanha_teste", "volumes": [100000]}), encoding="utf-8")
            with self.assertRaisesRegex(AnaliseError, "datasets"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_tempos_ou_throughput_nao_positivos_falham(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            caminho = campanha / "desempenho" / "enem_etl.csv"
            with caminho.open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo, delimiter=";"))
                campos = list(linhas[0])
            linhas[0]["tempo_total"] = "0"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "tempo_total deve ser positivo"):
                analisar_campanha("campanha_teste", Path(temporario))

            linhas[0]["tempo_total"] = "1"
            linhas[0]["throughput"] = "-1"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "throughput deve ser positivo"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_cpu_e_ram_negativas_falham(self):
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(Path(temporario))
            caminho = campanha / "recursos" / "enem_etl.csv"
            with caminho.open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo, delimiter=";"))
                campos = list(linhas[0])
            linhas[0]["cpu_media_total"] = "-0,1"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "cpu_media_total não pode ser negativo"):
                analisar_campanha("campanha_teste", Path(temporario))

    def test_cpu_times_agrega_somente_validas_e_conta_estados_parciais(self):
        statuses = {
            1: "valida",
            2: "parcial_ha_componentes_sem_deltas",
            3: "valida",
            4: "sem_leituras_validas",
            5: "valida",
        }
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(
                Path(temporario),
                separated=True,
                cpu_times_statuses=statuses,
            )
            destino = analisar_campanha("campanha_teste", Path(temporario))
            with (destino / "analise_recursos.csv").open(
                encoding="utf-8", newline=""
            ) as arquivo:
                linha = next(csv.DictReader(arquivo, delimiter=";"))

            self.assertEqual(linha["n_execucoes"], "5")
            self.assertEqual(linha["cpu_times_n_validas"], "3")
            self.assertEqual(linha["cpu_times_n_nao_validas"], "2")
            self.assertEqual(
                linha["cpu_times_status_parcial_ha_componentes_sem_deltas_n"],
                "1",
            )
            self.assertEqual(linha["cpu_times_status_sem_leituras_validas_n"], "1")
            self.assertEqual(linha["cpu_times_total_s_media"], "3,0")
            self.assertEqual(linha["cpu_times_total_s_mediana"], "3,0")
            self.assertEqual(linha["cpu_times_total_s_desvio_padrao"], "0,0")

    def test_cpu_times_valida_exige_valores_e_parcial_preserva_total_sem_agregar(self):
        statuses = {rodada: "valida" for rodada in range(1, 6)}
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(
                Path(temporario), cpu_times_statuses=statuses
            )
            caminho = campanha / "recursos" / "enem_etl.csv"
            with caminho.open(encoding="utf-8", newline="") as arquivo:
                linhas = list(csv.DictReader(arquivo, delimiter=";"))
                campos = list(linhas[0])
            linhas[0]["cpu_times_total_s"] = ""
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            with self.assertRaisesRegex(AnaliseError, "medição válida exige"):
                analisar_campanha("campanha_teste", Path(temporario))

            linhas[0]["cpu_times_status"] = "parcial_ha_processos_incompletos"
            linhas[0]["cpu_times_total_s"] = "3"
            with caminho.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
                escritor.writeheader()
                escritor.writerows(linhas)
            destino = analisar_campanha("campanha_teste", Path(temporario))
            with (destino / "analise_recursos.csv").open(
                encoding="utf-8", newline=""
            ) as arquivo:
                agregada = next(
                    linha
                    for linha in csv.DictReader(arquivo, delimiter=";")
                    if linha["dataset"] == "enem"
                    and linha["arquitetura"] == "etl"
                )
            self.assertEqual(agregada["cpu_times_n_validas"], "4")
            self.assertEqual(agregada["cpu_times_n_nao_validas"], "1")

    def test_cpu_times_sem_leituras_nao_vira_zero_na_analise(self):
        statuses = {rodada: "sem_leituras_validas" for rodada in range(1, 6)}
        with tempfile.TemporaryDirectory() as temporario:
            campanha = self._criar_campanha(
                Path(temporario), cpu_times_statuses=statuses
            )
            destino = analisar_campanha("campanha_teste", Path(temporario))
            with (destino / "analise_recursos.csv").open(
                encoding="utf-8", newline=""
            ) as arquivo:
                linha = next(csv.DictReader(arquivo, delimiter=";"))
            self.assertEqual(linha["cpu_times_n_validas"], "0")
            self.assertEqual(linha["cpu_times_n_nao_validas"], "5")
            self.assertEqual(linha["cpu_times_total_s_media"], "")
            self.assertEqual(linha["cpu_times_total_s_desvio_padrao"], "")
            self.assertEqual(linha["cpu_times_total_s_mediana"], "")


if __name__ == "__main__":
    unittest.main()
