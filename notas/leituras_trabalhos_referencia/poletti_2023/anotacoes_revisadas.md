# Poletti (2023) — Análises revisadas

**Trabalho:** *Uma análise exploratória e prática do uso do ETL em portais de transparência*

**Autor:** Marcus Vinicius Santana Poletti  
**Ano:** 2023  
**Tipo:** Dissertação de mestrado  
**Instituição:** Universidade Federal de Sergipe (UFS)

**Finalidade deste documento:** consolidar os principais aprendizados da leitura e discussão crítica, identificando as contribuições, limitações e relações do estudo com meu TCC de comparação experimental entre ETL e ELT.

---

## 1. Objetivo do trabalho

Poletti (2023) investiga a utilização de processos ETL no contexto de dados provenientes de portais de transparência.

O trabalho apresenta uma avaliação prática de diferentes ferramentas e estratégias de implementação, comparando processos desenvolvidos utilizando:

- Python;
- Pentaho Data Integration (Kettle);
- SQL Server Integration Services (SSIS).

O estudo também considera a percepção de profissionais envolvidos no desenvolvimento de processos ETL.

Seu objetivo está relacionado à avaliação da utilização dessas tecnologias em um domínio específico, considerando tanto o desempenho computacional quanto aspectos associados à construção dos processos.

**Principal distinção:** Poletti compara diferentes ferramentas de implementação ETL, enquanto meu TCC pretende comparar experimentalmente duas arquiteturas: ETL e ELT.

Essa diferença de objeto de estudo reduz a proximidade entre as pesquisas.

## 2. Estrutura metodológica

O estudo apresenta uma abordagem que combina avaliação experimental de desempenho com investigação da percepção de desenvolvedores.

Na dimensão experimental, são implementados processos ETL utilizando Python, Kettle e SSIS.

O autor avalia procedimentos de carga com características distintas, denominados PC1 e PC2.

Além disso, realiza uma pesquisa com três desenvolvedores com diferentes níveis de experiência profissional.

Essa combinação permite analisar tanto o comportamento temporal das implementações quanto a percepção dos participantes sobre sua utilização.

Entretanto, as duas dimensões da avaliação respondem a perguntas distintas:

- Os experimentos de desempenho investigam diferenças de tempo entre as implementações.
- As entrevistas investigam experiências e preferências dos participantes.

É importante não confundir evidências experimentais de desempenho com avaliações subjetivas relacionadas à facilidade de desenvolvimento.

## 3. Caracterização dos procedimentos de carga

Poletti utiliza dois procedimentos de carga:

**PC1:** caracterizado como mais complexo, envolvendo um conjunto maior de transformações.

**PC2:** caracterizado como mais simples, com processamento mais direto.

A classificação considera a avaliação dos desenvolvedores envolvidos.

Durante nossa discussão, identificamos que esse tipo de caracterização pode ajudar a diferenciar tarefas, mas não equivale necessariamente a uma definição objetiva e quantitativa de complexidade.

Para investigar experimentalmente os efeitos da complexidade, seria desejável estabelecer critérios operacionais explícitos.

### Relação com meu TCC

Inicialmente, meu experimento também considerava utilizar diferenças entre datasets para representar níveis de complexidade.

Entretanto, essa proposta foi posteriormente retirada do escopo experimental.

Atualmente, ENEM e TSE são tratados como conjuntos de dados com características distintas, sem afirmar que representam níveis controlados de complexidade.

Portanto, não precisamos reproduzir a classificação utilizada por Poletti.

**Aprendizado:** características de uma tarefa podem influenciar o desempenho, mas devem ser descritas com precisão para evitar interpretações que não sejam sustentadas pelo desenho experimental.

## 4. Resultados de desempenho

Nos experimentos apresentados, Python obteve os menores tempos médios entre as ferramentas avaliadas.

No terceiro ciclo, para o procedimento PC1, foram apresentados os seguintes resultados:

| Implementação | Tempo médio |
|---|---:|
| Python | 9,98 segundos |
| Kettle | 29,47 segundos |
| SSIS | 41,96 segundos |

