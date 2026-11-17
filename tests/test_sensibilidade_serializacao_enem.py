from __future__ import annotations

import os
from typing import Any

import pandas as pd
import pytest

from src.enem.experimental import sensibilidade_serializacao as experimento


class _SqlCompostoFalso:
    def __init__(self, texto: str):
        self.texto = texto

    def format(self, *partes: "_SqlCompostoFalso") -> "_SqlCompostoFalso":
        texto = self.texto
        for parte in partes:
            texto = texto.replace("{}", parte.texto, 1)
        return _SqlCompostoFalso(texto)

    def join(self, partes) -> "_SqlCompostoFalso":
        return _SqlCompostoFalso(self.texto.join(parte.texto for parte in partes))

    def as_string(self, _cursor) -> str:
        return self.texto


class _SqlFalso:
    SQL = staticmethod(lambda texto: _SqlCompostoFalso(texto))
    Identifier = staticmethod(lambda texto: _SqlCompostoFalso(f'"{texto}"'))


class _CursorFalso:
    def __init__(self):
        self.copias: list[tuple[str, str]] = []
        self.leituras_por_copy: list[int] = []

    def copy_expert(self, comando: str, buffer: Any) -> None:
        partes = []
        leituras = 0
        while True:
            parte = buffer.read(7)
            leituras += 1
            if not parte:
                break
            partes.append(parte)
        self.copias.append((comando, "".join(partes)))
        self.leituras_por_copy.append(leituras)


@pytest.fixture
def dataframe() -> pd.DataFrame:
    return pd.DataFrame({
        "id": pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
        "ativo": pd.Series([True, False, pd.NA, True, False], dtype="boolean"),
    })


