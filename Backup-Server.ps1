param([string]$InstallRoot=(Join-Path $env:LOCALAPPDATA 'MilenioServer'))
$ErrorActionPreference='Stop'
$maintenanceLock=[System.IO.File]::Open((Join-Path $InstallRoot '.install.lock'),[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
try {
$current=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/current.json') -Raw | ConvertFrom-Json
$env:MILENIO_DEPLOYMENT_CONFIG=Join-Path $InstallRoot 'private/infra.local.json'
$config=Get-Content -LiteralPath $env:MILENIO_DEPLOYMENT_CONFIG -Raw | ConvertFrom-Json
$python=Join-Path $current.release_dir '.venv/Scripts/python.exe'
$deploy=Join-Path $current.release_dir 'scripts/deploy.py'
$wasStopped=Test-Path -LiteralPath (Join-Path $config.data_dir '.stop-managed')
& $python $deploy stop
if ($LASTEXITCODE -ne 0) { throw 'No se detuvo; no se hace respaldo inconsistente.' }
try {
    & $python $deploy backup
    if ($LASTEXITCODE -ne 0) { throw 'Respaldo fallido; revisar destino, espacio y permisos.' }
} finally {
    if (-not $wasStopped) {
        & $python $deploy resume
        if ($LASTEXITCODE -eq 0) {
            Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $InstallRoot 'Run-Server.ps1')+'"')) -WindowStyle Hidden
        }
    }
}

} finally { $maintenanceLock.Dispose() }
