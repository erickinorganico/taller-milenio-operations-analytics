param([Parameter(Mandatory)][string]$InstanceId,[Parameter(Mandatory)][string]$ServerAddress,[Parameter(Mandatory)][string]$SshUser,[int]$SshPort=2222,[int]$ServerPort=8770,[int]$LocalPort=8770,[string]$ReleaseId,[string]$PublicHostKey,[string]$IdentityFile='')
$ErrorActionPreference='Stop'
if ($ServerAddress -notmatch '^[a-zA-Z0-9.:-]+$' -or $SshUser -notmatch '^[a-zA-Z0-9_.-]+$') { throw 'Servidor o usuario inválido.' }
if (@(@($SshPort,$ServerPort,$LocalPort) | Where-Object {$_ -lt 1024 -or $_ -gt 65535}).Count) { throw 'Puertos inválidos.' }
[guid]::Parse($InstanceId) | Out-Null
$privateRoot=Join-Path $PSScriptRoot 'private'
$configPath=Join-Path $privateRoot 'infra.local.json'
if (Test-Path -LiteralPath $configPath) { throw 'Ya existe configuración; revisa el rol antes de sustituirla.' }
if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) { throw 'Instala OpenSSH Client en Características opcionales de Windows.' }
New-Item -ItemType Directory -Force $privateRoot | Out-Null
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $privateRoot /inheritance:r /grant:r "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron proteger los archivos privados.' }
if (-not $IdentityFile) { $IdentityFile=Join-Path $privateRoot 'milenio_ed25519' }
if (-not (Test-Path -LiteralPath $IdentityFile)) {
    & ssh-keygen.exe -t ed25519 -f $IdentityFile -C 'milenio-client'
    if ($LASTEXITCODE -ne 0) { throw 'No se creó la llave.' }
}
if (-not $PublicHostKey -or $PublicHostKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+$') { throw 'Falta llave pública del servidor verificada por un canal confiable. No uses un ssh-keyscan sin verificar.' }
$known=Join-Path $privateRoot 'known_hosts'
"[$ServerAddress]:$SshPort $PublicHostKey" | Set-Content -LiteralPath $known -Encoding ASCII
@{schema_version=2;role='client';release_id=$ReleaseId;instance_id=$InstanceId;expected_hostname=$env:COMPUTERNAME;transport='ssh-loopback';central_url="http://127.0.0.1:$LocalPort";server_address=$ServerAddress;ssh_user=$SshUser;ssh_port=$SshPort;server_port=$ServerPort;local_port=$LocalPort;identity_file=$IdentityFile;known_hosts=$known;mail_worker_allowed=$false} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
Write-Output 'Cliente preparado. Entrega solo el archivo .pub al servidor. Usa Connect-Server.ps1; no inicies el taller local.'
