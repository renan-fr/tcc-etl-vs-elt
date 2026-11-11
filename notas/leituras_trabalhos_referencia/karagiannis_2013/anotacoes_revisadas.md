# Karagiannis et al. (2013) — Análises revisadas

**Trabalho:** *Scheduling Strategies for Efficient ETL Execution*

**Autores:** Karagiannis, Vassiliadis e Simitsis  
**Ano:** 2013  
**Publicação:** Information Systems — Elsevier  
**Tipo:** Artigo científico de periódico

**Finalidade:** consolidar os conhecimentos obtidos durante a leitura guiada e a discussão crítica do artigo, destacando sua contribuição para o entendimento do desempenho de pipelines ETL e sua relação com meu TCC.

---

## 1. Objetivo do trabalho

Karagiannis et al. (2013) investigam como diferentes estratégias de escalonamento (*scheduling*) das operações de um pipeline ETL podem influenciar seu desempenho.

O problema central está relacionado à organização da execução das operações que compõem um fluxo de processamento.

Em um pipeline ETL, diferentes operações podem produzir e consumir dados em velocidades distintas. Dependendo da forma como essas operações são executadas, podem surgir diferenças no tempo total de processamento e na quantidade de dados intermediários armazenados.

O estudo investiga estratégias para organizar essa execução, considerando principalmente dois aspectos:

- Tempo necessário para concluir o processamento.
- Utilização de memória pelas estruturas intermediárias de dados.

**O principal objetivo não é comparar ETL com ELT, mas investigar como diferentes políticas de execução influenciam o desempenho de processos ETL.**

Essa distinção é fundamental para compreender a relação entre o artigo e meu TCC.

## 2. O problema do acúmulo de dados intermediários

Um dos principais aprendizados da leitura foi compreender que as operações de um pipeline podem trabalhar em velocidades diferentes.

Imagine um processo em que a etapa de leitura produz registros mais rapidamente do que a transformação consegue processá-los.

Caso os registros produzidos sejam armazenados temporariamente enquanto aguardam processamento, poderá ocorrer um crescimento das estruturas intermediárias.

Esse crescimento pode aumentar a necessidade de memória.

Por exemplo, se uma operação produzir 10 mil registros por segundo e a seguinte conseguir processar somente 4 mil registros por segundo, haverá uma diferença de 6 mil registros por segundo entre produção e consumo.

Se não existir um mecanismo capaz de controlar esse desbalanceamento, a fila intermediária poderá crescer continuamente enquanto essa condição persistir.

### Aprendizado

O consumo de memória de um pipeline não depende exclusivamente do volume total de dados processados.

A organização da execução, a velocidade relativa das operações e o armazenamento intermediário também podem influenciar o comportamento observado.

Entretanto, esse mecanismo não está necessariamente presente em todos os pipelines da mesma maneira.

Sua ocorrência depende da implementação e das estruturas utilizadas.

## 3. Execução sequencial, execução em pipeline e escalonamento

Durante a primeira discussão, associei as estratégias de Karagiannis principalmente à diferença entre execução sequencial e execução simultânea.

Essa interpretação precisava ser corrigida.

### 3.1. Execução sequencial

Em uma execução sequencial por etapas completas, uma operação termina de processar todo o conjunto de dados antes de a próxima iniciar.

Por exemplo:

1. Todos os registros são extraídos.
2. Todos os registros são transformados.
3. Os resultados são carregados.

Essa organização não exige necessariamente que as diferentes etapas trabalhem simultaneamente.

### 3.2. Execução em pipeline

Na execução em pipeline, diferentes operações podem trabalhar sobre partes distintas dos dados durante intervalos de tempo sobrepostos.

Enquanto determinados registros são transformados, outros podem continuar sendo extraídos, e resultados já transformados podem começar a ser carregados.

Esse modelo permite sobreposição entre as etapas.

Entretanto, a existência dessa sobreposição não elimina a necessidade de gerenciar como as operações utilizam os recursos disponíveis.

### 3.3. Escalonamento de operações

