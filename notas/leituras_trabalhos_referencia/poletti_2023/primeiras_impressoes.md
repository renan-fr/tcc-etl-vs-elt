# Poletti (2023) — Primeiras impressões

**Trabalho:** Uma análise exploratória e prática do uso do ETL em portais de transparência  
**Autor:** Marcus Vinicius Santana Poletti  
**Ano:** 2023  
**Tipo:** Dissertação de mestrado

**Finalidade:** registrar as primeiras interpretações e observações sobre o trabalho, antes da discussão crítica.

---

## 1. Objetivo principal do trabalho

Pelo que compreendi, o principal objetivo de Poletti (2023) é comparar ferramentas específicas de ETL com implementações desenvolvidas diretamente em código Python.

O estudo está voltado ao processamento e tratamento de dados provenientes de portais de transparência.

A proposta é investigar como diferentes ferramentas e estratégias de implementação se comportam nesse contexto.

Esse objetivo é diferente do meu TCC, que busca comparar experimentalmente as arquiteturas ETL e ELT, e não diferentes ferramentas de uma mesma arquitetura.

## 2. Pesquisa com desenvolvedores

Um aspecto interessante foi a realização de uma pesquisa com três desenvolvedores formados, especializados na construção de processos ETL e com diferentes níveis de senioridade.

A pesquisa buscou compreender suas opiniões e experiências relacionadas às ferramentas utilizadas nesses processos.

Foram aplicadas perguntas de diferentes formatos:

- Perguntas objetivas.
- Perguntas descritivas.
- Questões relacionadas às ferramentas e à experiência dos desenvolvedores.

Achei interessante a inclusão dessa avaliação porque o trabalho não considera somente o desempenho computacional, mas também a percepção de profissionais que utilizam essas tecnologias.

## 3. Resultados experimentais do terceiro ciclo

Nos resultados do terceiro ciclo, identifiquei uma vantagem significativa do Python em relação às ferramentas Kettle e SSIS.

### Primeira comparação — PC1

| Ferramenta | Tempo médio |
|---|---:|
| Python | 9,98 segundos |
| Kettle | 29,47 segundos |
| SSIS | 41,96 segundos |

Nesse cenário, o Python apresentou o menor tempo médio de execução.

O Kettle ficou em segundo lugar, enquanto o SSIS apresentou o maior tempo.

### Segunda comparação — PC2

Na segunda comparação, o Python continuou apresentando o melhor desempenho temporal.

O restante da classificação também permaneceu igual:

1. Python.
2. Kettle.
3. SSIS.

Minha impressão foi que os resultados demonstraram uma vantagem consistente do Python nas avaliações apresentadas.

## 4. Escassez de estudos sobre o tema

Outro ponto que me chamou atenção foi a identificação de uma quantidade limitada de artigos relacionados ao uso de ETL em portais de transparência.

O autor destaca essa escassez e também aponta que a utilização de processos ETL nesse contexto está em expansão.

Considerei essa observação interessante porque demonstra uma preocupação em identificar lacunas na literatura e justificar a relevância do estudo.

Entretanto, essa lacuna está associada especificamente ao contexto dos portais de transparência, que não é o foco principal do meu TCC.

## 5. Percepção dos desenvolvedores sobre Python

Apesar dos melhores resultados temporais, o Python não recebeu a mesma aceitação das ferramentas especializadas de ETL entre os desenvolvedores participantes.

Pelo que entendi, um dos motivos apresentados foi a ausência de *steps* com funcionalidades previamente definidas, que poderiam facilitar e acelerar a construção dos processos.

As ferramentas Kettle e SSIS parecem oferecer recursos mais direcionados ao desenvolvimento de pipelines ETL.

Assim, embora o Python tenha demonstrado melhor desempenho temporal nos testes, os desenvolvedores manifestaram preferência pelas ferramentas especializadas.

### Dúvida sobre o conceito de steps

Ainda não compreendi completamente o significado de *steps* utilizado no trabalho.

Minha interpretação inicial é que seriam funcionalidades ou etapas previamente disponibilizadas pelas ferramentas, que facilitam a construção dos processos ETL sem exigir que todas as operações sejam desenvolvidas manualmente.

