# Análises do primeiro Benchmark

## Tempos de processamento:
- De forma geral, o ETL se saiu melhor nessa métrica. Considerando ambos os datasets, o ELT apresentou um tempo de processamento 37,1% maior que o ETL.
- Apesar disso, por conta da possível anomalia na carga do ENEM, o ETL apresentou um tempo de processamento 24,2% maior que o ELT.
- O TSE teve o ELT com tempo de processamento 148,3% maior que o ETL.

**Tabela 1 — Tempos médios de processamento por dataset e arquitetura (segundos)**

| Dataset | Etapa | ETL (s) | ELT (s) | Variação (%) |
|---|---|---:|---:|---:|
| ENEM | Leitura | 1,91 | 10,22 | +434,0% |
| ENEM | Transformação | 1,61 | 6,65 | +314,2% |
| ENEM | Carga | 18,88 | 1,01 | -94,6% |
| **ENEM** | **Total** | **22,43** | **18,06** | **-19,5%** |
| TSE | Leitura | 5,40 | 14,82 | +174,5% |
| TSE | Transformação | 5,75 | 12,55 | +118,4% |
| TSE | Carga | 0,26 | 0,92 | +247,1% |
| **TSE** | **Total** | **11,42** | **28,35** | **+148,3%** |
| Média | Leitura | 3,66 | 12,52 | +242,4% |
| Média | Transformação | 3,68 | 9,60 | +161,1% |
| Média | Carga | 9,57 | 0,97 | -89,9% |
| **Média** | **Total** | **16,92** | **23,20** | **+37,1%** |

### Carga (Anomalia a investigar):
- No dataset do ENEM tivemos um número assustador na carga do ETL: 18,9 segundos. Em comparação, o ETL do TSE carregou em 0,3 segundos. Uma diferença de 18,6 seg / aumento de 7.028,1%. Acredito ser por conta do ENEM ter de carregar duas tabelas, diferente do TSE que carrega apenas uma. Porém, mesmo assim, a diferença é assustadora, analisarei.
- No dataset do TSE o número foi próximo. O ETL registrou 0,3 segundos enquanto que o ELT 0,9 segundos (diferença de 0,7 segundos / aumento de 247,1%).

### Leitura e transformação:
- No ELT, em ambos a leitura e transformação registraram tempos superiores. No TSE, correspondendo a leitura e transformação respectivamente, tivemos 5,4 para 14,8 (diferença de 9,4 seg / aumento de 174,5%) e 5,7 para 12,6 (diferença de 6,8 seg / aumento de 118,4%).
- No ENEM, na leitura tivemos 1,9 e subimos pra 10,2 (diferença de 8,3 seg / aumento de 434,0%). E na transformação fomos de 1,6 pra 6,7 (diferença de 5,0 seg / aumento de 314,2%).

### Tempos totais:
- Quanto aos tempos totais, no dataset do ENEM tivemos 22,4 de tempo total do ETL e 18,1 do ELT (diferença de 4,4 seg / redução de 19,5%). O elevadíssimo tempo de carga do ETL nesse dataset foi o que compensou as vantagens do ETL nas outras etapas.
- No dataset do TSE, o ETL teve 11,4 segundos e no ELT 28,3 (diferença de 16,9 segundos / aumento de 148,3%).
- Abrangendo ambos os datasets em uma única média, o ETL teve 16,9 segundos e o ELT 23,2, uma diferença de 6,3 segundos e um aumento percentual de 37,1%.

## Consumo de Memória RAM:
- Podemos observar que o ELT foi mais eficiente no uso da memória RAM. No PostgreSQL teve um consumo médio e pico médio ligeiramente maior, porém vantajoso ao comparar com a grande redução que ocorreu do consumo no Python.

**Tabela 2 — Consumo médio e pico médio de memória RAM por dataset, arquitetura e processo (MB)**

| Dataset | Indicador | ETL (MB) | ELT (MB) | Variação (%) |
|---|---|---:|---:|---:|
| ENEM | Consumo médio total | 531,4 | 77,8 | -85,4% |
| ENEM | Consumo médio Python | 489,1 | 31,6 | -93,5% |
| ENEM | Consumo médio PostgreSQL | 42,4 | 46,2 | +9,0% |
| ENEM | Pico médio total | 729,0 | 87,8 | -88,0% |
| ENEM | Pico médio Python | 683,5 | 32,1 | -95,3% |
| ENEM | Pico médio PostgreSQL | 49,6 | 56,1 | +13,0% |
| TSE | Consumo médio total | 243,2 | 82,4 | -66,1% |
| TSE | Consumo médio Python | 205,2 | 34,4 | -83,2% |
| TSE | Consumo médio PostgreSQL | 38,0 | 48,0 | +26,3% |
| TSE | Pico médio total | 310,2 | 95,9 | -69,1% |
| TSE | Pico médio Python | 272,2 | 34,9 | -87,2% |
| TSE | Pico médio PostgreSQL | 41,9 | 61,4 | +46,5% |
| **Média** | **Consumo médio total** | **387,3** | **80,1** | **-79,3%** |
| Média | Consumo médio Python | 347,2 | 33,0 | -90,5% |
| Média | Consumo médio PostgreSQL | 40,2 | 47,1 | +17,2% |
| **Média** | **Pico médio total** | **519,6** | **91,8** | **-82,3%** |
| Média | Pico médio Python | 477,9 | 33,5 | -93,0% |
| Média | Pico médio PostgreSQL | 45,8 | 58,7 | +28,3% |

