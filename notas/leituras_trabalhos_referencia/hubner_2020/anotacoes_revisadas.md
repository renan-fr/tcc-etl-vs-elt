# Hübner (2020) — Versão revisada

**Trabalho:** *Big data sob a ótica de modelagem de dados multidimensional para soluções de business intelligence*

**Autor:** Alexandre Tomás Hübner  
**Instituição:** Universidade de Caxias do Sul (UCS)  
**Ano:** 2020  
**Tipo:** Trabalho de Conclusão de Curso

**Finalidade deste documento:** consolidar a interpretação crítica do estudo, destacando seus resultados, suas particularidades metodológicas e sua relação com o TCC de comparação experimental entre ETL e ELT.

---

## 1. Objetivo do trabalho

Hübner (2020) propõe uma abordagem denominada ELTL (*Extract, Load, Transform, Load*), buscando combinar características dos processos ETL e ELT.

A proposta está associada à integração entre soluções de Big Data e Business Intelligence.

O objetivo principal não é determinar qual das arquiteturas ETL e ELT apresenta o melhor desempenho em condições experimentais estritamente equivalentes.

O autor pretende desenvolver e avaliar uma alternativa arquitetural capaz de combinar características consideradas vantajosas das duas abordagens, verificando sua aplicabilidade em um contexto de disponibilização de informações para análise.

**Distinção importante:** o objetivo de Hübner é diferente do objetivo do meu TCC. Essa diferença precisa orientar qualquer avaliação crítica da metodologia empregada.

## 2. Funcionamento e proposta do ELTL

A arquitetura ELTL acrescenta uma segunda etapa de carga ao fluxo tradicional de ELT.

Em termos simplificados:

- Os dados são extraídos da fonte.
- Os dados são carregados em um ambiente destinado ao armazenamento de informações próximas da origem.
- São realizadas transformações para organizar os dados.
- Os resultados transformados são carregados em estruturas adequadas ao consumo analítico.

A proposta busca conciliar duas necessidades:

**Preservação dos dados originais:** manter informações próximas da fonte, oferecendo possibilidades de rastreabilidade e reutilização.

**Disponibilização de dados preparados:** organizar as informações em estruturas mais adequadas a aplicações de BI e análises pelas áreas de negócio.

O ELTL constitui, portanto, uma proposta de integração entre diferentes necessidades de armazenamento e consumo de dados.

Entretanto, preservar dados brutos e produzir modelos dimensionais não são capacidades exclusivas do ELTL. Arquiteturas ETL ou ELT também podem atender a esses requisitos, dependendo de como forem implementadas.

## 3. Desenho da avaliação experimental

O trabalho implementa três soluções:

- ETL, utilizando tecnologias relacionadas ao processamento e armazenamento relacional;
- ELT, utilizando tecnologias do ecossistema Hadoop;
- ELTL, combinando etapas de armazenamento e transformação para disponibilizar um modelo analítico.

As soluções são avaliadas por meio de testes envolvendo tempo de execução, integridade dos dados e características qualitativas dos modelos resultantes.

Uma observação importante é que as implementações não diferem exclusivamente pela ordem das operações.

Elas também apresentam diferenças relacionadas a:

- tecnologias utilizadas;
- ambientes de execução;
- operações realizadas;
- estruturas produzidas;
- finalidade dos dados disponibilizados.

Dessa forma, o experimento oferece evidências sobre o comportamento das soluções específicas implementadas, mas não isola completamente o efeito da ordem entre transformação e carga.

## 4. Resultados de desempenho temporal

O autor apresenta resultados temporais para as três abordagens.

Na terceira execução completa, foram registrados:

| Arquitetura | Tempo |
|---|---:|
| ELT | 32 minutos |
| ELTL | 127 minutos |
| ETL | 190 minutos |

Nos cenários avaliados, o ELT apresentou o menor tempo, seguido pelo ELTL e pelo ETL.

O autor utiliza esses resultados para sustentar que o ELTL possui vantagem de desempenho em relação ao ETL.

Entretanto, os tempos devem ser interpretados considerando as diferenças entre as operações executadas.

A implementação ELT não realiza todas as etapas necessárias para produzir o mesmo modelo dimensional disponibilizado pelas implementações ETL e ELTL.