No procedimento PC2, segundo a leitura realizada, a classificação permaneceu na mesma ordem, com Python apresentando o menor tempo médio, seguido por Kettle e SSIS.

Esses resultados indicam uma vantagem temporal das implementações Python nas condições experimentais avaliadas.

### Interpretação revisada

Inicialmente, os resultados chamaram atenção pela diferença significativa entre os tempos das ferramentas.

Após nossa discussão, reforçamos que não é adequado interpretar esses valores como demonstração de superioridade universal do Python.

O desempenho observado pode depender de fatores como:

- Estratégia de implementação.
- Bibliotecas utilizadas.
- Operações realizadas.
- Características dos dados.
- Configuração das ferramentas.
- Ambiente de execução.
- Procedimentos e critérios de medição.

Portanto, a conclusão mais defensável é que **as implementações Python avaliadas por Poletti apresentaram menor tempo médio de execução nos cenários analisados**.

Não é possível generalizar automaticamente esse resultado para qualquer implementação ETL desenvolvida em Python, Kettle ou SSIS.

## 5. Medição do processamento completo

Um aspecto metodológico identificado durante a revisão foi a consideração do processamento até o preenchimento das tabelas de destino.

Os testes envolvem as atividades necessárias à execução dos processos ETL, incluindo extração, transformação e carga.

O estudo também utiliza múltiplas execuções para calcular os tempos médios, incluindo dez repetições por ferramenta nos experimentos discutidos.

Essa característica apresenta alguma proximidade com meu TCC, pois também pretendo avaliar o tempo total de execução dos pipelines, além de medições específicas das etapas.

Entretanto, essa semelhança não é suficiente, isoladamente, para justificar a utilização do trabalho como referência principal.

A medição do tempo total é uma prática relativamente comum em avaliações de desempenho de processos de integração de dados.

## 6. Pesquisa com desenvolvedores

Poletti também realiza uma pesquisa envolvendo três desenvolvedores com diferentes níveis de experiência profissional.

A investigação utiliza perguntas objetivas e descritivas relacionadas às ferramentas de desenvolvimento ETL.

Um dos resultados que mais chamou atenção foi a diferença entre desempenho computacional e preferência dos participantes.

Embora Python tenha apresentado menores tempos nos experimentos, os participantes demonstraram preferência por ferramentas especializadas, como Kettle e SSIS.

Um dos motivos identificados está relacionado à disponibilidade de componentes prontos para a construção dos processos.

### 6.1. Significado de steps

Uma dúvida da primeira leitura estava relacionada ao significado de *steps*.

Durante nossa discussão, esclarecemos que, no contexto de ferramentas visuais de ETL, steps são componentes predefinidos que representam operações de processamento.

Esses componentes podem executar tarefas como:

- Leitura de arquivos.
- Seleção de colunas.
- Filtragem de registros.
- Junções entre tabelas.
- Aplicação de transformações.
- Gravação de dados.

Em ferramentas como Kettle, esses componentes podem ser configurados e conectados visualmente.

Isso reduz a necessidade de desenvolver manualmente todas as operações.

Em Python, operações equivalentes também podem ser realizadas por bibliotecas, mas frequentemente exigem maior construção e organização do código.

A existência de componentes predefinidos pode influenciar a experiência de desenvolvimento, embora não determine automaticamente o desempenho ou a qualidade da solução.

## 7. Limitações da avaliação com desenvolvedores

Durante nossa discussão, identificamos uma limitação importante: a pesquisa foi realizada com apenas três participantes.

Essa quantidade pode ser suficiente para uma investigação exploratória de percepções individuais, mas não permite generalizar os resultados para a população de desenvolvedores ETL.

Consequentemente, não seria adequado concluir que profissionais da área, em geral, preferem Kettle ou SSIS ao Python.

O estudo permite compreender as opiniões dos participantes e identificar possíveis fatores associados às suas preferências.

Entretanto, essas percepções não constituem evidência suficiente para estabelecer um padrão generalizável.

### Interpretação revisada

A conclusão deve permanecer restrita aos desenvolvedores consultados.

O resultado é interessante para discutir aspectos de usabilidade e produtividade de desenvolvimento, mas essa dimensão está fora do objetivo experimental do meu TCC.