### Consumo médio:
- No dataset do ENEM, o ETL utilizou 531MB de RAM enquanto que o ELT consumiu 78MB (diferença de 454MB / redução de 85,4%).
- No dataset do TSE, o ETL consumiu 243MB de RAM enquanto que o ELT 82MB (diferença de 161MB / redução de 66,1%).
- Unindo os datasets, o ETL registrou 387MB e ELT 80MB (diferença de 307MB / redução de 79,3%).

### Consumo médio por processo:
- Ao comparar o uso de RAM no Python e PostgreSQL, conseguimos identificar divergências que esclarecem mais as características de cada padrão.
- No dataset do ENEM, o ETL teve um consumo médio de 42MB no PostgreSQL e 489MB no Python. Enquanto que no ELT teve 46MB no PostgreSQL e 32MB no Python. Podemos perceber que, nesse dataset o ELT continuou sendo mais eficiente, reduzindo o consumo no Python em 457MB, 93,5% a menos. Uma troca vantajosa, pois o aumento no PostgreSQL foi mínimo, 4MB, um aumento de apenas 9,0%.
- No dataset do TSE, o ETL no PostgreSQL consumiu em média 38MB e no Python 205MB. No ELT o PostgreSQL foi 48MB e Python 34MB. O padrão observado se mantém, apesar da diferença ser menos expressiva que no dataset anterior. O Python reduziu em 171MB, cerca de 83,2%. Enquanto que o PostgreSQL teve um ligeiro aumento no consumo, 10MB, 26,3%.
- Unindo os datasets, o ETL teve 40MB no PostgreSQL e 347MB no Python, enquanto que o ELT teve 47MB e 33MB no Python. Ou seja, no PostgreSQL aumentou 7MB, 17,2%. Porém, no Python reduziu 314MB, 90,5%.

### Pico médio de consumo:
- No ENEM o pico médio do ETL foi 729MB e no ELT 88MB (diferença de 641MB / redução de 88,0%).
- No TSE o pico médio do ETL foi 310MB e no ELT 96MB (diferença de 214MB / redução de 69,1%).
- Unindo os datasets, o ETL registrou 520MB e o ELT 92MB (diferença de 428MB / redução de 82,3%).

### Pico médio de consumo por processo:
- No ENEM, o pico médio do ETL foi de 50MB no PostgreSQL e 684MB no Python. O ELT apresentou 56MB e 32MB. O PostgreSQL teve um aumento de 6MB, 13,0%. Enquanto que o Python teve uma redução de 651MB, 95,3%.
- No TSE, o pico médio do ETL foi de 42MB no PostgreSQL e 272MB no Python. O ELT apresentou 61MB e 35MB. O padrão se repete, o PostgreSQL teve um aumento de 19MB, 46,5%. Enquanto que o Python teve uma redução de 237MB, 87,2%.
- Unindo os datasets, no ETL o PostgreSQL teve pico médio de 46MB e Python 478MB. No ELT foi de 59MB e 33MB. Um aumento de 13MB, 28,3%. Porém, no Python tivemos uma redução de 444MB, 93,0%.

## Consumo de CPU
- De forma geral, o ELT apresentou maior consumo de CPU, tanto no uso médio quanto no pico médio. Ao analisar os processos individualmente, observamos que o PostgreSQL teve um aumento expressivo no consumo, enquanto o Python apresentou uma redução no uso médio e valores de pico muito próximos entre as arquiteturas. Diferentemente do observado na memória RAM, a redução no Python não foi suficiente para compensar o aumento no PostgreSQL.

**Tabela 3 — Consumo médio e pico médio de CPU por dataset, arquitetura e processo (%)**

| Dataset | Indicador | ETL (%) | ELT (%) | Variação (%) |
|---|---|---:|---:|---:|
| ENEM | Consumo médio total | 102,1 | 107,5 | +5,2% |
| ENEM | Consumo médio Python | 70,3 | 64,1 | -8,7% |
| ENEM | Consumo médio PostgreSQL | 31,9 | 43,3 | +36,0% |
| ENEM | Pico médio total | 151,2 | 191,8 | +26,9% |
| ENEM | Pico médio Python | 101,8 | 102,7 | +0,8% |
| ENEM | Pico médio PostgreSQL | 102,3 | 158,8 | +55,2% |
| TSE | Consumo médio total | 100,7 | 110,2 | +9,5% |
| TSE | Consumo médio Python | 96,6 | 61,7 | -36,2% |
| TSE | Consumo médio PostgreSQL | 4,1 | 48,6 | +1.093,8% |
| TSE | Pico médio total | 119,5 | 160,2 | +34,1% |
| TSE | Pico médio Python | 103,2 | 102,8 | -0,3% |
| TSE | Pico médio PostgreSQL | 21,4 | 130,6 | +509,8% |
| **Média** | **Consumo médio total** | **101,4** | **108,8** | **+7,3%** |
| Média | Consumo médio Python | 83,4 | 62,9 | -24,6% |
| Média | Consumo médio PostgreSQL | 18,0 | 45,9 | +155,7% |
| **Média** | **Pico médio total** | **135,4** | **176,0** | **+30,0%** |
| Média | Pico médio Python | 102,5 | 102,7 | +0,2% |
| Média | Pico médio PostgreSQL | 61,9 | 144,7 | +133,9% |