Assim, a comparação temporal não representa necessariamente três alternativas realizando o mesmo trabalho até um produto final equivalente.

### Interpretação revisada

É adequado afirmar que o ELT apresentou o menor tempo entre as implementações avaliadas.

Porém, não é adequado concluir que a arquitetura ELT seria necessariamente mais rápida caso todas as abordagens precisassem entregar o mesmo resultado analítico.

Essa hipótese exigiria outro desenho experimental.

## 5. Comparabilidade dos produtos finais

Este foi um dos principais pontos identificados durante nossa discussão.

Inicialmente, interpretei os resultados como uma comparação direta entre três arquiteturas capazes de entregar informações equivalentes.

Após analisar as diferenças entre as implementações, percebi que os produtos finais não possuem necessariamente o mesmo nível de preparação para consumo analítico.

No experimento:

- ETL disponibiliza um modelo dimensional;
- ELT disponibiliza estruturas e consultas mais próximas dos dados de origem;
- ELTL preserva o ambiente de dados originais e também disponibiliza um modelo dimensional.

Consequentemente, parte da diferença de tempo pode estar relacionada às atividades necessárias para produzir cada resultado.

### Principal aprendizado

Para uma comparação experimental cujo objetivo seja avaliar desempenho entre arquiteturas, é importante estabelecer previamente o resultado esperado e garantir sua equivalência.

Isso não significa exigir que os pipelines executem exatamente as mesmas operações intermediárias.

Significa que ambos precisam atender aos mesmos requisitos funcionais.

No meu TCC, a pergunta experimental é essencialmente:

**Diante de uma mesma entrada e de um mesmo resultado esperado, como ETL e ELT se comportam em termos de desempenho?**

Essa é uma diferença fundamental em relação ao estudo de Hübner.

## 6. Qualidade dos dados versus qualidade da modelagem

Uma interpretação equivocada da primeira leitura foi associar a menor qualidade atribuída ao ELT a possíveis erros, duplicações ou inconsistências nos dados.

Após a discussão, percebemos que o conceito de qualidade utilizado pelo autor está principalmente associado à organização e à apresentação do modelo de dados.

O autor destaca características como:

- clareza na nomenclatura dos campos;
- facilidade de interpretação;
- organização das entidades;
- utilização de estruturas dimensionais;
- adequação ao consumo pelas áreas de negócio.

Essas características são diferentes de medidas de qualidade dos valores, como precisão, completude, ausência de duplicatas e integridade.

O estudo também realiza verificações de integridade, incluindo comparações de quantidades de registros e valores agregados.

Portanto, não seria correto afirmar que o ELT apresentou menor qualidade porque produziu mais valores incorretos.

### Interpretação revisada

O ELT implementado por Hübner recebeu avaliação qualitativa inferior principalmente devido às características do modelo disponibilizado para análise.

Isso não significa que a arquitetura ELT seja incapaz de entregar modelos com qualidade equivalente àqueles produzidos por ETL ou ELTL.

## 7. Modelagem como decisão de implementação

Durante nossa discussão surgiu uma crítica metodológica relevante.

A organização em fatos e dimensões, a nomenclatura dos atributos e os relacionamentos entre tabelas são características que podem ser definidas durante o desenvolvimento de qualquer uma das arquiteturas.

Não existe uma exigência arquitetural que impeça o ELT de produzir um Data Warehouse dimensional.

Consequentemente, a menor adequação do modelo ELT implementado no experimento não demonstra uma limitação inerente dessa abordagem.

Essa diferença pode estar relacionada às decisões adotadas para representar cada solução.

**É importante, entretanto, não classificar automaticamente essa decisão como erro ou viés intencional.**

Como Hübner busca demonstrar a viabilidade de combinar características de Big Data e Business Intelligence, a adoção de estruturas diferentes está relacionada ao próprio escopo do estudo.

A crítica é mais adequada quando direcionada à generalização dos resultados, e não à legitimidade da proposta.

## 8. Diferença entre comparar soluções e comparar arquiteturas

Esta foi a distinção mais importante alcançada durante a leitura.

Existem duas perguntas experimentais diferentes.

**Comparação de soluções implementadas:**

