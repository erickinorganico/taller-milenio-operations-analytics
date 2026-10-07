# Run elevated on the assigned server after creating Gerencia locally.
param([string]$InstallRoot=(Join-Path $env:LOCALAPPDATA 'MilenioServer'),
      [Parameter(Mandatory)][string[]]$AllowedAddresses,
      [Parameter(Mandatory)][string[]]$ClientPublicKeyFiles,
      [string]$TunnelUser='milenio_tunnel',[int]$SshPort=2222)
$ErrorActionPreference='Stop'
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Requiere PowerShell elevado para instalar OpenSSH y la regla limitada de firewall.' }
if ($TunnelUser -notmatch '^[a-z][a-z0-9_]{3,24}$' -or $SshPort -lt 1024 -or $SshPort -gt 65535) { throw 'Usuario o puerto inválido.' }
foreach ($address in $AllowedAddresses) {
    # Explicit private IPv4 host addresses only; no broad subnet/public exposure.
    $parsed=[System.Net.IPAddress]::Parse($address)
    $bytes=$parsed.GetAddressBytes()
    if ($bytes.Length -ne 4 -or -not ($bytes[0] -eq 10 -or ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or ($bytes[0] -eq 192 -and $bytes[1] -eq 168) -or ($bytes[0] -eq 100 -and $bytes[1] -ge 64 -and $bytes[1] -le 127))) { throw 'Usa IP privada individual de cada cliente; no Internet, comodines ni subred completa.' }
}
$current=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/current.json') -Raw | ConvertFrom-Json
$env:MILENIO_DEPLOYMENT_CONFIG=Join-Path $InstallRoot 'private/infra.local.json'
$config=Get-Content -LiteralPath $env:MILENIO_DEPLOYMENT_CONFIG -Raw | ConvertFrom-Json
if ($config.role -ne 'server' -or $config.expected_hostname -ne $env:COMPUTERNAME) { throw 'Equipo no asignado como servidor.' }
& (Join-Path $current.release_dir '.venv/Scripts/python.exe') (Join-Path $current.release_dir 'scripts/deploy.py') manage remote_ready
if ($LASTEXITCODE -ne 0) { throw 'Crea Gerencia local antes de abrir acceso remoto.' }
$keys=@()
foreach ($file in $ClientPublicKeyFiles) {
    $key=(Get-Content -LiteralPath $file -Raw).Trim()
    if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?$') { throw 'Solo se aceptan llaves públicas Ed25519; nunca llaves privadas.' }
    $keys += (($key -split ' ')[0..1] -join ' ')
}
if (-not $keys.Count) { throw 'Faltan llaves públicas de clientes.' }
$capability=Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
if ($capability.State -ne 'Installed') { Add-WindowsCapability -Online -Name $capability.Name | Out-Null }
$sshRoot=Join-Path $env:ProgramData ('MilenioSSH-'+$config.instance_id)
$ownership=Join-Path $sshRoot 'owner.txt'
$existingUser=Get-LocalUser -Name $TunnelUser -ErrorAction SilentlyContinue
if ($existingUser -and (-not (Test-Path -LiteralPath $ownership) -or (Get-Content -LiteralPath $ownership -Raw).Trim() -ne $TunnelUser)) { throw 'El usuario ya existe y no pertenece a esta instalación. Elige otro nombre.' }
New-Item -ItemType Directory -Force $sshRoot | Out-Null
& icacls.exe $sshRoot /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se protegió la configuración SSH.' }
if (-not $existingUser) {
    $randomBytes=New-Object byte[] 48
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($randomBytes); $rng.Dispose()
    $password=ConvertTo-SecureString ([Convert]::ToBase64String($randomBytes)+'aA1!') -AsPlainText -Force
    New-LocalUser -Name $TunnelUser -Password $password -AccountNeverExpires -PasswordNeverExpires -Description 'Milenio: solo túnel SSH por llave, sin sesiones' | Out-Null
    $TunnelUser | Set-Content -LiteralPath $ownership -Encoding ASCII
}
$tunnelAccount=Get-LocalUser -Name $TunnelUser
$usersGroup=Get-LocalGroup -SID 'S-1-5-32-545'
if (-not (Get-LocalGroupMember -Group $usersGroup | Where-Object {$_.SID -eq $tunnelAccount.SID})) {
    Add-LocalGroupMember -Group $usersGroup -Member $tunnelAccount
}
# Permit traversal and reading the public authorization file, never the host private key.
$tunnelSid=$tunnelAccount.SID.Value
& icacls.exe $sshRoot /grant "*${tunnelSid}:(RX)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se concedió acceso al directorio de llaves públicas.' }
$sshBin=Join-Path $env:WINDIR 'System32/OpenSSH'
$hostKey=Join-Path $sshRoot 'host_ed25519'
if (-not (Test-Path -LiteralPath $hostKey)) {
    & (Join-Path $current.release_dir '.venv/Scripts/python.exe') -c 'import subprocess,sys; subprocess.run([sys.argv[1],"-t","ed25519","-N","","-f",sys.argv[2]],check=True)' (Join-Path $sshBin 'ssh-keygen.exe') $hostKey
    if ($LASTEXITCODE -ne 0) { throw 'No se generó llave de servidor.' }
}
$authorized=Join-Path $sshRoot 'authorized_keys'
$keys | Set-Content -LiteralPath $authorized -Encoding ASCII
& icacls.exe $authorized /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' "*${tunnelSid}:R" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se protegió la llave pública autorizada.' }

$sshConfig=Join-Path $sshRoot 'sshd_config'
$hostKeySlash=$hostKey.Replace('\','/')
$authorizedSlash=$authorized.Replace('\','/')
@"
Port $SshPort
HostKey "$hostKeySlash"
AuthorizedKeysFile "$authorizedSlash"
AllowUsers $TunnelUser
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowTcpForwarding local
PermitOpen 127.0.0.1:$($config.port)
GatewayPorts no
AllowAgentForwarding no
PermitTTY no
MaxSessions 0
MaxAuthTries 3
LoginGraceTime 30
LogLevel INFO
"@ | Set-Content -LiteralPath $sshConfig -Encoding ASCII
& (Join-Path $sshBin 'sshd.exe') -t -f $sshConfig
if ($LASTEXITCODE -ne 0) { throw 'OpenSSH rechazó la configuración. No se abrió firewall.' }
$ruleName='MilenioSSH-'+$config.instance_id
$rule=Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($rule) {
    $rule | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $AllowedAddresses
    $rule | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -LocalPort $SshPort -Protocol TCP
} else {
    New-NetFirewallRule -Name $ruleName -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $SshPort -RemoteAddress $AllowedAddresses -Profile Private,Domain -Program (Join-Path $sshBin 'sshd.exe') | Out-Null
}
$sshTask='MilenioSSH-'+$config.instance_id
$action=New-ScheduledTaskAction -Execute (Join-Path $sshBin 'sshd.exe') -Argument ('-D -f "'+$sshConfig+'"')
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$task=Get-ScheduledTask -TaskName $sshTask -ErrorAction SilentlyContinue
if ($task) { Stop-ScheduledTask -TaskName $sshTask }
Register-ScheduledTask -TaskName $sshTask -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -Settings $settings -User SYSTEM -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName $sshTask
Write-Output ('Llave pública del servidor para verificar en cada cliente: '+(Get-Content -LiteralPath ($hostKey+'.pub') -Raw).Trim())
Write-Output ('Usuario de túnel: '+$TunnelUser+'. Puerto SSH: '+$SshPort+'. Verifica conexión y reinicio desde el cliente antes de declarar el acceso operativo.')