O escalonamento trata da decisão sobre quais operações devem receber oportunidades de execução e como essa execução será organizada.

Diferentes políticas podem estabelecer prioridades diferentes.

Uma estratégia pode favorecer operações com menor custo de processamento, enquanto outra pode priorizar operações que contribuam para reduzir o acúmulo de dados intermediários.

Portanto, **Karagiannis não compara simplesmente execução sequencial com execução paralela**.

O artigo investiga políticas de escalonamento aplicadas ao processamento de workflows ETL.

Essa foi uma das principais correções conceituais realizadas durante nossa discussão.

## 4. Estratégias de escalonamento avaliadas

O artigo apresenta diferentes políticas de escalonamento, incluindo:

- **Round Robin:** distribui oportunidades de execução entre as operações de forma rotativa.
- **Minimum Cost:** considera estimativas de custo das operações para orientar a execução.
- **Minimum Memory:** prioriza a redução da ocupação das estruturas intermediárias de dados.
- **Mixed Policy:** combina critérios de escalonamento em diferentes partes do fluxo de processamento.

As políticas procuram responder ao mesmo problema geral, mas utilizam critérios diferentes para organizar a execução.

Não foi necessário compreender integralmente os algoritmos matemáticos ou os pseudocódigos para identificar a contribuição central do estudo.

O mais importante foi perceber que diferentes decisões internas de execução podem produzir comportamentos distintos.

### Relação com meu TCC

Não pretendo implementar ou comparar políticas de escalonamento.

Entretanto, o estudo demonstra que a estratégia de execução constitui um fator relevante para o desempenho de pipelines.

Esse entendimento ajuda a contextualizar a influência das decisões de implementação sobre os resultados experimentais.

## 5. Metodologia experimental

Os autores realizam experimentos com diferentes estruturas de workflows ETL e conjuntos de dados de volumes distintos.

O estudo utiliza dados gerados com base no benchmark TPC-H e considera diferentes organizações de operações.

Entre os cenários avaliados, aparecem estruturas lineares e fluxos com múltiplas operações e dependências.

As políticas de escalonamento são comparadas considerando principalmente:

- Tempo de execução.
- Ocupação de memória intermediária.
- Comportamento em diferentes volumes de entrada.
- Características estruturais dos workflows.

A utilização de diferentes estruturas permite avaliar o comportamento das políticas em condições de processamento distintas.

### Diferença em relação ao meu experimento

Karagiannis mantém o foco na arquitetura ETL e modifica as políticas de execução.

Meu experimento mantém duas implementações, uma ETL e outra ELT, e observa seu comportamento sob diferentes volumes e conjuntos de dados.

Assim, os estudos investigam fatores experimentais distintos.

No trabalho de Karagiannis, a política de escalonamento constitui o principal fator de comparação.

No meu TCC, o principal fator é a implementação arquitetural ETL ou ELT.

## 6. Resultados e relação entre tempo e memória

Os experimentos apresentados demonstram que diferentes estratégias de escalonamento podem modificar o comportamento dos workflows ETL.

Um aspecto importante é que as políticas não precisam apresentar a mesma vantagem em todas as métricas.

Uma estratégia pode favorecer o tempo de execução, enquanto outra pode reduzir a utilização de memória intermediária.

Isso evidencia que o desempenho de um pipeline possui múltiplas dimensões.

### Aprendizado revisado

Inicialmente, associei uma execução mais rápida a uma estratégia potencialmente superior.

Após a discussão, ficou claro que essa interpretação depende do critério de avaliação.

Um pipeline pode concluir o processamento mais rapidamente e, simultaneamente, exigir mais memória.

Da mesma forma, uma estratégia que reduz o consumo de memória pode não oferecer o menor tempo total.

Portanto, **o menor tempo de execução não significa necessariamente superioridade em todas as dimensões de desempenho**.

Essa conclusão é particularmente relevante para meu TCC, que pretende avaliar diferentes métricas computacionais.

## 7. Diferença entre memória intermediária e memória RAM