Como diferentes soluções de processamento e disponibilização de dados se comportam em seus respectivos contextos de utilização?

**Comparação controlada de arquiteturas:**

Como ETL e ELT se comportam quando precisam processar a mesma entrada e produzir resultados equivalentes, mantendo as demais condições tão controladas quanto possível?

O trabalho de Hübner está mais próximo da primeira pergunta.

Meu TCC busca responder à segunda.

Nenhuma das duas perguntas é necessariamente superior à outra. Elas possuem finalidades distintas.

Por isso, seria inadequado exigir que Hübner adotasse exatamente o mesmo isolamento de variáveis que pretendo utilizar no meu experimento.

Entretanto, essa diferença de objetivos limita comparações diretas entre os resultados dos dois estudos.

## 9. Relação entre ETL, ELT, Data Lake e Data Warehouse

Outra interpretação que precisou ser revisada foi a associação direta entre:

- ETL e Data Warehouse;
- ELT e Data Lake ou Big Data.

Essas associações representam configurações frequentes e estão presentes no cenário desenvolvido por Hübner.

Porém, não constituem definições obrigatórias das arquiteturas.

Um processo ELT também pode produzir um Data Warehouse dimensional e disponibilizar dados preparados para análises de negócio.

Da mesma forma, ETL pode ser empregado em diferentes ambientes tecnológicos.

O que define ETL e ELT é essencialmente a sequência entre extração, transformação e carga, e não a plataforma de armazenamento utilizada.

Portanto, é necessário evitar tratar diferenças entre Data Lake e Data Warehouse como se fossem automaticamente diferenças entre ETL e ELT.

## 10. Diferenças em relação ao meu TCC

O estudo de Hübner e meu TCC compartilham o interesse por arquiteturas de processamento de dados.

Entretanto, seus objetivos e desenhos experimentais são distintos.

| Aspecto | Hübner (2020) | Meu TCC |
|---|---|---|
| Objetivo | Propor e avaliar o ELTL | Comparar experimentalmente ETL e ELT |
| Abordagens | ETL, ELT e ELTL | ETL e ELT |
| Foco | Integração de Big Data e BI | Desempenho de pipelines |
| Tecnologias | Ecossistemas SQL e Hadoop | Python/Pandas e PostgreSQL |
| Métricas | Tempo, integridade e avaliação qualitativa | Tempo, CPU, RAM e throughput |
| Produto final | Estruturas distintas conforme a solução | Resultado equivalente entre os pipelines |
| Controle experimental | Avaliação de diferentes soluções implementadas | Busca de maior isolamento das variáveis |
| Dados | Cenário específico de dados empresariais | ENEM e TSE |

A principal diferença não está apenas na quantidade de arquiteturas avaliadas, mas na pergunta de pesquisa.

Enquanto Hübner investiga a aplicabilidade de uma solução alternativa, meu trabalho busca observar o desempenho relativo de ETL e ELT sob condições experimentais comparáveis.

## 11. Principais aprendizados para o meu TCC

A leitura trouxe contribuições metodológicas importantes.

### 11.1. Equivalência dos resultados finais

Para atribuir diferenças de desempenho aos pipelines comparados, ambos devem atender aos mesmos requisitos de saída.

Essa equivalência reduz o risco de que uma abordagem pareça mais rápida simplesmente por realizar menos atividades necessárias ao resultado esperado.

### 11.2. Separação entre arquitetura e implementação

Resultados observados em determinada implementação não devem ser automaticamente atribuídos a características universais da arquitetura.

Ferramentas, ambientes, estruturas e estratégias de processamento podem influenciar os resultados.

### 11.3. Interpretação contextualizada do desempenho

Uma arquitetura apresentar menor tempo de execução em determinado estudo não significa necessariamente que ela apresentará o mesmo comportamento em outro experimento.

Diferenças de carga de trabalho, ferramentas e requisitos de saída podem produzir comportamentos distintos.

### 11.4. Importância da integridade dos resultados

O estudo também chama atenção para a necessidade de verificar os resultados produzidos pelos pipelines.

Comparar somente tempos de execução, sem assegurar a coerência dos resultados, pode comprometer a interpretação experimental.

### 11.5. Limites das conclusões

