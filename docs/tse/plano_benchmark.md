# Plano do benchmark TSE

O TSE sera o cenario de maior complexidade do experimento, sem exigir a
construcao de um produto eleitoral completo. O resultado sera uma consolidacao
por eleicao, turno, municipio, zona e cargo.

## Fontes utilizadas

- `detalhe_votacao_munzona_2024`: tabela-base da totalizacao municipal;
- `detalhe_votacao_secao_2024`: fonte detalhada, agregada de secao para
  municipio/zona/cargo;
- `votacao_candidato_munzona_2024`: votos por candidato, agregados e usados
  para metricas de ranking.

`votacao_partido_munzona_2024` nao sera utilizada neste momento. Os arquivos
`BRASIL` tambem ficarao fora do benchmark principal, pois duplicam o universo
dos arquivos estaduais.

## Fluxo logico

```text
munzona
secao      -> agregacao por municipio/zona/cargo
candidato  -> agregacao e ranking por municipio/zona/cargo
             |
          joins
             |
          processed
```

Cada fonte devera ser agregada antes dos joins para evitar multiplicacao de
registros. ETL e ELT deverao executar as mesmas etapas e produzir o mesmo
contrato final.

## Produto final

O resultado final sera uma unica tabela processada:

```text
resultado_municipio_cargo
```

Cada linha representara uma combinacao de:

```text
eleicao + turno + municipio + zona + cargo
```

A chave logica sera formada por:

```text
ano_eleicao
cd_eleicao
nr_turno
cd_municipio
nr_zona
cd_cargo
```

O produto mantera codigos e descricoes juntos. Os codigos serao utilizados
para identificacao tecnica, joins, validacao e rastreabilidade; os nomes serao
utilizados para leitura e analise.

### Conteudo do produto

O contrato final contera quatro grupos de informacoes:

1. identificacao da eleicao, turno, UF, municipio, zona e cargo;
2. totalizacao municipal, incluindo aptos, comparecimento, abstencoes e tipos
   de voto;
3. metricas agregadas das secoes, incluindo quantidade de secoes e somas de
   comparecimento, abstencoes e votos;
4. metricas de candidatos, incluindo quantidade, total de votos, candidato
   mais votado e sua votacao.

Tambem serao calculados percentuais de comparecimento, abstencao e votacao do
candidato mais votado, alem de diferencas entre a totalizacao municipal e as
somas obtidas a partir das secoes.

### Equivalencia entre ETL e ELT

O contrato final devera ser identico nos dois processos quanto a:

- colunas;
- ordem das colunas;
- tipos;
- chave logica;
- quantidade de registros;
- valores e valores nulos.

As estruturas fisicas de `raw` e `staging` poderao ser diferentes entre ETL e
ELT. A equivalencia obrigatoria sera a tabela `processed`:

```text
ETL.processed = ELT.processed
```

Os nomes das colunas, os tipos SQL e a regra deterministica para desempate entre
candidatos estao definidos neste plano.

## Decisoes confirmadas

- Todos os turnos disponiveis serao utilizados.
- Todos os estados presentes nos arquivos estaduais serao utilizados.
- Os arquivos `BRASIL` permanecerao armazenados, mas ficarao fora do benchmark
  principal.
- `votacao_partido_munzona_2024` nao sera utilizada nesta versao.
- O ranking de candidatos usara `QT_VOTOS_NOMINAIS_VALIDOS`.
- O desempate sera deterministico: maior votacao e, em caso de empate, menor
  `SQ_CANDIDATO`.
- Diferencas entre totalizacao municipal e soma das secoes serao usadas na
  validacao, mas nao farao parte do produto final.
- ETL e ELT deverao usar exatamente o mesmo subconjunto e a mesma quantidade de
  registros em cada fonte para cada cenario.

## Selecao dos volumes

A selecao dos volumes sera uma estrategia compartilhada por ETL e ELT.

- somente arquivos estaduais serao considerados;
- os arquivos serao ordenados por UF;
- a ordem original das linhas sera preservada;
- `detalhe_votacao_secao_2024` sera a fonte de referencia do volume;
- as linhas serao selecionadas ate atingir o volume nominal;
- a chave logica completa sera preservada, incluindo ano, eleicao, turno,
  municipio, zona e cargo;
