param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [int]$Limite = 1000000,
    [int]$Repeticoes = 5,
    [int]$TamanhoBloco = 4096,
    [int]$Semente = 152024,
    [string]$SchemaA = "exp_enem_serializacao_a",
    [string]$SchemaB = "exp_enem_serializacao_b",
    [string]$DiretorioSaida = "data\experimentos\sensibilidade_serializacao_enem"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Interpretador Python nao encontrado: $Python"
}

& $Python -m src.enem.experimental.sensibilidade_serializacao `
    campanha `
    --limite $Limite `
    --repeticoes $Repeticoes `
    --tamanho-bloco $TamanhoBloco `
    --semente $Semente `
    --schema-a $SchemaA `
    --schema-b $SchemaB `
    --diretorio-saida $DiretorioSaida

if ($LASTEXITCODE -ne 0) {
    throw "Experimento interrompido com codigo $LASTEXITCODE."
}