As conclusões precisam estar relacionadas ao que foi efetivamente implementado, medido e avaliado.

É importante diferenciar:

- resultados observados;
- interpretações sobre os resultados;
- hipóteses explicativas;
- conclusões que podem ser generalizadas.

## 12. Pontos que não serão incorporados ao escopo experimental

Apesar de sua relevância, alguns aspectos do estudo de Hübner não serão aprofundados no meu TCC.

Entre eles:

- desenvolvimento de uma arquitetura ELTL;
- comparação de modelos de BI e Big Data como soluções organizacionais;
- avaliação qualitativa aprofundada da usabilidade dos modelos;
- comparação entre ecossistemas SQL e Hadoop;
- análise de ferramentas para self-service BI.

Esses temas extrapolam o objetivo experimental estabelecido.

O ELTL poderá ser mencionado como uma alternativa arquitetural, caso seja relevante para a contextualização, mas não constituirá o foco da pesquisa.

## 13. Possíveis contribuições para a seção de trabalhos relacionados

Hübner (2020) pode ser utilizado para contextualizar abordagens que combinam diferentes estratégias de integração de dados.

O trabalho também permite demonstrar que estudos relacionados a ETL e ELT podem possuir objetivos bastante diferentes.

Na revisão bibliográfica, sua contribuição pode ser apresentada de maneira breve, destacando:

- a proposta do ELTL;
- a comparação realizada entre as três soluções;
- os resultados temporais observados;
- a avaliação qualitativa da modelagem;
- a diferença entre o objetivo do autor e o objetivo experimental do meu TCC.

Não será necessário reproduzir extensamente a fundamentação teórica sobre Big Data, Data Warehouse e Business Intelligence.

O mais relevante será explicar por que o estudo é relacionado ao meu trabalho, mas não diretamente equivalente a ele.

## 14. Síntese final

Hübner (2020) apresenta uma proposta de integração entre características associadas a ETL e ELT por meio de uma terceira arquitetura, denominada ELTL.

Os resultados experimentais indicam que, nas implementações avaliadas, o ELT apresentou o menor tempo de execução, enquanto o ELTL apresentou vantagem temporal sobre o ETL e disponibilizou um modelo analítico considerado qualitativamente equivalente ao ETL.

A leitura inicial levou à interpretação de que o ELT produzia dados de menor qualidade e que o ELTL seria arquiteturalmente superior.

Após a discussão, essa interpretação foi refinada.

A avaliação qualitativa está principalmente relacionada à modelagem e à facilidade de consumo analítico, e não à identificação de erros nos valores processados.

Além disso, as soluções comparadas possuem diferenças de tecnologia, operações e estruturas de saída, o que limita conclusões sobre superioridade inerente entre arquiteturas.

Isso não invalida o trabalho de Hübner, pois seu objetivo principal é propor e demonstrar a aplicabilidade de uma solução alternativa.

**O principal aprendizado para meu TCC é a importância de distinguir a comparação entre soluções com finalidades diferentes de uma comparação experimental controlada entre arquiteturas que devem entregar resultados equivalentes.**

Essa distinção reforça a necessidade de controlar variáveis, definir requisitos funcionais comuns e interpretar os resultados de desempenho dentro das condições efetivamente avaliadas.

---

## 15. Observações para a revisão posterior dos benchmarks

As seguintes observações surgiram durante a análise e devem ser retomadas somente quando a revisão dos trabalhos relacionados e a implementação dos benchmarks estiverem concluídas.

- Verificar se os pipelines ETL e ELT produzem resultados finais equivalentes.
- Confirmar se todas as operações necessárias para atingir o resultado esperado estão contempladas nas medições de tempo.
- Identificar diferenças de implementação que possam influenciar o desempenho além da ordem entre transformação e carga.
- Validar a integridade dos resultados antes de comparar as métricas.
- Evitar atribuir diferenças exclusivamente à arquitetura quando houver outros fatores relevantes.
- Restringir as conclusões aos cenários e às tecnologias efetivamente avaliados.

Esses pontos não representam mudanças imediatas nos scripts, mas critérios para uma futura revisão metodológica conjunta entre literatura e implementação.

**Estado:** discussão concluída e versão revisada consolidada.