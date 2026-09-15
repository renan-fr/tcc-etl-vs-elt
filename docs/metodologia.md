# Metodologia Experimental — ETL × ELT

## 1. Objetivo do experimento

O experimento tem como objetivo comparar o desempenho das abordagens ETL e ELT sob diferentes volumes de dados e níveis de complexidade de processamento.

A análise buscará responder principalmente:

> **Em quais combinações de volume e complexidade de processamento ETL ou ELT apresenta melhor desempenho?**

A comparação será realizada em ambiente controlado, mantendo equivalentes as condições que não fazem parte do objeto de estudo e variando apenas os fatores relevantes para a comparação.

---

## 2. Bases de dados

Serão utilizadas duas bases públicas com características distintas.

### ENEM — base de menor complexidade

A base do ENEM representará o cenário de processamento mais simples.

As transformações deverão envolver principalmente:

- seleção e organização de colunas;
- renomeação ou remapeamento de campos;
- ajuste de tipos de dados;
- padronizações necessárias;
- tratamentos simples.

Não há previsão de joins ou transformações relacionais complexas.

### TSE — base de maior complexidade

A base do TSE representará o cenário de maior complexidade.

Por possuir estrutura potencialmente mais distribuída e demandar maior tratamento, poderá envolver operações adicionais, como relacionamentos entre dados, filtros, agregações e outras transformações necessárias.

As operações exatas serão definidas após a exploração completa dos arquivos.

### Bases de backup

As bases alternativas definidas anteriormente não participarão inicialmente do benchmark. Elas serão utilizadas somente caso algum problema impeça o uso do ENEM ou do TSE.

---

## 3. Volumes analisados

Cada base será avaliada nos seguintes volumes nominais:

- 100.000;
- 500.000;
- 1.000.000;
- 3.000.000.

Esses valores representam o limite nominal utilizado no experimento. A
interpretação exata desse limite poderá depender da estrutura do dataset e da
quantidade de arquivos de origem envolvidos.

No caso da base ENEM, o volume nominal será interpretado como a quantidade
máxima de registros por arquivo de origem, e não como a quantidade total de
registros somando todos os arquivos. Atualmente, a base ENEM utilizará dois
arquivos principais:

- `PARTICIPANTES_2024.csv`;
- `RESULTADOS_2024.csv`.

Assim, os cenários da base ENEM serão interpretados da seguinte forma:

```text
100k:
até 100.000 linhas de participantes
+
até 100.000 linhas de resultados

500k:
até 500.000 linhas de participantes
+
até 500.000 linhas de resultados

1M:
até 1.000.000 de linhas de participantes
+
até 1.000.000 de linhas de resultados

3M:
até 3.000.000 de linhas de participantes
+
até 3.000.000 de linhas de resultados
```

Portanto:

```text
volume nominal ≠ necessariamente quantidade total de linhas processadas
```

A quantidade total efetivamente processada deverá ser registrada separadamente.
Por exemplo:

```text
volume_por_arquivo = 500000

linhas_participantes = 500000
linhas_resultados = 500000

quantidade_registros_total = 1000000
```

Para cada combinação de base e volume, ETL e ELT deverão utilizar exatamente o
mesmo subconjunto de dados.

No caso do ENEM, a seleção será determinística, usando as primeiras `N` linhas
de cada arquivo de origem. Por exemplo, no cenário de 500k:

```text
ETL:
primeiras 500.000 linhas de PARTICIPANTES_2024.csv
primeiras 500.000 linhas de RESULTADOS_2024.csv

ELT:
primeiras 500.000 linhas de PARTICIPANTES_2024.csv
primeiras 500.000 linhas de RESULTADOS_2024.csv
```

A variação de volume será utilizada para analisar como cada abordagem se comporta conforme cresce a quantidade de dados processados.

---

## 4. Implementação dos pipelines

As duas abordagens deverão receber os mesmos dados de origem, executar regras de
transformação logicamente equivalentes e produzir exatamente o mesmo resultado
final para cada dataset.

