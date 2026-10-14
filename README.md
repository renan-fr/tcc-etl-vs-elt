# Benchmark ETL x ELT

Este projeto compara o desempenho de ETL e ELT em dois cenários:

- ENEM: transformações predominantemente por registro, sem joins entre as
  tabelas finais;
- TSE: múltiplas fontes, granularidades, agregações e joins.

## Documentação

- [Execução do benchmark do ENEM](docs/enem/README.md)
- [Metodologia experimental comum](docs/metodologia.md)
- [Plano do ELT do ENEM](docs/enem/plano_benchmark_elt.md)
- [Plano do TSE](docs/tse/plano_benchmark.md)

## Dados e resultados

Os dados brutos ficam separados por base em `data/raw/enem` e `data/raw/tse`.
Os resultados de benchmark ficam separados em:

```text
data/benchmark/enem/
data/benchmark/tse/
```

O pipeline TSE ainda será implementado conforme o escopo definido na
metodologia.
