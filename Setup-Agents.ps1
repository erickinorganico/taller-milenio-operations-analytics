[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtime = Join-Path $root '.runtime\codex'
$binary = Join-Path $runtime 'node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe'

if ($Force -or -not (Test-Path -LiteralPath $binary -PathType Leaf)) {
    $npm = Get-Command npm.cmd -ErrorAction Stop
    & $npm.Source install --prefix $runtime --no-fund --no-audit '@openai/codex@0.155.1'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar el CLI oficial de Codex.' }
}

if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
    throw "No se encontró el binario oficial esperado: $binary"
}

$env:MILENIO_CODEX_BIN = (Resolve-Path -LiteralPath $binary).Path
$env:MILENIO_CODEX_MODEL = 'gpt-5.6-luna'
Write-Host 'CLI local de Codex preparado para este proceso de PowerShell.'
Write-Host "MILENIO_CODEX_BIN=$env:MILENIO_CODEX_BIN"
Write-Host "MILENIO_CODEX_MODEL=$env:MILENIO_CODEX_MODEL"
Write-Host 'El script no inicia sesión, no modifica autenticación y no usa claves API.'
