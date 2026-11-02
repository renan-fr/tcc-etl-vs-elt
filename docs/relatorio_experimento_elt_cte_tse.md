# Experimento ELT com CTEs — TSE

Data da execução: 2 de novembro de 2026.

## Objetivo e escopo

Foi criada e avaliada uma variante experimental do ELT do TSE que mantém a
carga das três fontes em tabelas RAW, substitui as três tabelas STAGING por
CTEs e persiste o mesmo produto FINAL. O ELT e o ETL oficiais não foram
alterados. Os schemas e arquivos de resultados deste experimento são
independentes dos oficiais.

Ambiente observado: PostgreSQL 18.3 x86-64 em Windows, mesma conexão e mesma
máquina para todas as execuções. As duas arquiteturas foram executadas
sequencialmente.

## Arquivos criados

- `src/tse/experimental/elt_cte.py`: implementação RAW → CTEs → FINAL,
  validações adaptadas e medição.
- `src/tse/experimental/elt_staging.py`: invocador isolado da implementação
  oficial RAW → STAGING → FINAL, com schemas e saída experimentais.
- `src/tse/experimental/equivalencia.py`: comparação direta de estrutura,
  multiconjunto de valores e unicidade entre os dois ELTs.
- `src/tse/experimental/benchmark.py`: certificação obrigatória, aquecimento,
  randomização e três repetições.
- `src/tse/experimental/diagnostico_sql.py`: diagnóstico separado com
  `EXPLAIN (ANALYZE, BUFFERS)`.
- `data/benchmark/tse/experimental_cte/`: resultados, sequência, evidências de
  validação e planos SQL. Nenhum resultado histórico oficial foi removido ou
  modificado.

## Dependências das tabelas STAGING e equivalência da implementação

O mapeamento do ELT oficial identificou estas responsabilidades das STAGING:

1. `munzona`: conversão de chaves e métricas para `INTEGER`/`BIGINT`,
   normalização de `cd_municipio` com cinco posições e manutenção das
   descrições.
2. `secao`: tipagem e agregação por chave lógica, com contagem distinta de
   seções e somas de comparecimento, abstenções, votos nominais, brancos,
   nulos e de legenda.
3. `candidato`: tipagem, contagem distinta de candidatos, soma de votos e
   desempate do mais votado por votos decrescentes e `sq_candidato` crescente.
4. Verificação de ausência de chaves lógicas duplicadas nas três relações.
5. Construção final por `LEFT JOIN`, preenchimento com zero das métricas sem
   correspondência, preservação de nulos nos dados do candidato mais votado e
   cálculo dos três percentuais com seis casas.
6. Verificação de que os joins não alteram a quantidade de linhas de
   `munzona`, além das validações de contrato, nulidade, unicidade,
   não-negatividade, consistência dos percentuais, alertas de reconciliação e
   detecção de chaves órfãs de seção/candidato.

Na alternativa, `munzona`, `secao`, `candidato_tipado`, `candidato_totais`,
`candidato_ranking` e `candidato` são CTEs. As verificações de campos numéricos
obrigatórios continuam sobre RAW; unicidade e órfãos são avaliados sobre as
relações derivadas pelas mesmas CTEs. O contrato final é importado diretamente
de `src/tse/contrato.py`.

## Validação funcional

O benchmark só foi iniciado depois da certificação interna das duas versões e
da comparação direta entre seus produtos, em cada volume. A comparação usa
`EXCEPT ALL` nos dois sentidos, portanto independe da ordem física e preserva a
multiplicidade das linhas.

| Volume nominal | Linhas finais STAGING | Linhas finais CTE | Apenas STAGING | Apenas CTE | Duplicadas em cada versão | Resultado |
|---:|---:|---:|---:|---:|---:|:---:|
| 100.000 | 1.357 | 1.357 | 0 | 0 | 0 | OK |
| 500.000 | 6.478 | 6.478 | 0 | 0 | 0 | OK |

