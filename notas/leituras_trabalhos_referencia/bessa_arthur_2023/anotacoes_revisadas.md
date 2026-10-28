# Bessa e Santos (2023) — Versão revisada

## 1. Relação geral com o meu TCC

O trabalho de Bessa e Santos (2023) é diretamente relevante por comparar ETL e ELT em um cenário experimental.

A proximidade maior está no objetivo de comparar o comportamento das duas abordagens. Porém, o desenho experimental é bastante diferente do que pretendo utilizar.

As principais diferenças são:

- utilização de apenas um dataset;
- uso do AdventureWorks;
- extração dos dados a partir de SQL Server;
- uso de duas máquinas;
- transformação executada em ambientes diferentes dependendo do pipeline;
- presença de cenários com Pentaho;
- avaliação centrada principalmente no tempo de execução.

Isso faz com que o trabalho seja uma boa referência comparativa, mas não um modelo metodológico que precise ser reproduzido diretamente.

---

## 2. Uso de apenas um dataset

O trabalho utiliza somente o AdventureWorks.

Isso limita a capacidade de observar se os resultados obtidos se mantêm quando mudam as características dos dados.

Esse ponto é particularmente relevante para o meu trabalho, pois pretendo utilizar dois conjuntos de dados com características distintas:

- ENEM;
- TSE.

A utilização de mais de uma base pode permitir analisar se o comportamento relativo de ETL e ELT muda conforme variam fatores como volume, estrutura e complexidade das transformações.

Esse aspecto também se relaciona com as próprias possibilidades de trabalhos futuros levantadas pelos autores, que reconhecem que outros datasets e cenários podem produzir resultados diferentes.

---

## 3. Origem dos dados e controle experimental

Bessa e Santos trabalham com dados armazenados em SQL Server e executam os processos entre máquinas diferentes.

No meu TCC, a proposta atual é utilizar arquivos CSV como fonte bruta e executar todo o benchmark localmente.

Inicialmente, a utilização de CSV parecia uma simplificação excessiva em comparação ao cenário utilizado pelos autores.

Após a análise, porém, essa escolha passou a fazer mais sentido metodologicamente.

O objetivo do meu TCC não é reproduzir toda a complexidade de uma arquitetura empresarial real, mas construir um experimento controlado capaz de observar o comportamento de ETL e ELT reduzindo variáveis externas.

O uso de CSV local permite eliminar ou reduzir fatores como:

- latência de rede;
- diferenças entre máquinas;
- disponibilidade de sistemas externos;
- desempenho de conexão entre bancos;
- interferência de diferentes ambientes de origem.

Nesse contexto, utilizar CSV não necessariamente enfraquece o trabalho. Pode aumentar a validade interna do experimento ao tornar o ambiente mais controlável.

---

## 4. ETL e ELT não significam simplesmente “carregar pouco” e “carregar tudo”

Uma interpretação inicial foi que o ETL realizaria naturalmente uma carga seletiva, enquanto o ELT carregaria todos os dados brutos.

Essa interpretação precisa ser feita com mais cuidado.

A diferença fundamental entre as abordagens está na ordem das operações:

- ETL: extrair → transformar → carregar;
- ELT: extrair → carregar → transformar.

O ELT não exige necessariamente carregar absolutamente todos os dados existentes na fonte.

A questão é que os dados definidos como entrada são carregados antes da aplicação das transformações.

No experimento que pretendo desenvolver, o ideal é que ambos os pipelines partam exatamente da mesma entrada bruta.

Exemplo:

ETL:

CSV bruto → transformação → PostgreSQL

ELT:

CSV bruto → PostgreSQL → transformação

Se operações como remoção de colunas, filtros, eliminação de duplicatas ou agregações fizerem parte da transformação, então é natural que o ETL carregue menos dados no banco final.

Nesse caso, essa diferença de volume não representa uma falha metodológica. É uma consequência da posição da transformação dentro do pipeline.

O cuidado é evitar introduzir otimizações específicas em apenas uma das abordagens que não sejam consequência direta da diferença entre ETL e ELT.

---

## 5. Resultado favorável ao ETL

No estudo, o ETL apresentou tempos de execução consideravelmente menores que o ELT.

Uma interpretação inicial foi de que isso poderia estar relacionado à grande quantidade de tabelas do AdventureWorks.

A análise do trabalho mostra que essa interpretação estava próxima, mas precisava ser mais precisa.

O principal fator não é simplesmente a quantidade de tabelas.

O ponto relevante é que, no ELT, uma quantidade maior de dados brutos precisa ser carregada no ambiente de destino antes das transformações.

No ETL, parte desses dados pode ser filtrada, transformada ou reduzida antes da carga.

Assim, no cenário utilizado pelos autores, o ELT movimentou uma quantidade maior de dados antes de produzir o mesmo resultado final.

Essa característica contribuiu para o aumento do tempo de execução.