Para cada combinação experimental, ETL e ELT deverão utilizar:

- os mesmos arquivos;
- o mesmo volume nominal;
- as mesmas linhas;
- as mesmas regras de transformação;
- o mesmo contrato final.

A única diferença desejada entre as execuções será a arquitetura utilizada para
realizar as transformações.

A comparação não deverá ser prejudicada pela inclusão de etapas exclusivas em
apenas uma das arquiteturas. Por isso, a complexidade da base será tratada como
uma característica experimental do dataset, e não como exigência de que ENEM e
TSE utilizem a mesma quantidade de camadas.

### ETL

Fluxo geral:

```text
Arquivo bruto
    ↓
Python / Pandas
    ↓
Transformação
    ↓
PostgreSQL
```

Os dados serão lidos e transformados em Python antes de serem carregados no banco de dados.

A transformação deverá reproduzir exatamente as regras definidas para cada base.

### ELT

Fluxo geral:

```text
Arquivo bruto
    ↓
PostgreSQL RAW
    ↓
Transformação SQL
    ↓
Tabela final
```

Os dados serão inicialmente carregados em seu estado bruto no PostgreSQL. As transformações serão executadas posteriormente no próprio banco, utilizando SQL.

### ENEM — arquitetura simplificada

Para a base ENEM, que representa o cenário de menor complexidade, será adotada
uma arquitetura simplificada.

Fluxo conceitual do ETL:

```text
Arquivos CSV
    ↓
Extração em Python
    ↓
Transformação em Python/Pandas
    ↓
Carga no PostgreSQL
    ↓
Tabelas finais
```

Fluxo conceitual do ELT:

```text
Arquivos CSV
    ↓
Extração
    ↓
Carga bruta no PostgreSQL
    ↓
Transformação em SQL
    ↓
Tabelas finais
```

No ELT do ENEM não será criada uma camada intermediária de `staging` apenas por
convenção arquitetural, pois isso acrescentaria uma etapa de processamento sem
equivalente necessário no ETL e poderia introduzir viés no benchmark.

O ELT carregará inicialmente os dados em uma camada `raw` e, a partir dela,
gerará diretamente as tabelas finais.

As tabelas finais produzidas pelo ETL e pelo ELT deverão possuir exatamente o
mesmo contrato definido para:

- `enem_participantes`;
- `enem_resultados`.

As transformações realizadas no ETL em Python deverão possuir equivalentes em
SQL no ELT, incluindo mapeamentos de categorias, tratamento de valores ausentes,
conversões de tipos, criação de regiões, renomeação de campos, cálculo de
`nota_media_objetivas` e criação de `presente_completo`.

Conceitualmente:

```text
ETL ENEM

CSV
 ↓
Python/Pandas
 ↓
FINAL
```

e:

```text
ELT ENEM

CSV
 ↓
RAW PostgreSQL
 ↓
SQL
 ↓
FINAL
```

O objeto comparado será o resultado final, que deverá ser logicamente e
estruturalmente equivalente entre as duas arquiteturas.

### TSE — arquitetura em camadas

Para a base TSE, que representa o cenário de maior complexidade, será adotada
uma arquitetura em múltiplas camadas:

```text
raw
 ↓
staging
 ↓
processed
```

Essa estrutura segue um modelo semelhante à arquitetura medalhão, porém utiliza
nomenclatura diretamente relacionada ao papel de cada camada.

As responsabilidades serão:

`raw`:
armazenar os dados com mínima alteração em relação aos arquivos de origem.

`staging`:
realizar transformações intermediárias, como tipagem, padronização, tratamento
de valores ausentes, decodificação de códigos, preparação de chaves,
normalizações e outras operações necessárias antes da consolidação final.

`processed`:
representar o resultado final do pipeline, incluindo consolidações, joins,
regras derivadas, agregações ou demais transformações necessárias ao dataset
analítico final.

