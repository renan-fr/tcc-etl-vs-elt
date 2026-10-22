# Benchmark ETL x ELT — TSE

O contrato do produto está em [plano_benchmark.md](plano_benchmark.md), e o
protocolo comum está em [docs/metodologia.md](../metodologia.md).

## Preparação dos subconjuntos

Os manifestos fixam as mesmas chaves para ETL e ELT e ficam fora das execuções
medidas:

```powershell
python src\tse\preparar_subconjuntos.py
```

Para preparar apenas o piloto:

```powershell
python src\tse\preparar_subconjuntos.py --volumes 100000
```

Cada volume utiliza automaticamente:

```text
data/benchmark/tse/subconjuntos/chaves_<volume>.csv
```

Na cópia local de 2024, o limite nominal de 3 milhões esgota as fontes estaduais
em 1.055.460 linhas de seção. O volume configurado e as linhas efetivamente
processadas são registrados separadamente; portanto, esse cenário representa o
teto disponível da fonte, não três milhões de linhas efetivas.

## Certificação

A certificação executa ETL e ELT com validações internas e compara os produtos
finais. Também grava o log completo e um CSV com as contagens de diferenças
entre `munzona` e seções por volume e arquitetura:

```powershell
python src\tse\benchmark.py --certificar
```

Para certificar apenas o piloto:

```powershell
python src\tse\benchmark.py --certificar --volumes 100000
```

## Benchmark

O comando padrão executa um aquecimento e cinco rodadas válidas por volume:

```powershell
python src\tse\benchmark.py
```

Para um teste reduzido:

```powershell
python src\tse\benchmark.py --volumes 100000 --rodadas 1
```

Os únicos parâmetros do experimento são:

- `--volumes`: volumes nominais da fonte de seção;
- `--rodadas`: repetições válidas por volume;
- `--certificar`: executa validações e equivalência em vez de medir desempenho.
- `--seed`: seed da ordem reproduzível (padrão `20241027`);
- `--limpar-resultados`: remove explicitamente resultados anteriores antes de
  iniciar uma nova campanha.

Conexão, schemas, manifestos e arquivos de saída são inferidos pelo projeto. O
aquecimento não é gravado; somente as rodadas válidas são adicionadas aos CSVs:

```text
data/benchmark/tse/resultados/tse_etl.csv
data/benchmark/tse/resultados/tse_elt.csv
```