Uma distinção metodológica importante surgiu durante a análise.

Karagiannis avalia o consumo relacionado às estruturas intermediárias utilizadas pelos workflows, especialmente as filas responsáveis por armazenar registros entre operações.

Essa medida não é diretamente equivalente à memória RAM total consumida por um processo.

No meu TCC, a instrumentação busca acompanhar o consumo de memória dos processos envolvidos na execução dos pipelines.

A memória observada nesses processos pode incluir diferentes componentes, como:

- Estruturas utilizadas pelas transformações.
- Buffers e objetos temporários.
- Estruturas internas das bibliotecas.
- Dados intermediários.
- Outras alocações necessárias à execução.

Consequentemente, os resultados de memória apresentados por Karagiannis não devem ser comparados numericamente de maneira direta com as medições de RAM do meu benchmark.

### Principal aprendizado

As duas pesquisas investigam aspectos relacionados à utilização de memória, mas utilizam definições operacionais diferentes.

A relação conceitual entre elas é relevante, porém não significa que as métricas sejam equivalentes.

## 8. Acúmulo de dados e possíveis gargalos

Durante a discussão, inicialmente interpretei que o acúmulo de registros intermediários poderia representar uma causa direta de lentidão.

Essa interpretação foi refinada.

O acúmulo de dados pode elevar o consumo de memória, mas não implica obrigatoriamente aumento do tempo de execução.

Em determinadas implementações, manter dados em memória e permitir sobreposição entre operações pode contribuir para reduzir o tempo total.

Problemas de desempenho podem surgir quando o acúmulo provoca pressão sobre os recursos disponíveis, necessidade de paginação, bloqueios ou outras limitações.

Portanto, a relação entre acúmulo de dados e lentidão depende das condições de execução.

### Relação com meu benchmark

Caso uma implementação apresente maior consumo de memória, não será adequado concluir automaticamente que isso ocorreu devido ao acúmulo de registros intermediários.

Essa explicação poderá ser considerada como hipótese, mas precisará de evidências adicionais para ser sustentada.

O mesmo cuidado se aplica a possíveis diferenças de tempo de execução.

## 9. Diferença entre observar desempenho e explicar suas causas

Este foi um dos aprendizados metodológicos mais relevantes.

Durante nossa discussão, analisamos um exemplo hipotético em que o ETL apresentava menor tempo total, mas maior consumo de memória que o ELT.

Inicialmente, poderíamos considerar o acúmulo de dados intermediários como uma explicação.

Entretanto, somente as métricas de tempo e memória não permitem demonstrar esse mecanismo.

Outros fatores também poderiam influenciar os resultados, como:

- Estruturas de dados utilizadas.
- Estratégias de transformação.
- Alocações temporárias de memória.
- Mecanismos de execução das bibliotecas.
- Estratégias internas do banco de dados.
- Operações de leitura e escrita.

Assim, precisamos distinguir três níveis de afirmação:

**Resultado observado:** determinada implementação apresentou maior consumo de memória.

**Hipótese explicativa:** o consumo pode estar relacionado à utilização de estruturas intermediárias.

**Conclusão causal:** o aumento foi provocado por determinado mecanismo, demonstrado por evidências específicas.

Meu benchmark pode identificar diferenças de desempenho, mas nem sempre permitirá explicar completamente suas causas internas.

Essa limitação precisa ser respeitada na interpretação dos resultados.

## 10. Arquitetura versus implementação

Karagiannis contribui para compreender que o desempenho não depende exclusivamente da arquitetura de processamento.

Mesmo utilizando ETL, os autores investigam diferentes estratégias que podem alterar os resultados.

Essa observação se relaciona diretamente com uma limitação do meu experimento.

No desenho atual, ETL e ELT utilizam mecanismos distintos de transformação:

- ETL: processamento em Python/Pandas.
- ELT: processamento em SQL/PostgreSQL.

Assim, uma diferença temporal ou de consumo de recursos pode refletir simultaneamente características da ordem das operações e dos mecanismos de implementação utilizados.