A arquitetura em camadas do TSE deverá ser reproduzida logicamente tanto no ETL
quanto no ELT.

No ETL:

```text
Arquivos TSE
    ↓
Python
    ↓
Transformações equivalentes à camada staging
    ↓
Transformações equivalentes à camada processed
    ↓
Resultado final
```

No ELT:

```text
Arquivos TSE
    ↓
PostgreSQL RAW
    ↓
Transformações SQL
    ↓
STAGING
    ↓
Transformações SQL
    ↓
PROCESSED
```

O ETL não precisa obrigatoriamente persistir fisicamente cada camada
intermediária no PostgreSQL, mas deve executar as mesmas etapas lógicas e regras
utilizadas no ELT.

O requisito fundamental permanece:

```text
ETL.processed = ELT.processed
```

A camada `processed` representa o resultado final utilizado para a comparação.

Assim, os dois datasets terão papéis experimentais diferentes:

```text
ENEM
menor complexidade
poucas dependências entre transformações
arquitetura raw → final

TSE
maior complexidade
múltiplas transformações e dependências
arquitetura raw → staging → processed
```

Isso permitirá avaliar não somente o comportamento de ETL e ELT diante do
aumento do volume de dados, mas também diante do aumento da complexidade do
processamento.

Dentro de cada dataset, entretanto, ETL e ELT deverão executar transformações
equivalentes e produzir o mesmo resultado final.

Não será adicionada uma camada `analytics` ao benchmark principal. Caso sejam
posteriormente construídas tabelas agregadas, dashboards ou visualizações, elas
deverão ficar fora do tempo medido de ETL × ELT ou ser executadas igualmente a
partir das saídas das duas arquiteturas. Dessa forma, não interferirão na
comparação principal.

### Regra de equivalência

Para cada combinação de base e volume, ETL e ELT deverão produzir a mesma estrutura final e os mesmos resultados.

A equivalência exige que as duas abordagens utilizem os mesmos arquivos, o mesmo
volume nominal, as mesmas linhas, as mesmas regras de transformação e o mesmo
contrato final. A única diferença desejada será a arquitetura de processamento:
transformação antes da carga, no ETL, ou transformação após a carga bruta, no
ELT.

A equivalência será validada por meio de critérios como:

- quantidade de registros;
- nomes e ordem das colunas;
- tipos;
- valores;
- regras derivadas;
- valores nulos;
- categorias;
- comparação por hashes ou operações equivalentes;
- verificação de diferenças entre os resultados.

O objetivo é garantir que diferenças de tempo, CPU, RAM e throughput sejam
atribuíveis à arquitetura do pipeline, e não a diferenças no resultado produzido.

---

## 5. Método de carga

A carga em massa no PostgreSQL será realizada preferencialmente utilizando o mecanismo `COPY`.

O mesmo princípio de carga deverá ser utilizado nos dois pipelines sempre que aplicável, evitando que diferenças causadas exclusivamente pelo método de inserção sejam confundidas com diferenças entre ETL e ELT.

O uso de métodos como `pandas.to_sql()` não será priorizado no benchmark principal devido ao risco de introduzir um gargalo de carga não relacionado diretamente à arquitetura avaliada.

---

## 6. Métricas de desempenho

### Métrica principal

A principal métrica será:

**Tempo total de processamento**

Ela representará o tempo necessário para levar o dado desde sua origem até o resultado final pronto para utilização.

### Tempos por etapa

Também serão registrados separadamente:

- tempo de leitura;
- tempo de transformação;
- tempo de carga;
- tempo total.

A leitura do arquivo será incluída no tempo total, mas permanecerá registrada separadamente.

Isso permitirá analisar tanto o pipeline completo quanto o comportamento isolado das etapas.

### Throughput

Será calculado o throughput do processamento:

```text
Throughput = quantidade de registros processados / tempo total
```

A unidade principal será registros por segundo.

### CPU

Serão registrados:

