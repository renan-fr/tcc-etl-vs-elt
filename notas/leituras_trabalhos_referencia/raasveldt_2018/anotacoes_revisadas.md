# Raasveldt et al. (2018) — Análises revisadas

**Título:** *Fair Benchmarking Considered Difficult: Common Pitfalls in Database Performance Testing*

**Autores:** Mark Raasveldt, Pedro Holanda, Tim Gubner e Hannes Mühleisen  
**Ano:** 2018  
**Publicação:** International Workshop on Testing Database Systems (DBTest), ACM  
**DOI:** https://doi.org/10.1145/3209950.3209955

**Finalidade:** consolidar os conhecimentos adquiridos na leitura e discussão crítica do artigo, distinguindo os argumentos apresentados pelos autores, as interpretações desenvolvidas durante nossa análise e suas possíveis aplicações metodológicas ao TCC.

---

## 1. Objetivo do trabalho

Raasveldt et al. (2018) discutem problemas metodológicos recorrentes em benchmarks de desempenho de sistemas de bancos de dados.

Na introdução, os autores observam que comparações de desempenho são atrativas porque utilizam métricas aparentemente objetivas, como o tempo de execução.

Entretanto, a objetividade de uma medição não garante que a comparação seja justa.

Diferenças de configuração, funcionalidades, condições iniciais e procedimentos experimentais podem influenciar significativamente os resultados.

O trabalho busca identificar essas armadilhas e apresentar recomendações para produzir avaliações mais confiáveis.

### Contribuição central

Uma medição pode estar numericamente correta e, ainda assim, sustentar uma comparação metodologicamente inadequada.

A confiabilidade de um benchmark depende tanto da medição quanto das condições em que os sistemas são preparados, executados e avaliados.

## 2. Benchmarketing e possíveis vieses

Na introdução, os autores apresentam o conceito de *benchmarketing*, relacionado ao uso de resultados de benchmarks como instrumento de promoção de sistemas ou produtos.

Comparações podem ser construídas de maneira a favorecer determinada solução, especialmente quando seus responsáveis possuem interesse em demonstrar superioridade diante de concorrentes.

Entretanto, nem todo problema decorre necessariamente de manipulação deliberada.

Vieses também podem surgir por desconhecimento, escolhas inadequadas de configuração ou diferenças no esforço dedicado à preparação dos sistemas.

### Interpretação revisada

Embora o artigo apresente exemplos relacionados à promoção de novos sistemas, seus problemas metodológicos não estão restritos a comparações comerciais.

Pesquisas acadêmicas também podem produzir resultados enviesados involuntariamente.

No meu TCC, não pretendemos demonstrar a superioridade universal de ETL ou ELT.

Ainda assim, precisamos considerar se nossas decisões de implementação e execução podem favorecer uma das alternativas.

A ausência de intenção de favorecer determinada arquitetura não garante, por si só, uma comparação justa.

## 3. Reprodutibilidade — Seção 3.1: Non-Reproducibility

Os autores discutem a dificuldade de reproduzir benchmarks quando informações relevantes sobre o experimento não são disponibilizadas.

A documentação insuficiente de hardware, configurações, versões de software, dados ou procedimentos pode impedir que outros pesquisadores compreendam as condições em que os resultados foram obtidos.

### Nossa discussão

Inicialmente, considerei que, caso outro pesquisador executasse nossos scripts em um computador diferente e encontrasse a mesma tendência de desempenho, isso comprovaria nosso experimento.

Essa interpretação foi refinada.

Encontrar tendências semelhantes sob condições diferentes constitui uma evidência adicional de consistência, mas não representa comprovação universal.

O desempenho pode variar conforme hardware, configurações, ferramentas e condições de execução.

### Aplicação ao TCC

Documentar adequadamente:

- Processador, memória RAM e armazenamento.
- Sistema operacional.
- Versões de Python, Pandas e PostgreSQL.
- Configurações relevantes.
- Conjuntos e volumes de dados.
- Procedimentos de execução e medição.
- Critérios de preparação e aquecimento.

Essa documentação facilita a compreensão e possíveis tentativas de reprodução do experimento.

Entretanto, não garante que outros pesquisadores obtenham tempos numericamente idênticos.

### Aprendizado

Precisamos diferenciar validade experimental de generalização.

Um benchmark pode ser metodologicamente válido para o ambiente investigado sem demonstrar que os mesmos resultados ocorrerão em qualquer outro computador.

