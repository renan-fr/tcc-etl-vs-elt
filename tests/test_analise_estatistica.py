import csv
from pathlib import Path
import tempfile
import unittest

from src.analise_estatistica import AnaliseError, analisar_campanha


IDENTITY = ["run_id", "modalidade", "dataset", "volume_configurado", "arquitetura", "rodada"]
RESOURCE = ["cpu_media_total", "cpu_pico_total", "ram_media_total_mb", "ram_pico_total_mb"]
PERFORMANCE = ["tempo_total", "throughput", "tempo_leitura", "tempo_transformacao", "tempo_carga"]
SEPARATED_RESOURCE = ["cpu_media_python", "cpu_pico_python", "ram_media_python_mb", "ram_pico_python_mb", "cpu_media_postgres", "cpu_pico_postgres", "ram_media_postgres_mb", "ram_pico_postgres_mb"]


class TestAnaliseEstatistica(unittest.TestCase):
    def _criar_campanha(self, raiz: Path, rodadas=range(1, 6), volumes=(100000,), separated=False) -> Path:
        campanha = raiz / "campanha_teste"
        for modalidade in ("desempenho", "recursos"):
            (campanha / modalidade).mkdir(parents=True)
            for dataset in ("enem", "tse"):
                for arquitetura in ("etl", "elt"):
                    campos = IDENTITY + (PERFORMANCE if modalidade == "desempenho" else RESOURCE + (SEPARATED_RESOURCE if separated else []))
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
                            escritor.writerow(linha)
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
            self.assertAlmostEqual(float(comparacao["reducao_tempo_pct"].replace(",", ".")), -25.0, places=3)
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
            self.assertAlmostEqual(float(comparacao["reducao_tempo_pct"].replace(",", ".")), -18.181818, places=5)
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


if __name__ == "__main__":
    unittest.main()