- uso médio de CPU;
- pico de CPU.

Sempre que possível, o consumo associado ao Python e ao PostgreSQL será registrado separadamente e também considerado de forma combinada.

### Memória RAM

Será utilizado principalmente o pico de memória RAM durante cada execução.

Serão registrados, sempre que tecnicamente viável:

- média de RAM do Python;
- pico de RAM do Python;
- média de RAM do PostgreSQL;
- pico de RAM do PostgreSQL;
- média combinada associada ao pipeline;
- pico combinado associado ao pipeline.

O consumo total do sistema operacional não será utilizado como principal referência, pois poderá incluir processos externos ao experimento.

---

## 7. Monitoramento de recursos

CPU e RAM serão monitoradas programaticamente utilizando Python e a biblioteca `psutil`.

Durante cada execução, serão coletadas amostras aproximadamente a cada **0,5 segundo**.

O monitoramento acompanhará principalmente os processos relacionados ao:

- Python;
- PostgreSQL.

Ao término de cada execução serão calculados valores consolidados como:

- CPU média;
- CPU máxima;
- RAM média;
- RAM máxima.

O mesmo procedimento de monitoramento será aplicado a todos os cenários.

---

## 8. Repetições

Cada cenário terá:

- **1 execução preliminar de aquecimento**;
- **5 execuções válidas**.

A execução preliminar não será incluída nos resultados.

As cinco execuções válidas serão utilizadas para reduzir a influência de oscilações pontuais do ambiente.

Serão analisadas principalmente:

- média;
- mediana;
- dispersão dos resultados, quando relevante.

A mediana poderá ser especialmente útil para reduzir o efeito de execuções atípicas.

---

## 9. Cache e aquecimento

Não será realizada limpeza forçada do cache do PostgreSQL ou do sistema operacional entre execuções.

Antes das medições válidas será realizada uma execução de aquecimento, permitindo que o ambiente alcance um estado mais estável.

A utilização dessa mesma estratégia nos diferentes pipelines, juntamente com a randomização das execuções, busca reduzir possíveis vantagens ocasionais decorrentes do estado de cache.

---

## 10. Organização das execuções

Os testes serão divididos em uma execução de aquecimento e cinco rodadas
válidas.

A execução de aquecimento utilizará o mesmo subconjunto de dados definido para o
cenário correspondente, mas não participará das estatísticas finais.

Em cada rodada, todos os cenários previstos serão executados uma vez.

A ordem dos cenários será randomizada em cada rodada. Essa randomização se
aplicará somente à ordem das execuções, nunca aos dados pertencentes a cada
cenário.

```text
ordem das execuções = randomizada
dados de cada cenário = fixos
```

Os subconjuntos de dados permanecerão fixos durante todo o experimento. Assim,
as mesmas linhas deverão ser utilizadas:

- no ETL;
- no ELT;
- na execução de aquecimento;
- em todas as cinco rodadas válidas.

Não haverá nova amostragem ou sorteio de registros entre rodadas.

Exemplo conceitual:

```text
RODADA 1
ENEM | 500k | ELT
TSE  | 1M   | ETL
ENEM | 100k | ETL
TSE  | 3M   | ELT
...

RODADA 2
Nova ordem randomizada.

...

RODADA 5
Nova ordem randomizada.
```

A randomização será reproduzível por meio de uma seed definida no código.

Isso evita executar todos os testes ETL primeiro e todos os testes ELT posteriormente, reduzindo possíveis vieses temporais.

Na nomenclatura dos cenários, poderá continuar sendo utilizada a forma resumida,
como `ENEM | 500k | ETL` e `ENEM | 500k | ELT`. Para a base ENEM, entretanto,
`500k` significa limite de 500 mil linhas por arquivo de origem. Quando for
necessário evitar ambiguidade, poderá ser usada a forma mais explícita
`ENEM | 500k por arquivo | ETL`.

---

## 11. Controle do ambiente

