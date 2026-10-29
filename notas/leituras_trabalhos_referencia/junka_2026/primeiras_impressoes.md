# Junka (2026) — Primeiras impressões

**Trabalho:** Literature Review of the ETL and ELT Data Integration Pipelines

**Autor:** Jeremi Junka  
**Ano:** 2026  
**Tipo:** Registro inicial de leitura, anterior à discussão e revisão crítica.

---

## 1. Impressão geral sobre o trabalho

Minha primeira impressão foi que Junka (2026) apresenta muitos conceitos sobre ETL e ELT que eu já conhecia, mas desenvolve esses assuntos de maneiras interessantes, principalmente quando aborda possibilidades de otimização dos pipelines.

Diferentemente dos trabalhos que analisamos anteriormente, Junka apresenta uma perspectiva mais conceitual e técnica sobre o funcionamento das arquiteturas.

O que mais chamou minha atenção foi a discussão de diferentes estratégias para melhorar o desempenho das etapas de processamento.

Entre elas, destaco:

- Paralelismo nas transformações.
- Utilização de multithreading.
- Extração incremental.
- Diferentes possibilidades de otimização das etapas de ETL e ELT.

São assuntos com os quais ainda não tenho tanto contato prático, mas que considero interessantes para ampliar meu entendimento sobre processamento e integração de dados.

## 2. Extração incremental

Uma das técnicas de otimização que mais chamou minha atenção foi a extração incremental.

Pelo que compreendi, essa estratégia permite evitar a extração repetida de dados que já foram processados anteriormente.

O sistema mantém algum registro temporal, como um timestamp, para identificar até qual momento os dados foram extraídos.

Nas execuções seguintes, são extraídos apenas os registros mais recentes que ainda não foram incorporados ao processo.

Achei essa abordagem interessante porque pode reduzir a quantidade de dados movimentados e otimizar a etapa de extração.

Embora essa estratégia não esteja diretamente relacionada ao desenho atual do meu benchmark, considero interessante conhecer outras possibilidades de implementação e otimização de pipelines.

## 3. Paralelismo e multithreading

Outro aspecto interessante foi a discussão sobre paralelismo e multithreading.

Pelo que entendi, essas técnicas podem ser utilizadas para otimizar o processamento, especialmente durante as transformações.

Não possuo tanto conhecimento prático sobre essas estratégias, mas reconheço que elas podem influenciar significativamente o desempenho de um pipeline.

O trabalho mostrou que existem diferentes formas de melhorar a execução de ETL e ELT além da escolha entre as duas arquiteturas.

Não sei se essas estratégias serão abordadas no meu TCC, mas considero relevante conhecer sua existência e suas aplicações.

## 4. Situações favoráveis ao ETL

Minha interpretação foi que Junka apresenta o ETL como uma abordagem interessante para situações de processamento *on-demand*.

Entendi esse conceito de maneira semelhante ao que observei no trabalho de Hübner (2020).

No ETL, os dados são extraídos, transformados e carregados, ficando disponíveis para utilização pelas áreas de negócio.

Assim, o usuário final pode acessar informações previamente preparadas sem precisar realizar todo o processo de tratamento.

Já no ELT, os dados são inicialmente carregados em formato bruto, podendo exigir análises e transformações posteriores conforme a necessidade.

Na minha percepção, isso torna o ETL mais direto para situações nas quais se deseja disponibilizar informações prontas para utilização.

## 5. Rastreabilidade e preservação dos dados originais

Outra diferença que associei às arquiteturas foi a preservação dos dados brutos.

Minha interpretação é que o ELT apresenta vantagem nesse aspecto, pois os dados originais são carregados e podem permanecer disponíveis no ambiente de armazenamento.

Isso permite manter maior rastreabilidade em relação às informações de origem.

Já no ETL, como as transformações acontecem antes da carga, parte das informações originais pode deixar de estar disponível no destino.

Essa característica me parece semelhante ao que discutimos no trabalho de Hübner.

## 6. Métricas de desempenho: throughput e latência

Junka aborda indicadores relacionados ao desempenho dos pipelines.

Entre eles, identifiquei principalmente:

- Throughput.
- Latência.

O throughput é uma métrica com a qual já estou familiarizado, pois também será utilizado no meu benchmark.

Por isso, considerei essa parte alinhada com a proposta do meu TCC.

Entretanto, fiquei com uma dúvida sobre a latência.

O trabalho utiliza esse conceito, mas não compreendi exatamente como ele se diferencia do tempo de execução total ou do tempo de cada etapa do pipeline.

Essa é uma questão que gostaria de esclarecer durante nossa discussão.

## 7. Percepção sobre a comparação entre ETL e ELT

Durante a leitura, não identifiquei problemas evidentes na forma como Junka apresenta as diferenças entre ETL e ELT.

As explicações me pareceram coerentes, e não percebi inicialmente dificuldades importantes na comparação realizada.

Também não encontrei afirmações que contradissessem diretamente minhas expectativas ou os resultados iniciais do meu benchmark.

Minha impressão foi que o trabalho apresenta uma discussão conceitual consistente sobre as duas arquiteturas e suas possibilidades de otimização.

## 8. Relação com a metodologia do meu TCC

Em relação ao desenvolvimento experimental, não identifiquei muitas contribuições metodológicas diretas.