### Consumo médio:
- No dataset do ENEM, o ETL usou 102% e no ELT 107%, diferença de 5,3 pontos percentuais, 5,2%.
- No dataset do TSE, o ETL usou 101% e no ELT 110%, diferença de 9,6 pontos percentuais, 9,5%.
- Unindo ambos, o ETL usou 101% e o ELT 109%, diferença de 7,4 pontos percentuais, 7,3%.

### Consumo médio por processo:
- No ENEM, o ETL teve 32% no PostgreSQL e 70% no Python. Enquanto que no ELT teve 43% no PostgreSQL e 64% no Python. Aumento de 11,5 pontos percentuais, 36,0%, no PostgreSQL. No Python, redução de 6,1 pontos percentuais, 8,7%.
- No TSE, o ETL teve 4% no PostgreSQL e 97% no Python. Enquanto que no ELT teve 49% e 62%. No PostgreSQL, aumento de 44,5 pontos percentuais, 1.093,8%. No Python houve uma queda de 34,9 pontos percentuais, 36,2%.
- Ao unir ambos os datasets, o ETL teve 18% no PostgreSQL e 83% no Python. No ELT 46% e 63%. No PostgreSQL, aumento de 28,0 pontos percentuais, 155,7%. No Python redução de 20,5 pontos percentuais, 24,6%.

### Pico médio de consumo:
- No dataset do ENEM, o ETL usou 151% e no ELT 192%, diferença de 40,6 pontos percentuais, aumento de 26,9%.
- No dataset do TSE, o ETL usou 120% e no ELT 160%, diferença de 40,7 pontos percentuais, aumento de 34,1%.
- Unindo ambos, o ETL teve pico médio de 135% e o ELT 176%, diferença de 40,7 pontos percentuais, aumento de 30,0%.

### Pico médio por processo:
- No ENEM, o pico médio do ETL foi de 102% no PostgreSQL e 102% no Python. O ELT apresentou 159% no PostgreSQL e 103% no Python. O PostgreSQL teve um aumento de 56,5 pontos percentuais, 55,2%. Enquanto que o Python teve um aumento de 0,9 ponto percentual, 0,8%.
- No TSE, o pico médio do ETL foi de 21% no PostgreSQL e 103% no Python. O ELT apresentou 131% no PostgreSQL e 103% no Python. O PostgreSQL teve um aumento de 109,2 pontos percentuais, 509,8%. Enquanto que o Python teve uma redução de 0,4 ponto percentual, 0,3%.
- Unindo os datasets, no ETL o PostgreSQL teve pico médio de 62% e Python 102%. No ELT foi de 145% e 103%, respectivamente. O PostgreSQL teve um aumento de 82,9 pontos percentuais, 133,9%. Enquanto que o Python apresentou um aumento de 0,3 ponto percentual, 0,2%.

## Throughput:
- De forma geral, o ETL apresentou um throughput médio superior ao ELT, embora o comportamento tenha variado entre os datasets. No ENEM, o ELT apresentou uma ligeira vantagem, enquanto no TSE o ETL alcançou um throughput consideravelmente maior. Considerando ambos os datasets, o ELT apresentou um throughput médio 33,4% inferior ao ETL.

**Tabela 4 — Throughput médio por dataset e arquitetura (registros/s)**

| Dataset | ETL (registros/s) | ELT (registros/s) | Variação (%) |
|---|---:|---:|---:|
| ENEM | 51.698 | 56.148 | +8,6% |
| TSE | 88.732 | 37.379 | -57,9% |
| **Média** | **70.215** | **46.764** | **-33,4%** |

### Throughput médio:
- No dataset do ENEM, o ETL registrou 51.698 registros/s, enquanto o ELT alcançou 56.148 registros/s (diferença de 4.450 registros/s / aumento de 8,6%).
- No dataset do TSE, o ETL registrou 88.732 registros/s, enquanto o ELT alcançou 37.379 registros/s (diferença de 51.352 registros/s / redução de 57,9%).
- Unindo ambos os datasets, o ETL registrou 70.215 registros/s e o ELT 46.764 registros/s (diferença de 23.451 registros/s / redução de 33,4%).

---

**Nota metodológica das tabelas:** Os valores representam médias das execuções do primeiro benchmark. As variações percentuais foram calculadas utilizando os valores originais, sem arredondamento intermediário, tendo o ETL como referência. Valores positivos representam aumento do indicador no ELT; valores negativos representam redução. As médias conjuntas atribuem o mesmo peso às execuções dos dois datasets, pois ambos possuem a mesma quantidade de execuções.