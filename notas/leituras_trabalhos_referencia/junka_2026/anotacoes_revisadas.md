# Junka (2026) — Versão revisada

**Trabalho:** *Literature Review of the ETL and ELT Data Integration Pipelines*  
**Autor:** Jeremi Junka  
**Ano:** 2026  
**Tipo:** Revisão de literatura

**Finalidade deste documento:** consolidar as interpretações desenvolvidas durante a leitura e discussão do trabalho, destacando suas contribuições conceituais, os ajustes de entendimento e sua relação com o TCC de comparação experimental entre ETL e ELT.

---

## 1. Objetivo e características do trabalho

Junka (2026) apresenta uma revisão de literatura sobre as arquiteturas ETL e ELT, abordando seus princípios de funcionamento, indicadores de desempenho e possibilidades de otimização.

Diferentemente de Bessa e Santos (2023), o trabalho não apresenta uma comparação experimental própria entre duas implementações.

Sua contribuição está principalmente na organização e discussão de conhecimentos existentes sobre as arquiteturas de integração de dados.

Entre os temas que mais chamaram atenção durante a leitura estão:

- Funcionamento das etapas de ETL e ELT.
- Indicadores de desempenho, como throughput e latência.
- Extração incremental.
- Paralelismo e multithreading.
- Estratégias de otimização do processamento.

A principal contribuição potencial de Junka para meu TCC está na fundamentação conceitual e na compreensão dos fatores que podem influenciar o desempenho dos pipelines.

## 2. Estratégias de otimização

Um dos aspectos mais interessantes do trabalho foi a apresentação de estratégias que podem melhorar o desempenho de pipelines de dados.

Inicialmente, essas técnicas chamaram atenção por serem assuntos com os quais ainda tenho pouca experiência prática.

Após a discussão, ficou mais claro que **essas estratégias não são características exclusivas de ETL ou ELT**.

Elas representam decisões de implementação que podem ser aplicadas às diferentes arquiteturas.

### 2.1. Extração incremental

A extração incremental permite recuperar apenas dados novos ou modificados desde determinada referência de processamento.

Uma implementação possível utiliza timestamps para identificar os registros que precisam ser extraídos em uma nova execução.

Essa estratégia pode reduzir a necessidade de reprocessar continuamente todo o conjunto de dados.

Entretanto, sua aplicação exige mecanismos adequados para identificar alterações, inclusive atualizações em registros existentes.

O principal aprendizado foi compreender que a eficiência de extração pode depender da estratégia utilizada, independentemente da arquitetura.

### 2.2. Paralelismo e multithreading

Paralelismo e multithreading são estratégias que podem contribuir para melhorar o desempenho de determinadas operações.

O paralelismo permite distribuir atividades para execução simultânea, enquanto o multithreading é uma forma de organizar múltiplos fluxos de execução dentro de um processo.

O benefício efetivo depende de fatores como:

- Tipo de operação executada.
- Recursos computacionais disponíveis.
- Capacidade de paralelização da implementação.
- Limitações de CPU, memória e entrada/saída.
- Custos adicionais de coordenação.

Essas técnicas podem ser empregadas tanto em ETL quanto em ELT, embora os mecanismos e os benefícios variem conforme as ferramentas utilizadas.

### 2.3. Relação com meu TCC

Não pretendo ampliar o escopo do experimento para comparar diferentes técnicas de otimização.

Entretanto, o conhecimento dessas estratégias é útil para compreender que diferenças de desempenho podem decorrer de escolhas de implementação, não apenas da arquitetura ETL ou ELT.

**Decisão:** registrar essas estratégias como conhecimento complementar, sem necessariamente dedicar uma seção extensa a elas no artigo final.

## 3. Indicadores de desempenho

Junka aborda indicadores relacionados à eficiência do processamento, especialmente throughput e latência.

Durante a leitura, surgiu uma dúvida importante sobre a diferença entre latência e tempo de execução.

Essa questão foi esclarecida em nossa primeira microetapa.

### 3.1. Tempo de execução

O tempo de execução representa o intervalo necessário para concluir uma operação ou conjunto de operações.

No contexto do meu TCC, essa métrica será utilizada para avaliar o tempo necessário para executar os pipelines e suas etapas.

