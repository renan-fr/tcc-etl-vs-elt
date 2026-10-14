from __future__ import annotations

import argparse
import os

import psycopg2
from dotenv import load_dotenv


def comparar_tabela(cursor, schema_a: str, schema_b: str, tabela: str) -> dict[str, int]:
    consultas = {
        "linhas_a": f'SELECT COUNT(*) FROM "{schema_a}"."{tabela}"',
        "linhas_b": f'SELECT COUNT(*) FROM "{schema_b}"."{tabela}"',
        "a_menos_b": (
            f'SELECT COUNT(*) FROM (SELECT * FROM "{schema_a}"."{tabela}" '
            f'EXCEPT ALL SELECT * FROM "{schema_b}"."{tabela}") diferencas'
        ),
        "b_menos_a": (
            f'SELECT COUNT(*) FROM (SELECT * FROM "{schema_b}"."{tabela}" '
            f'EXCEPT ALL SELECT * FROM "{schema_a}"."{tabela}") diferencas'
        ),
    }
    resultado = {}
    for nome, consulta in consultas.items():
        cursor.execute(consulta)
        resultado[nome] = int(cursor.fetchone()[0])
    return resultado


def divergencias_por_coluna(cursor, schema_a: str, schema_b: str, tabela: str) -> list[tuple[str, int]]:
    cursor.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema_a, tabela),
    )
    colunas_a = [linha[0] for linha in cursor.fetchall()]
    cursor.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema_b, tabela),
    )
    colunas_b = [linha[0] for linha in cursor.fetchall()]
    if colunas_a != colunas_b or not colunas_a:
        return [("estrutura", 1)]
    chave = "id_participante" if tabela == "enem_participantes" else "id_resultado"
    divergencias = []
    for coluna in colunas_a:
        consulta = (
            f'SELECT COUNT(*) FROM "{schema_a}"."{tabela}" a '
            f'JOIN "{schema_b}"."{tabela}" b USING ("{chave}") '
            f'WHERE a."{coluna}" IS DISTINCT FROM b."{coluna}"'
        )
        cursor.execute(consulta)
        quantidade = int(cursor.fetchone()[0])
        if quantidade:
            divergencias.append((coluna, quantidade))
    return divergencias


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Compara resultados finais ETL e ELT")
    parser.add_argument("--schema-a", required=True)
    parser.add_argument("--schema-b", required=True)
    args = parser.parse_args()

    conexao = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    try:
        with conexao.cursor() as cursor:
            tabelas = ["enem_participantes", "enem_resultados"]
            equivalente = True
            for tabela in tabelas:
                resultado = comparar_tabela(cursor, args.schema_a, args.schema_b, tabela)
                tabela_equivalente = (
                    resultado["linhas_a"] == resultado["linhas_b"]
                    and resultado["a_menos_b"] == 0
                    and resultado["b_menos_a"] == 0
                )
                equivalente = equivalente and tabela_equivalente
                estado = "OK" if tabela_equivalente else "DIVERGENTE"
                print(f"{tabela}: {estado}")
                print(f"  linhas_a={resultado['linhas_a']}")
                print(f"  linhas_b={resultado['linhas_b']}")
                print(f"  a_menos_b={resultado['a_menos_b']}")
                print(f"  b_menos_a={resultado['b_menos_a']}")
                for coluna, quantidade in divergencias_por_coluna(
                    cursor, args.schema_a, args.schema_b, tabela
                ):
                    print(f"  divergencia_{coluna}={quantidade}")
                    if tabela == "enem_resultados" and coluna == "nota_media_objetivas":
                        cursor.execute(
                            f'SELECT a.id_resultado, a.nota_media_objetivas, '
                            f'b.nota_media_objetivas FROM "{args.schema_a}"."{tabela}" a '
                            f'JOIN "{args.schema_b}"."{tabela}" b USING (id_resultado) '
                            f'WHERE a.nota_media_objetivas IS DISTINCT FROM '
                            f'b.nota_media_objetivas LIMIT 5'
                        )
                        for amostra in cursor.fetchall():
                            print(f"  amostra={amostra}")
            print("equivalencia=OK" if equivalente else "equivalencia=FALHA")
            raise SystemExit(0 if equivalente else 1)
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
