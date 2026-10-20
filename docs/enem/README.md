# Benchmark ETL x ELT — ENEM

Este documento descreve a preparação e a execução do benchmark do ENEM. O
contrato do produto está em [plano_benchmark.md](plano_benchmark.md), e o
protocolo comum está em [docs/metodologia.md](../metodologia.md).

## Preparação dos dados

Na raiz do projeto:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure o PostgreSQL no `.env` e mantenha os arquivos em:

```text
data/raw/enem/microdados_enem_2024/DADOS/
```

Os schemas usados por padrão são configurados por
`POSTGRES_SCHEMA_ENEM_ETL_FINAL`, `POSTGRES_SCHEMA_ENEM_ELT_RAW` e
`POSTGRES_SCHEMA_ENEM_ELT_FINAL`.

O mesmo limite deve ser usado nos dois pipelines. No ENEM, o volume é aplicado
separadamente a `PARTICIPANTES_2024.csv` e `RESULTADOS_2024.csv`.

## ETL

Validação sem carga no PostgreSQL:

```powershell
.venv\Scripts\python.exe src\etl\enem\enem_etl.py `
  --limite 100000 --somente-validar
```

Execução com carga e registro das métricas:

```powershell
.venv\Scripts\python.exe src\etl\enem\enem_etl.py `
  --limite 100000 --benchmark --rodada 1 `
  --benchmark-output data\benchmark\enem\resultados\enem_etl.csv `
  --benchmark-summary-output data\benchmark\enem\resumos\enem_etl.txt
```

## ELT

O ELT carrega os arquivos como texto em `enem_elt_raw` e cria as tabelas
processadas em `enem_elt_final` por meio de transformações SQL.

Execução com carga e registro das métricas:

```powershell
.venv\Scripts\python.exe src\elt\enem\enem_elt.py `
  --limite 100000 --benchmark --rodada 1 `
  --benchmark-output data\benchmark\enem\resultados\enem_elt.csv `
  --benchmark-summary-output data\benchmark\enem\resumos\enem_elt.txt
```

Use `--aquecimento` para a execução preliminar e repita com `--rodada 1` até
`--rodada 5` nas execuções válidas.

## Orquestração

O orquestrador específico do ENEM é:

```powershell
.venv\Scripts\python.exe src\benchmark\enem\enem_benchmark.py --rodadas 5
```

Para um teste reduzido:

```powershell
.venv\Scripts\python.exe src\benchmark\enem\enem_benchmark.py --volumes 100000 --rodadas 1
```

## Equivalência do produto final

Após executar ETL e ELT com o mesmo volume:

```powershell
.venv\Scripts\python.exe src\validacao\enem\enem_equivalencia.py `
  --schema-a enem_etl_final --schema-b enem_elt_final
```

O resultado só deve ser utilizado na análise de desempenho quando as tabelas
`participantes` e `resultados` dos schemas finais forem equivalentes.

## Resultados

```text
data/benchmark/enem/resultados/enem_etl.csv
data/benchmark/enem/resultados/enem_elt.csv
data/benchmark/enem/resumos/
```