Ela permite comparar a duração das implementações ETL e ELT nas condições estabelecidas.

### 3.2. Throughput

O throughput representa a quantidade de dados ou unidades de trabalho processadas por unidade de tempo.

Por exemplo, um pipeline que processa 1 milhão de registros em 20 segundos apresenta throughput médio de 50 mil registros por segundo, desde que essa seja a quantidade efetivamente processada segundo a definição utilizada.

Essa métrica já faz parte do meu experimento.

Embora esteja matematicamente relacionada ao tempo de execução, oferece uma perspectiva de vazão do processamento.

**Observação metodológica:** quando o throughput é calculado diretamente a partir do volume e do tempo total, ele não representa uma medição independente dessas duas grandezas. Sua utilidade está em expressar a taxa de processamento e facilitar análises entre diferentes volumes.

### 3.3. Latência

A latência representa o intervalo entre um evento inicial e a disponibilização ou conclusão do resultado correspondente.

Sua interpretação depende da unidade analisada e dos eventos utilizados como referência.

Em um pipeline, podemos avaliar a latência de um registro, de uma operação ou de um lote inteiro.

Se todos os registros forem considerados recebidos no instante inicial e os resultados somente ficarem disponíveis após o término da execução, a latência de disponibilização do lote coincidirá com o tempo total.

Entretanto, em pipelines nos quais os registros chegam em momentos diferentes ou são disponibilizados progressivamente, as latências individuais podem variar.

### 3.4. Decisão sobre a utilização de latência

Após nossa discussão, considerei que não há necessidade de acrescentar latência ao conjunto atual de métricas do meu TCC.

Como o experimento trabalha com processamento em lote e geração de tabelas finais, a latência de disponibilização do lote poderia apresentar grande sobreposição com o tempo total de execução.

Sua inclusão não necessariamente acrescentaria informações relevantes à pergunta de pesquisa.

Isso não significa que latência seja uma métrica pouco importante em geral.

Em sistemas contínuos, aplicações sensíveis ao tempo de resposta e pipelines de streaming, ela pode ser fundamental.

**Decisão:** manter tempo de execução, CPU, RAM e throughput como métricas previstas, sem adicionar latência especificamente por causa da discussão de Junka.

## 4. ETL, ELT e disponibilização de dados para consumo

Uma das interpretações iniciais foi que ETL seria naturalmente mais adequado a situações nas quais os usuários de negócio precisam consumir dados já preparados.

Essa interpretação surgiu da associação entre:

- ETL e dados previamente tratados.
- ELT e armazenamento de dados brutos para transformação posterior.

Após nossa discussão, essa associação foi refinada.

A diferença fundamental entre ETL e ELT está na ordem entre transformação e carga, e não necessariamente na estrutura ou na qualidade dos dados entregues ao usuário.

Um pipeline ELT pode carregar dados brutos, realizar todas as transformações necessárias no ambiente de destino e disponibilizar uma tabela final completamente tratada.

Da mesma forma, um pipeline ETL pode produzir uma tabela final com estrutura e conteúdo equivalentes.

### 4.1. Relação com self-service BI

A facilidade de utilização dos dados por usuários de negócio depende de características como:

- Organização das tabelas.
- Clareza dos nomes e atributos.
- Relacionamentos e modelagem.
- Consistência das informações.
- Adequação dos dados às necessidades analíticas.

Essas características não são exclusivas de uma arquitetura.

Portanto, ETL e ELT podem oferecer experiências equivalentes de self-service BI quando produzem resultados igualmente preparados.

### 4.2. Aprendizado da discussão

A associação entre ETL e dados prontos para consumo não deve ser interpretada como uma superioridade inerente dessa arquitetura.

O importante é distinguir o funcionamento interno do pipeline da estrutura final disponibilizada.

Essa conclusão reforça uma questão que também apareceu na análise de Hübner (2020): **as arquiteturas podem seguir caminhos diferentes e entregar resultados funcionalmente equivalentes**.

## 5. Preservação dos dados brutos

Durante a leitura, associei o ELT à preservação dos dados originais e à possibilidade de rastrear informações até suas fontes.

