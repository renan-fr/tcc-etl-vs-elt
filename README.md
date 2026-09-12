# tcc-etl-vs-elt

## Como rodar os scripts

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Os arquivos brutos devem estar em:

```text
data/raw/enem/microdados_enem_2024/DADOS/
```

Rodar apenas extracao, transformacao e validacao:

```bash
python src\etl\enem_etl.py --limite 100000 --somente-validar
```

Validar todos os registros:

```bash
python src\etl\enem_etl.py --limite 0 --somente-validar
```

Rodar ETL com carga no PostgreSQL:

```bash
python src\etl\enem_etl.py --limite 100000
```

Por padrao, a carga usa o schema `etl` e substitui as tabelas existentes.

| Parametro | Padrao | Descricao |
| --- | --- | --- |
| `--limite` | `100000` | Quantidade maxima de linhas lidas de cada arquivo. Use `0` para ler tudo. |
| `--database-url` | `DATABASE_URL` ou `POSTGRES_URL` | URL completa de conexao com o PostgreSQL. Se omitida, o script usa as variaveis separadas do banco. |
| `--schema` | `POSTGRES_SCHEMA_ETL`, `POSTGRES_SCHEMA` ou `etl` | Schema de destino no PostgreSQL. |
| `--if-exists` | `replace` | Estrategia de carga das tabelas finais. Aceita `replace` ou `append`. |
| `--somente-validar` | desativado | Executa extracao, transformacao e validacao sem carregar no banco. |

O script le automaticamente o `.env`. A conexao pode ser configurada com:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_banco
```

Ou:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nome_banco
POSTGRES_USER=usuario
POSTGRES_PASSWORD=senha
POSTGRES_SCHEMA_ETL=etl
```