Portanto, a conclusão mais adequada não é:

> “ETL é mais rápido que ELT.”

Mas:

> “No cenário experimental utilizado pelos autores, o ETL apresentou menor tempo de execução que o ELT.”

A diferença é importante porque evita transformar um resultado específico em uma conclusão universal.

---

## 6. Local da transformação

Outro ponto metodológico importante é que as transformações não são executadas pelo mesmo mecanismo nos dois cenários.

No ETL, parte do processamento ocorre antes da carga, utilizando o ambiente relacionado ao SQL Server.

No ELT, a transformação ocorre no PostgreSQL depois da carga.

Isso significa que a comparação pode refletir não apenas a ordem das operações, mas também diferenças entre os mecanismos responsáveis pelo processamento.

Esse problema também pode aparecer no meu experimento.

No desenho atual:

- ETL utilizará Python/Polars para realizar transformações antes da carga;
- ELT utilizará PostgreSQL/SQL para realizar transformações depois da carga.

Essa diferença não torna o experimento inválido, pois ela está relacionada ao funcionamento prático das arquiteturas escolhidas.

Porém, precisa ser reconhecida como uma característica metodológica.

Assim, caso existam diferenças de desempenho, não será possível assumir automaticamente que toda a diferença ocorreu exclusivamente devido à ordem entre transformação e carga.

---

## 7. Uso de duas máquinas

O trabalho utiliza duas máquinas com configurações diferentes.

Esse aspecto aumenta a quantidade de variáveis que podem influenciar os resultados.

Diferenças de:

- processador;
- memória RAM;
- armazenamento;
- serviços em execução;
- comunicação entre máquinas;

podem afetar o desempenho observado.

No meu experimento, a decisão mais adequada é manter um único hardware fixo.

O hardware deve ser tratado como variável controlada e documentado detalhadamente.

Essa decisão reduz a quantidade de explicações alternativas para os resultados encontrados.

---

## 8. Possibilidade de estudos futuros com diferentes hardwares

A discussão sobre as máquinas também gerou uma possibilidade interessante para trabalhos futuros.

Embora não seja recomendável adicionar diferentes hardwares ao escopo atual, seria possível futuramente repetir o mesmo benchmark em máquinas com características distintas.

Esse tipo de experimento poderia investigar, por exemplo:

- se ETL e ELT respondem de forma diferente a maiores quantidades de RAM;
- se mudanças de CPU beneficiam uma abordagem mais que outra;
- se velocidade de armazenamento altera significativamente os resultados;
- se existe interação entre arquitetura de pipeline e capacidade computacional.

Essa possibilidade deve ser registrada como uma sugestão de continuidade do trabalho.

No TCC atual, porém, manter o hardware fixo fortalece o controle experimental.

---

## 9. Interferência de outras atividades durante os testes

Os autores relatam que algumas execuções sofreram interferência de outras atividades executadas na máquina.

Isso afetou significativamente alguns resultados.

Esse ponto funciona como um alerta metodológico importante.

Durante os testes do meu TCC, será necessário minimizar ao máximo interferências externas.

Entre os cuidados possíveis estão:

- evitar utilização da máquina durante os testes;
- reduzir processos desnecessários em segundo plano;
- manter condições semelhantes entre execuções;
- repetir os experimentos diversas vezes;
- documentar o ambiente utilizado.

O objetivo é garantir maior comparabilidade entre as execuções.

---

## 10. Repetições e análise estatística

O trabalho executa múltiplos testes, o que é positivo.

Porém, a análise dos resultados é concentrada principalmente em médias e comparações diretas de tempo.

A existência de execuções afetadas por fatores externos demonstra que utilizar apenas a média pode esconder ou distorcer parte do comportamento dos dados.

No meu trabalho, será importante utilizar medidas adicionais.

Entre as possibilidades:

- média;
- mediana;
- desvio-padrão;
- valores máximos e mínimos como informação complementar;
- eventualmente intervalos de confiança ou outras medidas de dispersão.

O objetivo não será apenas obter um valor médio, mas também observar a estabilidade e variabilidade das execuções.

---

## 11. Limitação das métricas utilizadas

Outro diferencial importante é que o trabalho de Bessa e Santos concentra a avaliação principalmente no tempo de execução.

Isso permite responder:

> Qual abordagem terminou primeiro?

Mas não permite avaliar completamente:

> Qual abordagem utilizou melhor os recursos disponíveis?

No meu TCC, pretendo ampliar a análise utilizando outras métricas.

Entre elas:

- tempo de execução;
- CPU;
- memória RAM;
- throughput.

Essa abordagem pode produzir conclusões mais completas.

Um pipeline pode, por exemplo:

- ser mais rápido, mas consumir mais memória;
- ser mais lento, mas apresentar menor uso de CPU;
- ter desempenho melhor em volumes pequenos e pior em volumes maiores;
- apresentar melhor escalabilidade à medida que o volume cresce.

