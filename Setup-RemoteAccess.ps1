# Run elevated on the assigned server after creating Gerencia locally.
param([string]$InstallRoot=(Join-Path $env:LOCALAPPDATA 'MilenioServer'),
      [Parameter(Mandatory)][string[]]$AllowedAddresses,
      [Parameter(Mandatory)][string[]]$ClientPublicKeyFiles,
      [string]$TunnelUser='milenio_tunnel',[int]$SshPort=2222,[switch]$AddClients)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'infra/Clientes-SSH.ps1')
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Requiere PowerShell elevado para instalar OpenSSH y la regla limitada de firewall.' }
if ($TunnelUser -notmatch '^[a-z][a-z0-9_]{3,24}$' -or $SshPort -lt 1024 -or $SshPort -gt 65535) { throw 'Usuario o puerto inválido.' }
foreach ($address in $AllowedAddresses) { Assert-MilenioPrivateAddress $address }
$current=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/current.json') -Raw | ConvertFrom-Json
$env:MILENIO_DEPLOYMENT_CONFIG=Join-Path $InstallRoot 'private/infra.local.json'
$config=Get-Content -LiteralPath $env:MILENIO_DEPLOYMENT_CONFIG -Raw | ConvertFrom-Json
if ($config.role -ne 'server' -or $config.expected_hostname -ne $env:COMPUTERNAME) { throw 'Equipo no asignado como servidor.' }
& (Join-Path $current.release_dir '.venv/Scripts/python.exe') (Join-Path $current.release_dir 'scripts/deploy.py') manage remote_ready
if ($LASTEXITCODE -ne 0) { throw 'Crea Gerencia local antes de abrir acceso remoto.' }
$keys=@()
foreach ($file in $ClientPublicKeyFiles) {
    $keys += Get-MilenioPublicKey (Get-Content -LiteralPath $file -Raw)
}
if (-not $keys.Count) { throw 'Faltan llaves públicas de clientes.' }
$lockPath=Join-Path $InstallRoot 'private/remote-access.lock'
$lock=[IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
try {
$sshRoot=Join-Path $env:ProgramData ('MilenioSSH-'+$config.instance_id)
$ownership=Join-Path $sshRoot 'owner.txt'
$existingUser=Get-LocalUser -Name $TunnelUser -ErrorAction SilentlyContinue
if ($existingUser -and (-not (Test-Path -LiteralPath $ownership) -or (Get-Content -LiteralPath $ownership -Raw).Trim() -ne $TunnelUser)) { throw 'El usuario ya existe y no pertenece a esta instalación. Elige otro nombre.' }
$sshBin=Join-Path $env:WINDIR 'System32/OpenSSH'
$hostKey=Join-Path $sshRoot 'host_ed25519'
$authorized=Join-Path $sshRoot 'authorized_keys'
$sshConfig=Join-Path $sshRoot 'sshd_config'
$ruleName='MilenioSSH-'+$config.instance_id
$rule=Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($AddClients) {
    if (-not $existingUser -or -not $rule -or -not (Test-Path -LiteralPath $authorized)) {
        throw 'Primero configura el acceso remoto inicial desde infra/INSTALAR.md.'
    }
    $directives=@(Get-Content -LiteralPath $sshConfig)
    if ($directives -notcontains "Port $SshPort" -or $directives -notcontains "AllowUsers $TunnelUser" -or
        $directives -notcontains "PermitOpen 127.0.0.1:$($config.port)") {
        throw 'Los puertos o el usuario difieren de la instalación existente. Comprueba la ficha del servidor.'
    }
    $fingerprint = & (Join-Path $sshBin 'ssh-keygen.exe') -E sha256 -lf ($hostKey+'.pub')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar la llave pública de este servidor.' }
    $filters = @($rule | Get-NetFirewallAddressFilter)
    if ($filters.Count -ne 1) { throw 'Se requiere una única regla de direcciones para esta instalación.' }
    Add-MilenioSshClients $filters[0] $authorized $AllowedAddresses $keys
    Write-Output "Alta terminada. Huella del servidor: $fingerprint"
    Write-Output "Usuario: $TunnelUser. Puerto SSH: $SshPort. Destino del túnel: 127.0.0.1:$($config.port)."
    return
}
$capability=Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
if ($capability.State -ne 'Installed') { Add-WindowsCapability -Online -Name $capability.Name | Out-Null }
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
if (-not (Test-Path -LiteralPath $hostKey)) {
    $generateHostKey = "import subprocess,sys; subprocess.run([sys.argv[1],'-t','ed25519','-N','','-f',sys.argv[2]],check=True)"
    & (Join-Path $current.release_dir '.venv/Scripts/python.exe') -c $generateHostKey (Join-Path $sshBin 'ssh-keygen.exe') $hostKey
    if ($LASTEXITCODE -ne 0) { throw 'No se generó llave de servidor.' }
}
$keys | Set-Content -LiteralPath $authorized -Encoding ASCII
& icacls.exe $authorized /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' "*${tunnelSid}:R" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se protegió la llave pública autorizada.' }

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
Write-Output ('Llave pública del servidor para verificar en cada cliente: '+(Get-MilenioPublicKey (Get-Content -LiteralPath ($hostKey+'.pub') -Raw)))
& (Join-Path $sshBin 'ssh-keygen.exe') -E sha256 -lf ($hostKey+'.pub')
Write-Output ('Usuario de túnel: '+$TunnelUser+'. Puerto SSH: '+$SshPort+'. Verifica conexión y reinicio desde el cliente antes de declarar el acceso operativo.')
} finally { $lock.Dispose() }