- a chave que ultrapassar o limite sera incluida integralmente;
- as demais fontes serao filtradas pelas mesmas chaves;
- as quantidades efetivas serao registradas separadamente por fonte.

O volume nominal podera resultar em uma quantidade efetiva ligeiramente maior,
pois nenhuma chave sera cortada no meio. O mesmo subconjunto e as mesmas
quantidades efetivas deverao ser utilizados no ETL e no ELT.

Os codigos municipais serao normalizados para texto com cinco posicoes antes
da selecao e dos joins. Os manifestos de chaves de cada volume serao preparados
antes das execucoes medidas e compartilhados entre ETL e ELT.

## Mapeamento das fontes

`detalhe_votacao_munzona_2024` sera a fonte-base da identificacao e da
totalizacao municipal. Seus campos alimentarao a chave, os codigos e nomes de
eleicao, UF, municipio, zona e cargo, alem das quantidades de aptos,
comparecimento, abstencoes e tipos de voto.

`detalhe_votacao_secao_2024` sera agrupada pela chave de
eleicao/turno/municipio/zona/cargo. A agregacao usara `COUNT(DISTINCT NR_SECAO)`
para a quantidade de secoes e `SUM` para comparecimento, abstencoes, votos
nominais, brancos, nulos e legenda.

`votacao_candidato_munzona_2024` sera agrupada pela mesma chave. A quantidade
de candidatos usara `COUNT(DISTINCT SQ_CANDIDATO)` e os votos de candidatos
usarao `SUM(QT_VOTOS_NOMINAIS_VALIDOS)`.

O candidato mais votado sera definido pela maior quantidade de
`QT_VOTOS_NOMINAIS_VALIDOS`. Em caso de empate, sera utilizado o menor
`SQ_CANDIDATO`. Seus dados preencherao o numero, nome, partido e quantidade de
votos do candidato mais votado no produto final.

O nome do candidato sera obtido de `NM_CANDIDATO`. A consolidacao utilizara
`detalhe_votacao_munzona_2024` como universo do produto e fara `LEFT JOIN` com
as agregacoes de secoes e candidatos. Chaves existentes somente nas fontes
secundarias serao registradas como alerta e nao criarao linhas adicionais.

As agregacoes de secoes e candidatos serao concluidas antes dos joins com a
totalizacao municipal, evitando multiplicacao de registros.

## Medicao do benchmark

A medicao seguira o mesmo padrao utilizado no ENEM.

No ETL:

```text
tempo_leitura       = leitura dos arquivos e selecao do subconjunto
tempo_transformacao = staging, agregacoes, ranking, joins e indicadores
tempo_carga         = preparacao, serializacao, COPY e confirmacao da carga
                       da tabela processed no PostgreSQL
tempo_total         = todo o pipeline, da leitura ao fim da carga
```

No ELT:

```text
tempo_leitura       = leitura, interpretacao e selecao dos arquivos e
                       subconjunto
tempo_carga         = preparacao dos blocos, serializacao, criacao e carga
                       dos arquivos na camada raw, incluindo a confirmacao
                       da transacao
tempo_transformacao = staging SQL, agregacoes, ranking, joins e processed
tempo_total         = todo o pipeline, da preparacao ao fim da processed
```

No ELT, a leitura e a serializacao ocorrem de forma intercalada durante o
`COPY`. A instrumentacao atribui o tempo de `next(linhas)` a leitura e o tempo
de `csv.writer.writerow(...)` a carga. O tempo da operacao de carga e calculado
descontando apenas o tempo atribuido a leitura.

Antes do benchmark, uma certificacao executara as validacoes internas e a
verificacao de equivalencia entre ETL e ELT uma vez para cada volume oficial.
Essas etapas nao serao executadas nas rodadas de desempenho e ficarao fora do
tempo, do monitoramento de recursos e das estatisticas oficiais. `tempo_total`
sera a metrica principal; as demais serao utilizadas para explicar o
comportamento de cada abordagem.

## Contrato final de colunas

A tabela `resultado_municipio_cargo` contera 34 colunas, organizadas assim.

### Identificacao

```text
ano_eleicao
cd_eleicao
nr_turno
sg_uf
cd_municipio
nm_municipio
nr_zona
cd_cargo
ds_cargo
```

### Totalizacao municipal

