# Karagiannis et al. (2013) — Primeiras impressões

**Trabalho:** *Scheduling Strategies for Efficient ETL Execution*

**Autores:** Karagiannis, Vassiliadis e Simitsis  
**Ano:** 2013  
**Tipo:** Artigo científico — Information Systems

**Finalidade:** registrar minhas primeiras percepções sobre o trabalho, incluindo as dificuldades iniciais, interpretações e ideias que surgiram durante a leitura guiada, antes da consolidação da análise crítica.

---

## 1. Primeira impressão sobre o trabalho

Inicialmente, tive bastante dificuldade para compreender o artigo.

O conteúdo apresentou conceitos e mecanismos de execução com os quais não tenho muita familiaridade, especialmente relacionados a escalonamento de operações e gerenciamento de memória.

Diferentemente de outros trabalhos que analisamos, não consegui realizar uma leitura independente suficientemente clara para construir minhas próprias anotações.

Por isso, optamos por uma discussão guiada, buscando compreender o problema central investigado pelos autores e identificar quais aspectos poderiam contribuir para meu TCC.

## 2. Entendimento inicial sobre o processamento de dados

Durante nossa discussão, comecei a compreender que as diferentes etapas de um pipeline podem produzir e consumir registros em velocidades distintas.

Um exemplo que me ajudou a entender o problema foi imaginar uma etapa de leitura que produz dados mais rapidamente do que a etapa de transformação consegue processá-los.

Nesse cenário, minha interpretação foi que **os registros começariam a se acumular na memória**, pois a quantidade de dados produzidos seria maior do que a quantidade processada.

Esse foi um dos primeiros aspectos do trabalho que consegui relacionar ao funcionamento de pipelines de dados.

## 3. Acúmulo de registros e consumo de memória

Minha primeira conclusão foi que, se uma etapa continuar produzindo registros sem considerar a capacidade da etapa seguinte, o consumo de memória pode aumentar significativamente.

Esse comportamento me chamou atenção porque eu ainda não tinha considerado o acúmulo de dados intermediários como um fator que poderia afetar o desempenho de um pipeline.

Passei a enxergar essa situação como uma possível explicação para diferenças no consumo de memória entre implementações.

Também considerei que o acúmulo de registros poderia estar relacionado a situações de lentidão no processamento.

Essa possibilidade me pareceu interessante para uma futura análise dos resultados do meu benchmark.

## 4. Diferentes estratégias de execução

Durante a discussão, compreendi que um pipeline pode ser organizado de maneiras diferentes.

Minha primeira interpretação foi distinguir duas formas principais de execução.

### 4.1. Execução sequencial

Uma possibilidade seria executar cada etapa completamente antes de iniciar a seguinte.

Nesse caso:

1. A leitura de todos os dados é concluída.
2. As transformações são executadas.
3. Os resultados são carregados no destino.

Essa organização faz com que uma etapa dependa da conclusão integral da anterior.

### 4.2. Execução simultânea ou em pipeline

Outra possibilidade seria permitir que as etapas trabalhassem de maneira simultânea.

Nesse cenário, enquanto alguns dados ainda estão sendo lidos, outros já podem estar sendo transformados e carregados.

Assim, leitura, transformação e carga podem ocorrer durante o mesmo intervalo de tempo, sem que seja necessário concluir todo o processamento de uma etapa para iniciar a seguinte.

Inicialmente, interpretei que essa diferença entre execução sequencial e simultânea era uma das principais formas de explicar as diferenças de desempenho investigadas no artigo.

## 5. Relação entre estratégia de execução e desempenho

Um dos pontos que consegui compreender foi que diferentes formas de organizar o processamento podem produzir resultados diferentes, mesmo quando estamos trabalhando com a mesma arquitetura ETL.

Minha interpretação foi que isso acontece porque as operações podem ser executadas e coordenadas de maneiras distintas.

Consequentemente, uma implementação pode utilizar os recursos computacionais de forma diferente de outra.

Essa percepção me ajudou a entender por que dois pipelines que realizam tarefas semelhantes podem apresentar tempos e consumos de memória diferentes.

## 6. Tempo de execução versus consumo de memória

Durante a discussão, analisamos a possibilidade de uma estratégia priorizar a redução do tempo total, enquanto outra procura limitar o consumo de memória.

Considerei perfeitamente possível que uma estratégia termine o processamento mais rapidamente, mas apresente maior consumo de memória.

Da mesma forma, outra estratégia pode consumir menos memória e exigir mais tempo para concluir o processamento.

A partir disso, concluí que **uma estratégia não pode ser considerada superior em todos os aspectos apenas porque apresenta menor tempo de execução**.

Essa observação se relaciona diretamente com meu TCC, pois pretendo avaliar diferentes dimensões de desempenho, e não somente o tempo total.

## 7. Importância das estratégias de execução

Durante nossa revisão, discutimos um cenário em que duas implementações utilizariam o mesmo pipeline ETL, os mesmos dados e o mesmo hardware, mas estratégias de execução diferentes.

Minha interpretação foi que essas estratégias são importantes porque podem impactar diretamente os resultados de desempenho.

Assim, mesmo que a arquitetura permaneça ETL, mudanças na organização interna das operações podem alterar o comportamento observado.

Esse foi um dos principais aprendizados que consegui extrair do trabalho.

## 8. Relação com as métricas do meu TCC

O trabalho chamou minha atenção principalmente pela relação entre tempo de execução e consumo de memória.

No meu benchmark, pretendo analisar:

- Tempo total e por etapas.
- Throughput.
- Uso de CPU.
- Consumo de memória RAM.

A discussão de Karagiannis trouxe uma perspectiva que eu ainda não tinha considerado: a possibilidade de diferenças de desempenho estarem associadas à forma como os dados intermediários são produzidos, armazenados e consumidos.