## 4. Otimização — Seção 3.2: Failure to Optimize

A seção *Failure to Optimize* discute comparações nas quais uma das alternativas não recebe configuração ou otimização adequada.

Os autores demonstram que escolhas de configuração podem influenciar significativamente o desempenho.

Isso representa um risco especialmente relevante quando pesquisadores comparam uma solução própria com outro sistema.

Uma alternativa pode parecer inferior simplesmente porque não foi preparada adequadamente.

### Nossa discussão

Considerei que não seria justo comparar um ETL bem otimizado com um ELT que utiliza consultas SQL claramente ineficientes.

Entretanto, também reconheci a dificuldade de estabelecer se duas implementações diferentes estão igualmente otimizadas.

Python/Pandas e SQL/PostgreSQL possuem mecanismos distintos, tornando problemática qualquer tentativa de estabelecer equivalência absoluta de otimização.

### Interpretação revisada

Condições experimentais equivalentes não exigem implementações internas idênticas.

Cada implementação deve utilizar procedimentos adequados às características da tecnologia empregada.

Nosso objetivo deve ser evitar ineficiências conhecidas ou desnecessárias, sem afirmar que alcançamos otimização máxima ou perfeitamente equivalente.

### Aplicação ao TCC

A discussão fundamenta a necessidade de:

- Revisar as estratégias de transformação.
- Evitar operações intermediárias desnecessárias.
- Utilizar mecanismos de carga adequados.
- Documentar configurações relevantes.
- Investigar gargalos evidentes.
- Reconhecer a influência dos mecanismos de implementação.

Essa contribuição dialoga diretamente com as críticas do orientador sobre as diferenças entre Pandas e PostgreSQL.

## 5. Equivalência funcional — Seção 3.3: Apples vs. Oranges

Na seção *Apples vs. Oranges*, os autores discutem comparações entre sistemas que oferecem funcionalidades diferentes.

Um exemplo envolve um programa especializado, desenvolvido para executar uma tarefa específica, e um sistema completo de gerenciamento de bancos de dados.

Embora ambos possam realizar determinada operação, o SGBD completo também precisa oferecer funcionalidades adicionais.

Essas diferenças podem afetar o desempenho e comprometer a interpretação da comparação.

### O que os autores efetivamente discutem

O problema central é comparar sistemas que não oferecem funcionalidades equivalentes e atribuir diferenças de desempenho exclusivamente à eficiência de cada alternativa.

Os autores defendem que uma comparação justa precisa considerar as funcionalidades efetivamente executadas e oferecidas pelos sistemas.

**Essa seção não trata principalmente de código incorreto, mas de diferenças funcionais entre sistemas que podem estar funcionando corretamente.**

### Nossa discussão

Relacionamos esse argumento aos pipelines ETL e ELT.

Na nossa implementação:

- O ETL transforma os dados no Pandas e posteriormente carrega os resultados no PostgreSQL.
- O ELT carrega os dados brutos no PostgreSQL e realiza as transformações com SQL.

Questionei se a diferença entre as operações realizadas tornaria a comparação injusta.

Minha interpretação foi que não devemos obrigar as duas arquiteturas a executar operações internas idênticas, pois parte dessas diferenças constitui justamente o objeto da comparação.

### Interpretação metodológica revisada

Para o objetivo do nosso experimento, precisamos garantir entradas comparáveis e resultados finais funcionalmente equivalentes.

Entretanto, isso não significa que os pipelines tenham necessariamente todas as mesmas funcionalidades internas.

A retenção dos dados brutos, por exemplo, pode representar uma capacidade adicional da implementação ELT.

Essa assimetria precisa ser reconhecida quando relevante.

A decisão de comparar os pipelines completos, permitindo operações internas diferentes, é uma escolha do nosso desenho experimental.

**Não devemos atribuir diretamente a Raasveldt a afirmação de que produzir as mesmas tabelas finais torna automaticamente justa qualquer comparação entre ETL e ELT.**

O artigo fornece o princípio da equivalência funcional; sua aplicação às arquiteturas é uma interpretação metodológica nossa.

## 6. Custos de preparação — Seção 3.7: Ignoring Preprocessing Time

Na seção *Ignoring Preprocessing Time*, os autores discutem problemas causados pela exclusão de custos de preparação das medições de desempenho.

Determinadas operações, como a criação de índices e outras atividades preparatórias, podem oferecer vantagens posteriores durante a execução das consultas.