### Interpretação metodológica

Se o ETL apresentar menor tempo de execução, isso demonstrará uma vantagem temporal da implementação avaliada naquele cenário.

Entretanto, não será possível concluir automaticamente que a arquitetura ETL é universalmente superior ou que a diferença decorreu exclusivamente da ordem entre transformação e carga.

Esse cuidado não significa que o experimento seja inválido.

Significa que suas conclusões precisam permanecer compatíveis com o desenho experimental adotado.

**Importante:** essa relação com ETL versus ELT é uma inferência metodológica desenvolvida durante nossa discussão. Karagiannis não demonstra experimentalmente qual dessas arquiteturas possui melhor desempenho.

## 11. Relação com meu TCC

O trabalho possui uma conexão relevante com minha pesquisa por investigar experimentalmente o desempenho de pipelines de dados.

Entretanto, os objetivos são diferentes.

| Aspecto | Karagiannis et al. (2013) | Meu TCC |
|---|---|---|
| Arquitetura | ETL | ETL e ELT |
| Objetivo | Avaliar políticas de escalonamento | Comparar desempenho de duas implementações |
| Principal fator experimental | Política de execução | ETL × ELT |
| Tempo de execução | Avaliado | Avaliado |
| Memória | Estruturas intermediárias | Memória dos processos |
| Volume de dados | Variado | Variado |
| Estruturas de processamento | Diferentes workflows | Pipelines definidos para ENEM e TSE |
| Principal contribuição | Otimização da execução | Comparação experimental de arquiteturas |

A principal proximidade está na avaliação do desempenho sob diferentes condições de processamento.

A principal diferença está no fator investigado.

Karagiannis analisa como executar um pipeline ETL de maneira mais eficiente.

Meu trabalho procura compreender como duas implementações arquiteturais diferentes se comportam ao processar os conjuntos de dados definidos.

## 12. Contribuições para Trabalhos Relacionados

Após nossa discussão, considerei que Karagiannis oferece uma contribuição relevante para minha revisão bibliográfica.

Embora não compare ETL e ELT diretamente, o estudo demonstra experimentalmente que decisões internas de execução podem influenciar o desempenho de pipelines.

Sua contribuição pode ser apresentada a partir de quatro elementos:

**Objetivo:** investigar estratégias eficientes de escalonamento de operações ETL.

**Metodologia:** comparar diferentes políticas de execução em workflows ETL, considerando tempo e memória intermediária.

**Resultados:** demonstrar que políticas diferentes podem apresentar comportamentos distintos de desempenho e utilização de recursos.

**Relação com meu TCC:** enquanto Karagiannis avalia a otimização interna de uma arquitetura ETL, meu experimento compara duas implementações baseadas em ETL e ELT, utilizando múltiplas métricas.

Não será necessário explicar detalhadamente todos os algoritmos apresentados pelos autores na seção de Trabalhos Relacionados.

O foco será a contribuição experimental e a diferença entre as perguntas de pesquisa.

## 13. O que não precisamos incorporar ao TCC

Apesar dos aprendizados, não considero necessário ampliar o escopo do meu experimento para investigar:

- Implementação de escalonadores próprios.
- Comparação entre Round Robin e outras políticas.
- Controle explícito das filas intermediárias.
- Modelagem matemática dos algoritmos de escalonamento.
- Comparação detalhada de estruturas de workflows.
- Avaliação específica de concorrência entre operações.

Esses assuntos fazem parte do objeto de estudo de Karagiannis, mas não são necessários para responder à pergunta experimental do meu TCC.

A contribuição do artigo está em oferecer evidências sobre fatores que influenciam o desempenho, e não em fornecer uma metodologia que precise ser reproduzida integralmente.

## 14. Pontos para uma futura revisão do benchmark

Durante nossa discussão, surgiram algumas observações que poderão ser retomadas quando confrontarmos a literatura com os scripts.

### 14.1. Comportamento da memória

