# Benchmark ETL x ELT

Este projeto compara o desempenho de ETL e ELT em dois cenários:

- ENEM: transformações predominantemente por registro, sem joins entre as
  tabelas finais;
- TSE: múltiplas fontes, granularidades, agregações e joins.

## Documentação

- [Execução do benchmark do ENEM](docs/enem/README.md)
- [Plano do benchmark do ENEM](docs/enem/plano_benchmark.md)
- [Metodologia experimental comum](docs/metodologia.md)
- [Execução do benchmark do TSE](docs/tse/README.md)
- [Plano do benchmark do TSE](docs/tse/plano_benchmark.md)

## Dados e resultados

Os dados brutos ficam separados por base em `data/raw/enem` e `data/raw/tse`.

### Fontes oficiais

- ENEM: [Microdados do Enem, do Inep](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem), pacote referente a 2024;
- TSE: [Resultados - 2024, do Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2024).

Os benchmarks utilizam exclusivamente as copias locais armazenadas em
`data/raw/enem` e `data/raw/tse`. Nenhum dado e baixado durante as execucoes.

Os resultados de benchmark ficam separados em:

```text
data/benchmark/enem/
data/benchmark/tse/
```

## Organização dos pipelines

Os scripts estão agrupados por base para manter ENEM e TSE visualmente
espelhados:

```text
src/
├── enem/
│   ├── etl.py
│   ├── elt.py
│   ├── benchmark.py
│   └── equivalencia.py
└── tse/
    ├── etl.py
    ├── elt.py
    ├── comum.py
    ├── preparar_subconjuntos.py
    └── equivalencia.py
```

O orquestrador do benchmark do TSE será acrescentado em uma etapa posterior.

## Organização no PostgreSQL

Os schemas seguem o padrão `<fonte>_<processo>_<camada>`:

```text
enem_etl_final
enem_elt_raw
enem_elt_final
tse_etl_final
tse_elt_raw
tse_elt_staging
tse_elt_final
```

Os nomes das tabelas representam apenas a entidade, pois fonte, processo e
camada já estão identificados pelo schema. As conexões e os nomes dos schemas
são configurados explicitamente no `.env`; use `.env.example` como modelo.