```text
qt_aptos
qt_comparecimento
qt_abstencoes
qt_total_votos_validos
qt_votos_nominais_validos
qt_total_votos_leg_validos
qt_votos_brancos
qt_total_votos_nulos
qt_total_votos_anulados
```

### Agregacao das secoes

```text
qt_secoes_processadas
qt_comparecimento_secao
qt_abstencoes_secao
qt_votos_nominais_secao
qt_votos_brancos_secao
qt_votos_nulos_secao
qt_votos_legenda_secao
```

### Candidatos

```text
qt_candidatos
qt_votos_candidatos
nr_candidato_mais_votado
nm_candidato_mais_votado
sg_partido_candidato_mais_votado
qt_votos_candidato_mais_votado
```

### Indicadores derivados

```text
pct_comparecimento
pct_abstencao
pct_votos_candidato_mais_votado
```

As formulas serao:

```text
pct_comparecimento = qt_comparecimento / qt_aptos
pct_abstencao = qt_abstencoes / qt_aptos
pct_votos_candidato_mais_votado =
    qt_votos_candidato_mais_votado / qt_votos_candidatos
```

Os percentuais serao nulos quando o denominador for nulo ou igual a zero.
Os resultados serao arredondados para seis casas decimais com a mesma regra no
ETL e no ELT.

## Tipos e nulos

As colunas de identificacao numerica serao `INTEGER`, incluindo `ano_eleicao`,
`cd_eleicao`, `nr_turno`, `nr_zona` e `cd_cargo`.

`cd_municipio` e `nr_candidato_mais_votado` serao armazenados como `TEXT` para
preservar zeros a esquerda e os valores originais dos codigos.

As colunas descritivas serao `TEXT`, incluindo UF, municipio, cargo, nome do
candidato e partido.

Todas as colunas de quantidade e votos usarao `BIGINT`.

Os percentuais usarao `NUMERIC(9,6)` e serao armazenados como decimais entre
zero e um:

```text
0.75 = 75%
0.25 = 25%
```

As regras de nulos serao:

- chaves e identificadores principais: `NOT NULL`;
- nomes descritivos principais: `NOT NULL`;
- ausencias informadas na origem: preservadas como `NULL`;
- candidato mais votado inexistente: campos do candidato como `NULL`;
- contagens agregadas sem registros correspondentes: `0`;
- percentuais sem denominador valido: `NULL`;
- valores numericos invalidos: erro de validacao.

O pipeline diferenciara ausencia de informacao (`NULL`) de valor medido igual a
zero (`0`).

## Validacoes

O TSE seguira o mesmo padrao de validacao utilizado no ENEM:

```text
erro critico -> interrompe o pipeline
alerta       -> registra e permite continuar
```

Serão erros criticos:

- colunas obrigatorias ausentes;
- falha na conversao de tipos;
- chaves principais nulas ou duplicadas;
- duplicidade inesperada na granularidade de staging;
- valores negativos em votos ou quantidades de eleitores;
- multiplicacao de registros apos os joins;
- chave duplicada na tabela final;
- divergencia entre ETL e ELT.

Serão alertas:

- valores nulos informados pela origem;
- ausencia de candidatos para uma chave;
- diferenca entre a soma das secoes e a totalizacao municipal;
- comparecimento mais abstencoes diferente de aptos;
- relacoes entre tipos de votos que precisem de confirmacao na documentacao
  oficial do TSE.

As validacoes especificas do ENEM, como intervalo de notas, presenca e
consistencia entre UF e regiao, nao serao reutilizadas no TSE.

## Separacao de resultados

Os resultados futuros do TSE deverao ser gravados em:

```text
data/benchmark/tse/resultados/
```

## Schemas e tabelas fisicas

O ETL utilizara:

```text
tse_etl_final.resultado_municipio_cargo
```

O ELT utilizara:

```text
tse_elt_raw.detalhe_votacao_munzona
tse_elt_raw.detalhe_votacao_secao
tse_elt_raw.votacao_candidato_munzona

tse_elt_staging.munzona
tse_elt_staging.secao
tse_elt_staging.candidato

tse_elt_final.resultado_municipio_cargo
```

A equivalencia final sera verificada entre:

```text
tse_etl_final.resultado_municipio_cargo
tse_elt_final.resultado_municipio_cargo
```
