# Anotacoes para revisao do projeto

## Contexto do projeto

- Tema: comparacao de desempenho entre ETL e ELT.
- Objetivo: identificar em quais cenarios ETL ou ELT apresenta melhor desempenho.
- Bases planejadas:
  - ENEM: menor complexidade.
  - TSE: maior complexidade.
- Volumes planejados: 100k, 500k, 1M e 3M registros.

## Estrutura atual

- `data/raw/`: arquivos brutos das bases.
- `docs/`: documentacao do projeto.
- `notebooks/`: exploracao dos dados e analises.
- `src/`: scripts Python do pipeline.
- `README.md`: instrucoes basicas de execucao.
- `AGENTS.md`: instrucoes locais para lembrar de atualizar estas anotacoes.

## Metodologia definida

- Comparar ETL e ELT usando os mesmos dados e volumes.
- Medir tempo total, tempos por etapa, throughput, CPU e memoria.
- Fazer 1 execucao de aquecimento e 5 execucoes validas por cenario.
- Randomizar a ordem dos testes para reduzir vieses.
- Usar PostgreSQL como banco de destino.
- Preferir `COPY` para carga em massa.

## ENEM - estado atual

- Pipeline ETL implementado em `src/etl/enem_etl.py`.
- O script concentra extração, transformação, validação, carga PostgreSQL via
  `COPY` e instrumentação do benchmark.
- Existe um resultado de benchmark ETL registrado em `data/benchmark/`, mas
  `src/benchmark.py` ainda está vazio.
- A reexecução operacional ficou pendente nesta revisão porque o `.venv`
  aponta para um executável Python que não está mais disponível no ambiente.
- Arquivos esperados:
  - `PARTICIPANTES_2024.csv`
  - `RESULTADOS_2024.csv`
- Tabelas finais:
  - `enem_participantes`
  - `enem_resultados`
- As tabelas sao independentes, sem `JOIN` obrigatorio.

## ENEM - regras principais

- Codigos originais sao convertidos para textos legiveis.
- Textos ausentes ou desconhecidos viram `Nao informado`.
- Valores desconhecidos sao registrados em relatorio.
- Regiao e derivada a partir da UF.
- `nota_media_objetivas` usa CN, CH, LC e MT.
- `presente_completo` exige presenca em CN, CH, LC, MT e redacao.

## Validacoes implementadas

- Estrutura das colunas finais.
- Identificadores nulos ou duplicados.
- Categorias fora do dominio esperado.
- Notas fora do intervalo 0 a 1000.
- Consistencia entre UF e regiao.
- Consistencia da media objetiva.
- Consistencia do campo `presente_completo`.
- Erros criticos interrompem a carga.

## Carga e configuracao

