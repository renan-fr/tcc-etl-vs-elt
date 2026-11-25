# Experimento de validação da USS

Este diagnóstico mede o efeito da remoção de processos PostgreSQL durante a
leitura de CPU, antes da leitura de USS. Ele não modifica o monitor nem os
pipelines oficiais.

Cada execução usa um único `MonitorUSSValidacao`, com intervalo de 0,5 segundo,
e produz duas consolidações a partir das mesmas amostras:

- `original`: mantém exatamente as amostras aceitas pelo monitor oficial;
- `corrigida`: exclui também as amostras nas quais pelo menos um processo
  PostgreSQL foi removido durante a leitura de CPU.

O plano contém um aquecimento e cinco medições de cada cenário:

- ENEM ELT, 100 mil registros nominais;
- ENEM ELT, 1 milhão de registros nominais;
- TSE ELT, 100 mil registros nominais.

As execuções são isoladas em subprocessos e embaralhadas por fase com a mesma
seed da campanha oficial. As validações internas dos pipelines permanecem
desativadas, como na modalidade oficial de recursos.

## Execução

A partir da raiz do repositório, com o PostgreSQL e o ambiente configurados:

```powershell
.\.venv\Scripts\python.exe src\experimental\uss_validation.py --run-id uss_validation_01
```

O comando cria exclusivamente
`data/experimentos/uss_validation/<run-id>/`. Um identificador já existente é
recusado para impedir sobrescrita.

## Artefatos

Cada execução possui um diretório próprio contendo:

- `resumo.json`: contagens, USS média e pico nos dois critérios e diferenças
  absolutas e percentuais;
- `amostras.jsonl`: agregados originais, USS por PID e marcação da amostra
  afetada;
- `eventos.jsonl`: descoberta de processos e encerramentos observados durante
  CPU ou USS.

Na raiz do `run-id`, `resumos.csv` reúne as 18 execuções e
`experimento.json` registra plano, seed, commit, versões e estado da execução.
