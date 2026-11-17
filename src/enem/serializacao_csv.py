from __future__ import annotations

from io import StringIO
import time

import pandas as pd


TAMANHO_BLOCO_PADRAO = 4_096


def preparar_dataframe_para_copy(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica a representacao usada pelo COPY sem alterar o DataFrame original."""
    preparado = df.copy()
    for coluna in preparado.select_dtypes(include=["boolean", "bool"]).columns:
        preparado[coluna] = preparado[coluna].map(
            {True: "true", False: "false", pd.NA: None}
        )
    return preparado


def _fatias(df: pd.DataFrame, tamanho_bloco: int):
    if df.empty:
        # Mesmo sem dados, o COPY com HEADER TRUE precisa receber o cabecalho.
        yield df
        return
    for inicio in range(0, len(df), tamanho_bloco):
        yield df.iloc[inicio : inicio + tamanho_bloco]


class LeitorCsvEmBlocos:
    """Fluxo CSV sob demanda que mantem no maximo um bloco serializado.

    O primeiro bloco usa ``header=True`` e os seguintes usam ``header=False``.
    Assim, uma unica chamada COPY recebe exatamente um cabecalho por tabela.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        tamanho_bloco: int = TAMANHO_BLOCO_PADRAO,
        instrumentar: bool = False,
    ) -> None:
        if tamanho_bloco < 1:
            raise ValueError("tamanho_bloco deve ser maior que zero")
        self._fatias = iter(_fatias(df, tamanho_bloco))
        self._conteudo_atual = ""
        self._posicao = 0
        self._primeiro_bloco = True
        self._esgotado = False
        self._instrumentar = instrumentar
        self.blocos = 0
        self.tempo_preparacao = 0.0
        self.tempo_serializacao = 0.0

    def readable(self) -> bool:
        return True

    def _preparar(self, bloco: pd.DataFrame) -> pd.DataFrame:
        if not self._instrumentar:
            return preparar_dataframe_para_copy(bloco)
        inicio = time.perf_counter()
        preparado = preparar_dataframe_para_copy(bloco)
        self.tempo_preparacao += time.perf_counter() - inicio
        return preparado

    def _serializar(self, preparado: pd.DataFrame) -> str:
        buffer = StringIO()
        if self._instrumentar:
            inicio = time.perf_counter()
        preparado.to_csv(
            buffer,
            index=False,
            header=self._primeiro_bloco,
            na_rep="",
        )
        if self._instrumentar:
            self.tempo_serializacao += time.perf_counter() - inicio
        conteudo = buffer.getvalue()
        buffer.close()
        return conteudo

    def _gerar_proximo_bloco(self) -> bool:
        # Libera o bloco consumido antes de preparar o seguinte.
        self._conteudo_atual = ""
        self._posicao = 0
        try:
            bloco = next(self._fatias)
        except StopIteration:
            self._esgotado = True
            return False

        preparado = self._preparar(bloco)
        self._conteudo_atual = self._serializar(preparado)
        self._primeiro_bloco = False
        self.blocos += 1
        return True

    def read(self, size: int = -1) -> str:
        if size == 0 or self._esgotado:
            return ""
        if size < -1:
            raise ValueError("size deve ser -1 ou nao negativo")

        partes: list[str] = []
        restantes = size
        while size < 0 or restantes > 0:
            if self._posicao >= len(self._conteudo_atual):
                if not self._gerar_proximo_bloco():
                    break
            disponivel = len(self._conteudo_atual) - self._posicao
            quantidade = disponivel if size < 0 else min(disponivel, restantes)
            fim = self._posicao + quantidade
            partes.append(self._conteudo_atual[self._posicao:fim])
            self._posicao = fim
            if size >= 0:
                restantes -= quantidade
        return "".join(partes)