Portanto, não será necessário aprofundá-la em nosso artigo.

## 8. Desempenho computacional versus facilidade de desenvolvimento

Uma contribuição conceitual identificada no trabalho é a distinção entre desempenho de execução e experiência de desenvolvimento.

Uma implementação pode executar determinada tarefa rapidamente, mas exigir maior esforço para ser construída ou mantida.

Da mesma forma, ferramentas com interfaces visuais e componentes predefinidos podem facilitar o desenvolvimento sem necessariamente apresentar os menores tempos de execução.

Essas características envolvem critérios distintos de avaliação.

Entretanto, meu TCC não pretende comparar produtividade de desenvolvimento, facilidade de manutenção ou preferência por ferramentas.

O foco permanece no desempenho computacional das implementações ETL e ELT.

Assim, embora a discussão seja relevante em outros contextos, não representa uma contribuição central para minha pesquisa.

## 9. Lacunas identificadas na literatura

Poletti destaca a escassez de estudos específicos sobre a utilização de ETL em portais de transparência.

Essa observação contribui para justificar a pesquisa desenvolvida pelo autor.

Entretanto, devemos ter cuidado ao relacioná-la ao meu TCC.

A escassez identificada está associada ao contexto específico de ETL aplicado a portais de transparência.

Ela não demonstra necessariamente a existência de uma lacuna geral na literatura sobre comparação experimental entre ETL e ELT.

Portanto, não seria adequado utilizar essa constatação como justificativa direta para meu problema de pesquisa.

**Aprendizado:** lacunas identificadas em trabalhos relacionados precisam ser interpretadas dentro do escopo em que foram investigadas.

## 10. Ameaças à validade e limites de generalização

Poletti reconhece limitações associadas à avaliação realizada, incluindo fatores relacionados aos participantes e às condições experimentais.

Essa preocupação é metodologicamente relevante.

Durante nossa discussão, destacamos que os resultados obtidos em determinado ambiente não devem ser automaticamente generalizados para todas as ferramentas ou aplicações.

O mesmo princípio será importante no meu TCC.

Entretanto, existem referências mais específicas sobre metodologia experimental e construção de benchmarks que podem fundamentar esse cuidado com maior profundidade.

Assim, embora Poletti apresente uma preocupação válida com a generalização, não precisamos utilizá-lo como principal referência para justificar o controle experimental do nosso benchmark.

## 11. Relação com meu TCC

Após a leitura e discussão, identificamos algumas semelhanças e diferenças entre os estudos.

| Aspecto | Poletti (2023) | Meu TCC |
|---|---|---|
| Objetivo | Avaliar ferramentas e implementações ETL | Comparar arquiteturas ETL e ELT |
| Implementações | Python, Kettle e SSIS | Python/Pandas e PostgreSQL |
| Dados | Portais de transparência | ENEM e TSE |
| Métricas centrais | Tempo de execução | Tempo, CPU, RAM e throughput |
| Comparação arquitetural | Não é o foco | É o objetivo principal |
| Avaliação de desenvolvedores | Sim | Não |
| Variação de tarefas | PC1 e PC2 | Dois datasets e diferentes volumes |
| Foco metodológico | Avaliação de ferramentas ETL em contexto aplicado | Comparação experimental sob condições controladas |

As principais proximidades estão no uso de Python, na medição temporal e na implementação de processos de integração de dados.

Entretanto, essas características não são suficientes para estabelecer uma relação metodológica especialmente forte entre os estudos.

## 12. Contribuições potencialmente aproveitáveis

Mesmo não sendo uma referência prioritária, Poletti apresenta alguns aspectos que podem ser aproveitados como conhecimento complementar.

**Avaliação do pipeline completo:** reforça a possibilidade de medir o processamento considerando as etapas necessárias para produzir o resultado final.

**Repetição dos experimentos:** exemplifica a utilização de múltiplas execuções para analisar tempos médios.

**Dependência da implementação:** demonstra que diferentes ferramentas podem apresentar desempenhos distintos em tarefas semelhantes.

**Limites de generalização:** reforça que resultados experimentais precisam ser interpretados dentro das condições avaliadas.

