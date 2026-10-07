param([string]$InstallRoot = $PSScriptRoot)
$ErrorActionPreference='Stop'
$current=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/current.json') -Raw | ConvertFrom-Json
$env:MILENIO_DEPLOYMENT_CONFIG=Join-Path $InstallRoot 'private/infra.local.json'
$env:PYTHONUTF8='1'
$log=Join-Path $InstallRoot 'private/supervisor.log'
& (Join-Path $current.release_dir '.venv/Scripts/python.exe') (Join-Path $current.release_dir 'scripts/deploy.py') serve >> $log 2>&1
exit $LASTEXITCODE
