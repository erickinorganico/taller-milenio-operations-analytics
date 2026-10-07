$ErrorActionPreference='Stop'
$config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'private/infra.local.json') -Raw | ConvertFrom-Json
if ($config.role -ne 'client' -or $config.expected_hostname -ne $env:COMPUTERNAME) { throw 'Configuración de cliente inválida.' }
$target=$config.ssh_user+'@'+$config.server_address
$forward='127.0.0.1:'+$config.local_port+':127.0.0.1:'+$config.server_port
Write-Output ('Mientras esta conexión siga abierta, usa '+$config.central_url)
& ssh.exe -N -T -p $config.ssh_port -i $config.identity_file -o ('UserKnownHostsFile='+$config.known_hosts) -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L $forward $target
if ($LASTEXITCODE -ne 0) { throw 'Túnel cerrado o conexión fallida; no inicies otra base.' }
