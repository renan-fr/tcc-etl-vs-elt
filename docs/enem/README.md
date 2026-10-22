# Benchmark ETL x ELT — ENEM

O contrato do produto está em [plano_benchmark.md](plano_benchmark.md), e o
protocolo comum está em [docs/metodologia.md](../metodologia.md).

## Preparação

Instale as dependências, configure o PostgreSQL no `.env` e mantenha os
arquivos do ENEM em:

```text
data/raw/enem/microdados_enem_2024/DADOS/
```

## Certificação

A certificação executa ETL e ELT com validações internas e compara os produtos
finais. Ela deve ser repetida depois de qualquer alteração que possa mudar os
resultados:

```powershell
python src\enem\benchmark.py --certificar
```

Para certificar apenas o piloto:

```powershell
python src\enem\benchmark.py --certificar --volumes 100000
```

## Benchmark

O comando padrão executa um aquecimento e cinco rodadas válidas por volume:

```powershell
python src\enem\benchmark.py
```

Para um teste reduzido:

```powershell
python src\enem\benchmark.py --volumes 100000 --rodadas 1
```

Os únicos parâmetros do experimento são:

- `--volumes`: quantidades máximas de linhas por arquivo;
- `--rodadas`: repetições válidas por volume;
- `--certificar`: executa validações e equivalência em vez de medir desempenho.
- `--seed`: seed da ordem reproduzível (padrão `20241027`);
- `--limpar-resultados`: remove explicitamente resultados anteriores antes de
  iniciar uma nova campanha.

Conexão e schemas são obtidos do `.env`. Os pipelines são chamados pelo
orquestrador e não precisam de configuração manual. O aquecimento não é gravado;
somente as rodadas válidas são adicionadas aos CSVs:

```text
data/benchmark/enem/resultados/enem_etl.csv
data/benchmark/enem/resultados/enem_elt.csv
```
