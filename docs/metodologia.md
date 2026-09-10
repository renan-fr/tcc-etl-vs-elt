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

Cada base será avaliada nos seguintes volumes:

- 100.000 registros;
- 500.000 registros;
- 1.000.000 de registros;
- 3.000.000 de registros.

Para cada volume, ETL e ELT deverão utilizar exatamente o mesmo conjunto de registros.

A variação de volume será utilizada para analisar como cada abordagem se comporta conforme cresce a quantidade de dados processados.

---

## 4. Implementação dos pipelines

As duas abordagens deverão gerar resultados finais logicamente equivalentes.

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

### Regra de equivalência

Para cada combinação de base e volume, ETL e ELT deverão produzir a mesma estrutura final e os mesmos resultados.

A equivalência será validada por meio de critérios como:

- quantidade de registros;
- estrutura das colunas;
- tipos esperados;
- validações dos valores resultantes.

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

- pico de RAM do Python;
- pico de RAM do PostgreSQL;
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

Os testes serão divididos em cinco rodadas válidas.

Em cada rodada, todos os cenários previstos serão executados uma vez.

A ordem dos cenários será randomizada em cada rodada.

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
- registros utilizados em cada volume;
- resultado final esperado;
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
volume
arquitetura
rodada
tempo_leitura
tempo_transformacao
tempo_carga
tempo_total
throughput
cpu_media
cpu_pico
ram_pico
quantidade_registros
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

Permanecem como detalhes técnicos a serem fechados durante a exploração e implementação:

- transformações exatas da base TSE;
- versões das ferramentas;
- características do armazenamento da máquina;
- implementação definitiva do mecanismo de monitoramento;
- eventual utilização de uma segunda máquina.

Esses pontos não alteram o objetivo central da metodologia e deverão ser registrados assim que forem definidos.
