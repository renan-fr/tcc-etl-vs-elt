# Metodologia Experimental — ETL × ELT

## 1. Objetivo do experimento

O experimento tem como objetivo comparar o desempenho das abordagens ETL e ELT sob diferentes volumes de dados e em dois cenários de processamento.

A análise buscará responder principalmente:

> **Como ETL e ELT se comportam, em cada dataset e volume, diante de cenários de processamento com características distintas?**

A comparação será realizada em ambiente controlado, mantendo equivalentes as condições que não fazem parte do objeto de estudo e variando apenas os fatores relevantes para a comparação.

---

## 2. Bases de dados

Serão utilizadas duas bases públicas com características distintas.

### ENEM — cenário predominantemente por registro

A base do ENEM representará um cenário com transformações predominantemente por registro.

As transformações deverão envolver principalmente:

- seleção e organização de colunas;
- renomeação ou remapeamento de campos;
- ajuste de tipos de dados;
- padronizações necessárias;
- tratamentos simples.

Não há previsão de joins ou transformações relacionais complexas.

### TSE — cenário com múltiplas fontes e relações

A base do TSE representará um cenário com múltiplas fontes e transformações relacionais.

O pipeline utiliza três fontes eleitorais, selecionadas por manifestos de chaves
compartilhados e normalizadas para a construção do produto final. As operações
implementadas incluem agregações de seções e candidatos, ranking determinístico
de candidatos segundo os critérios definidos e joins entre as fontes.

### Bases de backup

As bases alternativas definidas anteriormente não participarão inicialmente do benchmark. Elas serão utilizadas somente caso algum problema impeça o uso do ENEM ou do TSE.

---

## 3. Volumes analisados

Cada base será avaliada nos seguintes volumes nominais:

- 100.000;
- 250.000;
- 500.000;
- 1.000.000.

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

250k:
até 250.000 linhas de participantes
+
até 250.000 linhas de resultados

500k:
até 500.000 linhas de participantes
+
até 500.000 linhas de resultados

1M:
até 1.000.000 de linhas de participantes
+
até 1.000.000 de linhas de resultados

