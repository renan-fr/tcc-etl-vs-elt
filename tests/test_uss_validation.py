from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import psutil

from src.experimental.uss_validation import MonitorUSSValidacao
from src import resource_monitor as rm


class ProcessoFalso:
    def __init__(
        self,
        pid: int,
        *,
        nome: str = "postgres.exe",
        criado: float | None = None,
        cpu: list[float | BaseException] | None = None,
        uss: int | BaseException = 100,
    ) -> None:
        self.pid = pid
        self._nome = nome
        self._criado = float(criado if criado is not None else pid)
        self._cpu = list(cpu or [0.0])
        self._uss = uss
        self.filhos: list[ProcessoFalso] = []

    def create_time(self) -> float:
        return self._criado

    def name(self) -> str:
        return self._nome

    def parent(self):
        return None

    def children(self, recursive: bool = False):
        return list(self.filhos)

    def cpu_percent(self, interval=None):
        valor = self._cpu.pop(0) if len(self._cpu) > 1 else self._cpu[0]
        if isinstance(valor, BaseException):
            raise valor
        return valor

    def cpu_times(self):
        return SimpleNamespace(user=0.0, system=0.0)

    def memory_full_info(self):
        if isinstance(self._uss, BaseException):
            raise self._uss
        return SimpleNamespace(uss=self._uss)


def _monitor(python: ProcessoFalso, postgres: ProcessoFalso) -> MonitorUSSValidacao:
    with mock.patch.object(rm.psutil, "Process", return_value=python):
        monitor = MonitorUSSValidacao(relogio=mock.Mock(return_value=1.0))
    identidade = (postgres.pid, postgres.create_time())
    monitor._postgres_vinculado = True
    monitor._raiz_postgres = postgres
    monitor._identidade_raiz = identidade
    monitor._processos_postgres[identidade] = postgres
    monitor._ultimo_instante = 0.0
    monitor._ultimo_instante_postgres = 0.0
    monitor._memoria_disponivel_inicial = 10_000
    return monitor


@mock.patch.object(rm.psutil, "virtual_memory", return_value=SimpleNamespace(available=9_000))
def test_reproduz_original_e_descarta_amostra_removida_durante_cpu(_memoria) -> None:
    python = ProcessoFalso(10, nome="python.exe", cpu=[5.0], uss=200)
    postgres = ProcessoFalso(
        20,
        cpu=[psutil.NoSuchProcess(20)],
        uss=mock.Mock(side_effect=AssertionError("USS nao deve ser lida")),
    )
    monitor = _monitor(python, postgres)

    monitor._registrar_amostra()
    # Reproduz fielmente o defeito oficial: o processo removido vira soma zero.
    assert monitor._amostras[0]["ram_postgres"] == 0.0
    # Evita criar uma segunda amostra final neste teste unitario.
    monitor._resultado = {}
    resultado = monitor.consolidar_duplo()

    assert resultado["amostras_validas"]["original"]["postgres"] == 1
    assert resultado["amostras_validas"]["corrigida"]["postgres"] == 0
    assert resultado["amostras_adicionalmente_descartadas"] == 1
    assert resultado["metricas_uss"]["original"]["postgres"]["media_mb"] == 0.0
    assert resultado["metricas_uss"]["corrigida"]["postgres"]["media_mb"] is None
    amostra = monitor.amostras_auditoria()[0]
    assert amostra["afetada_pela_correcao"] is True
    assert amostra["postgres"] == [
        {
            "pid": 20,
            "create_time": 20.0,
            "uss_bytes": None,
            "leitura_uss_realizada": False,
            "removido_durante_cpu": True,
        }
    ]
    assert any(
        evento["tipo"] == "processo_removido_durante_cpu"
        for evento in monitor.eventos_auditoria()
    )


@mock.patch.object(rm.psutil, "virtual_memory", return_value=SimpleNamespace(available=9_000))
def test_amostra_sem_remocao_e_identica_nos_dois_criterios(_memoria) -> None:
    python = ProcessoFalso(10, nome="python.exe", cpu=[5.0], uss=200)
    postgres = ProcessoFalso(20, cpu=[3.0], uss=300)
    monitor = _monitor(python, postgres)

    monitor._registrar_amostra()
    monitor._resultado = {}
    resultado = monitor.consolidar_duplo()

    assert resultado["amostras_adicionalmente_descartadas"] == 0
    assert resultado["metricas_uss"]["original"] == resultado["metricas_uss"]["corrigida"]
    assert resultado["amostras_validas"]["original"] == resultado["amostras_validas"]["corrigida"]
    assert resultado["diferencas_corrigida_menos_original"]["total"]["media_mb"] == {
        "absoluta_mb": 0.0,
        "percentual": 0.0,
    }


@mock.patch.object(rm.psutil, "virtual_memory", return_value=SimpleNamespace(available=9_000))
def test_falha_na_propria_uss_nao_e_descarte_adicional(_memoria) -> None:
    python = ProcessoFalso(10, nome="python.exe", cpu=[5.0], uss=200)
    postgres = ProcessoFalso(20, cpu=[3.0], uss=psutil.NoSuchProcess(20))
    monitor = _monitor(python, postgres)

    monitor._registrar_amostra()
    monitor._resultado = {}
    resultado = monitor.consolidar_duplo()

    assert resultado["amostras_validas"]["original"]["postgres"] == 0
    assert resultado["amostras_validas"]["corrigida"]["postgres"] == 0
    assert resultado["amostras_adicionalmente_descartadas"] == 0
    assert monitor.amostras_auditoria()[0]["afetada_pela_correcao"] is False
    assert any(
        evento["tipo"] == "processo_encerrado_durante_uss"
        for evento in monitor.eventos_auditoria()
    )


@mock.patch.object(rm.psutil, "virtual_memory", return_value=SimpleNamespace(available=9_000))
def test_correcao_remove_somente_afetada_e_recalcula_diferencas(_memoria) -> None:
    python = ProcessoFalso(10, nome="python.exe", cpu=[5.0, 5.0], uss=200)
    postgres = ProcessoFalso(
        20,
        cpu=[3.0, psutil.NoSuchProcess(20)],
        uss=300,
    )
    monitor = _monitor(python, postgres)
    monitor._relogio = mock.Mock(side_effect=[1.0, 2.0])

    monitor._registrar_amostra()
    monitor._registrar_amostra()
    monitor._resultado = {}
    resultado = monitor.consolidar_duplo()

    assert [
        amostra["afetada_pela_correcao"]
        for amostra in monitor.amostras_auditoria()
    ] == [False, True]
    assert resultado["amostras_validas"]["original"]["postgres"] == 2
    assert resultado["amostras_validas"]["corrigida"]["postgres"] == 1
    assert resultado["amostras_adicionalmente_descartadas"] == 1
    original = resultado["metricas_uss"]["original"]["postgres"]
    corrigida = resultado["metricas_uss"]["corrigida"]["postgres"]
    assert original["media_mb"] == 150 / 1024**2
    assert corrigida["media_mb"] == 300 / 1024**2
    assert original["pico_mb"] == corrigida["pico_mb"] == 300 / 1024**2
    diferenca = resultado["diferencas_corrigida_menos_original"]["postgres"]
    assert diferenca["media_mb"]["absoluta_mb"] == 150 / 1024**2
    assert diferenca["media_mb"]["percentual"] == 100.0
