from __future__ import annotations

import os
from typing import Any

import pandas as pd
import pytest

from src.enem import etl


class _SqlCompostoFalso:
    def __init__(self, texto: str):
        self.texto = texto

    def format(self, *partes: "_SqlCompostoFalso") -> "_SqlCompostoFalso":
        texto = self.texto
        for parte in partes:
            texto = texto.replace("{}", parte.texto, 1)
        return _SqlCompostoFalso(texto)

    def join(self, partes: list["_SqlCompostoFalso"]) -> "_SqlCompostoFalso":
        return _SqlCompostoFalso(self.texto.join(parte.texto for parte in partes))

    def as_string(self, _cursor) -> str:
        return self.texto


class _SqlFalso:
    @staticmethod
    def SQL(texto: str) -> _SqlCompostoFalso:
        return _SqlCompostoFalso(texto)

    @staticmethod
    def Identifier(texto: str) -> _SqlCompostoFalso:
        return _SqlCompostoFalso(f'"{texto}"')


class _CursorFalso:
    def __init__(self):
        self.chamadas: list[tuple[str, str]] = []

    def copy_expert(self, comando: str, buffer: Any) -> None:
        partes = []
        while True:
            parte = buffer.read(7)
            if not parte:
                break
            partes.append(parte)
        self.chamadas.append((comando, "".join(partes)))

    def execute(self, *_args, **_kwargs) -> None:
        pass


class _ContextoFalso:
    def __init__(self, valor: Any):
        self.valor = valor

    def __enter__(self) -> Any:
        return self.valor

    def __exit__(self, *_args) -> bool:
        return False


class _ConexaoFalsa:
    def __init__(self, cursor: _CursorFalso):
        self._cursor = cursor

    def cursor(self) -> _ContextoFalso:
        return _ContextoFalso(self._cursor)


@pytest.fixture
def dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": pd.Series(["1", "2"], dtype="string"),
            "ativo": pd.Series([True, pd.NA], dtype="boolean"),
        }
    )