Nomes, ordem, tipos e nulabilidade das colunas foram iguais. O contrato
estrutural também foi comparado com a tabela ETL existente e foi igual. Os
valores dessa tabela ETL não foram comparados porque ela havia sido produzida
com outro volume; declarar equivalência de valores nesse caso seria inválido.

As validações existentes foram preservadas. Os mesmos alertas de domínio
apareceram nas duas versões:

- 100 mil: 361 divergências de votos nominais entre munzona e seções, 231 de
  votos nulos e 78 de votos de legenda.
- 500 mil: 27 chaves sem candidatos, 27 diferenças entre votos de candidatos e
  votos nominais de munzona, 1.468 divergências de votos nominais entre
  munzona e seções, 921 de votos nulos e 236 de votos de legenda.

São alertas já definidos no pipeline, não divergências entre as implementações.
Nenhum erro crítico foi encontrado.

## Volumes efetivos

| Volume nominal | Munzona | Seção | Candidato | Total carregado em RAW | Produto FINAL |
|---:|---:|---:|---:|---:|---:|
| 100.000 | 1.357 | 111.398 | 80.082 | 192.837 | 1.357 |
| 500.000 | 6.478 | 506.386 | 334.717 | 847.581 | 6.478 |

As contagens são iguais nas duas arquiteturas e refletem os manifestos
existentes; o volume nominal não corta uma chave lógica ao meio.

## Método do benchmark

- Volumes: 100 mil e 500 mil.
- Um aquecimento por arquitetura e volume.
- Três repetições medidas por arquitetura e volume.
- Seed: `20261102`.
- Fronteira total: leitura do manifesto/CSVs, carga e commit de RAW,
  transformação SQL e persistência/commit de FINAL.
- As validações completas de certificação ficaram fora das medições; as
  verificações de campos obrigatórios, unicidade das relações derivadas e
  preservação da quantidade de linhas continuaram dentro da transformação em
  ambas as arquiteturas.

A sequência completa está em `data/benchmark/tse/experimental_cte/sequencia.csv`.
Nos aquecimentos a ordem foi: 500k-STAGING, 500k-CTE, 100k-CTE,
100k-STAGING. Nas medições:

| Ordem | Rodada | Sequência |
|---:|---:|---|
| 5–8 | 1 | 500k-STAGING, 500k-CTE, 100k-CTE, 100k-STAGING |
| 9–12 | 2 | 100k-STAGING, 500k-STAGING, 500k-CTE, 100k-CTE |
| 13–16 | 3 | 500k-CTE, 100k-STAGING, 500k-STAGING, 100k-CTE |

## Tempos individuais

Tempos em segundos:

| Volume | Arquitetura | Rodada | Leitura | Carga RAW | SQL | Total |
|---:|---|---:|---:|---:|---:|---:|
| 100.000 | STAGING | 1 | 1,858 | 0,406 | 1,430 | 3,747 |
| 100.000 | STAGING | 2 | 1,786 | 0,318 | 1,442 | 3,693 |
| 100.000 | STAGING | 3 | 1,831 | 0,410 | 1,714 | 4,008 |
| 100.000 | CTE | 1 | 2,102 | 0,529 | 2,560 | 5,250 |
| 100.000 | CTE | 2 | 1,790 | 0,357 | 2,192 | 4,399 |
| 100.000 | CTE | 3 | 1,836 | 0,323 | 2,160 | 4,362 |
| 500.000 | STAGING | 1 | 13,723 | 3,139 | 13,411 | 30,340 |
| 500.000 | STAGING | 2 | 9,196 | 2,174 | 11,532 | 22,949 |
| 500.000 | STAGING | 3 | 8,032 | 2,079 | 11,214 | 21,376 |
| 500.000 | CTE | 1 | 12,784 | 3,938 | 18,004 | 34,804 |
| 500.000 | CTE | 2 | 8,587 | 1,530 | 15,462 | 25,646 |
| 500.000 | CTE | 3 | 8,312 | 1,989 | 15,157 | 25,517 |

## Médias, dispersão e diferenças percentuais

O desvio é o desvio-padrão amostral das três repetições. A diferença usa
STAGING como referência: `(CTE / STAGING - 1) × 100`.