```

No TSE, o gerador preserva todas as linhas pertencentes às chaves lógicas
selecionadas. Por isso, o total efetivo pode ficar ligeiramente acima do volume
nominal e será registrado nas métricas de linhas efetivamente processadas.

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

quantidade_registros = 1000000
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
uma característica associada ao dataset, e não como um fator independente
manipulado separadamente. ENEM e TSE não precisam utilizar a mesma quantidade de
camadas.

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

Para a base ENEM, que representa o cenário com transformações predominantemente
por registro, será adotada
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

- `participantes`;
- `resultados`.

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

Para a base TSE, que representa o cenário com características de processamento
mais complexas, será adotada
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

Isso permitirá avaliar o comportamento de ETL e ELT diante do aumento do volume
de dados em dois cenários de processamento distintos. A diferença entre os
datasets será interpretada como uma característica associada ao cenário, não
como evidência isolada do efeito da complexidade.

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

A equivalência será certificada previamente à campanha medida, por meio de
critérios como:

- quantidade de registros;
- nomes e ordem das colunas;
- tipos;
- valores;
- regras derivadas;
- valores nulos;
- categorias;
- comparação por hashes ou operações equivalentes;
- verificação de diferenças entre os resultados.

O objetivo metodológico é reduzir a possibilidade de que diferenças de tempo,
CPU, RAM e throughput decorram de resultados diferentes. A equivalência funcional
é um requisito a ser confirmado pela certificação, não uma conclusão antecipada
da campanha.

---

## 5. Método de carga

A carga em massa no PostgreSQL será realizada preferencialmente utilizando o mecanismo `COPY`.

O mesmo princípio de carga deverá ser utilizado nos dois pipelines sempre que aplicável, evitando que diferenças causadas exclusivamente pelo método de inserção sejam confundidas com diferenças entre ETL e ELT.

O uso de métodos como `pandas.to_sql()` não será priorizado no benchmark principal devido ao risco de introduzir um gargalo de carga não relacionado diretamente à arquitetura avaliada.

---

## 6. Métricas de desempenho

### Métrica principal

A principal métrica para a comparação de desempenho será:

**Tempo total de processamento**

Ela representará o tempo necessário para levar o dado desde sua origem até o resultado final pronto para utilização.

As validações de qualidade e a equivalência entre ETL e ELT serão executadas em
uma etapa prévia de certificação. No ETL, as validações internas ocorrem antes
da carga; no ELT, depois da materialização das tabelas finais. Na campanha
oficial, essas validações internas ficam desativadas. O benchmark medirá somente
leitura, transformação e carga, evitando que verificações auxiliares interfiram
no tempo, no uso de recursos e no estado de cache das rodadas de desempenho.

### Tempos por etapa

Também serão registrados separadamente, como indicadores diagnósticos:

- tempo de leitura;
- tempo de transformação;
- tempo de carga;
- tempo total.

As etapas serão definidas operacionalmente da seguinte forma. Como as operações
internas das duas arquiteturas não possuem fronteiras perfeitamente equivalentes,
diferenças entre etapas isoladas não serão interpretadas automaticamente como
vantagens arquiteturais:

- `tempo_leitura`: leitura e interpretação dos arquivos de entrada, incluindo
  seleção de linhas e colunas;
- `tempo_transformacao`: execução das regras de transformação de negócio;
- `tempo_carga`: preparação e serialização dos dados para gravação,
  transferência, operações de escrita, preparação das tabelas de destino e
  confirmação da transação, quando aplicável;
- `tempo_total`: tempo completo da execução, medido por um cronômetro
  independente.

No ETL, a serialização dos `DataFrames` para CSV e o `COPY` das tabelas finais
pertencem à carga. No ELT, a leitura e a seleção dos registros ocorrem em um
fluxo incremental durante o `COPY`; o tempo gasto em `next(linhas)` é atribuído
à leitura, enquanto a serialização por `csv.writer`, o envio, a gravação e o
`commit` pertencem à carga. O tempo de carga é obtido descontando do intervalo
da operação somente o tempo atribuído à leitura, evitando dupla contabilização.

Como algumas operações do ELT são intercaladas dentro da chamada ao `COPY`, a
soma das três etapas pode não coincidir exatamente com o tempo total. Diferenças
residuais correspondem a custos fora das etapas, como abertura da conexão e
outras operações de controle, e o `tempo_total` permanece a métrica principal
de ponta a ponta.

Isso permitirá analisar tanto o pipeline completo quanto o comportamento isolado das etapas.

### Throughput

O throughput será uma métrica complementar ao `tempo_total`, pois é calculado a
partir da quantidade de registros e do tempo total medido:

```text
Throughput = quantidade de registros processados / tempo total
```

A unidade principal será registros por segundo.

### CPU

Serão registrados:

- uso médio de CPU;
- pico de CPU.

O processo Python e os processos PostgreSQL são expressos como percentual de um
núcleo lógico, sem normalização pelo número total de CPUs. A soma pode,
portanto, ultrapassar 100%. A média de CPU é ponderada pela duração dos
intervalos válidos e o pico é o maior valor observado.

Antes da primeira conexão PostgreSQL, a CPU do Python é efetivamente medida, a
CPU do PostgreSQL participa com zero por convenção e a CPU agregada é igual à
CPU Python. Esses intervalos preservam sua duração e participam do cálculo da
média ponderada.

Depois da primeira vinculação, a CPU agregada é calculada em cada amostra como
a soma das CPUs Python e PostgreSQL observadas em intervalos temporalmente
compatíveis. O PostgreSQL permanece participante até o encerramento do pipeline,
inclusive entre conexões posteriores. Os zeros anteriores à primeira conexão
são identificados internamente como convencionais e não representam medições
efetivas iguais a zero; falhas reais de coleta permanecem inválidas e não são
convertidas em zero.

### Memória RAM

A métrica de memória será a USS (*Unique Set Size*), obtida homogeneamente para
Python e PostgreSQL por meio de `psutil.Process.memory_full_info().uss`. USS
representa a memória física exclusiva atribuída ao processo e exclui as páginas
compartilhadas com outros processos. Ela não representa a RAM física total do
sistema nem o consumo incremental causado exclusivamente pelo pipeline.

Para o Python, é monitorado o processo que executa o pipeline. Para o
PostgreSQL, a instância é identificada a partir do PID de backend da conexão
real; a USS é então somada apenas para os processos pertencentes à árvore dessa
instância.

Em cada amostra são calculados:

- `ram_python`: USS do processo Python;
- `ram_postgres`: soma da USS dos processos PostgreSQL participantes;
- `ram_total`: soma dos dois componentes na mesma amostra.

Antes da primeira conexão PostgreSQL, o processo Python já participa do
pipeline, mas a instância PostgreSQL ainda não foi vinculada. Nesse intervalo,
`ram_python` é a USS efetivamente medida, `ram_postgres` é zero por convenção de
participação — não por uma leitura USS igual a zero — e `ram_total` é igual à
USS Python.

Depois da primeira vinculação, o PostgreSQL permanece participante até o final
da execução, inclusive entre conexões posteriores. A média de PostgreSQL é a
média aritmética das amostras e inclui os zeros convencionais anteriores à
primeira conexão. O pico é o maior valor observado. A mesma regra de média e
pico é aplicada à RAM Python e à RAM total.

O consumo total do sistema operacional não será utilizado como referência, pois
poderia incluir processos externos ao experimento.

---

## 7. Monitoramento de recursos

CPU e RAM serão monitoradas programaticamente utilizando Python e a biblioteca
`psutil` somente na modalidade `recursos`. Na modalidade `desempenho`, o monitor
não será instanciado e nenhuma thread de coleta será iniciada.

Durante cada execução, serão coletadas amostras aproximadamente a cada **0,5 segundo**.

O monitor é executado dentro do próprio processo Python de cada pipeline. Ele
acompanha esse processo e, depois da primeira conexão local, a árvore de
processos PostgreSQL vinculada ao backend da conexão. A árvore é redescoberta
durante a execução para incluir processos novos e retirar processos encerrados,
com proteção contra reutilização de PID.

Para CPU, a média é ponderada pela duração dos intervalos válidos e o pico é o
maior valor observado. Para RAM, a média é aritmética sobre as amostras válidas
e o pico é o maior valor observado. A RAM total é calculada em cada instante
como `ram_python + ram_postgres`; ela não é obtida somando os picos individuais.

Encerramentos detectados durante a leitura de CPU são tratados como remoção
normal do processo e não invalidam automaticamente a amostra de RAM. Se um
processo encerrar durante a leitura de USS, a amostra correspondente de RAM
fica incompleta e não é usada como válida. `AccessDenied`, USS indisponível e
falhas inesperadas geram erro explícito; não há substituição silenciosa por RSS,
memória privada ou zero.

O mesmo procedimento de monitoramento será aplicado a todos os cenários da
modalidade `recursos`. O intervalo permanecerá fixo em 0,5 segundo.

Como indicador complementar, o monitor registrará `psutil.virtual_memory().available`
no início da execução e em cada amostra. O CSV da modalidade `recursos` conterá
`memoria_disponivel_inicial_mb` para diagnóstico e
`memoria_disponivel_reducao_maxima_mb`, calculado como a maior diferença entre o
valor inicial e uma amostra posterior, em MB. A métrica não será limitada a
zero: caso a memória disponível não fique abaixo do valor inicial, será
registrado `0`.

---

## 8. Repetições

Cada combinação de cenário e modalidade terá:

- **1 execução preliminar de aquecimento**;
- **5 execuções válidas**.

A execução preliminar não será incluída nos resultados.

As cinco execuções válidas serão utilizadas para reduzir a influência de oscilações pontuais do ambiente. A média aritmética será o principal indicador de tendência central, o desvio-padrão amostral (`ddof=1`) representará a dispersão e a mediana será utilizada como indicador complementar.

A análise será feita separadamente por dataset e volume, sem misturar as bases ou os volumes. Não haverá exclusão automática de outliers: todas as cinco execuções válidas participarão dos cálculos.

Serão calculadas média, desvio-padrão amostral e mediana para as métricas oficiais de cada modalidade.

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

Em cada rodada, todas as combinações de cenário e modalidade serão executadas
uma vez.

A ordem das 32 unidades formadas por modalidade, base, volume e arquitetura
será randomizada globalmente no aquecimento e em cada rodada. Essa randomização se
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
TSE  | 250k | ELT
...

RODADA 2
Nova ordem randomizada.

...

RODADA 5
Nova ordem randomizada.
```