Os benchmarks principais serão executados na mesma máquina e sob condições semelhantes.

Máquina inicialmente definida:

- processador AMD Ryzen 5 2600;
- 16 GB de memória RAM;
- GPU AMD Radeon RX 5500 XT.

A GPU não terá papel direto no experimento, mas poderá ser registrada como parte da configuração completa da máquina.

Também deverão ser documentados posteriormente:

- sistema operacional;
- tipo e modelo do armazenamento utilizado;
- versão do Python;
- versão do PostgreSQL;
- versão das principais bibliotecas.

Durante os benchmarks serão evitadas aplicações ou tarefas pesadas concorrentes.

---

## 12. Segunda máquina

O benchmark principal será inicialmente limitado a uma máquina.

A execução dos mesmos testes em um segundo computador poderá ser realizada posteriormente caso haja tempo disponível.

Nesse caso, o segundo hardware será tratado como uma análise adicional de reprodutibilidade e não como requisito obrigatório do experimento principal.

---

## 13. Variáveis experimentais

### Variáveis independentes

Os principais fatores deliberadamente modificados serão:

- arquitetura: ETL ou ELT;
- volume de dados: 100k, 500k, 1M e 3M;
- complexidade do processamento, representada pelas características distintas das bases ENEM e TSE.

### Variáveis dependentes

Serão observados:

- tempo total;
- tempos por etapa;
- throughput;
- utilização de CPU;
- utilização de memória RAM.

### Variáveis controladas

Serão mantidos equivalentes sempre que possível:

- máquina utilizada;
- dados de origem;
- arquivos utilizados em cada base;
- volume nominal;
- linhas utilizadas em cada volume;
- regras de transformação;
- contrato final esperado;
- ferramenta de carga;
- banco de dados;
- número de repetições;
- método de monitoramento;
- condições gerais de execução.

O foco do controle experimental será principalmente sobre fatores capazes de afetar ETL e ELT de maneira diferente.

Fatores equivalentes para ambos serão padronizados e documentados, evitando complexidade experimental desnecessária.

---

## 14. Estrutura geral do experimento

O cenário experimental pode ser representado como:

```text
Base × Volume × Arquitetura
```

Considerando:

- 2 bases;
- 4 volumes;
- 2 arquiteturas;

serão avaliadas:

```text
2 × 4 × 2 = 16 combinações principais
```

Com cinco execuções válidas por combinação:

```text
16 × 5 = 80 execuções válidas
```

Além disso, serão realizadas execuções de aquecimento que não participarão das estatísticas finais.

---

## 15. Registro dos resultados

Cada execução deverá gerar automaticamente um registro estruturado contendo, no mínimo:

```text
dataset
volume_nominal
arquitetura
rodada
aquecimento
tempo_leitura
tempo_transformacao
tempo_validacao
tempo_carga
tempo_total
throughput
cpu_media
cpu_pico
ram_media
ram_pico
quantidade_registros_total
timestamp
```

Quando aplicável, o campo genérico de volume deverá ser complementado ou
substituído por campos mais específicos. Para a base ENEM, deverão ser
registrados pelo menos:

```text
dataset
volume_por_arquivo
linhas_participantes
linhas_resultados
quantidade_registros_total
arquitetura
rodada
aquecimento
tempo_leitura
tempo_transformacao
tempo_validacao
tempo_carga
tempo_total
throughput
cpu_media
cpu_pico
ram_media
ram_pico
timestamp
```

Sempre que possível, CPU e RAM também serão registradas separadamente para Python e PostgreSQL.

Esses registros serão armazenados de forma estruturada para posterior análise estatística, geração de gráficos e construção dos resultados apresentados no TCC.

---

## 16. Contrato final da base ENEM

A base ENEM produzirá duas tabelas finais independentes. Não haverá `JOIN` entre
elas, nem relacionamento por chave estrangeira. Cada tabela alimentará gráficos
com objetivos diferentes.

### 16.1 Tabela `enem_participantes`