| Volume | Arquitetura | SQL média ± desvio (s) | Total médio ± desvio (s) | Mín.–máx. total (s) |
|---:|---|---:|---:|---:|
| 100.000 | STAGING | 1,529 ± 0,161 | 3,816 ± 0,168 | 3,693–4,008 |
| 100.000 | CTE | 2,304 ± 0,222 | 4,670 ± 0,502 | 4,362–5,250 |
| 500.000 | STAGING | 12,052 ± 1,187 | 24,888 ± 4,786 | 21,376–30,340 |
| 500.000 | CTE | 16,208 ± 1,563 | 28,656 ± 5,325 | 25,517–34,804 |

| Volume | Dif. leitura | Dif. carga RAW | Dif. SQL | Dif. total |
|---:|---:|---:|---:|---:|
| 100.000 | +4,62% | +6,61% | **+50,72%** | **+22,39%** |
| 500.000 | −4,10% | +0,88% | **+34,48%** | **+15,14%** |

Os componentes de leitura e carga variaram apesar de serem logicamente iguais,
o que é compatível com efeitos de cache e atividade da máquina. A diferença
mais estável e diretamente relacionada à implementação ocorreu na etapa SQL.

## Diagnóstico SQL

O diagnóstico foi executado separadamente no volume nominal de 500 mil, para
não contaminar os tempos principais. Os planos estão em
`data/benchmark/tse/experimental_cte/planos/`.

- O plano completo das CTEs levou 3.934,035 ms na execução instrumentada.
- `candidato_tipado`, usado pelos totais e pelo ranking, foi materializado
  internamente e lido duas vezes.
- As ordenações de candidatos usaram `external merge` (aproximadamente 31,5 MB
  e 19,0 MB em disco); a agregação de seções também gerou I/O temporário.
- O plano registrou 14.858 blocos temporários lidos e 14.887 escritos no total.
- A junção final sobre STAGING persistente levou 35,742 ms e usou apenas scans
  e ordenações em memória sobre as relações já reduzidas.

Os tempos de 3.934 ms e 35,742 ms **não são uma comparação ponta a ponta**: o
primeiro plano inclui tipagem/agregação/ranking desde RAW, enquanto o segundo
inclui apenas a junção final depois que as STAGING já foram materializadas. A
comparação ponta a ponta válida é a medição da etapa SQL e do tempo total
apresentada acima. O plano serve para explicar a pressão de ordenação e
materialização observada na alternativa.

## Limitações

- Apenas uma máquina, uma versão do PostgreSQL e três repetições por cenário.
- Cache do sistema operacional e do PostgreSQL não foi esvaziado entre runs;
  a ordem randomizada e os aquecimentos reduzem, mas não eliminam, esse efeito.
- Houve dispersão relevante no volume de 500 mil, especialmente na leitura.
- Foram avaliados somente dois volumes e os manifestos existentes.
- A campanha oficial de 96 runs não foi executada.
- O plano STAGING isolado não incorpora os comandos anteriores de criação das
  três tabelas; por isso ele é diagnóstico, não uma métrica comparável ao plano
  completo das CTEs.
- O PostgreSQL pode alterar decisões de inlining/materialização de CTEs em
  outras versões, estatísticas, parâmetros de memória ou volumes.

## Recomendação

Manter a implementação oficial com STAGING por enquanto. A alternativa com
CTEs preservou integralmente o resultado e as regras verificadas, mas nesta
amostra aumentou o tempo SQL médio em 34,48% a 50,72% e o tempo total em 15,14%
a 22,39%. Ela pode continuar como opção experimental se houver interesse em
reduzir objetos persistentes ou testar ajustes específicos de PostgreSQL, mas
não há evidência neste experimento para considerá-la superior em desempenho.

Antes de qualquer substituição, seria necessário ampliar repetições, volumes,
versões/configurações do PostgreSQL e investigar a materialização reutilizada
de `candidato_tipado`, sempre repetindo primeiro a certificação funcional.
