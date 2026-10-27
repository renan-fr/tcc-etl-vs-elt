# Análises do primeiro Benchmark

## Tempos de processamento:
- De forma geral, o ETL se saiu melhor nessa métrica, se provou 37% mais veloz unindo ambos os datasets. 
- Apesar disso, por conta da possível anomalia na carga do ENEM, o ETL foi 23% mais lento que o ELT. 
- O TSE teve o ETL 103% mais veloz que o ELT. 

### Carga (Anomalia a investigar):
-  No dataset do ENEM tivemos um número assustador na carga do ELT: 18,9 segundos. Em comparação, o ETL do TSE carregou em 0,3 segundos. Um diferença de 18,6 seg / aumento de 6.200%. Acredito ser por conta do ENEM ter de carregar duas tabelas, diferente do TSE que carrega apenas uma. Porém, mesmo assim, a diferença é assustadora, analisarei.
- No dataset do TSE o número foi próximo. O ETL registrou 0,3 segundos enquanto que o ELT 0,9 segundos (diferença de 0,6 segundos / aumento de 200%)

### Leitura e transformação:
- No ELT, em ambos a leitura e transformação registraram tempos superiores. No TSE, correspondedo a leitura e transformação respectivamente, tivemos 5,4 para 14,8 (diferença de 9,4 seg / aumento de 174%) e 5,7 para 12,6 (diferença de 6,9 seg / aumento de 121%).
- No ENEM, na leitura tivemos  1,9 e subimos pra 10,2 (diferença de 8,3 seg / aumento de 436%). E na transformação fomos de 1,6 pra 6,7 (diferença de 5,1 seg / aumento de 318%).

### Tempos totais:
- Quanto aos tempos totais, no dataset do ENEM tivemos 22,4 de tempo total do ETL e 18,1 do ELT (diferença de 4,3 seg / redução de 19%). O elevadíssimo tempo de carga do ETL nesse dataset foi o que compensou a vantagens do ETL nas outras etapas.
- No dataset do TSE, o ETL teve 11,4 segundos e no ELT 23,2 (diferença de 11,8 segundos / aumento de 103%). 
- Abrangendo ambos os datasets em uma única média, o ETL teve 16,9 segundos e o ELT 23,2, uma diferença de 6,3 segundos e um aumento percentual de 37%.

## Consumo de Memória RAM:
- 

### Consumo médio:
- No dataset do ENEM, o ETL utilizou 531MB de RAM enquanto que o ELT consumiu 78MB (diferença de 453MB / redução de 85%).
- No dataset do TSE, o ETL consumiu 243MB de RAM enquanto que o ELT 82MB (dif.erença de 161MB / redução de 66%)
- Unindo os datasets, o ETL registrou 387MB e ELT 80MB (diferença de 307 / redução de 79%).

### Pico médio de consumo:
- No ENEM o pico médio do ETL foi 729MB e no ELT 88MB (diferença de 641MB / redução de 88%)
- No TSE o pico médio do ETL foi 310MB e no ELT 96MB (diferença de 214MB / redução de 69%)
- Unindo os datasets, o ETL registrou 520MB e o ELT 92MB (diferença de 428MB / redução de 82%)