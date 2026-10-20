# Benchmark ETL x ELT — TSE

Este documento descreve a preparação e a execução do benchmark do TSE. O
contrato do produto está em [plano_benchmark.md](plano_benchmark.md), e o
protocolo comum está em [docs/metodologia.md](../metodologia.md).

## Preparação dos subconjuntos

Os manifestos determinam as chaves usadas igualmente pelo ETL e pelo ELT. Eles
devem ser gerados antes das execucoes medidas:

```powershell
python src\benchmark\tse\tse_preparar_subconjuntos.py
```

Para preparar somente o piloto de 100 mil linhas:

```powershell
python src\benchmark\tse\tse_preparar_subconjuntos.py --volumes 100000
```

## ETL

O schema final é configurado por `POSTGRES_SCHEMA_TSE_ETL_FINAL` e usa
`tse_etl_final` como padrão.

Validação sem carga no PostgreSQL:

```powershell
python src\etl\tse\tse_etl.py --limite 100000 --somente-validar `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv
```

Execução com carga e registro das métricas:

```powershell
python src\etl\tse\tse_etl.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv `
  --benchmark --rodada 1
```

O throughput usa a soma das linhas efetivas de `munzona`, seção e candidato.
As diferenças entre totalização municipal e seções são registradas como alertas.

## ELT

O ELT reutiliza a mesma selecao de fontes e o mesmo manifesto do ETL. As linhas
selecionadas sao carregadas como texto em `tse_elt_raw`, transformadas por SQL
em `tse_elt_staging` e consolidadas em
`tse_elt_final.resultado_municipio_cargo`.

Execução do piloto:

```powershell
python src\elt\tse\tse_elt.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv
```

Execução com registro das métricas:

```powershell
python src\elt\tse\tse_elt.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv `
  --benchmark --rodada 1
```

## Equivalência do produto final

Depois de executar ETL e ELT com o mesmo manifesto:

```powershell
python src\validacao\tse\tse_equivalencia.py
```

A verificação compara estrutura, tipos, nulabilidade, quantidade de linhas e
valores, incluindo duplicidades, por meio de diferenças nos dois sentidos.

## Resultados

```text
data/benchmark/tse/resultados/
data/benchmark/tse/resumos/
```
