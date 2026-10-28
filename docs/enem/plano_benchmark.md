# Plano do benchmark ENEM

O ENEM será o cenário de menor complexidade do experimento, com transformações
predominantemente por registro e sem joins entre as tabelas finais. ETL e ELT
deverão executar as mesmas regras e produzir o mesmo contrato final.

## Fontes utilizadas

- `PARTICIPANTES_2024.csv`: dados demográficos, sociais e geográficos dos
  participantes;
- `RESULTADOS_2024.csv`: presenças, características da escola e notas;
- `ITENS_PROVA_2024.csv`: mantido no conjunto de microdados, mas fora do
  benchmark principal.

Os identificadores de participantes e resultados são independentes. Não será
exigida correspondência entre `NU_INSCRICAO` e `NU_SEQUENCIAL`, nem será feito
join entre as duas fontes.

## Fluxo lógico

```text
participantes -> padronização e enriquecimento -> participantes
resultados    -> padronização e enriquecimento -> resultados
```

No ETL, as transformações são executadas em Python antes da carga. No ELT, os
arquivos são carregados como texto no PostgreSQL e transformados por SQL. O
ENEM utiliza a arquitetura `raw -> final`; não haverá uma camada intermediária
de staging apenas por convenção.

## Produto final

O resultado final será composto por duas tabelas independentes:

```text
participantes
resultados
```

`participantes` terá uma linha por registro do arquivo de participantes e será
usada para análises demográficas, sociais e geográficas. `resultados` terá uma
linha por registro do arquivo de resultados e será usada para análises de
presença, desempenho e características das escolas.

### Equivalência entre ETL e ELT

O contrato final deverá ser idêntico nos dois processos quanto a:

- tabelas;
- colunas e ordem das colunas;
- tipos e nulabilidade;
- identificadores lógicos;
- quantidade de registros;
- valores, valores nulos e duplicidades.

As estruturas físicas da camada `raw` poderão ser diferentes. A equivalência
obrigatória será:

```text
ETL.participantes = ELT.participantes
ETL.resultados = ELT.resultados
```

## Decisões confirmadas

- Os dois arquivos serão limitados separadamente pelo mesmo volume nominal.
- A ordem original das linhas será preservada.
- As tabelas finais permanecerão independentes e não terão chave estrangeira.
- Valores textuais ausentes serão representados por `Não informado`.
- Valores numéricos ausentes permanecerão nulos.
- A nota da redação não participará da média das provas objetivas.
- ETL e ELT deverão usar as mesmas linhas e as mesmas regras em cada cenário.
- A equivalência será verificada fora do tempo principal do pipeline.

## Seleção dos volumes

Os volumes oficiais serão 100 mil, 250 mil, 500 mil e 1 milhão de linhas por
arquivo. O limite será aplicado desde o início de cada arquivo, de maneira
determinística, tanto no ETL quanto no ELT.

Assim, um cenário nominal de 100 mil representa até 100 mil linhas de
`PARTICIPANTES_2024.csv` e até 100 mil linhas de `RESULTADOS_2024.csv`. As
quantidades efetivas de cada fonte e a soma processada serão registradas nas
métricas.

## Mapeamento das fontes

`PARTICIPANTES_2024.csv` alimentará identificação, faixa etária, sexo, cor ou
raça, situação de conclusão, indicador de treineiro, município e UF da prova,
faixa de renda, acesso à internet e tipo de escola do ensino médio. A região da
prova será derivada da UF.

`RESULTADOS_2024.csv` alimentará identificação, município e UF da escola,
dependência administrativa, localização, presenças e notas. A região da escola
será derivada da UF. Também serão calculados `nota_media_objetivas` e
`presente_completo`.

## Medição do benchmark

A medição seguirá o protocolo comum definido em
[docs/metodologia.md](../metodologia.md).

No ETL:

```text
tempo_leitura       = leitura dos dois arquivos
tempo_transformacao = mapeamentos, conversões e regras derivadas em Python
tempo_carga         = preparação, serialização, COPY e confirmação da carga
                       das duas tabelas finais no PostgreSQL
tempo_total         = todo o pipeline, da leitura ao fim da carga
```

No ELT:

