param(
    [ValidateSet('live','demo')][string]$Mode = 'demo',
    [string]$DataDir = '',
    [string]$ConfigDir = '',
    [int]$Port = 0,
    [switch]$NoBrowser,
    [switch]$Stop,
    [switch]$SkipSetup,
    [ValidateSet('Taller','Comercial')][string]$Seccion = 'Taller'
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pagePath = if ($Seccion -eq 'Comercial') { '/commercial/' } else { '/' }

function Get-MilenioHealth([string]$baseUrl) {
    $response = $null
    try {
        $request = [Net.HttpWebRequest]::Create($baseUrl.TrimEnd('/') + '/health/')
        $request.AllowAutoRedirect = $false
        $request.Proxy = $null
        $request.Timeout = 2500
        $request.ReadWriteTimeout = 2500
        $request.Accept = 'application/json'
        $response = $request.GetResponse()
        if ([int]$response.StatusCode -ne 200) { return $null }
        $reader = [IO.StreamReader]::new($response.GetResponseStream())
        try {
            $buffer = [char[]]::new(65537)
            $count = $reader.ReadBlock($buffer, 0, $buffer.Length)
            if ($count -eq $buffer.Length) { return $null }
            return ([string]::new($buffer, 0, $count) | ConvertFrom-Json)
        } finally { $reader.Dispose() }
    } catch { return $null }
    finally { if ($response) { $response.Dispose() } }
}

if ($Mode -eq 'live' -and $env:MILENIO_LEGACY_LOCAL -ne '1') {
    if ($Stop -or $DataDir -or $ConfigDir -or $Port -or $SkipSetup) {
        throw 'El acceso al taller usa la instalacion asignada. Para mantenimiento sigue infra/DESPLIEGUE-Y-RECUPERACION.md.'
    }
    $configPath = $env:MILENIO_DEPLOYMENT_CONFIG
    if (-not $configPath) {
        $configPath = Join-Path $projectRoot 'private/infra.local.json'
        if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
            $parent = Split-Path $projectRoot -Parent
            if ((Split-Path $parent -Leaf) -eq 'releases') {
                $configPath = Join-Path (Split-Path $parent -Parent) 'private/infra.local.json'
            } else {
                $configPath = Join-Path $env:LOCALAPPDATA 'MilenioServer/private/infra.local.json'
            }
        }
    }
    if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
        throw 'Falta la configuracion del equipo. En la PC central usa Instalar-Servidor.cmd; en otra PC usa Setup-Client.ps1 segun infra/INSTALAR.md.'
    }
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.schema_version -ne 2 -or $config.role -notin 'server','client' -or
        $config.transport -ne 'ssh-loopback' -or $config.expected_hostname -ne [Environment]::MachineName) {
        throw 'La configuracion no corresponde a esta computadora. Revisa infra/INSTALAR.md con la persona responsable.'
    }
    $instance = [guid]::Empty
    if (-not [guid]::TryParse([string]$config.instance_id, [ref]$instance) -or $instance -eq [guid]::Empty) {
        throw 'Falta la identidad valida de la instalacion. Revisa private/infra.local.json con la persona responsable.'
    }
    $configuredPort = if ($config.role -eq 'client') { $config.local_port } else { $config.port }
    $localPort = 0
    if (-not [int]::TryParse([string]$configuredPort, [ref]$localPort) -or $localPort -lt 1024 -or $localPort -gt 65535) {
        throw 'Puerto de acceso incorrecto. Revisa la configuracion del equipo.'
    }
    $baseUrl = "http://127.0.0.1:$localPort"
    if ($config.central_url -notin $baseUrl, ($baseUrl + '/')) {
        throw 'La direccion debe coincidir con el puerto de loopback configurado. Revisa la configuracion del equipo.'
    }
    if ($config.role -eq 'server' -and (Test-Path -LiteralPath (Join-Path $config.data_dir '.stop-managed'))) {
        throw 'El servidor esta pausado para mantenimiento. Espera a que el responsable reanude la instalacion.'
    }
    $health = Get-MilenioHealth $baseUrl
    if (-not $health) {
        if ($config.role -eq 'client') { throw 'Abre Connect-Server.ps1, deja el tunel abierto y vuelve a intentar. Si sigue sin responder, consulta si el servidor esta en mantenimiento.' }
        throw 'La central no responde. Comprueba su estado y private/supervisor.log segun infra/INSTALAR.md antes de reanudar el servicio.'
    }
    if ($health.application -ne 'milenio-operations' -or $health.mode -ne 'live' -or
        $health.status -ne 'ok' -or $health.instance_id -ne $config.instance_id) {
        throw 'La identidad del servicio o su estado no coincide. Verifica el tunel y el identificador de la central con el responsable.'
    }
    $targetUrl = $baseUrl + $pagePath
    if (-not $NoBrowser) { Start-Process $targetUrl }
    Write-Output "Milenio disponible: $targetUrl"
    exit 0
}
if (-not $ConfigDir) { $ConfigDir = Join-Path $projectRoot "private" }
$configFile = Join-Path $ConfigDir "launcher-$Mode.json"
if (-not $DataDir -and $env:MILENIO_DATA_DIR) { $DataDir = $env:MILENIO_DATA_DIR }
if (-not $DataDir -and (Test-Path -LiteralPath $configFile)) {
    $saved = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
    $DataDir = $saved.data_dir
    if (-not $Port) { $Port = $saved.port }
}
if (-not $DataDir) { $DataDir = Join-Path $env:LOCALAPPDATA "Milenio\operational\$Mode" }
$DataDir = [IO.Path]::GetFullPath($DataDir)
if ([IO.Path]::GetFileName($DataDir.TrimEnd('\','/')) -ne $Mode) { throw 'La carpeta de datos debe terminar en el modo seleccionado: live o demo.' }
if (-not $Port) { $Port = if ($Mode -eq 'demo') { 8766 } elseif ($Seccion -eq 'Comercial') { 8770 } else { 8765 } }
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Puerto fuera de rango.' }
$legacy = Join-Path $projectRoot "private\operational\$Mode\workshop.sqlite3"
if ((Test-Path -LiteralPath $legacy) -and -not (Test-Path -LiteralPath (Join-Path $DataDir 'workshop.sqlite3'))) {
    throw 'Hay una base anterior en private/operational. Indique -DataDir para usarla; no se creara otra instalacion vacia.'
}
$url = "http://127.0.0.1:$Port/"
$recordFile = Join-Path $DataDir '.launcher.json'
$health = Get-MilenioHealth $url
if ($Stop) {
    if (-not $health) { Write-Output 'Milenio ya esta detenido.'; exit 0 }
    if (-not (Test-Path -LiteralPath $recordFile)) { throw 'Esta instancia no fue iniciada por Abrir-Milenio.ps1. Cierre su consola con Ctrl+C.' }
    $record = Get-Content -LiteralPath $recordFile -Raw | ConvertFrom-Json
    if ($health.application -ne 'milenio-operations' -or $health.mode -ne $Mode -or $health.launch_id -ne $record.launch_id) {
        throw 'El servidor del puerto no coincide con esta instancia. No se detuvo ningun proceso.'
    }
    if ($record.launch_id -notmatch '^[a-f0-9]{32}$') { throw 'Identificador local de cierre no valido.' }
    $signal = Join-Path $DataDir ('.stop-' + $record.launch_id)
    [IO.File]::WriteAllText($signal, 'stop')
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        $stillRunning = Get-Process -Id $record.process_id -ErrorAction SilentlyContinue
        if (-not $stillRunning -and -not (Get-MilenioHealth $url)) { Write-Output 'Milenio detenido; sus datos siguen guardados.'; exit 0 }
    }
    throw 'El cierre aun no termina. Consulte server-error.log; no se forzo el cierre de la base.'
}
if ($health) {
    if ($health.application -ne 'milenio-operations' -or $health.mode -ne $Mode) { throw 'El puerto pertenece a otra aplicacion o modo. No se modifico.' }
    # Never redirect a selected data directory to a different running instance.
    if (-not (Test-Path -LiteralPath $recordFile)) { throw 'Hay otra instancia en ese puerto. Use su acceso original o cierre su consola antes de iniciar esta carpeta.' }
    $record = Get-Content -LiteralPath $recordFile -Raw | ConvertFrom-Json
    if ($record.launch_id -ne $health.launch_id) { throw 'El puerto esta sirviendo otra carpeta de datos.' }
    if (-not $NoBrowser) { Start-Process ($url.TrimEnd('/') + $pagePath) }
    Write-Output "Milenio ya esta disponible: $url"
    exit 0
}
# A non-Milenio service must not be replaced, even if it has no /health/ route.
$probe = New-Object Net.Sockets.TcpClient
try { $probe.Connect('127.0.0.1',$Port); $occupied=$true } catch { $occupied=$false } finally { $probe.Dispose() }
if ($occupied) { throw 'El puerto esta ocupado por otro servicio. No se detuvo ningun proceso.' }
if (-not $SkipSetup) { & (Join-Path $projectRoot 'Setup-Web.ps1'); if ($LASTEXITCODE) { throw 'No se pudo preparar el entorno.' } }
$python = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta el entorno Python. Ejecute Setup-Web.ps1.' }
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
$launchId = [Guid]::NewGuid().ToString('N')
$signal = Join-Path $DataDir ('.stop-' + $launchId)
$env:MILENIO_DATA_DIR = $DataDir
$env:MILENIO_MODE = $Mode
$env:MILENIO_LAUNCH_ID = $launchId
$env:PYTHONIOENCODING = 'utf-8'
$quotedScript = '"' + (Join-Path $projectRoot 'scripts\run_web.py') + '"'
$quotedSignal = '"' + $signal + '"'
$arguments = @($quotedScript, '--mode', $Mode, '--no-browser', '--background', '--port', "$Port", '--stop-file', $quotedSignal)
# PowerShell 5.1 cannot construct a child environment with both Path and PATH.
# Normalize only this process environment, retaining its original search path.
$launchSearchPath = [Environment]::GetEnvironmentVariable('Path', 'Process')
[Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
[Environment]::SetEnvironmentVariable('Path', $null, 'Process')
[Environment]::SetEnvironmentVariable('Path', $launchSearchPath, 'Process')
$childProcess = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
@{launch_id=$launchId; process_id=$childProcess.Id; port=$Port; mode=$Mode} | ConvertTo-Json | Set-Content -LiteralPath $recordFile -Encoding UTF8
for ($attempt=0; $attempt -lt 90; $attempt++) {
    $childProcess.Refresh()
    if ($childProcess.HasExited) { throw "No se pudo iniciar Milenio. Consulte $DataDir\server-error.log" }
    $health = Get-MilenioHealth $url
    if ($health -and $health.application -eq 'milenio-operations' -and $health.mode -eq $Mode -and $health.launch_id -eq $launchId) {
        New-Item -ItemType Directory -Path (Split-Path $configFile) -Force | Out-Null
        @{data_dir=$DataDir;port=$Port} | ConvertTo-Json | Set-Content -LiteralPath $configFile -Encoding UTF8
        if (-not $NoBrowser) { Start-Process ($url.TrimEnd('/') + $pagePath) }
        Write-Output "Milenio disponible en segundo plano: $url"
        Write-Output "Para detenerlo: powershell -File Abrir-Milenio.ps1 -Mode $Mode -Stop"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
[IO.File]::WriteAllText($signal, 'stop')
throw "No se confirmo el arranque. Consulte $DataDir\server-error.log"