A randomização será reproduzível pela seed padrão `20241027`, definida no código
e configurável no orquestrador.

Isso evita executar todos os testes ETL primeiro e todos os testes ELT posteriormente, reduzindo possíveis vieses temporais.

Na nomenclatura dos cenários, poderá continuar sendo utilizada a forma resumida,
como `ENEM | 500k | ETL` e `ENEM | 500k | ELT`. Para a base ENEM, entretanto,
`500k` significa limite de 500 mil linhas por arquivo de origem. Quando for
necessário evitar ambiguidade, poderá ser usada a forma mais explícita
`ENEM | 500k por arquivo | ETL`.

---

## 11. Controle do ambiente

Os benchmarks principais serão executados na mesma máquina e sob condições semelhantes.

Máquina oficial declarada para a campanha:

- Acer Aspire 16 A16-71M-55H0;
- processador Intel Core Ultra 5 115U;
- 16 GB de memória RAM;
- armazenamento SSD;
- Windows 11.

O PostgreSQL e os arquivos CSV da campanha oficial permanecerão na própria
máquina, sem transferência de rede durante os benchmarks. Essa é uma condição
declarada do experimento, não uma inferência feita pelo código.

Antes da campanha oficial deverão ser documentados:

- sistema operacional e arquitetura;
- versão e implementação do Python;
- versão do PostgreSQL consultada pela conexão da campanha;
- versões das principais bibliotecas;
- nome da máquina e processador;
- quantidade lógica de CPUs e memória RAM total detectada;
- parâmetros relevantes do PostgreSQL.