Cada registro representa um participante no arquivo de participantes.

As colunas finais são:

```text
id_participante       TEXT
faixa_etaria          TEXT
sexo                  TEXT
cor_raca              TEXT
situacao_conclusao    TEXT
treineiro             BOOLEAN
municipio_prova       TEXT
uf_prova              TEXT
faixa_renda           TEXT
possui_internet       BOOLEAN
tipo_escola_em        TEXT
regiao_prova          TEXT
```

Essa tabela será utilizada para gráficos demográficos, sociais e geográficos.

### 16.2 Tabela `enem_resultados`

Cada registro representa um resultado no arquivo de resultados.

As colunas finais são:

```text
id_resultado              TEXT
municipio_escola          TEXT
uf_escola                 TEXT
dependencia_escola        TEXT
localizacao_escola        TEXT
presenca_cn               TEXT
presenca_ch               TEXT
presenca_lc               TEXT
presenca_mt               TEXT
presenca_redacao          TEXT
nota_cn                   NUMERIC
nota_ch                   NUMERIC
nota_lc                   NUMERIC
nota_mt                   NUMERIC
nota_redacao              NUMERIC
regiao_escola             TEXT
nota_media_objetivas      NUMERIC
presente_completo         BOOLEAN
```

Essa tabela será utilizada para gráficos de presença, desempenho e
características das escolas.

Os identificadores das duas tabelas são independentes. Não será exigida
correspondência entre `id_participante` e `id_resultado`.

### 16.3 Nulos, categorias e valores desconhecidos

Valores textuais ausentes serão representados por `Não informado`. Valores
numéricos ausentes permanecerão nulos, inclusive quando a ausência decorrer da
falta do participante à prova.

Indicadores booleanos poderão permanecer nulos quando não houver informação.
Valores de origem que não estiverem nos mapeamentos conhecidos serão registrados
em relatório, sem interromper inicialmente o processamento. A quantidade desses
valores será acompanhada para avaliar posteriormente se é necessário alterar o
tratamento.

As categorias finais serão entregues apenas como texto, sem duplicar os códigos
originais.

### 16.4 Regras derivadas

As regiões serão derivadas da UF correspondente à prova ou à escola.

`nota_media_objetivas` será a média de CN, CH, LC e MT. A média usará `skipna=False`,
será nula quando alguma dessas quatro notas estiver ausente e será arredondada
para duas casas decimais. A nota da redação será mantida separadamente e não
participará dessa média.

`presente_completo` será verdadeiro somente quando o participante estiver
presente em CN, CH, LC, MT e redação. A redação participa dessa regra, mas não da
média objetiva.

### 16.5 Validações

Cada tabela deverá ser validada antes da carga final. As validações abrangerão:

- presença e estrutura das colunas esperadas;
- identificadores não nulos e sem duplicidade;
- categorias pertencentes aos domínios definidos;
- notas dentro dos limites válidos;
- consistência entre UF e região;
- consistência entre presenças, notas e `presente_completo`;
- quantidade de linhas lidas e produzidas;
- quantidade de nulos, valores `Não informado` e valores desconhecidos.

Falhas estruturais, identificadores duplicados e notas inválidas serão erros
críticos e interromperão o processamento. Valores desconhecidos e aumento de
ausências serão inicialmente alertas, permitindo a continuidade e o registro
para análise.

## 17. Pontos ainda a detalhar durante a implementação

O desenho experimental principal está definido.

A decisão de utilizar as camadas `raw`, `staging` e `processed` no TSE já está
definida e não será tratada como uma pendência arquitetural.

Permanecem como detalhes técnicos a serem fechados durante a exploração e implementação:

- transformações exatas da base TSE;
- versões das ferramentas;
- características do armazenamento da máquina;
- implementação definitiva do mecanismo de monitoramento;
- eventual utilização de uma segunda máquina.

Esses pontos não alteram o objetivo central da metodologia e deverão ser registrados assim que forem definidos.