Isso torna possível evitar uma visão simplificada de desempenho como apenas “menor tempo”.

---

## 12. Escalabilidade e comportamento conforme o volume cresce

A utilização de diferentes volumes de dados pode permitir observar tendências que não aparecem em uma comparação única.

A ideia é analisar como as métricas evoluem conforme aumenta a quantidade de dados processados.

Por exemplo:

- tempo em função do volume;
- RAM em função do volume;
- CPU em função do volume;
- throughput em função do volume.

Esse tipo de análise pode revelar se as diferenças entre ETL e ELT aumentam, diminuem ou se invertem conforme o volume cresce.

Isso pode ser mais relevante do que identificar apenas qual abordagem apresentou o melhor resultado em uma execução específica.

---

## 13. Pentaho

Bessa e Santos também analisam cenários utilizando Pentaho.

Essa dimensão não será reproduzida no meu TCC.

A introdução de diferentes ferramentas aumentaria significativamente o número de variáveis experimentais.

Como o objetivo principal é comparar ETL e ELT, a intenção é manter a implementação o mais consistente possível entre os cenários.

O estudo do Pentaho permanece relevante para compreender o desenho experimental dos autores, mas não representa uma dimensão que pretendo explorar.

---

## 14. Acessibilidade da ferramenta e evidência experimental

Os autores também discutem a maior acessibilidade ou facilidade de utilização do Pentaho.

Esse tipo de conclusão é diferente das conclusões baseadas no tempo de execução.

O tempo é medido objetivamente no experimento.

Já facilidade de uso, acessibilidade ou curva de aprendizado são características mais qualitativas e não foram avaliadas da mesma forma.

Esse ponto serve como alerta para o meu próprio trabalho.

É importante distinguir claramente:

- o que foi medido;
- o que foi observado;
- o que foi interpretado;
- o que é uma avaliação subjetiva.

As conclusões devem permanecer proporcionais às evidências coletadas.

---

## 15. Principal aprendizado metodológico

O ponto mais relevante da leitura não é simplesmente que o ETL apresentou melhor desempenho.

O principal aprendizado é que resultados de benchmarks precisam ser interpretados dentro do desenho experimental que os produziu.

No caso de Bessa e Santos, os resultados estão associados a:

- um dataset específico;
- uma arquitetura específica;
- máquinas específicas;
- ferramentas específicas;
- diferentes locais de processamento;
- volume de dados movimentado;
- condições particulares de execução.

Portanto, o trabalho fornece evidência válida para o cenário analisado, mas não demonstra que ETL será universalmente superior a ELT.

---

## 16. Contribuição para o meu TCC

O trabalho contribui diretamente para algumas decisões do meu projeto.

Entre os principais aprendizados estão:

- utilizar mais de um dataset para analisar comportamentos diferentes;
- controlar o hardware;
- evitar interferências durante os testes;
- manter as ferramentas o mais fixas possível;
- partir da mesma entrada bruta para ETL e ELT;
- garantir que o produto final dos dois pipelines seja equivalente;
- utilizar múltiplas métricas;
- analisar dispersão e não apenas médias;
- evitar conclusões universais a partir de um cenário específico;
- reconhecer as limitações impostas pelo ambiente de transformação.

Também reforça a importância de avaliar não apenas qual abordagem apresenta menor tempo, mas como cada uma se comporta conforme mudam as características da carga de trabalho.

---

## 17. Possíveis relações com a contribuição original do meu trabalho

A comparação com Bessa e Santos ajuda a identificar alguns diferenciais potenciais do meu TCC:

- utilização de dois datasets com características distintas;
- variação controlada de volume;
- análise de múltiplas métricas de desempenho;
- maior controle sobre interferências externas;
- hardware fixo;
- tentativa de observar tendências de comportamento e escalabilidade;
- análise menos focada em identificar um “vencedor geral” e mais focada em entender em quais condições cada abordagem apresenta vantagens ou desvantagens.

Esses pontos não devem ser tratados automaticamente como superioridade metodológica.

Eles representam diferenças de escopo e desenho experimental que podem ampliar a análise feita por trabalhos anteriores.

---

## 18. Síntese final

Bessa e Santos (2023) é uma referência importante por realizar uma comparação direta entre ETL e ELT.

O resultado favorável ao ETL é relevante, mas precisa ser entendido dentro das condições específicas do experimento.

A principal contribuição desse trabalho para o meu TCC não está apenas no resultado obtido, mas nas questões metodológicas que ele ajuda a levantar.

A leitura reforçou a importância de controlar variáveis, diversificar métricas, observar diferentes volumes e evitar generalizações.

Também abriu uma possibilidade de trabalho futuro relacionada à repetição do benchmark em diferentes configurações de hardware.

De forma geral, o estudo serve tanto como referência conceitual quanto como ponto de comparação metodológica para o desenvolvimento do meu próprio experimento.