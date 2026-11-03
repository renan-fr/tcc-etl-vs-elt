# Raasveldt et al. (2018) — Primeiras impressões

**Trabalho:** *Fair Benchmarking Considered Difficult: Common Pitfalls in Database Performance Testing*

**Ano:** 2018

**Finalidade:** registrar minhas primeiras interpretações sobre o artigo, preservando observações, hipóteses e percepções antes da discussão crítica.

---

## 1. Impressão inicial sobre os benchmarks de desempenho

Na introdução, os autores comentam como análises de desempenho são atrativas e podem parecer relativamente simples de realizar, especialmente porque trabalham com métricas aparentemente objetivas.

Entretanto, existem diversas armadilhas e vieses que precisam ser considerados.

Minha interpretação é que medir o tempo de execução de dois sistemas parece uma tarefa direta, mas isso não significa que a comparação seja necessariamente justa ou metodologicamente correta.

Esse aspecto chamou minha atenção porque meu TCC também realiza uma comparação de desempenho.

## 2. Benchmarketing e apresentação enviesada de resultados

Os autores mencionam o termo *benchmarketing*, relacionado ao uso de benchmarks com interesses comerciais ou promocionais.

Achei o termo interessante porque representa situações em que empresas podem utilizar comparações de desempenho para favorecer seus produtos em relação aos concorrentes.

Minha impressão é que existe uma preocupação importante dos autores com o uso de benchmarks para sustentar afirmações de superioridade que podem não representar adequadamente as condições reais de comparação.

## 3. Foco crítico do artigo

Percebi que o artigo dedica bastante atenção à crítica de publicações e comparações de desempenho que apresentam vieses.

Esse foco é um pouco diferente do meu TCC, que não pretende promover um sistema ou demonstrar a superioridade de um produto.

Por isso, acredito que devemos dar atenção especial às partes em que os autores discutem as armadilhas metodológicas dos benchmarks, independentemente de sua utilização comercial.

Essas partes parecem ser as mais relevantes para nossa pesquisa.

## 4. Reprodutibilidade dos experimentos

Um dos pontos importantes abordados foi a reprodutibilidade.

Os autores destacam a necessidade de documentar o ambiente e as condições de execução dos experimentos.

Minha interpretação é que um benchmark precisa apresentar informações suficientes para que suas condições possam ser compreendidas e, idealmente, reproduzidas.

Esse aspecto possui relação direta com meu TCC, pois estamos executando experimentos em um ambiente computacional específico.

## 5. Comparações entre sistemas novos e antigos

Outro ponto interessante foi a discussão sobre trabalhos que apresentam novos sistemas e realizam comparações com alternativas já existentes.

Nessas situações, o novo sistema costuma ser apresentado como superior em desempenho.

Entretanto, podem existir vieses associados à configuração dos sistemas comparados.

Minha interpretação foi que os responsáveis por um novo sistema podem não ter o mesmo interesse em otimizar uma solução concorrente ou mais antiga.

Consequentemente, o sistema utilizado como referência pode acabar apresentando desempenho inferior à sua capacidade real.

Isso pode acontecer por interesse em favorecer o novo sistema ou simplesmente pela ausência de esforço suficiente para configurar adequadamente a alternativa existente.

Esse ponto me fez perceber que a maneira como os sistemas são preparados antes dos testes pode influenciar a comparação.

## 6. Comparação de funcionalidades equivalentes — Apples vs. Oranges

Uma das seções que mais chamou minha atenção foi *Apples vs. Oranges*, ou Maçãs versus Laranjas.

Os autores discutem situações em que sistemas são comparados mesmo oferecendo funcionalidades diferentes.

Minha interpretação foi que uma comparação de desempenho precisa avaliar as mesmas funcionalidades em ambos os sistemas.

O artigo apresenta um exemplo envolvendo um sistema menor e especializado e outro maior, com funcionalidades adicionais.

Nesse cenário, o sistema maior pode realizar operações que o sistema menor não executa.

Por isso, acredito que uma comparação justa precisa delimitar claramente quais funcionalidades estão sendo avaliadas.

Esse cuidado parece particularmente importante para meu TCC, já que estamos comparando duas arquiteturas distintas.

## 7. Hot runs, cold runs e warm runs

Outro tópico interessante foi a distinção entre diferentes condições de execução dos benchmarks.

Os autores discutem as chamadas *hot runs* e *cold runs*.

Minha interpretação é que as condições de aquecimento dos sistemas podem influenciar os resultados das medições.

O artigo também menciona situações de *warm runs*, nas quais uma execução apresentada como fria pode não representar realmente uma condição de partida totalmente fria, especialmente quando o sistema não é reiniciado.

Esse ponto me chamou atenção porque já consideramos a questão do aquecimento no planejamento do meu benchmark.

Nosso experimento foi estruturado para utilizar aquecimento antes das execuções medidas, mantendo um procedimento padronizado.

Acredito que o artigo pode servir como referência para justificar essa decisão na metodologia.

Não pretendemos comparar diretamente execuções frias e aquecidas, mas considero importante reconhecer que essas condições podem afetar a interpretação de resultados.

## 8. Relação geral com meu TCC

Minha impressão é que o artigo está bastante direcionado a comparações entre sistemas novos e sistemas antigos, principalmente em situações nas quais se pretende demonstrar a superioridade de uma nova solução.

Essa abordagem difere do objetivo do meu TCC.

Nossa pesquisa compara duas arquiteturas de processamento, ETL e ELT, sem pressupor que uma seja uma versão mais avançada ou necessariamente superior à outra.

Entretanto, acredito que muitos dos cuidados metodológicos discutidos pelos autores podem ser aproveitados.

Especialmente:

- Documentação do ambiente experimental.
- Controle das condições de execução.
- Preparação e otimização dos sistemas comparados.
- Equivalência das funcionalidades avaliadas.
- Padronização das condições de aquecimento.
- Cuidado com possíveis vieses nas conclusões.

Minha percepção inicial é que o artigo pode contribuir mais diretamente para justificar e fortalecer nossas decisões metodológicas do que para a seção de Trabalhos Relacionados.

## 9. Avaliação preliminar

Considero o artigo relevante por apresentar cuidados que precisamos observar ao realizar comparações de desempenho.

Mesmo que seu contexto seja diferente do meu, as discussões sobre comparações injustas, preparação dos sistemas, reprodutibilidade e condições de execução parecem aplicáveis ao nosso experimento.

O principal valor que identifiquei está em **compreender como um benchmark pode produzir resultados aparentemente objetivos, mas metodologicamente enviesados**.

Acredito que o artigo pode ajudar a justificar algumas decisões que já adotamos no experimento e orientar futuras verificações de sua validade.

---

**Estado do documento:** primeiras impressões registradas. As interpretações ainda precisam ser confrontadas com o conteúdo original do artigo antes de serem utilizadas na redação acadêmica.