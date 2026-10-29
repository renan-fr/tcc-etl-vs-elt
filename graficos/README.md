# Gráficos científicos

Este diretório gera as duas figuras iniciais da subseção 4.1 — Tempo de Processamento — diretamente dos CSVs dos benchmarks. O script usa `tempo_total`, em segundos, e considera apenas as rodadas válidas `1` a `5`. Os aquecimentos não são gravados nos arquivos de resultados e, portanto, não entram nas médias.

## Dependências

Na raiz do projeto, instale as dependências com:

```text
python -m pip install -r requirements.txt
```

As bibliotecas específicas desta geração são Pandas e Matplotlib.

## Execução

A partir da raiz do projeto:

```text
python graficos/gerar_graficos.py
```

O script lê os quatro arquivos em `data/benchmark/{enem,tse}/resultados/`. Os CSVs são separados por `;` e os tempos usam vírgula como separador decimal. Antes de gerar os arquivos, o script valida colunas, volumes, rodadas, duplicidades e a quantidade de observações por cenário, imprimindo no terminal as contagens e médias.

As saídas ficam em subpastas temáticas de `graficos/figuras/`. As figuras desta tarefa ficam em `graficos/figuras/tempo_processamento/`:

- `tempo_medio_geral.pdf`: média por arquitetura;
- `tempo_medio_dataset.pdf`: média por conjunto de dados e arquitetura;
- `tempo_medio_volume_enem.pdf`: linhas de ETL e ELT por volume nominal no ENEM;
- `tempo_medio_volume_tse.pdf`: linhas de ETL e ELT por volume nominal no TSE.

As figuras de linhas usam a média das cinco rodadas válidas de cada volume nominal. Novos temas devem usar uma subpasta própria, evitando misturar arquivos de métricas diferentes. A única saída gerada é o PDF vetorial. Para atualizar após alterar os CSVs, execute novamente o mesmo comando. Os CSVs originais e os scripts dos benchmarks não são modificados.
