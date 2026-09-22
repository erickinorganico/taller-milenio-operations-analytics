param([string]$PythonPath = '', [switch]$Offline, [string]$EnvironmentPath = '.venv')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.mpl-cache'
$envDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $EnvironmentPath))
if (-not $envDir.StartsWith($PSScriptRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'El entorno debe quedar dentro del proyecto' }
$envPython = Join-Path $envDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $envPython)) {
    $candidates = @()
    if ($PythonPath) { $candidates += $PythonPath }
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $candidates += $found.Source }
    $candidates += "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $candidates += "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    $chosen = $null
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            try {
                & $candidate -c "import sys,sqlite3; assert sys.version_info >= (3,12)" 2>$null
                if ($LASTEXITCODE -eq 0) { $chosen = $candidate; break }
            } catch { continue }
        }
    }
    if (-not $chosen) { throw 'Instale Python 3.12+ o use -PythonPath C:\ruta\python.exe' }
    & $chosen -m venv $envDir
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno' }
}
& $envPython -c "import sys,sqlite3; assert sys.version_info >= (3,12)"
if ($LASTEXITCODE -ne 0) { throw 'Entorno Python invalido' }
if ($Offline) {
    & $envPython -m pip install --no-index --find-links '.runtime\wheels' -r requirements.txt
} else {
    & $envPython -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Instalacion incompleta; para offline prepare .runtime\wheels' }
& $envPython -c "import matplotlib,openpyxl,xlsxwriter; print('Entorno analitico listo: graficos, SQL y Excel.')"
if ($LASTEXITCODE -ne 0) { throw 'Verificacion del entorno fallo' }
Write-Output "Abra Run-Cliente.cmd para la guia; arrastre un Excel sobre ese archivo para generar un corte privado. Run-Studio.cmd conserva el estudio V2."