Essa interpretação possui fundamento, mas exigia maior precisão.

No ELT, os dados extraídos são carregados no ambiente de destino antes das transformações.

Isso favorece a disponibilidade de uma camada de dados brutos no próprio destino, permitindo que essas informações sejam posteriormente consultadas ou reprocessadas.

Entretanto, essa vantagem não significa que o ELT preserve obrigatoriamente os dados com maior segurança ou confiabilidade.

### 5.1. Preservação também é possível no ETL

Um pipeline ETL pode preservar os arquivos ou registros originais em um ambiente separado.

Por exemplo, mesmo que o Python transforme dados CSV antes de carregá-los no PostgreSQL, os arquivos originais podem continuar armazenados.

Assim, ambos os pipelines podem preservar as informações de origem.

A principal diferença está na forma como essa preservação é incorporada à implementação.

### 5.2. Preservação não significa robustez automática

A confiabilidade da preservação depende de outros fatores, como:

- Integridade dos arquivos ou registros.
- Versionamento.
- Backups.
- Políticas de retenção.
- Proteção contra alterações indevidas.

Armazenar os dados brutos em um banco de dados não garante, por si só, uma preservação mais robusta do que mantê-los em arquivos adequadamente gerenciados.

### 5.3. Conclusão revisada

O ELT frequentemente facilita a manutenção de dados brutos no ambiente de destino.

Entretanto, preservar os dados originais não é uma capacidade exclusiva dessa arquitetura.

A robustez da preservação depende das estratégias de armazenamento e governança adotadas.

## 6. Preservação dos dados e rastreabilidade

Outro aprendizado importante foi compreender que preservar dados brutos não é o mesmo que garantir rastreabilidade.

A rastreabilidade envolve a capacidade de identificar:

- A origem dos dados.
- As transformações aplicadas.
- As regras e parâmetros utilizados.
- As versões das implementações.
- O caminho percorrido até o resultado final.

Durante a discussão, utilizamos o exemplo de tentar reproduzir um resultado gerado seis meses antes.

Mesmo que os dados originais ainda estejam disponíveis, não seria possível garantir a reprodução exata do resultado sem conhecer as regras e condições utilizadas no processamento original.

Assim, **a preservação dos dados brutos pode contribuir para a rastreabilidade, mas não é suficiente para garanti-la**.

Tanto ETL quanto ELT podem possuir mecanismos adequados de rastreabilidade.

Esses mecanismos dependem das decisões de implementação, documentação e controle do processamento.

### Relação com meu TCC

Essa distinção é importante conceitualmente, mas não precisa receber grande aprofundamento na fundamentação do artigo.

Meu objetivo principal é avaliar desempenho, e não comparar políticas de governança ou rastreabilidade entre arquiteturas.

O conceito poderá ser mencionado caso seja necessário caracterizar diferenças comuns entre as implementações.

## 7. Diferença entre arquitetura e otimização

A análise de Junka reforçou um aprendizado que também apareceu nos trabalhos anteriores.

O desempenho de uma implementação não depende exclusivamente da escolha entre ETL e ELT.

Existem diferentes fatores associados à implementação que podem influenciar os resultados.

Entre eles:

- Estratégias de extração.
- Paralelismo.
- Uso de threads.
- Ferramentas de transformação.
- Mecanismos de carga.
- Recursos computacionais disponíveis.

Assim, duas implementações ETL podem apresentar desempenhos bastante diferentes entre si.

O mesmo pode acontecer com duas implementações ELT.

Isso significa que o desempenho observado em uma implementação específica não deve ser automaticamente generalizado para toda a arquitetura.

**Distinção de origem:** essa conclusão metodológica foi desenvolvida durante nossa discussão a partir das estratégias estudadas. Não corresponde a um resultado experimental próprio de Junka.

## 8. Natureza da evidência apresentada por Junka

Um aspecto importante é que o trabalho de Junka constitui uma revisão de literatura.

Isso significa que ele reúne e discute conhecimentos e evidências provenientes de outras publicações.

Diferentemente dos estudos experimentais que analisamos, não devemos tratar suas considerações como resultados de um benchmark executado pelo próprio autor.

