from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from io import StringIO
import json
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import sys
import time
from typing import Any, Sequence

from dotenv import load_dotenv
import pandas as pd
from psycopg2 import sql

try:
    from src.enem import equivalencia, etl
    from src.enem.serializacao_csv import (
        LeitorCsvEmBlocos,
        TAMANHO_BLOCO_PADRAO,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from src.enem import equivalencia, etl
    from src.enem.serializacao_csv import (
        LeitorCsvEmBlocos,
        TAMANHO_BLOCO_PADRAO,
    )


BASE_DIR = Path(__file__).resolve().parents[3]
DIRETORIO_SAIDA_PADRAO = (
    BASE_DIR / "data" / "experimentos" / "sensibilidade_serializacao_enem"
)
CONFIGURACOES = ("A", "B")
SEMENTE_PADRAO = 15_2024
SCHEMA_A_PADRAO = "exp_enem_serializacao_a"
SCHEMA_B_PADRAO = "exp_enem_serializacao_b"
PADRAO_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class MedicaoTabela:
    tabela: str
    linhas: int
    blocos: int
    chamadas_copy: int
    tempo_preparacao: float
    tempo_serializacao: float
    tempo_chamada_copy: float
    serializacao_durante_copy: bool
    tempo_carga_total: float

    @property
    def tempo_preparacao_serializacao(self) -> float:
        return self.tempo_preparacao + self.tempo_serializacao


def _agregar_medicoes(medicoes: Sequence[MedicaoTabela]) -> dict[str, float | int]:
    return {
        "linhas": sum(item.linhas for item in medicoes),
        "blocos": sum(item.blocos for item in medicoes),
        "chamadas_copy": sum(item.chamadas_copy for item in medicoes),
        "tempo_preparacao": sum(item.tempo_preparacao for item in medicoes),
        "tempo_serializacao": sum(item.tempo_serializacao for item in medicoes),
        "tempo_preparacao_serializacao": sum(
            item.tempo_preparacao_serializacao for item in medicoes
        ),
        "tempo_chamada_copy": sum(
            item.tempo_chamada_copy for item in medicoes
        ),
        "serializacao_durante_copy": any(
            item.serializacao_durante_copy for item in medicoes
        ),
        "tempo_carga_tabelas": sum(item.tempo_carga_total for item in medicoes),
    }


def _comando_copy(cursor: Any, schema: str, tabela: str, colunas: Sequence[str]) -> str:
    comando = sql.SQL(
        "COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(tabela),
        sql.SQL(", ").join(sql.Identifier(coluna) for coluna in colunas),
    )
    return comando.as_string(cursor)


def copiar_dataframe(
    cursor: Any,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    configuracao: str,
    tamanho_bloco: int = TAMANHO_BLOCO_PADRAO,
) -> MedicaoTabela:
    """Serializa e copia um DataFrame com uma unica chamada COPY.

    A materializa todo o CSV antes do COPY. B fornece um unico fluxo progressivo:
    somente o primeiro bloco tem cabecalho e nenhum buffer integral e acumulado.
    Em B, a duracao de ``copy_expert`` inclui a serializacao sob demanda.
    """
    if configuracao not in CONFIGURACOES:
        raise ValueError("configuracao deve ser A ou B")
    if tamanho_bloco < 1:
        raise ValueError("tamanho_bloco deve ser maior que zero")

    comando = _comando_copy(cursor, schema, tabela, list(df.columns))
    inicio_tabela = time.perf_counter()
    if configuracao == "A":
        inicio = time.perf_counter()
        preparado = etl._preparar_dataframe_para_copy(df)
        preparacao = time.perf_counter() - inicio

        buffer = StringIO()
        inicio = time.perf_counter()
        preparado.to_csv(buffer, index=False, header=True, na_rep="")
        serializacao = time.perf_counter() - inicio
        buffer.seek(0)
        inicio = time.perf_counter()
        cursor.copy_expert(comando, buffer)
        tempo_chamada_copy = time.perf_counter() - inicio
        buffer.close()
        blocos = 1
        serializacao_durante_copy = False
    else:
        leitor = LeitorCsvEmBlocos(df, tamanho_bloco, instrumentar=True)
        inicio = time.perf_counter()
        cursor.copy_expert(comando, leitor)
        tempo_chamada_copy = time.perf_counter() - inicio
        preparacao = leitor.tempo_preparacao
        serializacao = leitor.tempo_serializacao
        blocos = leitor.blocos
        serializacao_durante_copy = True

    return MedicaoTabela(
        tabela=tabela,
        linhas=len(df),
        blocos=blocos,
        chamadas_copy=1,
        tempo_preparacao=preparacao,
        tempo_serializacao=serializacao,
        tempo_chamada_copy=tempo_chamada_copy,
        serializacao_durante_copy=serializacao_durante_copy,
        tempo_carga_total=time.perf_counter() - inicio_tabela,
    )


def _carregar_tabela(
    cursor: Any,
    df: pd.DataFrame,
    schema: str,
    tabela: str,
    contrato: list[tuple[str, str]],
    configuracao: str,
    tamanho_bloco: int,
) -> MedicaoTabela:
    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
    )
    cursor.execute(
        sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(schema), sql.Identifier(tabela)
        )
    )
    etl._criar_tabela(cursor, schema, tabela, contrato)
    return copiar_dataframe(
        cursor, df, schema, tabela, configuracao, tamanho_bloco
    )


