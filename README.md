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

## Campanha oficial

Depois da certificação, a campanha completa deve ser iniciada pelo orquestrador
global. Ele randomiza ENEM/TSE, volumes e arquiteturas com seed reproduzível,
identifica os resultados com um `run_id` e exige CSVs de resultado vazios:

```powershell
python src\benchmark.py --run-id oficial_01 --limpar-resultados
```

O comando executa um aquecimento e cinco rodadas válidas para cada uma das 16
combinações (2 bases × 4 volumes × 2 arquiteturas), totalizando 80 medições
gravadas e 16 aquecimentos, ou 96 execuções de pipeline. O uso de
`--limpar-resultados` remove os CSVs e os metadados da campanha anterior.
Por segurança, o orquestrador também recusa iniciar a campanha oficial quando
a árvore Git contém alterações não registradas.

Os parâmetros e o andamento da campanha ficam centralizados em um único arquivo:

```text
data/benchmark/campanha.json
```

O arquivo registra `run_id`, seed, volumes, rodadas, commit Git, contagens,
horários e estado final, sem gerar logs separados por execução.

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
    ├── benchmark.py
    ├── contrato.py
    ├── comum.py
    ├── preparar_subconjuntos.py
    └── equivalencia.py
```

Os pipelines ETL e ELT não importam um ao outro. Ambos usam o mesmo contrato
final e os mesmos manifestos de subconjuntos, mas implementam separadamente a
leitura e o processamento das fontes.

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
