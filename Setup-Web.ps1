param([string]$PythonPath = '', [switch]$Offline)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$venvDir = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirements = Join-Path $projectRoot 'requirements-web.txt'
if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) { throw 'Falta requirements-web.txt' }

$verifyPython = if ($Offline) {
    "import sys,sysconfig; sys.exit(0 if sys.version_info[:2]==(3,12) and sysconfig.get_platform()=='win-amd64' else 1)"
} else {
    'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    if ($PythonPath) {
        if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'PythonPath no existe' }
    } else {
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            $detected = & { $ErrorActionPreference = 'Continue'; py.exe -3.12 -c 'import sys; print(sys.executable)' 2>$null }
            if ($LASTEXITCODE -eq 0) { $PythonPath = $detected }
        }
        if (-not $PythonPath) {
            $python = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($python) { $PythonPath = $python.Source }
        }
    }
    if (-not $PythonPath) { throw 'Instala Python 3.12 de 64 bits o indica -PythonPath.' }
    & $PythonPath -c $verifyPython
    if ($LASTEXITCODE -ne 0) { throw 'Selecciona Python 3.12 de 64 bits para el paquete de Windows.' }
    & $PythonPath -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw 'No se pudo crear .venv' }
}

& $venvPython -c $verifyPython
if ($LASTEXITCODE -ne 0) { throw 'Extrae el paquete en una carpeta limpia y usa Python 3.12 de 64 bits.' }
function Test-WebDependencies {
    & $venvPython (Join-Path $projectRoot 'scripts\check_web_dependencies.py') $requirements
    return ($LASTEXITCODE -eq 0)
}
if (-not (Test-WebDependencies)) {
    if ($Offline) {
        $wheels = Join-Path $projectRoot '.runtime\wheels'
        if (-not (Test-Path -LiteralPath $wheels -PathType Container)) { throw 'Falta .runtime\wheels para instalación offline' }
        & $venvPython -m pip install --no-index --find-links $wheels -r $requirements
    } else {
        & $venvPython -m pip install -r $requirements
    }
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar dependencias web' }
    if (-not (Test-WebDependencies)) { throw 'La verificación de dependencias web falló' }
}
Write-Output 'Entorno web listo. Use Abrir-Taller.cmd o Abrir-Demo.cmd.'
