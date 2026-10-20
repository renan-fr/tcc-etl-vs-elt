# Benchmark ETL x ELT — TSE

Este documento descreve a preparacao e a execucao do benchmark do TSE. O
contrato do produto esta em [plano_benchmark.md](plano_benchmark.md), e o
protocolo comum esta em [docs/metodologia.md](../metodologia.md).

## Preparacao dos subconjuntos

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

Validacao sem carga no PostgreSQL:

```powershell
python src\etl\tse\tse_etl.py --limite 100000 --somente-validar `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv
```

Execucao com carga e registro das metricas:

```powershell
python src\etl\tse\tse_etl.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv `
  --benchmark --rodada 1
```

O throughput usa a soma das linhas efetivas de `munzona`, secao e candidato.
As diferencas entre totalizacao municipal e secoes sao registradas como alertas.

## ELT

O ELT reutiliza a mesma selecao de fontes e o mesmo manifesto do ETL. As linhas
selecionadas sao carregadas como texto em `tse_elt_raw`, transformadas por SQL
em `tse_elt_staging` e consolidadas em
`tse_elt_final.resultado_municipio_cargo`.

Execucao do piloto:

```powershell
python src\elt\tse\tse_elt.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv
```

Execucao com registro das metricas:

```powershell
python src\elt\tse\tse_elt.py --limite 100000 `
  --manifesto-chaves data\benchmark\tse\subconjuntos\chaves_100000.csv `
  --benchmark --rodada 1
```

## Equivalencia do produto final

Depois de executar ETL e ELT com o mesmo manifesto:

```powershell
python src\validacao\tse\tse_equivalencia.py
```

A verificacao compara estrutura, tipos, nulabilidade, quantidade de linhas e
valores, incluindo duplicidades, por meio de diferencas nos dois sentidos.
