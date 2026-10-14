# Plano do benchmark TSE

O TSE será o cenário de maior complexidade do experimento, sem exigir a
construção de um produto eleitoral completo. O resultado será uma consolidação
por eleição, turno, município, zona e cargo.

## Fontes utilizadas

- `detalhe_votacao_munzona_2024`: tabela-base da totalização municipal;
- `detalhe_votacao_secao_2024`: fonte detalhada, agregada de seção para
  município/zona/cargo;
- `votacao_candidato_munzona_2024`: votos por candidato, agregados e usados
  para métricas de ranking.

`votacao_partido_munzona_2024` não será utilizada neste momento. Os arquivos
`BRASIL` também ficarão fora do benchmark principal, pois duplicam o universo
dos arquivos estaduais.

## Fluxo lógico

```text
munzona
seção      -> agregação por município/zona/cargo
candidato  -> agregação e ranking por município/zona/cargo
             ↓
          joins
             ↓
          processed
```

Cada fonte deverá ser agregada antes dos joins para evitar multiplicação de
registros. ETL e ELT deverão executar as mesmas etapas e produzir o mesmo
contrato final.

## Separação de resultados

Os resultados futuros do TSE deverão ser gravados em:

```text
data/benchmark/tse/resultados/
data/benchmark/tse/resumos/
```
