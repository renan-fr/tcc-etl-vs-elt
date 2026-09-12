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
- Implementar o benchmark em `src/benchmark.py`.
- Documentar melhor as bases em `docs/datasets.md`.
- Fechar as transformacoes da base TSE.
- Registrar versoes de Python, PostgreSQL e bibliotecas.
- Definir formato final de armazenamento dos resultados.
- Criar graficos e analises comparativas.

## Decisoes recentes

- Criamos `AGENTS.md` para lembrar de atualizar este arquivo a cada passo relevante.
- Adicionamos `AGENTS.md` ao `.gitignore`, mantendo essa instrucao apenas local.

## O que revisar antes de continuar

- Conferir se o contrato do ENEM em `docs/metodologia.md` bate com `src/etl/enem_etl.py`.
- Conferir se os nomes das colunas finais estao adequados para os graficos.
- Avaliar se `Nao informado` deve manter acento na saida final.
- Verificar se a regra de presenca da redacao esta correta para o ENEM.
- Decidir se o benchmark medira Python e PostgreSQL separadamente ou juntos.