def _executar(monkeypatch, dataframe, configuracao):
    cursor = _CursorFalso()
    monkeypatch.setattr(experimento.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(experimento.sql, "Identifier", _SqlFalso.Identifier)
    medicao = experimento.copiar_dataframe(
        cursor, dataframe, "exp", "participantes", configuracao, tamanho_bloco=2
    )
    return cursor, medicao


def test_configuracao_a_preserva_um_unico_copy_integral(monkeypatch, dataframe) -> None:
    cursor, medicao = _executar(monkeypatch, dataframe, "A")
    assert medicao.blocos == 1
    assert medicao.chamadas_copy == 1
    assert medicao.serializacao_durante_copy is False
    assert len(cursor.copias) == 1
    assert cursor.copias[0][1] == os.linesep.join([
        "id,ativo", "1,true", "2,false", "3,", "4,true", "5,false", ""
    ])


def test_configuracao_b_usa_um_copy_e_um_cabecalho_para_multiplos_blocos(
    monkeypatch, dataframe
) -> None:
    cursor, medicao = _executar(monkeypatch, dataframe, "B")
    assert medicao.blocos == 3
    assert medicao.chamadas_copy == 1
    assert medicao.serializacao_durante_copy is True
    assert len(cursor.copias) == 1
    conteudo = cursor.copias[0][1]
    assert conteudo == os.linesep.join([
        "id,ativo", "1,true", "2,false", "3,", "4,true", "5,false", ""
    ])
    assert conteudo.count(f"id,ativo{os.linesep}") == 1
    assert all("HEADER TRUE, NULL ''" in comando for comando, _ in cursor.copias)


def test_a_e_b_reconstituem_as_mesmas_linhas_csv(monkeypatch, dataframe) -> None:
    cursor_a, _ = _executar(monkeypatch, dataframe, "A")
    cursor_b, _ = _executar(monkeypatch, dataframe, "B")
    assert cursor_a.copias[0][1] == cursor_b.copias[0][1]


def test_csvs_sao_identicos_com_null_booleanos_texto_e_multiplos_blocos(
    monkeypatch,
) -> None:
    dataframe = pd.DataFrame({
        "id": pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
        "ativo": pd.Series([True, pd.NA, False, True, pd.NA], dtype="boolean"),
        "texto": pd.Series(["a,b", 'com "aspas"', pd.NA, "linha\nnova", ""], dtype="string"),
    })
    cursor_a, _ = _executar(monkeypatch, dataframe, "A")
    cursor_b, medicao_b = _executar(monkeypatch, dataframe, "B")
    assert medicao_b.blocos == 3
    assert len(cursor_a.copias) == len(cursor_b.copias) == 1
    assert cursor_a.copias[0][1] == cursor_b.copias[0][1]
    assert cursor_b.copias[0][1].count("id,ativo,texto") == 1


def test_leitor_b_serializa_somente_sob_demanda(dataframe) -> None:
    leitor = experimento.LeitorCsvEmBlocos(dataframe, tamanho_bloco=2)
    assert leitor.blocos == 0
    primeira_parte = leitor.read(1)
    assert primeira_parte == "i"
    assert leitor.blocos == 1
    while leitor.read(7):
        pass
    assert leitor.blocos == 3


def test_dataframe_vazio_mantem_um_copy_apenas_com_cabecalho(monkeypatch) -> None:
    vazio = pd.DataFrame({"id": pd.Series([], dtype="string")})
    cursor_a, medicao_a = _executar(monkeypatch, vazio, "A")
    cursor_b, medicao_b = _executar(monkeypatch, vazio, "B")
    assert medicao_a.blocos == medicao_b.blocos == 1
    assert cursor_a.copias[0][1] == cursor_b.copias[0][1] == f"id{os.linesep}"


def test_ativacao_e_explicita_e_caminhos_oficiais_nao_sao_opcoes() -> None:
    parser = experimento.construir_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    args = parser.parse_args([
        "executar", "--configuracao", "B", "--rodada", "1",
        "--fase", "medicao", "--schema", "exp_teste", "--saida-json", "x.json",
    ])
    assert args.configuracao == "B"
    assert args.tamanho_bloco == 4096
    assert not hasattr(args, "benchmark_output")


def test_ordem_tem_cinco_de_cada_e_e_reprodutivel() -> None:
    ordem = experimento.gerar_ordem(5, 152024)
    assert ordem == experimento.gerar_ordem(5, 152024)
    assert ordem != experimento.gerar_ordem(5, 152025)
    assert [configuracao for configuracao, _ in ordem].count("A") == 5
    assert [configuracao for configuracao, _ in ordem].count("B") == 5
    assert sorted(rodada for config, rodada in ordem if config == "A") == list(range(1, 6))


def test_schemas_oficiais_e_iguais_sao_recusados(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_SCHEMA_ENEM_ETL_FINAL", "etl_oficial")
    with pytest.raises(ValueError, match="oficial"):
        experimento._validar_schemas("etl_oficial", "exp_b")
    with pytest.raises(ValueError, match="distintos"):
        experimento._validar_schemas("exp_a", "exp_a")


def test_resumo_calcula_dp_amostral_cv_e_diferenca_percentual() -> None:
    def resultado(configuracao: str, rodada: int, valor: float):
        return {
            "configuracao": configuracao, "rodada": rodada,
            "tempo_leitura": valor, "tempo_transformacao": valor,
            "tempo_carga_total": valor, "tempo_total": valor,
            "agregado_tabelas": {
                "tempo_preparacao": valor, "tempo_serializacao": valor,
                "tempo_preparacao_serializacao": valor,
                "tempo_chamada_copy": valor, "tempo_carga_tabelas": valor,
            },
            "tabelas": [],
        }
    resumo = experimento.calcular_resumo([
        resultado("A", 1, 1.0), resultado("A", 2, 3.0),
        resultado("B", 1, 2.0), resultado("B", 2, 6.0),
    ])
    total = next(item for item in resumo if item["metrica"] == "tempo_total")
    assert total["media_A"] == 2.0
    assert total["desvio_padrao_amostral_A"] == pytest.approx(2 ** 0.5)
    assert total["cv_A"] == pytest.approx(2 ** 0.5 / 2)
    assert total["diferenca_percentual_b_vs_a"] == 100.0


def test_equivalencia_usa_except_all_nas_duas_direcoes(monkeypatch) -> None:
    class Contexto:
        def __init__(self, valor): self.valor = valor
        def __enter__(self): return self.valor
        def __exit__(self, *_): return False
    cursor = object()
    conexao = type("Conexao", (), {"cursor": lambda self: Contexto(cursor)})()
    monkeypatch.setattr(experimento.equivalencia, "obter_conexao", lambda _: Contexto(conexao))
    monkeypatch.setattr(experimento.equivalencia, "obter_estrutura", lambda *_: [("id", "text")])
    monkeypatch.setattr(experimento.equivalencia, "contar_linhas", lambda *_: 5)
    chamadas = []
    monkeypatch.setattr(
        experimento.equivalencia, "contar_diferencas",
        lambda *args: chamadas.append(args[1:]) or (0, 0),
    )
    resultado = experimento.verificar_equivalencia(None, "exp_a", "exp_b")
    assert resultado["equivalente"] is True
    assert len(chamadas) == len(experimento.equivalencia.TABELAS)
    assert all(chamada[:2] == ("exp_a", "exp_b") for chamada in chamadas)
