param([ValidateSet('live','demo')][string]$Mode='live', [string]$DataDir='')
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$commercialPython=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $commercialPython)) { & (Join-Path $PSScriptRoot 'Setup-Web.ps1'); if ($LASTEXITCODE) { throw 'Instalacion del taller incompleta.' } }
$savedLauncher=Join-Path $PSScriptRoot "private/launcher-$Mode.json"
if (-not $DataDir -and (Test-Path -LiteralPath $savedLauncher)) { $DataDir=(Get-Content -LiteralPath $savedLauncher -Raw | ConvertFrom-Json).data_dir }
if (-not $DataDir) { $DataDir=Join-Path $env:LOCALAPPDATA "Milenio/operational/$Mode" }
$DataDir=[IO.Path]::GetFullPath($DataDir)
if ([IO.Path]::GetFileName($DataDir.TrimEnd('\','/')) -ne $Mode) { throw 'La carpeta de datos debe terminar en live o demo segun el modo.' }
$legacy=Join-Path $PSScriptRoot "private/operational/$Mode/workshop.sqlite3"
if ((Test-Path -LiteralPath $legacy) -and -not (Test-Path -LiteralPath (Join-Path $DataDir 'workshop.sqlite3'))) { throw 'Existe una instalacion anterior. Use -DataDir con su carpeta; no se crea una segunda base.' }
$env:MILENIO_MODE=$Mode
$env:MILENIO_DATA_DIR=$DataDir
if (Test-Path -LiteralPath (Join-Path $DataDir 'workshop.sqlite3')) {
    $backupPath=Join-Path (Split-Path $DataDir -Parent) ('backups/commercial-before-'+$Mode+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    & $commercialPython manage.py backup_workshop --output $backupPath
    if ($LASTEXITCODE -ne 0) { throw 'Respaldo fallido; no se aplicaron migraciones.' }
}
& $commercialPython manage.py migrate commercial --noinput
if ($LASTEXITCODE -ne 0) { throw 'Migracion comercial fallida. Conserve el respaldo.' }
& $commercialPython manage.py check
if ($LASTEXITCODE -ne 0) { throw 'Revision de Django fallida.' }
Write-Output "Modulo comercial instalado en $Mode. Abra Abrir-Comercial.cmd; el primer acceso crea gerencia si no existe."