def test_copy_sem_diagnostico_preserva_serializacao_e_nao_consulta_relogio(
    monkeypatch: pytest.MonkeyPatch,
    dataframe: pd.DataFrame,
) -> None:
    cursor = _CursorFalso()
    chamadas_to_csv = 0
    to_csv_original = pd.DataFrame.to_csv

    def contar_to_csv(self, *args, **kwargs):
        nonlocal chamadas_to_csv
        chamadas_to_csv += 1
        return to_csv_original(self, *args, **kwargs)

    monkeypatch.setattr(etl.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(etl.sql, "Identifier", _SqlFalso.Identifier)
    monkeypatch.setattr(pd.DataFrame, "to_csv", contar_to_csv)
    monkeypatch.setattr(
        etl.time,
        "perf_counter",
        lambda: (_ for _ in ()).throw(AssertionError("relogio consultado")),
    )

    etl._copy_dataframe(cursor, dataframe, "diag", "participantes")

    assert chamadas_to_csv == 1
    assert cursor.chamadas == [
        (
            'COPY "diag"."participantes" ("id", "ativo") '
            "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')",
            os.linesep.join(["id,ativo", "1,true", "2,", ""]),
        )
    ]


def test_copy_diagnostico_mede_as_tres_etapas_sem_duplicar_serializacao(
    monkeypatch: pytest.MonkeyPatch,
    dataframe: pd.DataFrame,
) -> None:
    cursor = _CursorFalso()
    diagnostico = etl.DiagnosticoSerializacao(medicoes=[])
    instantes = iter([1.0, 3.0, 10.0, 15.0, 20.0, 27.0])
    chamadas_to_csv = 0
    to_csv_original = pd.DataFrame.to_csv

    def contar_to_csv(self, *args, **kwargs):
        nonlocal chamadas_to_csv
        chamadas_to_csv += 1
        return to_csv_original(self, *args, **kwargs)

    monkeypatch.setattr(etl.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(etl.sql, "Identifier", _SqlFalso.Identifier)
    monkeypatch.setattr(pd.DataFrame, "to_csv", contar_to_csv)
    monkeypatch.setattr(etl.time, "perf_counter", lambda: next(instantes))

    etl._copy_dataframe(
        cursor,
        dataframe,
        "diag",
        "participantes",
        diagnostico,
    )

    assert chamadas_to_csv == 1
    assert len(cursor.chamadas) == 1
    assert diagnostico.medicoes == [
        etl.MedicaoSerializacaoTabela(
            tabela="participantes",
            tempo_preparacao=7.0,
            tempo_serializacao=5.0,
            tempo_chamada_copy=26.0,
            blocos=1,
        )
    ]


def test_resumo_agrega_tabelas_e_calcula_percentuais(capsys) -> None:
    diagnostico = etl.DiagnosticoSerializacao(
        medicoes=[
            etl.MedicaoSerializacaoTabela("participantes", 1.0, 2.0, 6.0, 1),
            etl.MedicaoSerializacaoTabela("resultados", 4.0, 8.0, 17.0, 2),
        ]
    )

    etl._imprimir_diagnostico_serializacao(
        diagnostico,
        tempo_carga=20.0,
        tempo_total=50.0,
    )

    saida = capsys.readouterr().out
    assert "Tabela participantes:" in saida
    assert "Tabela resultados:" in saida
    assert "Preparacao: 5.000000 s" in saida
    assert "Serializacao to_csv: 10.000000 s" in saida
    assert "Chamadas COPY (incluem preparacao e serializacao): 23.000000 s" in saida
    assert "Carga total do ENEM: 20.000000 s" in saida
    assert "Tempo total do pipeline: 50.000000 s" in saida
    assert "Serializacao / carga total: 50.00%" in saida
    assert "Serializacao / tempo total: 20.00%" in saida
    assert "nao devem ser somadas" in saida


def test_copy_oficial_incremental_usa_um_cabecalho_e_um_copy_com_casos_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataframe = pd.DataFrame(
        {
            "id": pd.Series(["1", "2", "3", "4", "5"], dtype="string"),
            "ativo": pd.Series(
                [True, pd.NA, False, True, pd.NA], dtype="boolean"
            ),
            "texto": pd.Series(
                ["a,b", 'com "aspas"', pd.NA, "linha\nnova", ""],
                dtype="string",
            ),
        }
    )
    esperado = etl._preparar_dataframe_para_copy(dataframe).to_csv(
        index=False,
        header=True,
        na_rep="",
    )
    cursor = _CursorFalso()
    monkeypatch.setattr(etl.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(etl.sql, "Identifier", _SqlFalso.Identifier)
    monkeypatch.setattr(etl, "TAMANHO_BLOCO_PADRAO", 2)
    diagnostico = etl.DiagnosticoSerializacao(medicoes=[])

    etl._copy_dataframe(
        cursor, dataframe, "diag", "participantes", diagnostico
    )

    assert len(cursor.chamadas) == 1
    assert diagnostico.medicoes[0].blocos == 3
    assert cursor.chamadas[0][1] == esperado
    assert cursor.chamadas[0][1].count("id,ativo,texto") == 1


def test_copy_oficial_tabela_vazia_envia_apenas_cabecalho(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataframe = pd.DataFrame(
        {
            "id": pd.Series([], dtype="string"),
            "ativo": pd.Series([], dtype="boolean"),
        }
    )
    cursor = _CursorFalso()
    monkeypatch.setattr(etl.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(etl.sql, "Identifier", _SqlFalso.Identifier)

    etl._copy_dataframe(cursor, dataframe, "diag", "participantes")

    assert len(cursor.chamadas) == 1
    assert cursor.chamadas[0][1] == os.linesep.join(["id,ativo", ""])


def test_carregar_enem_executa_exatamente_um_copy_por_tabela(
    monkeypatch: pytest.MonkeyPatch,
    dataframe: pd.DataFrame,
) -> None:
    cursor = _CursorFalso()
    conexao = _ConexaoFalsa(cursor)
    monkeypatch.setattr(etl.sql, "SQL", _SqlFalso.SQL)
    monkeypatch.setattr(etl.sql, "Identifier", _SqlFalso.Identifier)
    monkeypatch.setattr(
        etl,
        "_conectar_postgres",
        lambda _configuracao: _ContextoFalso(conexao),
    )

    etl.carregar_enem(
        dataframe,
        dataframe,
        conexao_postgres=object(),
        schema="diag",
        if_exists="replace",
    )

    assert len(cursor.chamadas) == 2
    assert sum('"participantes"' in comando for comando, _ in cursor.chamadas) == 1
    assert sum('"resultados"' in comando for comando, _ in cursor.chamadas) == 1
