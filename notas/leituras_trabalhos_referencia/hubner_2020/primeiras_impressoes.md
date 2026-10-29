# Hübner (2020) — Primeiras impressões

**Trabalho:** Big data sob a ótica de modelagem de dados multidimensional para soluções de business intelligence

**Autor:** Alexandre Tomás Hübner  
**Ano:** 2020  
**Tipo:** Registro inicial de leitura, anterior à discussão crítica.

---

## 1. Objetivo do trabalho e proposta do ELTL

O trabalho de Hübner (2020) apresenta uma terceira abordagem de processamento de dados, denominada ELTL, que combina características do ETL e do ELT.

Pelo que compreendi, a proposta procura aproveitar vantagens das duas arquiteturas:

- **ELT:** preservação dos dados brutos, permitindo manter a rastreabilidade e uma fonte de verdade dos dados originais.
- **ETL:** aplicação de transformações que garantem maior qualidade e consistência aos dados disponibilizados.
- **ELTL:** combinação dessas características em uma arquitetura que preserva os dados originais e disponibiliza informações tratadas para utilização.

Achei interessante a possibilidade de manter os dados brutos armazenados e, ao mesmo tempo, disponibilizar informações transformadas e preparadas para análise.

## 2. Funcionamento e arquitetura do ELTL

Pelo que entendi, o processo utiliza um Data Lake para armazenar os dados brutos, preservando as informações originais.

Posteriormente, esses dados passam por transformações e são disponibilizados em um Data Warehouse, já preparados para utilização.

O processo seria, de forma simplificada:

1. Extração dos dados da origem.
2. Armazenamento dos dados brutos em um Data Lake.
3. Aplicação das transformações necessárias.
4. Carregamento dos dados tratados em um Data Warehouse.
5. Disponibilização das informações para as áreas de negócio.

Essa arquitetura parece interessante porque combina a preservação dos dados originais com a entrega de dados tratados e estruturados.

## 3. Resultados apresentados pelo autor

Nos resultados que analisei, o ELTL apresentou vantagens diferentes em relação às outras duas abordagens.

Minha interpretação foi que:

- O ELTL apresentou melhor desempenho de tempo de execução em comparação ao ETL.
- O ELTL apresentou melhor qualidade dos dados em comparação ao ELT.
- O ETL apresentou desempenho temporal inferior ao ELTL no experimento.
- O ELT apresentou mais problemas relacionados à qualidade e consistência dos dados.

Assim, o ELTL parece funcionar como uma alternativa que busca equilibrar desempenho e qualidade.

Inicialmente, tive dúvidas sobre o motivo desses resultados, principalmente sobre o desempenho inferior do ETL. Entretanto, ao observar os resultados apresentados, entendi que as conclusões do autor parecem coerentes com as medições realizadas.

## 4. Diferença entre os resultados do trabalho e do meu benchmark

Uma das observações mais interessantes foi a diferença entre os resultados de Hübner e os resultados iniciais do meu experimento.

No trabalho de Hübner, o ETL apresentou desempenho temporal inferior ao ELTL.

Já no meu benchmark, pelo que lembro dos resultados iniciais, o ETL apresentou melhor desempenho em diversas métricas, incluindo o tempo de execução.

Isso chamou minha atenção porque mostra que diferentes implementações e cenários experimentais podem apresentar resultados distintos.

Ainda não compreendi exatamente por que o ETL apresentou desempenho inferior no experimento de Hübner.

Essa é uma questão que considero interessante investigar durante a discussão do trabalho.

## 5. Métricas utilizadas

Minha impressão foi que o trabalho utiliza o tempo de execução como principal métrica de desempenho.

Além disso, apresenta uma análise relacionada à qualidade dos dados resultantes dos processos.

Isso permite avaliar as arquiteturas considerando duas perspectivas:

- desempenho temporal;
- qualidade e consistência dos dados.

No meu TCC, a proposta é diferente, pois pretendo comparar ETL e ELT utilizando outras métricas de desempenho:

- tempo de execução;
- consumo de CPU;
- consumo de memória RAM;
- throughput.

A qualidade dos dados não é o foco principal da minha avaliação, embora seja importante garantir que ambos os pipelines produzam resultados equivalentes.

## 6. Percepção sobre a justiça da comparação

Pelo que consegui compreender, a comparação entre ETL, ELT e ELTL parece justa.

Os resultados apresentados parecem sustentar as principais conclusões do autor sobre desempenho e qualidade.

Entretanto, essa é uma impressão inicial. Não consegui identificar completamente quais características da implementação explicam as diferenças observadas.

Principalmente no caso do tempo de execução, ainda tenho dúvidas sobre o motivo de o ETL ter apresentado resultados inferiores.

## 7. Aplicação prática e modelo self-service

Outro ponto que achei bastante interessante foi a aplicação do ELTL em ambientes de Business Intelligence.