Quando o custo dessas operações é desconsiderado, o desempenho apresentado pode não representar adequadamente o trabalho necessário.

### Correção importante

O artigo não estabelece que todos os benchmarks devem obrigatoriamente incluir todo o pré-processamento no tempo medido.

A preocupação dos autores é evitar que custos relevantes sejam excluídos de maneira a produzir comparações enganosas.

O tratamento dessas operações depende do objetivo e dos limites definidos para o benchmark.

### Nossa discussão

No nosso experimento, definimos que o tempo total deve contemplar as operações necessárias à execução dos pipelines.

Isso inclui a carga dos dados brutos no ELT.

Discutimos que descartar as tabelas brutas posteriormente não elimina o custo inicial de carregá-las.

Esse custo já ocorreu e faz parte da implementação avaliada.

Também reconhecemos que a retenção permanente dos dados brutos não é uma obrigação universal do ELT.

### Aplicação ao TCC

Precisamos definir claramente:

- O início e o término das medições.
- Quais operações são contabilizadas.
- Quais atividades preparatórias ficam fora do intervalo medido.
- Se existem custos excluídos capazes de favorecer uma implementação.
- Se as escolhas são coerentes com o objetivo de comparar pipelines completos.

Nossa decisão de contabilizar leitura, transformação e carga pode ser fundamentada pela preocupação metodológica apresentada pelos autores.

Entretanto, a definição dessas etapas como componentes do tempo total é uma decisão específica do nosso experimento.

## 7. Correção dos resultados — Seção 3.8: Incorrect Code

A seção *Incorrect Code* aborda o risco de comparar implementações que produzem resultados incorretos.

Uma implementação pode apresentar menor tempo de execução porque não está realizando corretamente todas as operações necessárias.

Nesse cenário, a aparente vantagem de desempenho pode decorrer de um defeito, e não de maior eficiência.

### Distinção em relação à seção 3.3

**Apples vs. Oranges:** os sistemas podem funcionar corretamente, mas oferecer funcionalidades diferentes.

**Incorrect Code:** uma implementação pode estar executando incorretamente a tarefa pretendida.

Esses problemas são relacionados à validade da comparação, mas possuem naturezas diferentes.

### Aplicação ao TCC

Antes de interpretar os tempos, precisamos verificar que ETL e ELT produzem resultados finais equivalentes.

Isso envolve validar:

- Estrutura das tabelas finais.
- Quantidade de registros.
- Valores produzidos.
- Regras de transformação.
- Comportamento nos diferentes volumes.

Uma implementação que processa menos dados ou produz resultados incorretos não deve ser considerada superior simplesmente por apresentar menor tempo.

A validação pode ocorrer fora do intervalo cronometrado, desde que esse procedimento seja consistente e devidamente documentado.

O princípio sustentado pelo artigo é a necessidade de garantir a correção das implementações comparadas.

## 8. Condições de execução — Seção 3.5: Cold vs Hot Runs

Os autores discutem a diferença entre execuções em condições frias e aquecidas.

Uma execução fria pode envolver custos associados à ausência de dados em cache e à preparação inicial do sistema.

Em execuções aquecidas, determinados dados ou estruturas podem permanecer disponíveis, alterando o comportamento temporal.

### Nossa discussão

Consideramos que comparar uma execução fria de ETL com uma execução aquecida de ELT poderia introduzir um desequilíbrio.

Essa diferença poderia favorecer uma arquitetura por fatores relacionados ao estado inicial, e não necessariamente por sua eficiência.

### Aplicação ao TCC

O procedimento de aquecimento que adotamos busca reduzir diferenças relacionadas à partida a frio.

Entretanto, aquecer os dois pipelines não garante estados internos perfeitamente idênticos.

Python/Pandas e PostgreSQL podem utilizar mecanismos distintos de cache e gerenciamento de recursos.

Portanto, precisamos padronizar e documentar o aquecimento, sem afirmar que ele elimina todas as diferenças de estado.

### Limite da interpretação

Os autores não demonstram que hot runs devem ser utilizadas obrigatoriamente em qualquer benchmark.

A escolha entre execuções frias e aquecidas depende do comportamento que se pretende investigar.

## 9. Execuções aparentemente frias — Seção 3.6: Cold vs Warm Runs

Nesta seção, os autores discutem situações em que uma execução apresentada como fria não representa necessariamente uma condição completamente fria.

Reiniciar o serviço de banco de dados, por exemplo, não garante que dados anteriormente acessados tenham sido removidos dos caches do sistema operacional.

