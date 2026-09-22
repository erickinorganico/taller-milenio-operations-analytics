param([string]$InputWorkbook)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $InputWorkbook) {
    Start-Process -FilePath (Join-Path $PSScriptRoot 'CLIENTE.html') -WindowStyle Hidden
    exit 0
}
$pythonClient = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonClient)) {
    Write-Host 'Ejecute Setup.ps1 una vez para preparar el analisis local.'
    exit 1
}
$env:PYTHONUTF8 = '1'
$clientResult = & $pythonClient -m milenio client-analyze --input $InputWorkbook
$clientExit = $LASTEXITCODE
Write-Host $clientResult
if ($clientExit -ne 0) { exit $clientExit }
$clientReport = $clientResult | ConvertFrom-Json
Start-Process -FilePath (Join-Path $clientReport.output 'INICIO.html') -WindowStyle Hidden
