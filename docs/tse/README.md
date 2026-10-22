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

O gerador preserva a chave lógica completa de cada seção selecionada. Por isso,
o total efetivo pode ficar ligeiramente acima do limite nominal. O volume
configurado e as linhas efetivamente processadas são registrados separadamente.

## Certificação

A certificação executa ETL e ELT com validações internas e compara os produtos
finais. Os resultados são exibidos no terminal:

```powershell
python src\tse\benchmark.py --certificar
```

Para certificar apenas o piloto:

```powershell
python src\tse\benchmark.py --certificar --volumes 100000
```

### Alertas das fontes

A certificação completa encontrou diferenças entre os valores consolidados em
`munzona` e a soma das seções. ETL e ELT encontraram exatamente as mesmas
contagens; portanto, estes são alertas das fontes, não divergências entre as
arquiteturas.

| Volume nominal | Votos nominais | Votos nulos | Votos de legenda |
|---:|---:|---:|---:|
| 100 mil | 361 | 231 | 78 |
| 250 mil | 697 | 427 | 133 |
| 500 mil | 1.468 | 921 | 236 |
| 1 milhão | 2.922 | 1.676 | 539 |

Não foram encontradas diferenças em comparecimento, abstenções ou votos
brancos. As quantidades representam chaves de município, zona e cargo, não a
quantidade de votos divergentes.

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
- `--run-id`: identificação gravada nas linhas da campanha;
- `--limpar-resultados`: remove explicitamente resultados anteriores antes de
  iniciar uma nova campanha.

Conexão, schemas, manifestos e arquivos de saída são inferidos pelo projeto. O
aquecimento não é gravado; somente as rodadas válidas são adicionadas aos CSVs:

```text
data/benchmark/tse/resultados/tse_etl.csv
data/benchmark/tse/resultados/tse_elt.csv
```