O trabalho aborda a possibilidade de disponibilizar informações para utilização direta pelas áreas de negócio, dentro de uma proposta de self-service BI.

Pelo que compreendi, a ideia é permitir que usuários dessas áreas consultem e utilizem dados preparados sem depender constantemente de profissionais com conhecimento técnico mais aprofundado.

Nesse cenário, a utilização de um Data Warehouse com informações previamente tratadas facilita o consumo e a análise dos dados.

Essa aplicação prática me chamou atenção porque demonstra que o autor não se preocupa somente com desempenho, mas também com a forma como os dados serão utilizados dentro de uma organização.

## 8. Diferenças em relação ao meu TCC

Embora Hübner também investigue arquiteturas de processamento de dados, considero que o objetivo do trabalho dele é diferente do meu.

Hübner procura propor e avaliar uma terceira abordagem, o ELTL, demonstrando seu funcionamento, suas características e suas possíveis vantagens.

No meu TCC, não pretendo desenvolver uma nova arquitetura.

O objetivo é realizar uma comparação experimental entre duas arquiteturas já existentes: ETL e ELT.

As principais diferenças que identifiquei são:

- Hübner compara três abordagens; meu trabalho compara duas.
- Hübner dedica grande atenção à proposta e ao funcionamento do ELTL.
- Meu trabalho será direcionado à avaliação experimental de desempenho.
- Hübner considera aspectos relacionados à qualidade dos dados e à aplicação em Business Intelligence.
- Meu trabalho pretende avaliar tempo, CPU, RAM e throughput.
- Meu trabalho também utilizará diferentes volumes e datasets para observar mudanças no comportamento das arquiteturas.

Assim, os dois trabalhos possuem uma proximidade temática, mas abordam problemas de pesquisa diferentes.

## 9. Meu objetivo não é identificar um vencedor universal

Uma reflexão que tive durante a leitura é que meu TCC não precisa necessariamente determinar qual arquitetura é superior em todas as situações.

A proposta é compreender o comportamento de ETL e ELT em diferentes condições experimentais.

Por exemplo, pode acontecer de:

- ETL apresentar melhor desempenho em determinado volume;
- ELT apresentar vantagens em outra situação;
- uma arquitetura ser mais rápida, mas consumir mais memória;
- o desempenho relativo das arquiteturas mudar conforme as características dos dados.

Dessa forma, quero que o estudo ajude a entender **em quais situações cada abordagem pode apresentar vantagens**, em vez de estabelecer uma classificação universal de superioridade.

## 10. Impressão geral

Achei o trabalho interessante principalmente pela proposta de combinar vantagens de ETL e ELT em uma terceira arquitetura.

A preservação dos dados brutos em um Data Lake, associada à transformação e disponibilização de informações em um Data Warehouse, parece uma solução prática interessante.

Também achei relevante a preocupação com a utilização dos dados pelas áreas de negócio, especialmente dentro da proposta de self-service BI.

Em relação ao meu TCC, o trabalho contribui mais como uma referência sobre alternativas arquiteturais, avaliação de desempenho e aplicação prática de pipelines do que como um modelo experimental diretamente equivalente.

### Principais pontos que ficaram da leitura

- O ELTL busca combinar características de ETL e ELT.
- A preservação dos dados brutos permite manter rastreabilidade e acesso à informação original.
- A transformação dos dados busca garantir maior qualidade e consistência.
- O ELTL apresentou vantagens de desempenho em relação ao ETL e de qualidade em relação ao ELT, segundo minha interpretação dos resultados.
- Ainda não compreendi exatamente as causas do desempenho temporal inferior do ETL.
- Os resultados diferem do comportamento inicial observado no meu benchmark.
- A arquitetura proposta tem uma aplicação interessante em Business Intelligence e self-service BI.
- O trabalho de Hübner está mais direcionado à proposta de uma terceira arquitetura, enquanto o meu busca comparar experimentalmente ETL e ELT.
- Meu objetivo é compreender o comportamento das duas arquiteturas sob diferentes condições, não necessariamente eleger uma vencedora universal.

## 11. Dúvidas para a discussão posterior

1. Por que o ETL apresentou desempenho temporal inferior ao ELTL no experimento?
2. A comparação entre as três arquiteturas foi realmente conduzida sob condições equivalentes?
3. Como o autor avaliou a qualidade dos dados e quais evidências sustentam a superioridade do ELTL nesse aspecto?
4. Até que ponto as diferenças observadas são consequência das arquiteturas, e não das ferramentas ou implementações utilizadas?
5. Quais resultados desse estudo podem ser relacionados diretamente ao meu TCC, considerando as diferenças entre os objetivos experimentais?

---

**Estado do documento:** primeiras impressões registradas, sem incorporar as correções e conclusões da discussão posterior.