def executar_uma_carga(
    configuracao: str,
    rodada: int,
    limite: int,
    schema: str,
    tamanho_bloco: int,
    database_url: str | None,
    fase: str,
) -> dict[str, Any]:
    inicio_total = time.perf_counter()
    inicio = time.perf_counter()
    participantes = etl.extrair_participantes(limite)
    resultados = etl.extrair_resultados(limite)
    tempo_leitura = time.perf_counter() - inicio

    inicio = time.perf_counter()
    participantes = etl.transformar_participantes(participantes)
    resultados = etl.transformar_resultados(resultados)
    tempo_transformacao = time.perf_counter() - inicio

    conexao_config = etl.obter_conexao_postgres(database_url)
    inicio_carga = time.perf_counter()
    with etl._conectar_postgres(conexao_config) as conexao:
        with conexao.cursor() as cursor:
            medicoes = [
                _carregar_tabela(
                    cursor,
                    participantes,
                    schema,
                    etl.TABELA_PARTICIPANTES,
                    etl.CONTRATO_PARTICIPANTES,
                    configuracao,
                    tamanho_bloco,
                ),
                _carregar_tabela(
                    cursor,
                    resultados,
                    schema,
                    etl.TABELA_RESULTADOS,
                    etl.CONTRATO_RESULTADOS,
                    configuracao,
                    tamanho_bloco,
                ),
            ]
    tempo_carga_total = time.perf_counter() - inicio_carga
    tempo_total = time.perf_counter() - inicio_total

    return {
        "experimento_id": 15,
        "fase": fase,
        "configuracao": configuracao,
        "rodada": rodada,
        "limite_por_fonte": limite,
        "tamanho_bloco": tamanho_bloco,
        "schema": schema,
        "tempo_leitura": tempo_leitura,
        "tempo_transformacao": tempo_transformacao,
        "tempo_carga_total": tempo_carga_total,
        "tempo_total": tempo_total,
        "tabelas": [
            {**asdict(item), "tempo_preparacao_serializacao": item.tempo_preparacao_serializacao}
            for item in medicoes
        ],
        "agregado_tabelas": _agregar_medicoes(medicoes),
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def verificar_equivalencia(
    database_url: str | None, schema_a: str, schema_b: str
) -> dict[str, Any]:
    resultado: dict[str, Any] = {"equivalente": True, "tabelas": {}}
    with equivalencia.obter_conexao(database_url) as conexao:
        with conexao.cursor() as cursor:
            for tabela in equivalencia.TABELAS:
                estrutura_a = equivalencia.obter_estrutura(cursor, schema_a, tabela)
                estrutura_b = equivalencia.obter_estrutura(cursor, schema_b, tabela)
                estrutura_igual = bool(estrutura_a) and estrutura_a == estrutura_b
                linhas_a = (
                    equivalencia.contar_linhas(cursor, schema_a, tabela)
                    if estrutura_a
                    else None
                )
                linhas_b = (
                    equivalencia.contar_linhas(cursor, schema_b, tabela)
                    if estrutura_b
                    else None
                )
                apenas_a = apenas_b = None
                if estrutura_igual:
                    apenas_a, apenas_b = equivalencia.contar_diferencas(
                        cursor, schema_a, schema_b, tabela
                    )
                tabela_ok = (
                    estrutura_igual
                    and linhas_a == linhas_b
                    and apenas_a == 0
                    and apenas_b == 0
                )
                resultado["equivalente"] = resultado["equivalente"] and tabela_ok
                resultado["tabelas"][tabela] = {
                    "estrutura_e_tipos_iguais": estrutura_igual,
                    "linhas_a": linhas_a,
                    "linhas_b": linhas_b,
                    "except_all_a_menos_b": apenas_a,
                    "except_all_b_menos_a": apenas_b,
                    "equivalente": tabela_ok,
                }
    return resultado


def gerar_ordem(repeticoes: int, semente: int) -> list[tuple[str, int]]:
    itens = [
        (configuracao, rodada)
        for rodada in range(1, repeticoes + 1)
        for configuracao in CONFIGURACOES
    ]
    random.Random(semente).shuffle(itens)
    return itens


def _achatar_resultado(resultado: dict[str, Any]) -> dict[str, Any]:
    linha = {
        chave: valor
        for chave, valor in resultado.items()
        if chave not in {"tabelas", "agregado_tabelas"}
    }
    linha.update(resultado["agregado_tabelas"])
    for tabela in resultado["tabelas"]:
        prefixo = tabela["tabela"]
        for chave, valor in tabela.items():
            if chave != "tabela":
                linha[f"{prefixo}_{chave}"] = valor
    return linha


def calcular_resumo(resultados: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    metricas = [
        "tempo_leitura", "tempo_transformacao", "tempo_preparacao",
        "tempo_serializacao", "tempo_preparacao_serializacao",
        "tempo_chamada_copy",
        "tempo_carga_tabelas", "tempo_carga_total", "tempo_total",
    ]
    linhas = [_achatar_resultado(item) for item in resultados]
    resumo: list[dict[str, Any]] = []
    for metrica in metricas:
        valores = {
            configuracao: [
                float(linha[metrica])
                for linha in linhas
                if linha["configuracao"] == configuracao
            ]
            for configuracao in CONFIGURACOES
        }
        medias = {chave: statistics.mean(valor) for chave, valor in valores.items()}
        registro: dict[str, Any] = {"metrica": metrica}
        for configuracao in CONFIGURACOES:
            serie = valores[configuracao]
            desvio = statistics.stdev(serie) if len(serie) > 1 else 0.0
            registro.update({
                f"media_{configuracao}": medias[configuracao],
                f"mediana_{configuracao}": statistics.median(serie),
                f"desvio_padrao_amostral_{configuracao}": desvio,
                f"cv_{configuracao}": (
                    desvio / medias[configuracao] if medias[configuracao] else 0.0
                ),
            })
        registro["diferenca_percentual_b_vs_a"] = (
            100.0 * (medias["B"] / medias["A"] - 1.0)
            if medias["A"]
            else None
        )
        resumo.append(registro)
    return resumo


def _escrever_csv(caminho: Path, linhas: Sequence[dict[str, Any]]) -> None:
    if not linhas:
        return
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def _escrever_resumo_markdown(
    caminho: Path,
    resultados: Sequence[dict[str, Any]],
    resumo: Sequence[dict[str, Any]],
    ordem: Sequence[tuple[str, int]],
) -> None:
    linhas = [
        "# Sensibilidade de serializacao do ETL ENEM - experimento 15",
        "",
        "A e B usam exatamente um COPY por tabela. B fornece ao COPY um fluxo CSV ",
        "progressivo em blocos de 4.096 linhas, sem acumular o conteudo integral. ",
        "Somente o primeiro bloco possui cabecalho, consumido por `HEADER TRUE`.",
        "",
        "**Limitacao de temporizacao:** em B, `tempo_chamada_copy` inclui preparacao e ",
        "serializacao sob demanda executadas pelas chamadas `read()` do COPY. O tempo ",
        "de serializacao e instrumentado separadamente para diagnostico, mas se sobrepoe ",
        "ao tempo da chamada COPY e nao deve ser somado a ele. Em A, a serializacao ",
        "ocorre antes do COPY. Para comparacao aditiva, use os tempos de carga e total.",
        "",
        "## Resumo agregado das duas tabelas",
        "",
        "| Metrica | Media A | Mediana A | DP A | CV A | Media B | Mediana B | DP B | CV B | B vs A |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in resumo:
        linhas.append(
            f"| {item['metrica']} | {item['media_A']:.6f} | "
            f"{item['mediana_A']:.6f} | {item['desvio_padrao_amostral_A']:.6f} | "
            f"{item['cv_A']:.4f} | {item['media_B']:.6f} | "
            f"{item['mediana_B']:.6f} | {item['desvio_padrao_amostral_B']:.6f} | "
            f"{item['cv_B']:.4f} | {item['diferenca_percentual_b_vs_a']:.2f}% |"
        )
    linhas.extend([
        "", "## Execucoes", "",
        "| Ordem | Configuracao | Rodada | Leitura | Transformacao | Preparacao+serializacao* | Chamada COPY* | Carga total | Total |",
        "|---:|:---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    por_chave = {(r["configuracao"], r["rodada"]): r for r in resultados}
    for posicao, chave in enumerate(ordem, 1):
        item = por_chave[chave]
        agregado = item["agregado_tabelas"]
        linhas.append(
            f"| {posicao} | {item['configuracao']} | {item['rodada']} | "
            f"{item['tempo_leitura']:.6f} | {item['tempo_transformacao']:.6f} | "
            f"{agregado['tempo_preparacao_serializacao']:.6f} | "
            f"{agregado['tempo_chamada_copy']:.6f} | "
            f"{item['tempo_carga_total']:.6f} | "
            f"{item['tempo_total']:.6f} |"
        )
    linhas.extend([
        "",
        "\\* Em B, preparacao/serializacao esta contida na duracao da chamada COPY; ",
        "as duas colunas nao sao componentes aditivos.",
    ])
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _validar_schemas(schema_a: str, schema_b: str) -> None:
    oficiais = {
        "public",
        os.getenv("POSTGRES_SCHEMA_ENEM_ETL_FINAL", "enem_etl_final"),
        os.getenv("POSTGRES_SCHEMA_ENEM_ELT_FINAL", "enem_elt_final"),
    }
    for schema in (schema_a, schema_b):
        if not PADRAO_IDENTIFICADOR.fullmatch(schema):
            raise ValueError(f"schema experimental invalido: {schema!r}")
        if schema in oficiais:
            raise ValueError(f"schema experimental coincide com schema oficial: {schema}")
    if schema_a == schema_b:
        raise ValueError("os schemas A e B devem ser distintos")


def _executar_subprocesso(
    argumentos: argparse.Namespace,
    configuracao: str,
    rodada: int,
    fase: str,
    destino: Path,
) -> dict[str, Any]:
    schema = argumentos.schema_a if configuracao == "A" else argumentos.schema_b
    comando = [
        sys.executable, "-m", "src.enem.experimental.sensibilidade_serializacao",
        "executar", "--configuracao", configuracao, "--rodada", str(rodada),
        "--fase", fase, "--limite", str(argumentos.limite), "--schema", schema,
        "--tamanho-bloco", str(argumentos.tamanho_bloco),
        "--saida-json", str(destino),
    ]
    ambiente = os.environ.copy()
    if argumentos.database_url:
        ambiente["DATABASE_URL"] = argumentos.database_url
    subprocess.run(comando, cwd=BASE_DIR, env=ambiente, check=True)
    return json.loads(destino.read_text(encoding="utf-8"))


def executar_campanha(args: argparse.Namespace) -> Path:
    _validar_schemas(args.schema_a, args.schema_b)
    if args.repeticoes < 2:
        raise ValueError("repeticoes deve ser pelo menos 2 para o desvio-padrao amostral")
    raiz = args.diretorio_saida.resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    campanha = raiz / datetime.now().strftime("campanha_%Y%m%d_%H%M%S")
    campanha.mkdir()

    validacoes = []
    for configuracao in CONFIGURACOES:
        validacoes.append(_executar_subprocesso(
            args, configuracao, 0, "validacao", campanha / f"validacao_{configuracao}.json"
        ))
    inicial = verificar_equivalencia(args.database_url, args.schema_a, args.schema_b)
    (campanha / "equivalencia_inicial.json").write_text(
        json.dumps(inicial, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not inicial["equivalente"]:
        raise RuntimeError("equivalencia inicial falhou; tempos nao serao interpretados")

    ordem = gerar_ordem(args.repeticoes, args.semente)
    resultados = []
    for posicao, (configuracao, rodada) in enumerate(ordem, 1):
        destino = campanha / f"execucao_{posicao:02d}_{configuracao}_r{rodada}.json"
        resultados.append(_executar_subprocesso(
            args, configuracao, rodada, "medicao", destino
        ))

    final = verificar_equivalencia(args.database_url, args.schema_a, args.schema_b)
    (campanha / "equivalencia_final.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not final["equivalente"]:
        raise RuntimeError("equivalencia final falhou; tempos nao serao interpretados")

    linhas = [_achatar_resultado(item) for item in resultados]
    resumo = calcular_resumo(resultados)
    _escrever_csv(campanha / "resultados.csv", linhas)
    _escrever_csv(campanha / "resumo_estatistico.csv", resumo)
    _escrever_resumo_markdown(campanha / "resumo.md", resultados, resumo, ordem)
    metadados = {
        "experimento_id": 15,
        "limite_por_fonte": args.limite,
        "repeticoes_por_configuracao": args.repeticoes,
        "tamanho_bloco": args.tamanho_bloco,
        "semente": args.semente,
        "ordem": [{"configuracao": c, "rodada": r} for c, r in ordem],
        "schema_a": args.schema_a,
        "schema_b": args.schema_b,
        "monitoramento_continuo_recursos": False,
        "equivalencia_inicial": inicial,
        "equivalencia_final": final,
    }
    (campanha / "metadados.json").write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return campanha


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimento 15: sensibilidade da serializacao ENEM")
    subparsers = parser.add_subparsers(dest="comando", required=True)
    executar = subparsers.add_parser("executar", help="Executa uma unica carga experimental")
    executar.add_argument("--configuracao", choices=CONFIGURACOES, required=True)
    executar.add_argument("--rodada", type=int, required=True)
    executar.add_argument("--fase", choices=("validacao", "medicao"), required=True)
    executar.add_argument("--limite", type=int, default=1_000_000)
    executar.add_argument("--schema", required=True)
    executar.add_argument("--tamanho-bloco", type=int, default=TAMANHO_BLOCO_PADRAO)
    executar.add_argument("--saida-json", type=Path, required=True)
    executar.add_argument("--database-url")

    campanha = subparsers.add_parser("campanha", help="Valida e executa a campanha isolada")
    campanha.add_argument("--limite", type=int, default=1_000_000)
    campanha.add_argument("--repeticoes", type=int, default=5)
    campanha.add_argument("--tamanho-bloco", type=int, default=TAMANHO_BLOCO_PADRAO)
    campanha.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    campanha.add_argument("--schema-a", default=SCHEMA_A_PADRAO)
    campanha.add_argument("--schema-b", default=SCHEMA_B_PADRAO)
    campanha.add_argument("--diretorio-saida", type=Path, default=DIRETORIO_SAIDA_PADRAO)
    campanha.add_argument("--database-url")
    return parser


def main() -> None:
    load_dotenv()
    parser = construir_parser()
    args = parser.parse_args()
    if args.limite < 1 or args.tamanho_bloco < 1:
        parser.error("limite e tamanho-bloco devem ser maiores que zero")
    database_url = args.database_url or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    args.database_url = database_url

    if args.comando == "executar":
        oficiais = {
            "public",
            os.getenv("POSTGRES_SCHEMA_ENEM_ETL_FINAL", "enem_etl_final"),
            os.getenv("POSTGRES_SCHEMA_ENEM_ELT_FINAL", "enem_elt_final"),
        }
        if not PADRAO_IDENTIFICADOR.fullmatch(args.schema) or args.schema in oficiais:
            parser.error("--schema deve identificar um schema experimental nao oficial")
        resultado = executar_uma_carga(
            args.configuracao, args.rodada, args.limite, args.schema,
            args.tamanho_bloco, args.database_url, args.fase,
        )
        args.saida_json.parent.mkdir(parents=True, exist_ok=True)
        args.saida_json.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(args.saida_json)
    else:
        try:
            destino = executar_campanha(args)
        except (ValueError, RuntimeError) as erro:
            raise SystemExit(str(erro)) from erro
        print(f"Campanha concluida: {destino}")


if __name__ == "__main__":
    main()