Ao utilizar suas contribuições no TCC, será necessário distinguir:

**Fundamentação conceitual:** explicações e sistematizações apresentadas pelo autor sobre ETL, ELT, indicadores e estratégias.

**Evidências de outros estudos:** resultados experimentais de pesquisas citadas na revisão.

Quando uma conclusão depender diretamente de resultados de outro experimento, será preferível consultar o trabalho original antes de utilizá-la.

Isso ajudará a evitar interpretações sem contexto ou atribuições equivocadas de resultados.

## 9. Relação com os trabalhos anteriormente analisados

Os três trabalhos estudados até aqui possuem contribuições diferentes.

| Trabalho | Principal contribuição percebida |
|---|---|
| Bessa e Santos (2023) | Comparação experimental direta entre ETL e ELT |
| Hübner (2020) | Proposta arquitetural alternativa e discussão de soluções para BI |
| Junka (2026) | Fundamentação conceitual, indicadores e otimização de pipelines |

### 9.1. Bessa e Santos (2023)

Continua sendo o estudo mais próximo do objetivo experimental do meu TCC.

Sua relevância está principalmente no desenho da comparação, nas métricas utilizadas e nas limitações metodológicas identificadas.

### 9.2. Hübner (2020)

Foi relevante para entender que comparar soluções diferentes não significa necessariamente realizar um experimento controlado entre arquiteturas.

Também contribuiu para discutir equivalência dos resultados finais e diferenças entre arquitetura e implementação.

### 9.3. Junka (2026)

Apresenta uma contribuição de natureza diferente.

Seu valor está principalmente na organização de conceitos, na explicação de indicadores e na apresentação de técnicas que influenciam o desempenho.

Portanto, os três trabalhos não precisam exercer a mesma função na revisão bibliográfica.

## 10. Contribuição de Junka para a fundamentação do meu TCC

Após a discussão, mantive minha avaliação de que Junka é mais útil como referência conceitual do que como estudo experimental diretamente comparável ao meu.

Sua contribuição potencial envolve:

- Explicação do funcionamento de ETL e ELT.
- Caracterização das etapas dos pipelines.
- Definição e contextualização de indicadores de desempenho.
- Discussão de estratégias de otimização.
- Compreensão de fatores associados à eficiência de processamento.

Entre as possibilidades, considero especialmente relevante sua utilização na apresentação dos indicadores throughput e latência, assim como na contextualização das estratégias de processamento.

Entretanto, não será necessário reproduzir extensamente sua discussão sobre otimizações que não fazem parte do meu experimento.

### Decisão sobre a fundamentação

A importância definitiva de Junka dependerá da estrutura e do nível de aprofundamento teórico exigidos para o artigo.

Caso a fundamentação precise apresentar detalhadamente conceitos e estratégias relacionadas aos pipelines, sua revisão poderá exercer um papel importante.

Se a estrutura acadêmica exigir uma discussão mais curta e diretamente relacionada ao experimento, sua utilização poderá ser mais pontual.

## 11. Relação com a metodologia experimental

Junka não trouxe, na minha leitura inicial, contribuições tão diretamente relacionadas ao desenho experimental quanto Bessa e Santos.

Não identifiquei nele discussões especialmente relevantes para fundamentar a escolha de CSVs locais, o isolamento da rede ou a variação controlada de datasets.

Porém, a discussão de otimizações reforçou a importância de distinguir decisões de implementação das diferenças arquiteturais que pretendo investigar.

Esse aprendizado poderá ser retomado futuramente durante a revisão conjunta dos scripts e benchmarks.

Ainda assim, não pretendo modificar imediatamente os pipelines em função das técnicas apresentadas por Junka.

A prioridade atual continua sendo finalizar a leitura dos trabalhos relacionados e consolidar seus aprendizados.

## 12. Pontos que não precisam ser aprofundados no TCC

Embora sejam tecnicamente interessantes, alguns temas abordados durante nossa leitura não precisam integrar o núcleo da pesquisa:

- Comparação entre diferentes estratégias de paralelismo.
- Avaliação específica de multithreading.
- Implementação de mecanismos incrementais de extração.
- Comparação aprofundada de latência em diferentes modelos de processamento.
- Governança e rastreabilidade de dados.
- Avaliação de usabilidade para self-service BI.