Consequentemente, uma execução supostamente fria pode se beneficiar de informações armazenadas anteriormente.

### Aprendizado revisado

É importante distinguir o estado do processo de banco de dados do estado de outros componentes do sistema.

A ausência de uma instância previamente ativa não significa necessariamente ausência de efeitos de cache.

### Relação com nosso TCC

Não estamos comparando diretamente execuções frias e aquecidas.

Portanto, não precisamos desenvolver um procedimento específico para medir essas diferenças.

Entretanto, o artigo reforça a importância de definir com precisão quais condições experimentais estamos adotando.

## 10. Ordem das execuções e randomização

Durante nossa discussão, avaliamos a possibilidade de realizar todas as execuções ETL antes das execuções ELT.

Identificamos que isso poderia associar sistematicamente determinadas condições do computador a uma das arquiteturas.

Entre essas condições estão:

- Temperatura do processador.
- Frequência de operação.
- Utilização de memória.
- Processos em segundo plano.
- Estado dos caches.
- Outras flutuações do ambiente.

### Nossa interpretação

Randomizar a ordem das execuções pode reduzir a associação sistemática entre esses fatores e a arquitetura avaliada.

Entretanto, a randomização não elimina completamente essas influências.

Além disso, com poucas repetições, uma ordem aleatória não garante equilíbrio perfeito.

### Distinção de autoria

A randomização faz parte das decisões metodológicas do nosso benchmark.

Ela é coerente com a preocupação geral de Raasveldt sobre comparações justas, mas **não deve ser apresentada como uma recomendação específica dos autores sem evidência textual correspondente**.

Essa distinção é importante para não atribuir ao artigo conclusões que desenvolvemos durante nossa própria discussão.

## 11. Otimização específica — Seção 3.4: Overly-specific Tuning

Os autores também discutem o problema de otimizar excessivamente um sistema para um benchmark específico.

Uma implementação pode apresentar resultados excelentes em um conjunto conhecido de operações, mas não demonstrar a mesma eficiência em outras situações.

Isso compromete a interpretação de sua capacidade geral.

### Interpretação revisada

Existe uma diferença entre utilizar adequadamente os recursos de uma tecnologia e explorar particularidades de um benchmark de maneira excessivamente específica.

A primeira prática contribui para uma comparação mais justa.

A segunda pode limitar a representatividade dos resultados.

### Aplicação ao TCC

Devemos evitar implementações que dependam indevidamente de características acidentais dos CSVs utilizados.

A utilização de diferentes conjuntos e volumes de dados ajuda a observar o comportamento das implementações em cenários distintos.

Entretanto, isso não garante que os resultados sejam generalizáveis para qualquer conjunto de dados ou aplicação.

## 12. Repetições e variabilidade — Apêndice A e apresentação dos experimentos

O artigo apresenta um checklist de boas práticas para benchmarks.

Entre os cuidados relevantes estão a repetição das medições e a consideração da variabilidade dos resultados.

Os próprios autores também utilizam medidas estatísticas, incluindo medianas e intervalos de confiança, na apresentação de exemplos experimentais.

### Nossa discussão

Analisamos um cenário hipotético em que o ETL apresentava menor tempo de execução em dois computadores diferentes.

Entretanto, a magnitude da vantagem era muito menor no segundo ambiente.

Concluímos que observar a mesma direção da diferença não significa necessariamente possuir evidências igualmente fortes de vantagem temporal.

Também reconhecemos que diferenças pequenas precisam ser interpretadas considerando a variabilidade das medições.

### Aplicação ao TCC

Nossas cinco execuções por combinação permitem observar diferenças entre repetições.

Entretanto, não devemos pressupor que cinco execuções sejam automaticamente suficientes para qualquer cenário.

Precisamos considerar a dispersão dos resultados antes de interpretar a magnitude das diferenças.

### Limite da referência

O artigo fornece fundamento para a importância das repetições e da análise de variabilidade.

Não devemos atribuir aos autores uma exigência específica de cinco execuções nem afirmar que essa quantidade foi validada pelo estudo para nosso experimento.

## 13. Limites das conclusões

Na última etapa da discussão, avaliamos duas formas de interpretar uma diferença hipotética de desempenho.

**Afirmação excessiva:** ETL é universalmente mais rápido que ELT.

**Afirmação delimitada:** nas condições experimentais avaliadas, a implementação ETL apresentou menor tempo médio de execução que a implementação ELT.

