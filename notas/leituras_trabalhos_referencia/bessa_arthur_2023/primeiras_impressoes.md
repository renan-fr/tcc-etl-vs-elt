# Bessa e Santos (2023) — Primeiras impressões

## 1. Proximidade com o meu trabalho

O trabalho de Bessa e Santos (2023) tem uma fundamentação bastante próxima do que estou propondo no meu TCC, principalmente porque também trabalha com a comparação entre ETL e ELT.

Apesar dessa proximidade no objetivo, a metodologia utilizada por eles é consideravelmente diferente da que estou planejando.

---

## 2. Uso de apenas uma base de dados

O trabalho utiliza somente uma base de dados, o AdventureWorks.

Com isso, não existe uma comparação entre datasets com diferentes níveis de complexidade.

Esse é um ponto de diferença importante em relação ao meu trabalho, porque pretendo utilizar duas bases diferentes:

- ENEM, como uma base mais simples;
- TSE, como uma base mais complexa.

A utilização de duas bases pode permitir observar se o comportamento de ETL e ELT muda dependendo das características ou da complexidade dos dados.

---

## 3. Diferença na origem dos dados

Outra diferença importante está na forma como os dados são obtidos.

No meu trabalho, a ideia atual é utilizar arquivos CSV como dados brutos e realizar os processos a partir desses arquivos.

No trabalho de Bessa e Santos, os dados estão em um SQL Server localizado em outra máquina. Uma máquina realiza a conexão com o SQL Server da outra para buscar os dados.

Essa diferença metodológica pode ter impacto nos resultados.

Fiquei com a dúvida de até que ponto utilizar CSVs no meu experimento poderia favorecer ou prejudicar ETL ou ELT.

Não necessariamente seria necessário reproduzir exatamente o ambiente utilizado pelos autores. Porém, é importante entender qual abordagem representa melhor uma situação prática e se utilizar CSV é simples demais ou se pode representar justamente uma configuração experimental diferente e válida.

---

## 4. Uso do Pentaho e diferentes cenários

Os autores também utilizam o Pentaho em outros cenários experimentais.

Eles testam ETL e ELT com diferentes formas de execução, incluindo o uso dessa ferramenta.

Isso adiciona ao trabalho uma variabilidade relacionada à ferramenta utilizada para executar os processos.

No meu TCC, a princípio, não pretendo trabalhar com essa variação de ferramentas.

Mesmo assim, considero interessante destacar essa diferença, já que eles não estão comparando apenas as abordagens ETL e ELT de forma isolada, mas também diferentes formas de implementá-las.

---

## 5. Uso da máquina durante os experimentos

Um ponto que me chamou bastante atenção foi o fato de os autores relatarem que, durante alguns testes, a máquina também estava sendo utilizada para outras atividades que demandavam poder de processamento.

Isso acabou impactando alguns resultados específicos.

Esse é um ponto metodológico que quero evitar no meu trabalho.

Pretendo executar os testes com a máquina sem outras atividades relevantes em execução, tentando manter as mesmas condições entre todas as execuções.

A intenção é garantir que cada teste possa ser comparado de maneira mais justa com os demais, evitando interferências externas no consumo de recursos ou no tempo de execução.

Vejo isso como um ponto de cuidado importante para o meu experimento.

---

## 6. Resultado favorável ao ETL

Nos resultados apresentados pelos autores, o ETL teve desempenho muito melhor que o ELT.

A diferença entre as duas abordagens foi bastante grande.

O que me chamou atenção foi principalmente o tempo gasto pelo ELT durante a etapa de carga.

Minha hipótese inicial é que isso possa estar relacionado à grande quantidade de tabelas existentes no AdventureWorks.

Como o ELT carrega inicialmente os dados brutos para depois realizar as transformações, a necessidade de carregar muitas tabelas pode ter aumentado bastante o tempo dessa abordagem.

Não lembro se os próprios autores apresentam essa explicação como causa do resultado. Por enquanto, essa é uma interpretação ou hipótese minha a partir do que observei.

---

## 7. Possível relação entre quantidade de dados/tabelas e desempenho

A diferença muito grande entre ETL e ELT levantou a possibilidade de que as características da base tenham influenciado diretamente os resultados.

Talvez a quantidade de tabelas e de informações carregadas tenha pesado principalmente para o ELT.

Esse ponto pode ser interessante para o meu trabalho porque pretendo utilizar duas bases com características diferentes.

O ENEM possui uma estrutura com poucas tabelas, enquanto o TSE possui uma quantidade maior.

Mesmo que a diferença entre elas talvez não seja tão grande quanto no AdventureWorks, isso pode permitir observar se mudanças na estrutura ou complexidade dos datasets influenciam o comportamento das duas abordagens.

Isso talvez permita investigar melhor essa possível relação.

---

## 8. Semelhanças e diferenças gerais

De forma geral, considero o trabalho semelhante ao meu em relação às premissas e ao objetivo principal, mas bastante diferente na execução.

Entre as principais diferenças estão:

- utilização de apenas um dataset;
- uso do AdventureWorks;
- origem dos dados em outro banco SQL Server;
- comunicação entre duas máquinas;
- utilização do Pentaho;
- comparação de diferentes formas de implementação;
- ausência de uma comparação entre datasets com diferentes níveis de complexidade.

Mesmo com essas diferenças, o objetivo de comparar ETL e ELT é muito direcionado ao problema que também estou investigando.

Por isso, considero o trabalho bastante relevante como referência.

---

## 9. Estrutura e fundamentação teórica

O trabalho de Bessa e Santos é consideravelmente mais longo e possui uma carga teórica bastante forte.

Os autores abordam conceitos como:

- definição de ETL;
- definição de ELT;
- Star Schema;
- outros conceitos relacionados ao contexto de integração e armazenamento de dados.

Minha impressão atual é que talvez o meu trabalho não precise trazer uma fundamentação teórica com o mesmo nível de profundidade, principalmente considerando o modelo de trabalho que estou seguindo.

Porém, ainda quero conversar com meu orientador para entender melhor qual deve ser o nível de aprofundamento teórico necessário.

É possível que parte dessa fundamentação precise estar presente, mas talvez de maneira mais curta e direcionada ao experimento.

---

## 10. Impressão geral

O trabalho foi bastante interessante por possuir um objetivo muito próximo ao meu.

Ao mesmo tempo, as diferenças metodológicas são grandes o suficiente para que os dois trabalhos não sejam simplesmente equivalentes.

Os principais pontos que ficaram para mim nesta primeira leitura foram:

- a influência que a origem dos dados pode ter sobre o resultado;
- a diferença entre utilizar CSVs e extrair dados diretamente de outro banco;
- a utilização de apenas um dataset pelos autores;
- a presença do Pentaho como variável adicional;
- a importância de controlar o uso da máquina durante os testes;
- o desempenho muito superior do ETL observado no trabalho;
- a hipótese de que a grande quantidade de tabelas possa ter prejudicado o ELT;
- a possibilidade de utilizar ENEM e TSE para observar se características diferentes das bases alteram esse comportamento;
- a dúvida sobre o nível de fundamentação teórica necessário no meu próprio TCC.