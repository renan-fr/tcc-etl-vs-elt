# Benchmark ETL x ELT — ENEM

## 1. Preparação

No PowerShell, a partir da raiz do projeto:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure a conexão PostgreSQL no `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tcc_etl_vs_elt
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha
```

Os arquivos ENEM devem estar em:

```text
data/raw/enem/microdados_enem_2024/DADOS/
```

## 2. Executar uma rodada ETL

O volume é aplicado separadamente a cada arquivo de origem.

```powershell
.venv\Scripts\python.exe src\etl\enem_etl.py `
  --limite 100000 `
  --schema etl_benchmark `
  --benchmark `
  --rodada 1 `
  --benchmark-output data\benchmark\resultados\enem_etl.csv `
  --benchmark-summary-output data\benchmark\resumos\enem_etl.txt
```

## 3. Executar uma rodada ELT

Use schemas diferentes para RAW e resultado final:

```powershell
.venv\Scripts\python.exe src\elt\enem_elt.py `
  --limite 100000 `
  --schema-raw raw_benchmark `
  --schema-final elt_benchmark `
  --benchmark `
  --rodada 1 `
  --benchmark-output data\benchmark\resultados\enem_elt.csv `
  --benchmark-summary-output data\benchmark\resumos\enem_elt.txt
```

Use `--limite 0` para processar todos os registros. Os volumes definidos são:

```text
100000, 500000, 1000000 e 3000000 registros por arquivo
```

Use `--aquecimento` na execução de aquecimento. O aquecimento deve ser separado
das cinco rodadas válidas:

```powershell
.venv\Scripts\python.exe src\etl\enem_etl.py --limite 100000 --schema etl_benchmark --benchmark --aquecimento --benchmark-output data\benchmark\resultados\enem_etl.csv
.venv\Scripts\python.exe src\elt\enem_elt.py --limite 100000 --schema-raw raw_benchmark --schema-final elt_benchmark --benchmark --aquecimento --benchmark-output data\benchmark\resultados\enem_elt.csv
```

Repita cada cenário com `--rodada 1` até `--rodada 5`. Os resultados são
acumulados nos arquivos CSV informados.

## 4. Comparar os resultados ETL e ELT

Após executar os dois pipelines com o mesmo volume:

```powershell
.venv\Scripts\python.exe src\comparar_equivalencia.py `
  --schema-a etl_benchmark `
  --schema-b elt_benchmark
```

O resultado esperado é:

```text
enem_participantes: OK
enem_resultados: OK
equivalencia=OK
```

Se houver divergência, o cenário não deve ser usado na análise de desempenho
até que a causa seja corrigida.

## 5. Arquivos de resultados

- `data/benchmark/resultados/enem_etl.csv`: métricas do ETL;
- `data/benchmark/resultados/enem_elt.csv`: métricas do ELT;
- `data/benchmark/resumos/`: resumos das execuções.

Os CSVs têm tempos com três casas decimais e as demais métricas numéricas com
duas casas, sendo os arquivos principais para a análise dos tempos, throughput,
CPU, RAM e quantidade de registros.

As execuções oficiais ainda são manuais. O arquivo `src/benchmark.py` será
implementado posteriormente como orquestrador automático.