Concluímos que a segunda formulação é mais defensável.

### Justificativa

Nosso experimento utiliza:

- Dois conjuntos de dados específicos.
- Quatro volumes de entrada.
- Um ambiente computacional determinado.
- Ferramentas e bibliotecas particulares.
- Estratégias concretas de implementação.

Os resultados descrevem o comportamento dessas implementações nas condições avaliadas.

Não demonstram superioridade universal de uma arquitetura.

### Nuance importante

Mesmo uma afirmação delimitada precisa considerar a estabilidade das medições.

Se houver grande variabilidade, uma diferença entre médias pode não representar uma vantagem consistente.

Portanto, precisamos distinguir:

**Resultado observado:** diferença identificada nas medições.

**Interpretação:** significado dessa diferença no contexto experimental.

**Generalização:** possibilidade de estender a conclusão para outros cenários.

**Explicação causal:** identificação dos mecanismos responsáveis pela diferença.

Esses níveis não devem ser confundidos.

## 14. Relação com o TCC ETL × ELT

Raasveldt não compara experimentalmente ETL e ELT.

Seu trabalho analisa problemas metodológicos em benchmarks de sistemas de bancos de dados.

Meu TCC, por outro lado, compara duas implementações de pipelines de dados.

A relação entre os trabalhos está principalmente nos critérios utilizados para construir e interpretar uma comparação experimental confiável.

| Aspecto | Raasveldt et al. (2018) | Meu TCC |
|---|---|---|
| Objetivo | Identificar armadilhas em benchmarks | Comparar desempenho ETL × ELT |
| Equivalência | Funcionalidades comparáveis | Resultados finais equivalentes |
| Correção | Evitar comparar implementações incorretas | Validar saídas dos pipelines |
| Otimização | Evitar configurações inadequadas | Buscar implementações eficientes |
| Pré-processamento | Evitar exclusões enganosas de custos | Definir operações cronometradas |
| Condições iniciais | Distinguir cold, hot e warm runs | Padronizar aquecimento |
| Reprodutibilidade | Documentar os experimentos | Registrar ambiente e procedimentos |
| Variabilidade | Considerar repetições e dispersão | Avaliar cinco execuções por combinação |

O artigo não fornece evidências sobre qual arquitetura deve apresentar melhor desempenho.

Sua contribuição está em oferecer princípios que ajudam a avaliar a confiabilidade de comparações experimentais.

## 15. Aplicações prioritárias na metodologia

Após a revisão, considero seis aplicações especialmente importantes.

### 15.1. Documentação do ambiente

**Fundamento:** seção 3.1.

Registrar hardware, sistema operacional, versões, configurações e procedimentos.

### 15.2. Preparação eficiente das implementações

**Fundamento:** seção 3.2.

Evitar ineficiências conhecidas e documentar as escolhas relevantes.

### 15.3. Equivalência funcional

**Fundamento:** seção 3.3.

Delimitar as funcionalidades e os resultados que constituem o objeto da comparação.

### 15.4. Contabilização dos custos

**Fundamento:** seção 3.7.

Definir quais operações entram nas medições, evitando exclusões que possam favorecer uma implementação.

### 15.5. Correção dos resultados

**Fundamento:** seção 3.8.

Verificar se os pipelines produzem corretamente os resultados esperados.

### 15.6. Condições de execução e variabilidade

**Fundamentos:** seções 3.5, 3.6 e Apêndice A.

Explicitar o aquecimento, repetir medições e considerar sua dispersão.

Essas aplicações poderão fundamentar decisões já adotadas e orientar futuras verificações do benchmark.

## 16. Cuidados para a próxima revisão dos scripts

A discussão do artigo permite construir algumas perguntas para nossa revisão metodológica posterior.

**Equivalência funcional:** ETL e ELT produzem os mesmos resultados finais?

**Correção:** as transformações foram implementadas corretamente em ambos?

**Otimização:** existem operações desnecessárias que prejudicam alguma implementação?

**Preparação:** há índices, consultas ou outras operações preparatórias capazes de favorecer uma alternativa?

**Contabilização:** os custos de leitura, carga e transformação estão definidos de maneira consistente?

**Aquecimento:** os dois pipelines utilizam procedimentos experimentais comparáveis?

**Repetições:** os resultados apresentam variabilidade compatível com as conclusões pretendidas?

**Documentação:** os procedimentos permitem compreender e tentar reproduzir o benchmark?

Essas perguntas representam aplicações metodológicas derivadas de nossa leitura.