Esses assuntos poderão aparecer pontualmente quando necessários, mas não devem desviar o foco do objetivo experimental.

O estudo não pretende demonstrar todas as possibilidades de otimização de ETL e ELT.

Seu objetivo é comparar o comportamento das implementações definidas sob condições controladas.

## 13. Principais aprendizados

Após a leitura e discussão de Junka, consolidei os seguintes entendimentos:

1. **As estratégias de otimização não definem a arquitetura.** Paralelismo, multithreading e extração incremental podem ser aplicados a diferentes pipelines.

2. **Latência e tempo de execução não são necessariamente equivalentes.** A relação entre eles depende dos eventos e das unidades de processamento utilizados na medição.

3. **Throughput representa a vazão de processamento.** Embora esteja relacionado ao tempo e ao volume, permite expressar o desempenho como uma taxa.

4. **ETL e ELT podem entregar dados igualmente preparados para consumo.** A qualidade e a organização do resultado final dependem das transformações e da modelagem adotadas.

5. **O ELT favorece a disponibilidade de dados brutos no destino, mas não possui exclusividade sobre sua preservação.**

6. **Preservação e rastreabilidade são conceitos distintos.** Manter dados originais não garante a reprodução ou a auditoria completa de um processamento anterior.

7. **O desempenho depende também das decisões de implementação.** Resultados específicos não devem ser automaticamente generalizados para todas as implementações de uma arquitetura.

8. **Junka é uma referência conceitual, não um benchmark próprio.** Seus argumentos e as evidências experimentais dos trabalhos citados devem ser diferenciados.

## 14. Observações para a revisão posterior dos benchmarks

Os seguintes pontos poderão ser retomados quando a etapa de leitura estiver concluída e os scripts forem analisados em conjunto com a literatura:

- Confirmar a definição operacional de throughput utilizada no benchmark.
- Verificar a coerência entre volume processado e tempo utilizado no cálculo da vazão.
- Avaliar se as diferentes estratégias de implementação introduzem fatores que precisam ser reconhecidos nas limitações.
- Garantir que ambos os pipelines entreguem resultados funcionalmente equivalentes.
- Distinguir resultados específicos das implementações de afirmações gerais sobre ETL e ELT.
- Documentar adequadamente as condições experimentais utilizadas.

Esses pontos representam critérios para uma análise metodológica posterior, não alterações imediatas na implementação.

## 15. Síntese final

Junka (2026) apresenta uma revisão conceitual sobre ETL e ELT, discutindo suas características, indicadores de desempenho e possibilidades de otimização.

O principal destaque da leitura foi a compreensão de que diferentes técnicas, como extração incremental, paralelismo e multithreading, podem modificar o desempenho dos pipelines sem constituir características exclusivas de determinada arquitetura.

A discussão também permitiu esclarecer conceitos importantes, especialmente a diferença entre latência, throughput e tempo de execução.

Outras interpretações iniciais foram refinadas.

ETL e ELT não possuem diferenças obrigatórias quanto à qualidade dos dados disponibilizados para consumo analítico. Ambas as arquiteturas podem entregar resultados equivalentes.

Da mesma forma, embora ELT favoreça a manutenção de dados brutos no destino, a preservação e a rastreabilidade dependem de decisões adicionais de implementação.

Em relação ao meu TCC, Junka não será utilizado principalmente como referência experimental, mas como uma fonte para fundamentar conceitos e contextualizar fatores que influenciam o desempenho.

**A principal contribuição do trabalho para minha pesquisa é fortalecer o entendimento conceitual das arquiteturas e dos indicadores utilizados, ajudando a construir uma análise experimental tecnicamente coerente e evitando generalizações sobre desempenho.**

---

**Estado do documento:** discussão concluída e versão revisada consolidada.

**Nota de revisão:** este documento foi construído a partir das primeiras impressões e das cinco microetapas discutidas. As interpretações sobre implicações metodológicas para meu TCC foram desenvolvidas durante o debate. Antes de aproveitar afirmações específicas no artigo acadêmico, será necessário conferir sua correspondência com as seções e referências originais de Junka.