Investigar, caso os resultados justifiquem, se determinadas operações utilizam estruturas intermediárias com consumo relevante de memória.

Essa investigação deve ser conduzida com base na implementação real, sem pressupor a existência dos mecanismos descritos por Karagiannis.

### 14.2. Diferenças entre mecanismos de execução

Documentar que Python/Pandas e PostgreSQL possuem mecanismos internos distintos.

Essas diferenças precisam ser consideradas ao interpretar os resultados.

### 14.3. Interpretação de múltiplas métricas

Evitar classificar uma arquitetura como superior apenas com base no menor tempo total.

Observar também o comportamento de CPU, memória RAM e throughput.

### 14.4. Limites das explicações causais

Não atribuir diferenças observadas a mecanismos específicos sem evidências suficientes.

Quando necessário, apresentar possíveis explicações como hipóteses, claramente separadas dos resultados medidos.

**Esses pontos devem ser retomados na revisão conjunta entre literatura e benchmark, não representam decisões imediatas de alteração dos scripts.**

## 15. Avaliação final da relevância

Inicialmente, tive bastante dificuldade para compreender o artigo.

Sua discussão sobre algoritmos, escalonamento e estruturas de processamento estava distante dos assuntos com os quais tenho maior familiaridade.

Por isso, a leitura precisou ser conduzida de maneira guiada.

Ao longo da discussão, consegui compreender o problema central e identificar uma contribuição que não havia considerado anteriormente: **a organização interna da execução pode influenciar significativamente o comportamento de um pipeline, mesmo quando sua arquitetura permanece a mesma**.

Esse aprendizado acrescenta uma perspectiva diferente das encontradas nos estudos anteriores.

Também reforça a importância de analisar múltiplas métricas e interpretar cuidadosamente as causas das diferenças observadas.

### Decisão consolidada

Karagiannis et al. (2013) será mantido como candidato relevante para a seção de Trabalhos Relacionados.

Sua contribuição está relacionada à avaliação experimental de desempenho e às estratégias internas de execução de pipelines ETL.

Entretanto, o artigo não deverá ser utilizado como evidência direta de superioridade entre ETL e ELT.

Sua função será complementar a discussão sobre desempenho e demonstrar a influência das decisões de implementação.

## 16. Síntese final

Karagiannis et al. (2013) investigam diferentes políticas de escalonamento de operações ETL, avaliando seus efeitos sobre o tempo de execução e a utilização de memória intermediária.

O artigo demonstra que diferentes estratégias de organização da execução podem produzir resultados distintos, mesmo quando a arquitetura de processamento permanece ETL.

Durante a leitura, compreendi que as operações de um pipeline podem produzir e consumir registros em velocidades diferentes, criando a possibilidade de acúmulo de dados intermediários.

Também compreendi que escalonamento não é simplesmente a diferença entre execução sequencial e paralela, mas envolve decisões sobre como distribuir oportunidades de processamento entre as operações.

Outro aprendizado importante foi reconhecer que melhor desempenho temporal não significa necessariamente menor utilização de memória.

Por fim, o estudo reforçou a importância de separar resultados observados de hipóteses sobre suas causas.

**A principal contribuição de Karagiannis para meu TCC é demonstrar que decisões internas de execução podem influenciar o desempenho de pipelines, reforçando a necessidade de interpretar os resultados de ETL e ELT considerando tanto as arquiteturas quanto as implementações efetivamente avaliadas.**

Essa perspectiva torna o artigo relevante para a seção de Trabalhos Relacionados, mesmo que ele não realize uma comparação direta entre ETL e ELT.

---

**Estado:** leitura guiada e discussão crítica concluídas.

**Classificação:** candidato relevante para Trabalhos Relacionados.

**Decisão:** manter na seleção inicial, com foco em desempenho, memória e influência das estratégias de execução.

**Observação metodológica:** as discussões sobre possíveis efeitos desses mecanismos no benchmark ENEM/TSE são inferências desenvolvidas durante nossa análise. Não representam resultados demonstrados por Karagiannis para nossas implementações.