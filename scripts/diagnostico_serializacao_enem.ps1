param(
    [int]$Repeticoes = 5,
    [int]$Limite = 1000000,
    [string]$Schema = "enem_etl_serializacao_diag",
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$DiretorioSaida = "data\experimentos\diagnostico_serializacao_enem"
)

$ErrorActionPreference = "Stop"

if ($Repeticoes -lt 1) {
    throw "Repeticoes deve ser maior que zero."
}
if ($Limite -lt 1) {
    throw "Limite deve ser maior que zero."
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Interpretador Python nao encontrado: $Python"
}

New-Item -ItemType Directory -Force -Path $DiretorioSaida | Out-Null

for ($rodada = 1; $rodada -le $Repeticoes; $rodada++) {
    $log = Join-Path $DiretorioSaida ("rodada_{0:D2}.log" -f $rodada)
    Write-Host "Rodada diagnostica $rodada de $Repeticoes -> $log"

    & $Python src\enem\etl.py `
        --limite $Limite `
        --modo certificar `
        --sem-monitoramento `
        --diagnostico-serializacao `
        --schema-diagnostico $Schema 2>&1 |
        Tee-Object -FilePath $log

    if ($LASTEXITCODE -ne 0) {
        throw "A rodada diagnostica $rodada falhou com codigo $LASTEXITCODE."
    }
}