Esse conceito precisa ser esclarecido durante nossa discussão.

## 6. Diferença entre desempenho e preferência dos desenvolvedores

Um dos pontos mais interessantes do estudo foi perceber que a ferramenta mais rápida não foi necessariamente a preferida pelos participantes da pesquisa.

O Python apresentou melhores resultados de tempo, mas Kettle e SSIS foram melhor recebidos pelos desenvolvedores consultados.

Isso sugere que a escolha de uma ferramenta pode envolver outros critérios além do desempenho computacional.

Entre esses critérios, na minha interpretação, está a facilidade de desenvolver processos utilizando funcionalidades previamente disponíveis.

Achei essa diferença interessante, embora meu TCC não pretenda avaliar a preferência de desenvolvedores ou a facilidade de utilização das ferramentas.

## 7. Relação com meu TCC

O trabalho de Poletti possui algumas aproximações com meu TCC, mas também apresenta diferenças consideráveis.

A principal aproximação está na avaliação experimental do tempo de execução de processos de tratamento e integração de dados.

Além disso, o estudo utiliza Python, ferramenta que também faz parte do ambiente experimental do meu projeto.

Por outro lado, existem diferenças importantes:

- Poletti compara ferramentas e implementações ETL.
- Meu trabalho compara ETL e ELT.
- Poletti utiliza dados provenientes de portais de transparência.
- Meu experimento utiliza dados do ENEM e do TSE.
- Poletti considera a percepção de desenvolvedores.
- Meu trabalho prioriza métricas computacionais de desempenho.
- Poletti avalia principalmente diferenças de tempo entre ferramentas.
- Meu experimento pretende analisar tempo, CPU, RAM e throughput.

Portanto, embora exista proximidade temática, os objetos de comparação são diferentes.

## 8. Impressão geral sobre a relevância do trabalho

Minha impressão é que Poletti apresenta um estudo bastante direcionado ao uso de ETL em portais de transparência.

O trabalho dedica atenção à escassez de estudos nesse contexto e à comparação entre ferramentas especializadas e implementações Python.

Achei interessantes os resultados que mostram o Python com menor tempo médio, ao mesmo tempo que Kettle e SSIS receberam avaliações mais favoráveis dos desenvolvedores.

Entretanto, ainda não consegui identificar claramente como essas conclusões poderiam contribuir para o meu TCC.

A diferença entre comparar ferramentas ETL e comparar arquiteturas ETL e ELT me faz questionar se esse trabalho será uma referência suficientemente relevante.

### Pontos que mais chamaram minha atenção

- A comparação entre Python, Kettle e SSIS.
- A utilização de dados de portais de transparência.
- A pesquisa com três desenvolvedores de diferentes níveis de senioridade.
- A vantagem temporal do Python nos resultados do terceiro ciclo.
- A permanência do mesmo ranking de desempenho em PC1 e PC2.
- A identificação de poucos estudos sobre ETL em portais de transparência.
- A preferência dos desenvolvedores por ferramentas especializadas, apesar do melhor desempenho temporal do Python.
- A dúvida sobre o significado de *steps*.
- A dificuldade de identificar uma contribuição diretamente aproveitável no meu TCC.

## 9. Dúvidas para discussão posterior

1. O que exatamente são os *steps* mencionados pelo autor?
2. Quais condições experimentais foram utilizadas para comparar Python, Kettle e SSIS?
3. Os resultados permitem concluir que Python é mais eficiente em geral ou apenas nas implementações avaliadas?
4. Como interpretar a diferença entre desempenho temporal e preferência dos desenvolvedores?
5. Até que ponto os resultados obtidos com apenas três participantes permitem conclusões sobre preferência por ferramentas?
6. Existe alguma contribuição metodológica de Poletti que possa ser aproveitada no meu benchmark?
7. A dissertação é suficientemente relevante para integrar a seção de Trabalhos Relacionados ou seria melhor buscar um estudo mais próximo da comparação ETL × ELT?

---

**Estado do documento:** primeiras impressões registradas, aguardando discussão crítica e revisão.