Não devem ser tratadas como uma lista de alterações obrigatórias nos scripts.

## 17. Contribuição para a redação do TCC

A principal utilização prevista para Raasveldt é na seção de Metodologia.

O artigo pode fundamentar especialmente:

- A necessidade de controlar fatores capazes de enviesar comparações.
- A documentação detalhada das condições experimentais.
- A equivalência funcional das implementações.
- A validação da correção dos resultados.
- A preocupação com a eficiência dos pipelines.
- A definição dos custos contabilizados.
- A padronização de condições de aquecimento.
- A apresentação e interpretação cuidadosa das medições.

Também poderá ser utilizado na discussão de resultados e limitações, principalmente para contextualizar a influência de configurações e decisões de implementação.

### Onde não devemos forçar sua utilização

Não considero necessário utilizá-lo como referência principal da seção de Trabalhos Relacionados.

O artigo não apresenta uma nova arquitetura de integração de dados nem realiza uma comparação experimental ETL versus ELT.

Seu valor é predominantemente metodológico.

Também não devemos atribuir aos autores nossas decisões específicas de randomização, escolha de cinco repetições ou definição dos limites temporais do pipeline.

Essas decisões podem ser coerentes com os princípios discutidos, mas possuem justificativas próprias.

## 18. Avaliação final

Considero Raasveldt et al. (2018) uma referência metodológica prioritária para meu TCC.

A leitura permitiu compreender que a qualidade de um benchmark depende de fatores que vão além da precisão da medição.

Comparações podem ser influenciadas por diferenças funcionais, configurações inadequadas, custos de preparação omitidos, resultados incorretos e condições de execução inconsistentes.

Durante nossa discussão, também compreendi que comparar duas arquiteturas não exige obrigatoriamente que elas realizem operações internas idênticas.

Entretanto, precisamos delimitar as funcionalidades comparadas e reconhecer diferenças relevantes entre as implementações.

Outro aprendizado importante foi distinguir a equivalência funcional da correção dos resultados.

Sistemas com funcionalidades diferentes podem produzir comparações injustas mesmo quando funcionam corretamente.

Da mesma forma, implementações que deveriam executar a mesma tarefa podem apresentar resultados incorretos e aparentar maior eficiência.

Por fim, compreendi que o aquecimento, a documentação e as repetições fortalecem a confiabilidade das medições, mas não eliminam todas as variáveis nem garantem generalização universal.

### Decisão consolidada

**Manter Raasveldt et al. (2018) como referência metodológica prioritária.**

Sua principal aplicação será fundamentar a preparação, a execução e a interpretação do benchmark ETL × ELT.

Não será utilizado como evidência experimental de superioridade de qualquer uma das arquiteturas.

## 19. Síntese final

Raasveldt et al. (2018) analisam armadilhas metodológicas presentes em benchmarks de sistemas de bancos de dados e apresentam recomendações para tornar essas comparações mais confiáveis.

O artigo aborda reprodutibilidade, otimização inadequada, diferenças funcionais, otimizações excessivamente específicas, condições frias e aquecidas, contabilização de pré-processamento e correção das implementações.

Durante nossa discussão, compreendi que **um benchmark justo não depende apenas de medir corretamente o tempo de execução, mas também de garantir que os sistemas sejam preparados e comparados de maneira metodologicamente coerente**.

Para meu TCC, os principais aprendizados estão relacionados à equivalência funcional, à validação dos resultados, ao controle das condições experimentais e à cautela na interpretação de diferenças de desempenho.

Também reconheci que nossas implementações ETL e ELT possuem mecanismos internos diferentes e que essas diferenças precisam ser consideradas ao interpretar os resultados.

A principal contribuição de Raasveldt para minha pesquisa é fornecer fundamentos metodológicos para construir uma comparação mais transparente e defensável, sem extrapolar as conclusões além das evidências efetivamente produzidas.

---

**Estado:** leitura, discussão crítica e auditoria das atribuições às seções concluídas.

**Classificação:** referência metodológica prioritária.

**Utilização principal:** Metodologia.

**Utilização complementar:** Resultados e Discussão; Limitações.

**Decisão:** manter na seleção bibliográfica.

**Correções incorporadas:** distinção entre *Apples vs. Oranges* (3.3) e *Incorrect Code* (3.8); interpretação restrita de *Ignoring Preprocessing Time* (3.7); separação entre recomendações dos autores e aplicações metodológicas próprias do TCC.