- Carga feita no PostgreSQL via `COPY`.
- Schema configuravel por parametro ou `.env`.
- Suporte a `replace` e `append`.
- Conexao via `DATABASE_URL` ou variaveis separadas:
  - `POSTGRES_HOST`
  - `POSTGRES_PORT`
  - `POSTGRES_DB`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`

## Pontos pendentes

- Implementar o pipeline ELT.
- Recuperar/recriar o ambiente Python e reexecutar a validação do ETL antes da
  comparação final.
- Definir e implementar o carregamento bruto do ELT, as tabelas RAW e as
  transformações SQL equivalentes ao contrato do ENEM.
- Implementar o benchmark em `src/benchmark.py`.
- Documentar melhor as bases em `docs/datasets.md`.
- Fechar as transformacoes da base TSE.
- Registrar versoes de Python, PostgreSQL e bibliotecas.
- Definir formato final de armazenamento dos resultados.
- Criar graficos e analises comparativas.

## Decisoes recentes

- Criamos `AGENTS.md` para lembrar de atualizar este arquivo a cada passo relevante.
- Adicionamos `AGENTS.md` ao `.gitignore`, mantendo essa instrucao apenas local.
- Adicionada RAM media ao benchmark como metrica complementar; RAM pico continua sendo a referencia principal de memoria.

## O que revisar antes de continuar

- Conferir se o contrato do ENEM em `docs/metodologia.md` bate com `src/etl/enem_etl.py`.
- Conferir se os nomes das colunas finais estao adequados para os graficos.
- Avaliar se `Nao informado` deve manter acento na saida final.
- Verificar se a regra de presenca da redacao esta correta para o ENEM.
- Decidir se o benchmark medira Python e PostgreSQL separadamente ou juntos.

## Revisao do planejamento do ELT - ENEM

- O desenho metodologico esta adequado: `arquivos CSV -> PostgreSQL RAW -> SQL ->
  tabelas finais`.
- Para o ENEM, a ausencia de uma camada `staging` e coerente com a metodologia,
  pois as transformacoes sao independentes e o objetivo e comparar com o ETL.
- O ELT devera reproduzir o contrato final, as regras de mapeamento, os nulos,
  as regioes, a media objetiva e `presente_completo` do ETL.
- O contrato final do ELT foi fechado: RAW preserva a origem e as tabelas finais
  devem ser exatamente equivalentes as tabelas finais do ETL.
- Pontos que podem ser tratados diretamente na implementacao: SQL dos
  mapeamentos, consultas de validacao, carga via `COPY` e organizacao do script.

### Decisoes para a medicao do ELT

- A camada RAW permanecera cruamente representada, com colunas da origem e sem
  mapeamentos ou regras derivadas.
- O modo `replace` sera utilizado nas rodadas principais para garantir execucoes
  independentes e repetiveis.
- O tempo principal sera medido pelo relogio do processo executor, envolvendo
  cada operacao PostgreSQL e incluindo execucao, transferencia e `COMMIT`.
- O ELT registrara separadamente carga RAW, transformacao SQL e validacao, alem
  do tempo total do pipeline.
- Metricas internas como `EXPLAIN ANALYZE` ou `pg_stat_statements` serao
  complementares/diagnosticas, sem substituir o tempo de parede do benchmark.

### Contrato ELT encerrado

- Nao ha novas decisoes de regra de negocio previstas para o ELT.
- Divergencias encontradas durante a implementacao serao tratadas como erros a
  corrigir, e nao como variacoes aceitaveis do resultado final.

## Inicio da implementacao do ELT - ENEM

- Criado o esqueleto `src/elt/enem_elt.py`.
- O primeiro esqueleto cria tabelas RAW com as colunas originais do CSV em
  `TEXT`, carrega os arquivos por `COPY`, cria tabelas finais por SQL e mede
  carga RAW, transformacao, validacao e tempo total.
- O parametro `--limite` foi implementado com a mesma semantica do ETL: limita
  as linhas de cada arquivo, preservando a ordem; `0` carrega todos os registros.
- A implementacao ainda e uma primeira etapa: permanecem a validacao completa,
  o suporte efetivo aos volumes de benchmark, a coleta de CPU/RAM e a
  comparacao automatica entre ETL e ELT.
- A tentativa de iniciar os testes em 21/09/2026 foi bloqueada porque o Python
  do `.venv` nao esta disponivel; o ambiente aponta para um executavel removido.
- O PostgreSQL 18 esta instalado e disponivel (`psql`, `postgres` e `pg_ctl`),
  mas os testes Python dependem primeiro da recuperacao do interpretador.
- A primeira comparacao identificou divergencias somente em
  `nota_media_objetivas`; o ELT foi ajustado para reproduzir o arredondamento
  half-even usado pelo `pandas.round(2)` no ETL.

## Roteiro imediato do ELT

1. Revisar e fechar o contrato das tabelas RAW e finais.
2. Implementar o recorte por volume sem alterar a ordem das linhas.
3. Completar as validacoes SQL equivalentes as validacoes do ETL.
4. Executar ETL e ELT com um volume pequeno e comparar os resultados.
5. Corrigir divergencias de tipos, nulos, categorias e regras derivadas.
6. Adicionar monitoramento de CPU/RAM e registro padronizado das metricas.
7. Executar aquecimento e rodadas validas nos volumes definidos na metodologia.
8. Consolidar resultados, equivalencia e graficos comparativos.

## Inicio do planejamento do benchmark ELT

- Criado `docs/plano_benchmark_elt.md` com o plano de integracao do ELT ao
  protocolo experimental.
- A primeira etapa do benchmark ficara restrita ao ENEM e aos volumes de 100k,
  500k, 1M e 3M por arquivo, antes da incorporacao da base TSE.
- O trabalho foi dividido em interface de execucao, metricas padronizadas,
  validacao SQL, comparacao de equivalencia e orquestracao das rodadas.
- A ordem recomendada e validar primeiro um piloto pequeno e somente depois
  executar as cinco rodadas oficiais.
- Pendencias relevantes confirmadas: recuperar o interpretador do `.venv`,
  evitar colisao de tabelas entre pipelines e alinhar a coleta de CPU/RAM.

## Diagnostico do estado em 26/09/2026

- O ETL do ENEM possui transformacao, validacoes, carga via `COPY` e coleta de
  metricas; existe apenas uma rodada registrada para 100k.
- O ELT ainda e um esqueleto: usa schemas fixos, valida somente contagens e nao
  possui a interface nem as metricas completas do benchmark.
- `src/benchmark.py` continua vazio; a orquestracao, a comparacao ETL x ELT e a
  analise dos resultados ainda nao foram implementadas.
- A base TSE esta presente em `data/raw`, mas ainda nao existe pipeline TSE em
  `src/`; ela deve ficar para depois da validacao completa do ENEM.
- Proxima sequencia recomendada: recuperar o ambiente Python, completar o ELT,
  criar a comparacao de equivalencia, executar um piloto pequeno e somente
  depois implementar/orquestrar as rodadas oficiais.

## Acoplamento inicial do benchmark ao ELT

- `src/elt/enem_elt.py` passou a aceitar schemas RAW/final configuraveis.
- Adicionadas as opcoes `--benchmark`, `--benchmark-output`,
  `--benchmark-summary-output`, `--rodada` e `--aquecimento`.
- Adicionado registro estruturado das metricas de tempo, throughput, CPU e RAM
  no formato equivalente ao ETL.
- A medicao ainda precisa ser executada e revisada com Python/PostgreSQL. A
  leitura/preparacao dos arquivos agora e registrada separadamente da criacao
  das tabelas RAW, `COPY` e contagem da carga RAW; a leitura direta do arquivo
  completo continua ocorrendo durante o `COPY`, por isso essa definicao deve
  ser mantida igual em todos os cenarios.
- As validacoes SQL ainda estao limitadas a contagem de linhas.

## Primeiro piloto ETL x ELT

- Executado piloto com 1.000 registros por arquivo, usando schemas separados
  para ETL, RAW e ELT.
- As quantidades de registros foram equivalentes nas duas tabelas finais.
- Foi criado `src/comparar_equivalencia.py` para verificar contagens e
  diferencas registro a registro com `EXCEPT ALL`.
- A primeira comparacao encontrou 54 divergencias em `nota_media_objetivas`.
- A causa foi a diferenca entre o arredondamento sobre `float` no pandas e o
  calculo exato em `numeric` no PostgreSQL; a formula SQL foi ajustada para
  preservar a semantica do ETL.
- O piloto foi repetido e terminou com equivalencia total nas tabelas
  `enem_participantes` e `enem_resultados`.

## Preparacao para execucao manual dos benchmarks

- O `README.md` foi simplificado para documentar somente preparacao, execucao
  manual do ETL/ELT, aquecimento, cinco rodadas, comparacao de equivalencia e
  local dos CSVs de metricas.
- As interfaces de linha de comando dos dois pipelines foram verificadas com
  `--help` e estao prontas para os benchmarks manuais.

## Organizacao dos resultados de benchmark

- Os resultados foram padronizados em `data/benchmark/resultados/` e os
  resumos em `data/benchmark/resumos/`.
- Os CSVs passaram a arredondar tempos para tres casas e demais metricas
  numericas para duas casas, mantendo a leitura adequada para analise.
- Arquivos gerados antigos de pilotos e execucoes anteriores foram removidos;
  os resultados podem ser recriados pelos comandos documentados no README.

## Orquestrador rudimentar do benchmark

- `src/benchmark.py` foi implementado para executar, por volume, um
  aquecimento e a quantidade configurada de rodadas ETL e ELT.
- O script recebe volumes, quantidade de rodadas, diretorio de resultados e
  executavel Python por parametros.
- A primeira versao nao compara resultados nem produz analise; apenas chama os
  pipelines e acumula os CSVs e resumos.
- O teste tecnico com um volume e uma rodada foi concluido com sucesso.