O tipo e modelo do armazenamento é uma informação declarada manualmente, pois
não é identificado de forma portável pelo orquestrador.

No Windows 11 do Acer, a coleta de USS dos processos PostgreSQL exigirá a
execução do PowerShell com privilégios administrativos. A campanha oficial
deverá preservar o mesmo nível de privilégios nas duas arquiteturas e nas duas
modalidades, para que a disponibilidade da métrica não seja um fator de
comparação.

O orquestrador grava essas informações no objeto `ambiente` de
`campanha.json`. O objeto separa `declarado_para_campanha_oficial` de
`capturado_automaticamente`: a segunda seção descreve o host que executou a
campanha e pode conter `null` quando uma informação não estiver disponível.
Versões e características do host são capturadas uma única vez, no início da
campanha. A consulta ao PostgreSQL usa somente `SELECT version()` e `SHOW`, sem
alterar parâmetros do servidor e sem gravar credenciais.

### Protocolo operacional da campanha

A campanha oficial será executada com o notebook conectado à alimentação elétrica, utilizando o plano de energia Acer e o modo Equilibrado do Windows. Serão preservadas as configurações de desempenho mínimo (5%) e máximo (100%) do processador, sem alterações deliberadas nos limites de potência.

Para evitar interrupções, a tampa permanecerá aberta e a hibernação automática durante a alimentação elétrica será temporariamente desativada. O equipamento será mantido sobre superfície rígida, com ventilação adequada.

