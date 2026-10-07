$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$researchPython = Join-Path $PSScriptRoot '.venv-research/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $researchPython)) {
    $workshopPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $workshopPython)) { throw 'Ejecuta Setup-Web.ps1 primero.' }
    & $workshopPython -m venv .venv-research
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de investigación.' }
}
& $researchPython -m pip install -r requirements-research.txt
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de investigación.' }
& $researchPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Las dependencias no son consistentes.' }
Write-Output 'Investigación lista. No se ejecutó ninguna búsqueda ni envío.'