Não percebi discussões especialmente aprofundadas sobre:

- Variação de volumes de dados em experimentos comparativos.
- Controle de interferências externas.
- Isolamento de variáveis experimentais.
- Influência da rede nos resultados.
- Justificativas para utilização de fontes locais, como arquivos CSV.

Essas são questões importantes para o meu trabalho, mas não foram os aspectos que mais se destacaram na leitura de Junka.

Por outro lado, acredito que suas discussões sobre métricas e otimização possam ajudar na interpretação dos resultados do meu benchmark.

## 9. Importância para a fundamentação teórica

Considero que a principal contribuição potencial de Junka para meu TCC esteja na fundamentação teórica.

O trabalho apresenta explicações sobre ETL e ELT e aborda diferentes possibilidades de otimização.

Caso seja necessário desenvolver uma fundamentação teórica mais aprofundada, acredito que ele poderá ser uma referência útil para discutir:

- Funcionamento das arquiteturas.
- Diferenças entre ETL e ELT.
- Estratégias de otimização.
- Paralelismo e multithreading.
- Extração incremental.
- Métricas de desempenho.

Ainda preciso definir, junto ao orientador e considerando o modelo acadêmico adotado, qual será o nível de aprofundamento teórico necessário no artigo.

Essa decisão influenciará a importância de Junka na revisão bibliográfica.

## 10. Comparação com Bessa e Santos (2023) e Hübner (2020)

Considerando os três trabalhos que analisei até agora, percebo contribuições diferentes.

**Bessa e Santos (2023)**

É o trabalho mais próximo do meu em termos de objetivo, pois também realiza uma comparação experimental direta entre ETL e ELT.

Entretanto, meu experimento pretende utilizar dois datasets, controlar mais rigorosamente as variáveis e reduzir possíveis interferências externas.

**Hübner (2020)**

Apresenta uma fundamentação teórica bastante extensa e propõe uma terceira arquitetura, o ELTL.

Achei interessante sua discussão sobre diferentes soluções de processamento e armazenamento, especialmente a relação entre ETL, ELT e ELTL.

**Junka (2026)**

Apresenta uma perspectiva mais voltada aos conceitos e às estratégias de otimização.

Seu principal diferencial, na minha percepção, é discutir técnicas como paralelismo, multithreading e extração incremental.

Assim, considero que os três trabalhos podem contribuir de maneiras distintas para a construção do meu TCC.

## 11. Relevância de Junka para meu trabalho

Neste momento, considero Junka o menos importante dos três trabalhos como referência diretamente relacionada ao meu experimento.

Isso não significa que ele seja irrelevante.

Sua importância dependerá principalmente do nível de fundamentação teórica que será necessário desenvolver.

Se meu TCC exigir uma discussão conceitual mais aprofundada sobre ETL, ELT e suas estratégias de otimização, Junka poderá ser uma referência importante.

Por outro lado, se o foco permanecer predominantemente na comparação experimental, acredito que Bessa e Santos e Hübner ofereçam discussões mais diretamente aproveitáveis.

## 12. Impressão geral consolidada

Junka (2026) foi interessante principalmente por ampliar minha compreensão sobre possibilidades de otimização em pipelines de dados.

Apesar de apresentar conceitos que eu já conhecia, o trabalho mostrou técnicas e estratégias com as quais ainda tenho pouca familiaridade.

A extração incremental, o paralelismo e o multithreading foram os aspectos que mais chamaram minha atenção.

Em relação ao meu TCC, considero que sua principal contribuição poderá estar na fundamentação conceitual e na interpretação das métricas, mais do que no desenho experimental propriamente dito.

### Principais pontos que ficaram da leitura

- Junka apresenta conceitos conhecidos de ETL e ELT sob perspectivas interessantes.
- As estratégias de otimização foram o principal destaque.
- A extração incremental permite evitar a leitura repetida de dados já extraídos.
- Paralelismo e multithreading representam alternativas para melhorar o desempenho.
- Interpretei o ETL como mais adequado à disponibilização direta de dados tratados para usuários de negócio.
- Associei o ELT à preservação dos dados brutos e à rastreabilidade.
- O throughput está alinhado às métricas do meu benchmark.
- Ainda não compreendi completamente a diferença entre latência e tempo de execução.
- Não identifiquei contradições relevantes em relação aos trabalhos anteriores.
- O trabalho parece contribuir mais para a fundamentação teórica do que para o desenho experimental.
- Sua importância definitiva dependerá do nível de aprofundamento teórico exigido no meu TCC.

## 13. Dúvidas para a discussão posterior

1. Qual é exatamente a diferença entre latência, tempo de execução total e tempo de execução por etapa?
2. A associação entre ETL e disponibilização de dados preparados para consumo imediato está correta?
3. O ELT possui uma vantagem inerente de rastreabilidade ou isso depende de como os dados originais são armazenados?
4. As estratégias de paralelismo, multithreading e extração incremental podem ser aplicadas às duas arquiteturas?
5. Quais argumentos de Junka são mais úteis para interpretar resultados experimentais de ETL e ELT?
6. O trabalho deve ser utilizado principalmente como fundamentação conceitual ou possui contribuições metodológicas relevantes que não percebi?

---

**Estado do documento:** primeiras impressões registradas, sem incorporar correções ou conclusões posteriores.