Antes do início da campanha, serão adotados os seguintes procedimentos:

- encerramento de aplicações pesadas e prevenção de atualizações ou tarefas concorrentes durante as medições;
- verificação da disponibilidade do PostgreSQL e manutenção de suas configurações;
- conferência da integridade dos arquivos de entrada por meio do manifesto SHA-256 versionado no repositório;
- confirmação da ausência de alterações não registradas no Git, identificação do commit e verificação do espaço disponível no SSD;
- execução da certificação de equivalência entre os produtos finais das implementações ETL e ELT.

A campanha utilizará uma única máquina, os mesmos conjuntos de dados e a mesma configuração operacional para ambas as arquiteturas. A ordem das execuções será randomizada com seed fixa, conforme o procedimento experimental definido.

Em caso de interrupção ou falha que comprometa a campanha, os resultados parciais não serão combinados com os de outra campanha como se pertencessem à mesma execução experimental. Após a conclusão, serão conferidos os metadados e os arquivos de resultados, e a configuração original de hibernação será restaurada.

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
- volume de dados: 100k, 250k, 500k e 1M;
- dataset/cenário: ENEM e TSE representam características distintas de
  processamento, mas dataset e complexidade estão associados e não permitem
  atribuir diferenças exclusivamente à complexidade.

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

O foco do controle experimental será principalmente sobre fatores capazes de
afetar ETL e ELT de maneira diferente. As comparações principais serão feitas
dentro de cada dataset e volume; a comparação entre datasets caracteriza
cenários distintos, não um teste isolado do efeito da complexidade.

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

Com duas modalidades e cinco execuções válidas por unidade experimental:

```text
16 × 2 × 5 = 160 execuções válidas
```

Além disso, serão realizadas 32 execuções de aquecimento que não participarão
das estatísticas finais, totalizando 192 execuções de pipeline na campanha.

---

## 15. Registro dos resultados

Cada execução válida deverá gerar automaticamente um registro estruturado. O
aquecimento e a certificação não serão gravados no arquivo de desempenho.

Os campos comuns aos CSVs são:

```text
run_id
dataset
volume_configurado
arquitetura
rodada
modalidade
monitoramento_ativo
intervalo_monitoramento_s
tempo_leitura
tempo_transformacao
tempo_carga
tempo_total
throughput
cpu_media_python
cpu_pico_python
ram_media_python_mb
ram_pico_python_mb
cpu_media_postgres
cpu_pico_postgres
ram_media_postgres_mb
ram_pico_postgres_mb
cpu_media_total
cpu_pico_total
ram_media_total_mb
ram_pico_total_mb
memoria_disponivel_inicial_mb
memoria_disponivel_reducao_maxima_mb
timestamp
```

Os CSVs do ENEM acrescentam `quantidade_registros`,
`linhas_participantes` e `linhas_resultados`. Os CSVs do TSE acrescentam
`quantidade_registros`, `linhas_munzona`, `linhas_secao`, `linhas_candidato` e
`linhas_processadas`.

Cada linha também conterá um `run_id`, usado para identificar a campanha à qual
o resultado pertence. A campanha oficial usará `oficial_01`.

Os metadados comuns serão mantidos em um único arquivo
`data/benchmark/campanhas/<run_id>/campanha.json`. Ele registrará `run_id`, seed, volumes, rodadas,
commit Git, contagens, horários e estado da campanha. O andamento será atualizado
nesse mesmo arquivo, sem criar logs individuais por execução.

Cada campanha terá quatro CSVs em `desempenho/`, quatro em `recursos/` e os
metadados em um diretório próprio. Se o
`run_id` já existir, o orquestrador interromperá a execução para impedir
sobrescrita. O orquestrador global exigirá uma árvore Git limpa antes de criar
ou alterar resultados.

Para a base ENEM, os campos específicos efetivamente gravados são:

