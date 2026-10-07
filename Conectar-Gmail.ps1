param([string]$ClientJson = '', [string]$Owner = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$gmailPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$gmailConfig = Join-Path $PSScriptRoot 'private/launcher-live.json'
if (-not (Test-Path -LiteralPath $gmailPython)) { throw 'Ejecuta Setup-Web.ps1 primero.' }
$env:MILENIO_MODE = 'live'
$managedConfig = if ($env:MILENIO_DEPLOYMENT_CONFIG) { $env:MILENIO_DEPLOYMENT_CONFIG } else { Join-Path $PSScriptRoot 'private/infra.local.json' }
if (Test-Path -LiteralPath $managedConfig) {
    $managed = Get-Content -LiteralPath $managedConfig -Raw | ConvertFrom-Json
    if ($managed.role -ne 'server' -or $managed.expected_hostname -ne $env:COMPUTERNAME) { throw 'Conecta Gmail en el servidor asignado.' }
    $env:MILENIO_DEPLOYMENT_CONFIG = $managedConfig
    $env:MILENIO_DATA_DIR = $managed.data_dir
} elseif (Test-Path -LiteralPath $gmailConfig) {
    $env:MILENIO_DATA_DIR = (Get-Content -LiteralPath $gmailConfig -Raw | ConvertFrom-Json).data_dir
} else {
    $env:MILENIO_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Milenio/operational/live'
}
if (-not $ClientJson) {
    Add-Type -AssemblyName System.Windows.Forms
    $gmailDialog = New-Object System.Windows.Forms.OpenFileDialog
    $gmailDialog.Title = 'Selecciona el JSON OAuth de escritorio descargado de Google Cloud'
    $gmailDialog.Filter = 'JSON OAuth (*.json)|*.json'
    if ($gmailDialog.ShowDialog() -ne 'OK') { Write-Output 'Conexion cancelada.'; exit 0 }
    $ClientJson = $gmailDialog.FileName
}
if (-not $Owner) { $Owner = Read-Host 'Usuario de Gerencia que creaste al abrir Milenio' }
& $gmailPython manage.py connect_gmail --client $ClientJson --owner $Owner
if ($LASTEXITCODE) { throw 'Gmail no se conecto; revisa el mensaje anterior.' }
