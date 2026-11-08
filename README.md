# Benchmark ETL × ELT

Este projeto compara duas formas de implementar o mesmo processamento de dados:

- ETL: leitura, transformação e carga realizadas principalmente em Python;
- ELT: carga inicial no PostgreSQL e transformações executadas no banco com SQL.

Os cenários são os microdados do ENEM 2024, com transformações por registro, e
os resultados eleitorais do TSE 2024, com múltiplas fontes, agregações e joins.
O experimento mede o comportamento dessas implementações específicas em Python,
Pandas e PostgreSQL. Os resultados não representam uma superioridade universal
de ETL ou ELT.

## Índice

- [Fluxo resumido](#fluxo-resumido)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração do PostgreSQL](#configuração-do-postgresql)
- [Dados de entrada](#dados-de-entrada)
- [Preparação dos subconjuntos TSE](#preparação-dos-subconjuntos-tse)
- [Certificação de equivalência](#certificação-de-equivalência)
- [Execução do benchmark](#execução-do-benchmark)
- [Resultados e metadados](#resultados-e-metadados)
- [Geração de gráficos](#geração-de-gráficos)
- [Problemas comuns](#problemas-comuns)
- [Documentação complementar](#documentação-complementar)

## Fluxo resumido

```text
clonar o repositório
  → instalar as dependências Python
  → criar/configurar um PostgreSQL dedicado
  → obter e organizar os dados oficiais
  → preparar ou conferir os manifestos TSE
  → certificar a equivalência ETL × ELT
  → executar uma campanha com o orquestrador
  → consultar CSVs, metadados e gráficos da campanha
```

A execução é local. O projeto não baixa dados automaticamente e depende de um
PostgreSQL acessível durante a certificação e o benchmark.

## Pré-requisitos

São necessários:

- Git;
- Python com suporte a `venv` e `pip`;
- PostgreSQL acessível localmente ou pela rede;
- espaço em disco para os microdados oficiais e as tabelas carregadas.

O projeto não declara uma versão mínima de Python ou PostgreSQL em seus arquivos
de configuração. Use uma versão compatível com as dependências fixadas em
`requirements.txt`. A campanha oficial foi preparada para Windows; os scripts
usam caminhos do Python e podem funcionar em outros sistemas, mas essa
compatibilidade não é aqui assegurada.

## Instalação

O repositório público é:

```powershell
git clone https://github.com/renan-fr/tcc-etl-vs-elt.git
cd tcc-etl-vs-elt
```

No Windows PowerShell, crie e ative um ambiente virtual e instale as
dependências:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Em outro sistema, adapte apenas a ativação do ambiente virtual, por exemplo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

As versões instaladas pelo projeto estão em `requirements.txt`, incluindo
Pandas, Matplotlib, `python-dotenv`, SQLAlchemy, `psycopg2-binary` e `psutil`.

## Configuração do PostgreSQL

Use um banco dedicado ao experimento. Ele pode ser criado ou selecionado com
`psql`, pgAdmin ou outra ferramenta administrativa disponível no ambiente.
Não use um banco de produção: os pipelines criam schemas, removem tabelas das
suas próprias áreas e recriam tabelas durante as execuções.

O banco informado em `POSTGRES_DB` precisa existir antes da certificação ou do
benchmark. Crie-o com uma ferramenta administrativa, como pgAdmin, ou conectado
ao PostgreSQL pelo `psql` com uma role que tenha permissão para criar bancos,
usando o comando SQL `CREATE DATABASE`. Depois, informe no `.env` o nome do
banco criado e use um usuário com permissão para conectar, criar schemas e
tabelas e executar as operações de carga.

Copie o modelo de configuração:

```powershell
Copy-Item .env.example .env
```

Preencha no `.env` os valores reais da instalação local:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nome_do_banco_dedicado
POSTGRES_USER=usuario_com_permissao_de_conexao
POSTGRES_PASSWORD=senha_local
```

O modelo também define os schemas usados pelo projeto:

```text
POSTGRES_SCHEMA_ENEM_ETL_FINAL=enem_etl_final
POSTGRES_SCHEMA_ENEM_ELT_RAW=enem_elt_raw
POSTGRES_SCHEMA_ENEM_ELT_FINAL=enem_elt_final
POSTGRES_SCHEMA_TSE_ETL_FINAL=tse_etl_final
POSTGRES_SCHEMA_TSE_ELT_RAW=tse_elt_raw
POSTGRES_SCHEMA_TSE_ELT_STAGING=tse_elt_staging
POSTGRES_SCHEMA_TSE_ELT_FINAL=tse_elt_final
```

O usuário configurado precisa conseguir conectar ao banco e criar schemas e
tabelas, além de executar as operações de carga. Os scripts não exigem uma
senha ou credencial específica do projeto; use somente credenciais locais.

## Dados de entrada

Os dados brutos precisam ser baixados manualmente. Nenhum download acontece
durante a certificação ou o benchmark. Use os portais oficiais:

- [Microdados do ENEM — INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem), pacote de 2024;
- [Resultados 2024 — Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2024).

Após o clone, existem apenas as pastas `data/raw/enem/` e `data/raw/tse/`, cada
uma com seu arquivo `.gitkeep`. As subpastas internas serão criadas durante a
extração dos pacotes oficiais. Os arquivos baixados não são rastreados pelo
Git; preserve nomes, colunas, codificação e delimitadores.

### Verificação da integridade dos dados

O repositório disponibiliza o arquivo `data/benchmark/integridade/hashes_fontes.sha256`, contendo os hashes SHA-256 dos 84 arquivos utilizados como referência para o experimento. O manifesto contempla os dois CSVs do ENEM, os arquivos estaduais das três fontes do TSE e os quatro manifestos de seleção dos subconjuntos.

Após preparar os dados de entrada, é possível verificar sua correspondência com o manifesto utilizando:

```powershell
Get-Content data/benchmark/integridade/hashes_fontes.sha256 | ForEach-Object {
    $hash, $caminho = $_ -split '  ', 2
    $atual = (Get-FileHash -LiteralPath $caminho -Algorithm SHA256).Hash
    if ($atual -ine $hash) {
        Write-Output "DIVERGENTE: $caminho"
    }
}
```

A ausência de divergências indica que os arquivos encontrados correspondem aos hashes registrados. Essa verificação permite identificar modificações nas fontes, mas não certifica, por si só, sua autenticidade em relação aos arquivos originalmente publicados pelo INEP e pelo TSE.

### ENEM

Na página do INEP, baixe o pacote oficial **Microdados do Enem 2024** e
extraia-o dentro de `data/raw/enem/`, criando `microdados_enem_2024/` e
preservando a subpasta `DADOS/` e seus CSVs:

```text
data/raw/enem/microdados_enem_2024/DADOS/
├── PARTICIPANTES_2024.csv
├── RESULTADOS_2024.csv
└── ITENS_PROVA_2024.csv
```

`PARTICIPANTES_2024.csv` e `RESULTADOS_2024.csv` são obrigatórios para o
benchmark. `ITENS_PROVA_2024.csv` é opcional e não é utilizado. Os leitores ETL
e ELT usam delimitador `;` e codificação `latin-1`; não é necessário renomear os
arquivos.

### TSE

No portal oficial do TSE, abra a seção **Dados e recursos** do conjunto
**Resultados 2024**, baixe os três recursos correspondentes e extraia os pacotes
diretamente em `data/raw/tse/`:

1. **Votação nominal por município e zona**;
2. **Detalhe da apuração por município e zona**;
3. **Detalhe da apuração por seção eleitoral**.

```text
data/raw/tse/
├── votacao_candidato_munzona_2024/
├── detalhe_votacao_munzona_2024/
└── detalhe_votacao_secao_2024/
```

Os arquivos CSV estaduais devem permanecer dentro de suas respectivas pastas,
com os nomes originais. Não é necessário selecionar, mover ou renomear os CSVs
individualmente.

O recurso **Votação em partido por município e zona**, que corresponderia a
`votacao_partido_munzona_2024/`, não faz parte das três fontes usadas pelo
benchmark e não precisa ser baixado.

## Preparação dos subconjuntos TSE

Os manifestos fixam as mesmas chaves de seleção para ETL e ELT. Eles são
necessários para que cada volume use o mesmo subconjunto nas duas arquiteturas.
Os manifestos oficiais já estão versionados em:

```text
data/benchmark/tse/subconjuntos/
├── chaves_100000.csv
├── chaves_250000.csv
├── chaves_500000.csv
└── chaves_1000000.csv
```

Depois de clonar o repositório, não é necessário regenerá-los. Se os dados
brutos forem preparados novamente ou substituídos, o comando real de geração é:

```powershell
python src\tse\preparar_subconjuntos.py
```

Por padrão, arquivos de manifesto já existentes são preservados. A opção
`--sobrescrever` existe para uma regeneração deliberada; não a use na
reprodução da campanha oficial sem verificar que as fontes são as mesmas.
É possível limitar a preparação, por exemplo:

```powershell
python src\tse\preparar_subconjuntos.py --volumes 100000
```

Os volumes suportados pelo orquestrador padrão são `100000`, `250000`, `500000`
e `1000000`. No TSE, o volume nominal seleciona chaves completas de seção; a
quantidade efetivamente processada é registrada separadamente.

## Certificação de equivalência

A certificação deve ocorrer antes da campanha oficial. Ela executa ETL e ELT em
modo de certificação e compara os produtos finais no PostgreSQL; não é uma
medição de desempenho.

Certificação completa do ENEM:

```powershell
python src\enem\benchmark.py --certificar
```

Certificação piloto do ENEM:

```powershell
python src\enem\benchmark.py --certificar --volumes 100000
```

Certificação completa do TSE:

```powershell
python src\tse\benchmark.py --certificar
```

Certificação piloto do TSE:

```powershell
python src\tse\benchmark.py --certificar --volumes 100000
```

As comparações verificam a estrutura e os valores dos produtos finais. No
ENEM, a comparação é feita para as tabelas finais do contrato; no TSE, são
comparadas estrutura, quantidade de linhas e diferenças entre os conjuntos de
linhas. A certificação depende de dados, PostgreSQL e configuração corretos;
este README não afirma que ela foi executada em uma máquina específica.

## Execução do benchmark

Após a certificação, execute a campanha global pelo orquestrador:

```powershell
python src\benchmark.py --run-id oficial_01
```

Com os valores padrão, o comando usa:

- volumes `100000`, `250000`, `500000` e `1000000`;
- cinco rodadas válidas (`--rodadas 5`);
- uma execução de aquecimento por cenário;
- seed `20241027` (`--seed 20241027`);
- ENEM e TSE, cada um com ETL e ELT;
- duas modalidades por cenário: `desempenho`, sem monitor, e `recursos`, com
  monitoramento a cada 0,5 s.

São 16 cenários de base, volume e arquitetura e 32 unidades experimentais ao
incluir as duas modalidades. Portanto, a configuração padrão realiza 32
aquecimentos e 160 medições válidas, totalizando 192 execuções de pipeline. Cada
modalidade e cenário recebe um aquecimento e cinco rodadas válidas; os
aquecimentos não são gravados nos CSVs.

Exemplo de configuração reduzida:

```powershell
python src\benchmark.py --run-id piloto_01 --volumes 100000 --rodadas 1 --seed 20241027
```

O `run_id` identifica a campanha e deve conter somente letras, números, ponto,
hífen ou sublinhado. O orquestrador exige uma árvore Git limpa antes de criar
resultados. Se o diretório do `run_id` já existir, a execução é recusada e os
arquivos anteriores não são removidos nem sobrescritos. O argumento
`--limpar-resultados` não existe mais.

Os wrappers individuais (`src\enem\benchmark.py` e
`src\tse\benchmark.py`) são úteis para certificação ou testes específicos. Para
uma campanha comparável entre as duas bases, use o orquestrador global acima.

## Resultados e metadados

Cada campanha usa seu próprio diretório:

```text
data/benchmark/campanhas/<run_id>/
├── campanha.json
├── desempenho/
│   ├── enem_etl.csv
│   ├── enem_elt.csv
│   ├── tse_etl.csv
│   └── tse_elt.csv
└── recursos/
    ├── enem_etl.csv
    ├── enem_elt.csv
    ├── tse_etl.csv
    └── tse_elt.csv
```

O `campanha.json` registra `run_id`, status, horários de início e fim, commit
Git, seed, volumes, número de rodadas, combinações, aquecimentos, execuções
previstas e execuções concluídas.

Também registra o objeto `ambiente`, capturado uma única vez no início da
campanha. Ele contém duas partes:

- `declarado_para_campanha_oficial`: ambiente oficial declarado para o TCC;
- `capturado_automaticamente`: sistema operacional, Python, versões das
  dependências, hardware básico e informações do PostgreSQL observadas no host
  da campanha.

O PostgreSQL é consultado somente com `SELECT version()` e `SHOW` para os
parâmetros relevantes. Host, porta e banco são registrados sem credenciais;
senhas, tokens e a URL completa de conexão nunca são gravados. Quando uma
informação não pode ser coletada, o campo fica `null` ou recebe um status
explícito de indisponibilidade. Para conferir os valores registrados, abra o
`campanha.json` da campanha e compare `ambiente.declarado_para_campanha_oficial`
com `ambiente.capturado_automaticamente`.

Na campanha oficial, `capturado_automaticamente` deve ser conferido na máquina
Acer Aspire 16 A16-71M-55H0 com Windows 11. Uma captura realizada em outro
computador, como um macOS de preparação, não substitui essa validação.

Os CSVs usam `;` como delimitador e registram `modalidade`,
`monitoramento_ativo` e `intervalo_monitoramento_s`. Os tempos e o throughput de
`desempenho` são oficiais; seus campos de CPU/RAM ficam vazios. CPU e RAM de
`recursos` são oficiais, enquanto seus tempos e throughput são apenas
diagnósticos. Essa proveniência também fica registrada em `campanha.json`.

Resultados gerados e gráficos são ignorados pelo Git. Os manifestos TSE em
`data/benchmark/tse/subconjuntos/` permanecem versionados porque fazem parte da
reprodução do experimento. Para transferir resultados entre máquinas, copie o
diretório completo da campanha, incluindo `campanha.json`; não há um sistema de
publicação ou aprovação de campanhas.

## Geração de gráficos

Para uma campanha completa com os quatro volumes padrão e cinco rodadas
válidas, execute:

```powershell
python graficos\gerar_graficos.py --run-id oficial_01
```

O script lê exclusivamente os quatro CSVs de `desempenho/`, rejeita mistura de
modalidades e grava as figuras em:

```text
data/benchmark/campanhas/<run_id>/graficos/tempo_processamento/
├── tempo_medio_geral.pdf
├── tempo_medio_dataset.pdf
├── tempo_medio_volume_enem.pdf
└── tempo_medio_volume_tse.pdf
```

O gerador valida colunas, volumes, rodadas, duplicidades e quantidade de
observações. Como ele exige os quatro volumes e 20 observações válidas por
dataset/arquitetura, campanhas reduzidas não atendem ao formato esperado por
esse script.

## Problemas comuns

- **CSV ENEM ausente:** confira `data/raw/enem/microdados_enem_2024/DADOS/` e
  os nomes `PARTICIPANTES_2024.csv` e `RESULTADOS_2024.csv`.
- **CSV TSE ausente ou fora da pasta:** confira as três pastas de fontes em
  `data/raw/tse/` e se os arquivos foram extraídos como CSV.
- **Manifesto TSE ausente:** confira `data/benchmark/tse/subconjuntos/` ou
  execute o preparador somente quando for necessário regenerar os manifestos.
- **PostgreSQL inacessível:** verifique host, porta, banco, usuário, senha e
  permissões no `.env`; confirme também que o servidor está disponível.
- **Variáveis de ambiente incompletas:** compare `.env` com `.env.example`.
- **Árvore Git suja:** registre ou remova alterações de código/configuração
  antes de iniciar a campanha; o orquestrador bloqueia a execução.
- **`run_id` já utilizado:** escolha outro identificador; campanhas existentes
  não são limpas automaticamente.
- **Dependência Python ausente:** ative o ambiente virtual e execute
  `python -m pip install -r requirements.txt`.

## Documentação complementar

- [Execução do benchmark do ENEM](docs/enem/README.md): preparação,
  certificação e comandos específicos do ENEM;
- [Plano do benchmark do ENEM](docs/enem/plano_benchmark.md): fontes, contrato e
  regras do cenário ENEM;
- [Execução do benchmark do TSE](docs/tse/README.md): manifestos, certificação
  e comandos específicos do TSE;
- [Plano do benchmark do TSE](docs/tse/plano_benchmark.md): fontes, agregações e
  contrato do cenário TSE;
- [Metodologia experimental](docs/metodologia.md): protocolo, amostragem,
  métricas e critérios de equivalência;
- [Relatório do experimento TSE CTE](docs/relatorio_experimento_elt_cte_tse.md):
  experimento exploratório separado com ELT usando CTEs;
- [Geração de gráficos](graficos/README.md): detalhes do gerador de figuras.