```text
tempo_leitura       = leitura, interpretação e seleção dos dois arquivos
tempo_carga         = preparação dos blocos, serialização, criação e carga
                       das tabelas raw, incluindo a confirmação da transação
tempo_transformacao = transformações SQL e criação das tabelas finais
tempo_total         = todo o pipeline, da leitura ao fim das tabelas finais
```

No ELT, a leitura e a serialização ocorrem de forma intercalada durante o
`COPY`. A instrumentação atribui o tempo de `next(linhas)` à leitura e o tempo
de `csv.writer.writerow(...)` à carga. O tempo da operação de carga é então
descontado apenas do tempo de leitura, de modo que a serialização e a gravação
permaneçam na carga.

O throughput usará a soma das linhas efetivas dos dois arquivos dividida pelo
tempo total. Antes do benchmark, uma certificação executará as validações
internas e a comparação de equivalência uma vez para cada volume oficial. Essas
etapas não serão executadas nas rodadas de desempenho e ficarão fora do tempo,
do monitoramento de recursos e das estatísticas oficiais.

## Contrato final de colunas

### Tabela `participantes`

```text
id_participante
faixa_etaria
sexo
cor_raca
situacao_conclusao
treineiro
municipio_prova
uf_prova
faixa_renda
possui_internet
tipo_escola_em
regiao_prova
```

### Tabela `resultados`

```text
id_resultado
municipio_escola
uf_escola
dependencia_escola
localizacao_escola
presenca_cn
presenca_ch
presenca_lc
presenca_mt
presenca_redacao
nota_cn
nota_ch
nota_lc
nota_mt
nota_redacao
regiao_escola
nota_media_objetivas
presente_completo
```

## Regras derivadas

`regiao_prova` e `regiao_escola` serão derivadas da UF correspondente.

`nota_media_objetivas` será a média de CN, CH, LC e MT, arredondada para duas
casas decimais. A média será nula quando qualquer uma das quatro notas estiver
ausente. A nota da redação será mantida separadamente.

`presente_completo` será verdadeiro somente quando houver presença em CN, CH,
LC, MT e redação.

## Tipos e nulos

Os identificadores, descrições, categorias, municípios, UFs e regiões serão
armazenados como `TEXT`. `treineiro`, `possui_internet` e
`presente_completo` serão `BOOLEAN`. As notas e a média serão `NUMERIC`.

As regras de nulos serão:

- identificadores finais: `NOT NULL` e sem duplicidade;
- textos ausentes: `Não informado`;
- notas ausentes: `NULL`;
- indicadores sem informação na origem: `NULL`, quando aplicável;
- `nota_media_objetivas`: `NULL` quando faltar qualquer nota objetiva;
- valores numéricos inválidos: erro de validação.

## Validações

O ENEM seguirá o padrão comum:

```text
erro crítico -> interrompe o pipeline
alerta       -> registra e permite continuar
```

Serão erros críticos:

- colunas obrigatórias ausentes ou fora de ordem;
- falha na conversão de tipos;
- identificadores nulos ou duplicados;
- categorias fora dos domínios definidos;
- notas fora do intervalo de 0 a 1000;
- inconsistência entre UF e região;
- cálculo incorreto de `nota_media_objetivas`;
- cálculo incorreto de `presente_completo`;
- quantidade final de linhas diferente da origem selecionada;
- divergência entre ETL e ELT.

Serão alertas:

- valores nulos permitidos;
- textos convertidos para `Não informado`;
- códigos desconhecidos encontrados na origem;
- nota preenchida quando a presença correspondente for diferente de presente.

## Separação de resultados

Os resultados do ENEM serão gravados em:

```text
data/benchmark/enem/resultados/
```

## Schemas e tabelas físicas

O ETL utilizará:

```text
enem_etl_final.participantes
enem_etl_final.resultados
```

O ELT utilizará:

```text
enem_elt_raw.participantes
enem_elt_raw.resultados

enem_elt_final.participantes
enem_elt_final.resultados
```

A camada `enem_elt_raw` armazenará somente as colunas pertencentes ao extrato
experimental, exatamente as mesmas lidas pelo ETL. A projeção de colunas faz
parte da extração comum aos dois pipelines; conversões, regras de negócio e
campos derivados continuam sendo executados somente depois da carga no ELT.

A equivalência final será verificada entre as tabelas de mesmo nome nos
schemas `enem_etl_final` e `enem_elt_final`.