Entretanto, nenhum desses aspectos foi considerado suficientemente exclusivo ou diretamente relacionado ao objetivo do meu TCC para justificar sua inclusão prioritária.

Essas questões podem ser fundamentadas por artigos mais próximos de nossa pergunta de pesquisa.

## 13. Avaliação crítica da relevância

Este foi o principal ponto da nossa discussão.

Inicialmente, considerei Poletti potencialmente interessante por utilizar Python e realizar testes experimentais de desempenho.

Entretanto, conforme avançamos na análise, percebi que essas semelhanças eram relativamente superficiais.

O trabalho se concentra em uma pergunta diferente da minha.

Poletti busca avaliar ferramentas específicas para a construção de processos ETL em portais de transparência.

Meu TCC busca comparar o desempenho de duas arquiteturas distintas, utilizando conjuntos de dados e volumes diferentes sob condições comparáveis.

Além disso, parte importante da contribuição de Poletti está relacionada à percepção de desenvolvedores e à facilidade de construção dos processos.

Esses temas não fazem parte do escopo do meu experimento.

### Decisão consolidada

**Poletti (2023) não será priorizado como referência principal na seção de Trabalhos Relacionados.**

A dissertação poderá permanecer como leitura complementar, caso futuramente seja necessário recuperar alguma discussão específica sobre implementações ETL em Python ou avaliação experimental de ferramentas.

Essa decisão não representa uma avaliação negativa da qualidade acadêmica do estudo.

Ela decorre da ausência de uma conexão suficientemente forte com o objetivo do meu trabalho.

## 14. Principais aprendizados

A leitura e o debate permitiram consolidar os seguintes pontos:

1. Resultados favoráveis a uma ferramenta devem ser interpretados dentro das condições experimentais utilizadas.
2. Desempenho computacional e facilidade de desenvolvimento representam dimensões diferentes de avaliação.
3. A existência de componentes predefinidos pode facilitar o desenvolvimento de processos ETL.
4. Pesquisas exploratórias com poucos participantes não permitem generalizar preferências para toda uma população.
5. Classificações subjetivas de complexidade não substituem critérios objetivos quando a complexidade é tratada como variável experimental.
6. Lacunas identificadas na literatura precisam ser interpretadas dentro do contexto específico investigado.
7. A utilização de tecnologias semelhantes não garante que dois estudos possuam perguntas de pesquisa comparáveis.
8. Uma referência academicamente válida não precisa necessariamente integrar a bibliografia final se sua contribuição para o problema investigado for pequena.

## 15. Síntese final

Poletti (2023) apresenta uma investigação sobre o uso de processos ETL em portais de transparência, comparando implementações desenvolvidas em Python, Kettle e SSIS.

Nos experimentos analisados, Python apresentou menores tempos médios, enquanto as ferramentas especializadas receberam avaliações favoráveis dos desenvolvedores participantes.

Esses resultados mostram que o desempenho computacional e a experiência de desenvolvimento podem conduzir a avaliações diferentes de uma mesma tecnologia.

Entretanto, as conclusões devem permanecer vinculadas às condições experimentais e à amostra de profissionais consultados.

Em relação ao meu TCC, a principal limitação de relevância está na diferença entre os objetivos.

O estudo de Poletti avalia diferentes ferramentas dentro da arquitetura ETL, enquanto meu trabalho pretende comparar experimentalmente ETL e ELT.

Embora existam semelhanças técnicas e metodológicas, elas não estabelecem uma conexão suficientemente forte para justificar sua utilização como referência principal em uma bibliografia enxuta.

**Conclusão da análise:** Poletti permanece como referência complementar, mas não será incluído na seleção prioritária de Trabalhos Relacionados. A pesquisa bibliográfica deve continuar buscando estudos mais diretamente associados à comparação ETL × ELT ou à metodologia de benchmarks de desempenho.

---

**Estado:** leitura e discussão concluídas.

**Classificação:** referência complementar — não prioritária.

**Decisão para o TCC:** não incluir na bibliografia principal neste momento; reavaliar somente se surgir uma necessidade específica que justifique sua utilização.