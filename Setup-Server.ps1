param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'MilenioServer'),
    [string]$BackupDir = '',
    [int]$Port = 8770,
    [string]$PythonPath = '',
    [switch]$Offline,
    [switch]$NoStart
)
$ErrorActionPreference = 'Stop'
if (-not $PythonPath -and -not (Get-Command py.exe -ErrorAction SilentlyContinue) -and -not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    if ($Offline) { throw 'Instala Python 3.12 antes de usar el paquete offline.' }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Instala Python 3.12 desde python.org y vuelve a ejecutar.' }
    & winget.exe install --id Python.Python.3.12 --exact --scope user --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw 'No se instaló Python.' }
    $PythonPath = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python312/python.exe'
}
& (Join-Path $PSScriptRoot 'Setup-Web.ps1') -PythonPath $PythonPath -Offline:$Offline
$sourcePython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $InstallRoot) {
    if (@(Get-ChildItem -LiteralPath $InstallRoot -Force).Count -and -not (Test-Path -LiteralPath (Join-Path $InstallRoot 'private/current.json')) -and -not (Test-Path -LiteralPath (Join-Path $InstallRoot '.install-in-progress'))) { throw 'Destino no vacío ajeno a Milenio.' }
}
New-Item -ItemType Directory -Force $InstallRoot | Out-Null
$installationLock=[System.IO.File]::Open((Join-Path $InstallRoot '.install.lock'),[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
try {
New-Item -ItemType File -Force (Join-Path $InstallRoot '.install-in-progress') | Out-Null
$stageOutput = & $sourcePython (Join-Path $PSScriptRoot 'scripts/stage_install.py') --install-root $InstallRoot
if ($LASTEXITCODE -ne 0) { throw 'No se preparó la release.' }
$release = $stageOutput | ConvertFrom-Json
$releaseRoot = $release.release_dir
if ($Offline) {
    $offlineSource = Join-Path $PSScriptRoot '.runtime/wheels'
    $offlineTarget = Join-Path $releaseRoot '.runtime'
    New-Item -ItemType Directory -Force $offlineTarget | Out-Null
    Copy-Item -LiteralPath $offlineSource -Destination $offlineTarget -Recurse -Force
}
& (Join-Path $releaseRoot 'Setup-Web.ps1') -PythonPath $PythonPath -Offline:$Offline
$serverPython = Join-Path $releaseRoot '.venv/Scripts/python.exe'
$privateRoot = Join-Path $InstallRoot 'private'
New-Item -ItemType Directory -Force $privateRoot | Out-Null
$identitySid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $InstallRoot /inheritance:r /grant:r "*${identitySid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron proteger los permisos de instalación.' }
$env:MILENIO_DEPLOYMENT_CONFIG = Join-Path $privateRoot 'infra.local.json'
if (-not $BackupDir) { $BackupDir = Join-Path $InstallRoot 'backups' }
$previous = Join-Path $privateRoot 'current.json'
if (Test-Path -LiteralPath $previous) {
    $old = Get-Content -LiteralPath $previous -Raw | ConvertFrom-Json
    & (Join-Path $old.release_dir '.venv/Scripts/python.exe') (Join-Path $old.release_dir 'scripts/deploy.py') stop
    if ($LASTEXITCODE -ne 0) { throw 'La versión anterior no se detuvo; actualización cancelada.' }
}
& $serverPython (Join-Path $releaseRoot 'scripts/deploy.py') init --data-dir (Join-Path $InstallRoot 'data/live') --backup-dir $BackupDir --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Instalación detenida; consulta la salida. No se arrancó el servidor.' }
$release | ConvertTo-Json | Set-Content -LiteralPath $previous -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $releaseRoot 'Run-Server.ps1') -Destination (Join-Path $InstallRoot 'Run-Server.ps1') -Force
if ($NoStart) {
    & $serverPython (Join-Path $releaseRoot 'scripts/deploy.py') stop
    if ($LASTEXITCODE -ne 0) { throw 'No se confirmó la pausa de instalación.' }
} else {
    & $serverPython (Join-Path $releaseRoot 'scripts/deploy.py') resume
    if ($LASTEXITCODE -ne 0) { throw 'No se habilitó el arranque.' }
    Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $InstallRoot 'Run-Server.ps1')+'"')) -WindowStyle Hidden
}
Write-Output "Servidor preparado en $InstallRoot. Abre http://127.0.0.1:$Port/setup/ para crear Gerencia. Gmail permanece detenido."
Write-Output 'Siguiente: Register-ServerStartup.ps1 y Setup-RemoteAccess.ps1. El respaldo local debe complementarse con una copia en otro disco.'

} finally { $installationLock.Dispose() }
