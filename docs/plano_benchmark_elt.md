# Plano de implementação do benchmark ELT

## Objetivo

Integrar o pipeline ELT do ENEM ao mesmo protocolo experimental já definido para
o ETL, garantindo que os dois pipelines usem os mesmos arquivos, subconjuntos,
volumes, regras de negócio e critérios de medição.

O resultado final esperado é uma execução reproduzível de cada cenário, com
métricas comparáveis e uma verificação automática de equivalência entre as
tabelas finais do ETL e do ELT.

## Estado de partida

- `src/elt/enem_elt.py` já carrega os arquivos em tabelas `raw` via `COPY`.
- O script já executa as transformações SQL para as tabelas finais do schema
  `elt`.
- O parâmetro `--limite` já limita cada arquivo de forma determinística.
- O ELT mede carga RAW, transformação SQL, validação e tempo total, mas ainda não
  produz o contrato completo de métricas usado pelo ETL.
- `src/benchmark.py` está vazio e poderá ser usado posteriormente como
  orquestrador das rodadas, depois que os dois pipelines tiverem interfaces
  compatíveis.

## Escopo da primeira implementação

A primeira versão deve cobrir somente o ENEM, nos volumes de 100k, 500k, 1M e
3M por arquivo, com os schemas `raw` e `elt`. A base TSE e análises gráficas
ficam fora desta etapa.

## Etapas planejadas

### 1. Fechar a interface de execução do ELT

Adicionar ao `src/elt/enem_elt.py` os parâmetros equivalentes aos disponíveis no
ETL:

- `--benchmark`;
- `--benchmark-output`;
- `--benchmark-summary-output`;
- `--rodada`;
- `--aquecimento`;
- schema RAW e schema final configuráveis, se isso for necessário para executar
  ETL e ELT no mesmo banco sem colisões.

O modo normal de execução deve continuar funcionando sem benchmark. No modo de
benchmark, a execução deve usar `replace`, recriando as tabelas do cenário para
evitar resíduos de rodadas anteriores.

### 2. Padronizar as métricas

O ELT deve emitir o mesmo registro estruturado do ETL, preservando os campos
atuais e preenchendo-os com a semântica correspondente:

- leitura: abertura e preparação dos arquivos de origem;
- transformação: criação das tabelas finais e execução dos `SELECT`/`CREATE`;
- carga: criação e carga das tabelas RAW;
- validação: consultas de contagem, estrutura e regras do resultado;
- total: desde o início do processo até a conclusão do resultado final;
- throughput: quantidade total de registros dos dois arquivos dividida pelo
  tempo total.

CPU e RAM deverão ser coletadas com o mesmo monitoramento usado pelo ETL,
separando Python, PostgreSQL e o total combinado quando tecnicamente possível.

### 3. Completar a validação do ELT

Implementar validações SQL equivalentes às validações críticas do ETL:

- colunas e tipos do contrato final;
- identificadores nulos ou duplicados;
- domínios categóricos;
- intervalo das notas;
- consistência de UF e região;
- cálculo de `nota_media_objetivas`;
- regra de `presente_completo`.

Erros críticos devem interromper a execução e impedir que o resultado seja
registrado como válido.

### 4. Criar a comparação de equivalência

Depois de uma execução ETL e uma execução ELT com o mesmo volume, comparar as
tabelas finais por:

1. quantidade de linhas;
2. nomes, ordem e tipos das colunas;
3. chaves e valores;
4. quantidade de nulos;
5. hash determinístico ou comparação ordenada por registro.

A comparação deve gerar um relatório explícito de divergências. Diferenças de
resultado serão tratadas como falha do cenário, não como variação aceitável de
implementação.

### 5. Extrair a orquestração para `src/benchmark.py`

Quando as interfaces ETL e ELT estiverem estáveis, o orquestrador deverá:

- definir os cenários por dataset, volume e arquitetura;
- executar um aquecimento por cenário;
- executar cinco rodadas válidas;
- randomizar a ordem dos cenários com seed registrada;
- reutilizar exatamente os mesmos volumes em todas as rodadas;
- consolidar os CSVs de métricas;
- executar a comparação de equivalência fora do tempo principal, ou registrar
  claramente essa etapa como validação pós-processamento.

O orquestrador não deve duplicar regras de transformação nem alterar os dados
de entrada de cada pipeline.

## Critérios de aceite

- Uma execução ELT de cada volume produz um registro no mesmo formato do ETL.
- O modo de aquecimento é identificado e não entra nas estatísticas finais.
- As tabelas finais do ETL e do ELT passam na comparação de equivalência para um
  volume pequeno antes da execução dos volumes oficiais.
- A carga RAW, a transformação SQL e o tempo total aparecem separadamente.
- Uma falha de validação ou equivalência interrompe o cenário e fica registrada.
- O protocolo de cinco rodadas e a seed da randomização podem ser reproduzidos.
- A documentação de metodologia e os resultados identificam que, no ENEM, o
  volume é aplicado separadamente a cada arquivo de origem.

## Ordem recomendada de implementação

1. Refatorar o retorno do ELT para o contrato de métricas comum.
2. Reutilizar ou extrair o monitoramento de CPU/RAM do ETL.
3. Implementar validações SQL e mensagens de falha.
4. Adicionar a comparação ETL × ELT em volume pequeno.
5. Adicionar flags de benchmark e persistência dos resultados.
6. Implementar o orquestrador das rodadas em `src/benchmark.py`.
7. Executar piloto de 100k e revisar métricas, equivalência e consumo de
   recursos antes dos demais volumes.

## Pendências e riscos

- O interpretador do `.venv` está indisponível e precisa ser recuperado antes
  da execução oficial.
- É preciso evitar colisão entre tabelas `raw`/`elt` e `etl` durante cenários
  consecutivos no mesmo banco.
- A coleta de CPU/RAM do PostgreSQL precisa manter a mesma definição usada no
  ETL para que a comparação seja válida.
- A ordenação usada na comparação deve ser determinística mesmo quando não
  houver uma chave comum entre participantes e resultados.
- O tempo da validação deve ser separado do tempo principal conforme a
  metodologia, sem deixar de ser registrado.
