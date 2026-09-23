param([string]$PythonPath = '', [switch]$Offline)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$venvDir = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirements = Join-Path $projectRoot 'requirements-web.txt'
if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) { throw 'Falta requirements-web.txt' }

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    if ($PythonPath) {
        if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'PythonPath no existe' }
        & $PythonPath -c 'import sys; assert sys.version_info >= (3,12)'
        if ($LASTEXITCODE -ne 0) { throw 'Se requiere Python 3.12 o posterior' }
        & $PythonPath -m venv $venvDir
    } elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
        & py.exe -3.12 -c 'import sys; assert sys.version_info >= (3,12)'
        if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.12 o use -PythonPath' }
        & py.exe -3.12 -m venv $venvDir
    } else {
        $python = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $python) { throw 'Instale Python 3.12 o use -PythonPath' }
        & $python.Source -c 'import sys; assert sys.version_info >= (3,12)'
        if ($LASTEXITCODE -ne 0) { throw 'Se requiere Python 3.12 o posterior' }
        & $python.Source -m venv $venvDir
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw 'No se pudo crear .venv' }
}

& $venvPython -c 'import sys; assert sys.version_info >= (3,12)'
if ($LASTEXITCODE -ne 0) { throw 'El Python de .venv debe ser 3.12 o posterior' }
function Test-WebDependencies {
    $raw = & $venvPython -m pip list --format=json
    if ($LASTEXITCODE -ne 0) { return $false }
    $installed = @{}
    foreach ($package in ($raw | ConvertFrom-Json)) {
        $installed[$package.name.ToLowerInvariant()] = $package.version
    }
    foreach ($line in (Get-Content -LiteralPath $requirements)) {
        if ($line -match '^\s*([^#\s=]+)==([^\s#]+)') {
            $name = $matches[1].ToLowerInvariant()
            $version = $matches[2]
            if (-not $installed.ContainsKey($name) -or $installed[$name] -ne $version) { return $false }
        }
    }
    return $true
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
}
if (-not (Test-WebDependencies)) { throw 'La verificación de dependencias web falló' }
Write-Output 'Entorno web listo. Use Iniciar-Milenio.cmd o Iniciar-Demo.cmd.'