Inicialmente, enxerguei isso como um possível cuidado para a avaliação dos meus pipelines.

Entretanto, ainda não sei se os mecanismos descritos no artigo estão presentes nas minhas implementações ou se poderiam explicar os resultados que obtenho.

## 9. Limitações para explicar resultados experimentais

Durante nossa discussão, consideramos um exemplo em que um pipeline ETL apresentava menor tempo total, mas consumia mais memória do que um pipeline ELT.

Minha interpretação foi que essas métricas, isoladamente, não seriam suficientes para explicar o motivo da diferença.

Para afirmar que o consumo de memória foi provocado pelo acúmulo de dados intermediários, precisaríamos de informações adicionais sobre o funcionamento do processamento.

Por exemplo, seria necessário compreender se existe um desbalanceamento entre a velocidade de produção e de consumo dos registros pelas etapas.

Assim, percebi que observar uma diferença nas métricas não significa necessariamente conhecer sua causa.

## 10. Relação entre arquitetura e implementação

Outra reflexão importante surgiu quando relacionamos o artigo ao meu benchmark ETL versus ELT.

No meu experimento, ETL e ELT utilizam mecanismos diferentes de processamento.

Portanto, mesmo que o ETL apresente resultados melhores em determinadas métricas, não considero correto afirmar automaticamente que isso aconteceu exclusivamente por causa da arquitetura.

Minha interpretação foi que essa conclusão seria uma suposição sem evidência suficiente.

As decisões de implementação e as estratégias internas de execução também podem influenciar os resultados.

Essa questão me pareceu relevante para interpretar corretamente as diferenças observadas no meu experimento.

## 11. Contribuição percebida para meu TCC

Apesar da dificuldade inicial de leitura, passei a considerar que Karagiannis pode oferecer uma contribuição interessante para meu trabalho.

Antes dessa discussão, eu não conhecia suficientemente o problema do acúmulo de dados intermediários nem havia pensado nele como um possível fator de consumo de memória.

Também não tinha considerado com tanta clareza a influência das estratégias de execução sobre o desempenho.

Os principais aspectos que considero aproveitáveis são:

- A importância da organização interna das operações.
- A possibilidade de acúmulo de registros intermediários.
- A relação entre velocidade de produção e consumo dos dados.
- A influência das estratégias de execução sobre tempo e memória.
- A necessidade de interpretar diferentes métricas em conjunto.
- O cuidado para não atribuir automaticamente uma diferença de desempenho à arquitetura utilizada.

Essas questões podem contribuir tanto para minha compreensão sobre pipelines quanto para a interpretação posterior dos resultados do benchmark.

## 12. Diferenças em relação ao meu TCC

Karagiannis não realiza uma comparação direta entre ETL e ELT.

Seu estudo está concentrado nas estratégias utilizadas para executar operações dentro de processos ETL.

Já meu trabalho busca comparar experimentalmente duas arquiteturas, observando seu comportamento em diferentes conjuntos e volumes de dados.

Portanto, os objetos de investigação são diferentes.

Entretanto, identifiquei uma relação relevante: **a forma de implementar e executar um pipeline pode influenciar seu desempenho, independentemente da arquitetura escolhida**.

Essa perspectiva pode ajudar a estabelecer limites para as conclusões do meu experimento.

## 13. Impressão geral consolidada

Minha experiência com Karagiannis foi diferente das leituras anteriores.

Inicialmente, o artigo pareceu excessivamente técnico, e não consegui compreender sua metodologia de maneira independente.

A discussão guiada permitiu identificar uma questão que considero interessante: os mecanismos internos de execução podem modificar o comportamento de um pipeline, especialmente quanto ao tempo de processamento e ao consumo de memória.

O acúmulo de dados intermediários foi o aspecto que mais chamou minha atenção.

Também considerei importante perceber que estratégias diferentes podem favorecer métricas diferentes e que resultados de desempenho não revelam automaticamente suas causas.

Mesmo sem compreender detalhadamente os algoritmos apresentados pelos autores, passei a considerar que o artigo oferece uma perspectiva relevante para meu TCC.

### Principais pontos que ficaram da leitura

- O artigo foi tecnicamente difícil de compreender.
- Diferentes etapas podem produzir e consumir registros em velocidades distintas.
- O desbalanceamento entre essas velocidades pode provocar acúmulo de dados intermediários.
- Esse acúmulo pode aumentar o consumo de memória.
- Inicialmente, relacionei as estratégias de execução à diferença entre processamento sequencial e simultâneo.
- Diferentes estratégias podem produzir tempos e consumos de memória distintos.
- Uma estratégia mais rápida não é necessariamente superior em todas as métricas.
- A organização interna das operações pode influenciar o desempenho mesmo quando a arquitetura não muda.
- Diferenças de desempenho observadas no benchmark não permitem identificar automaticamente suas causas.
- Karagiannis pode contribuir para compreender fatores internos que influenciam o processamento.

## 14. Dúvidas que permaneceram

1. Como funcionam exatamente as políticas de escalonamento propostas pelos autores?
2. Qual é a diferença entre executar operações simultaneamente e utilizar diferentes políticas de escalonamento?
3. Como os autores medem o consumo de memória durante os experimentos?
4. O acúmulo de dados intermediários pode ocorrer nas implementações Python/Pandas e PostgreSQL do meu TCC?
5. Até que ponto o estudo pode ajudar a explicar diferenças de desempenho entre ETL e ELT?
6. Quais resultados específicos de Karagiannis são mais relevantes para nossa análise experimental?

---

**Estado do documento:** primeiras impressões registradas a partir da leitura guiada e das interpretações iniciais, preservando dúvidas e hipóteses anteriores à consolidação da versão revisada.