```text
quantidade_registros
linhas_participantes
linhas_resultados
```

Para o TSE, o registro também poderá conter os campos específicos gerados para
as três fontes (`linhas_munzona`, `linhas_secao` e `linhas_candidato`) e para o
produto final (`linhas_processadas`). Esses campos distinguem a quantidade
efetiva de linhas por fonte do volume configurado.

CPU e RAM são registradas separadamente para Python e PostgreSQL nos campos
listados acima. Não existe um campo adicional que registre, em cada linha, o
"tipo de métrica"; a definição USS e a convenção pré-conexão fazem parte deste
protocolo metodológico.

Os tempos por etapa, `tempo_total` e throughput da modalidade `desempenho` são
as métricas oficiais de desempenho; os campos de CPU e RAM dessas linhas ficam
vazios. CPU e RAM da modalidade `recursos`, coletadas a cada 0,5 segundo, são as
métricas oficiais de recursos. Os tempos e throughput das execuções monitoradas
continuam registrados somente para diagnóstico. A proveniência oficial e
diagnóstica fica declarada em `campanha.json`.

Os campos de memória disponível do sistema também permanecem nos CSVs de
`recursos` como indicadores complementares para diagnóstico e não alteram as
métricas de USS.

Na análise estatística, a modalidade `desempenho` consolidará `tempo_total` e
`throughput`, podendo apresentar os tempos por etapa como indicadores
diagnósticos. A modalidade `recursos` consolidará CPU média e de pico e RAM
média e de pico usando os campos totais presentes nos CSVs; quando disponíveis,
as métricas separadas de Python e PostgreSQL também serão consolidadas. Os
tempos e o throughput dos CSVs de `recursos` não serão usados como resultados
oficiais de desempenho.

Para cada campanha, o comando `python3 src/analise_estatistica.py <run_id>`
produzirá, sem alterar os CSVs de origem, os arquivos:

```text
data/benchmark/campanhas/<run_id>/analise/analise_desempenho.csv
data/benchmark/campanhas/<run_id>/analise/analise_recursos.csv
data/benchmark/campanhas/<run_id>/analise/comparacao_etl_elt.csv
```

Os dois primeiros terão uma linha por dataset, volume e arquitetura, com as
colunas de média, desvio-padrão amostral, mediana e número de execuções para
cada métrica. A tabela de
comparação terá uma linha por dataset e volume, as três estatísticas de
`tempo_total` de ETL e ELT e `reducao_tempo_pct`, calculada a partir das médias.
Essa comparação descreve diferenças observadas e não constitui teste de
hipótese ou evidência de diferença significativa.

Esses registros serão armazenados de forma estruturada para posterior análise estatística, geração de gráficos e construção dos resultados apresentados no TCC.

---

## 16. Contrato final da base ENEM

O ELT devera reproduzir exatamente este mesmo contrato final. A camada RAW do
ELT preservara os campos originais, e as transformacoes SQL deverao gerar as
mesmas tabelas finais, colunas, tipos, nulos e valores do ETL.

A base ENEM produzirá duas tabelas finais independentes. Não haverá `JOIN` entre
elas, nem relacionamento por chave estrangeira. Cada tabela alimentará gráficos
com objetivos diferentes.

### 16.1 Tabela `participantes`

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

### 16.2 Tabela `resultados`

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

Na certificação funcional prévia, cada tabela deverá ser validada no ponto
correspondente ao pipeline. No ETL, as validações internas ocorrem antes da
carga final. No ELT, ocorrem depois da materialização das tabelas finais. Na
campanha oficial, as validações internas são desativadas para não interferirem
nas medições; a certificação de equivalência entre ETL e ELT ocorre antes dela.

As validações abrangerão:

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

Permanecem como detalhes técnicos de documentação final:

- características do armazenamento da máquina;
- eventual utilização de uma segunda máquina.

Esses pontos não alteram o objetivo central da metodologia e deverão ser registrados assim que forem definidos.
