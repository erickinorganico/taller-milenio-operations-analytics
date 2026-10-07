param([string]$InstallRoot=(Join-Path $env:LOCALAPPDATA 'MilenioServer'),[System.Management.Automation.PSCredential]$StartupCredential,[switch]$AtLogon)
$ErrorActionPreference='Stop'
$config=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/infra.local.json') -Raw | ConvertFrom-Json
if ($config.role -ne 'server' -or $config.expected_hostname -ne $env:COMPUTERNAME) { throw 'No es el servidor asignado.' }
$taskName='Milenio-'+$config.instance_id
$scriptPath=Join-Path $InstallRoot 'Run-Server.ps1'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$scriptPath+'"') -WorkingDirectory $InstallRoot
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$currentIdentity=[System.Security.Principal.WindowsIdentity]::GetCurrent()
if ($AtLogon) {
    $trigger=New-ScheduledTaskTrigger -AtLogOn -User $currentIdentity.Name
    $principal=New-ScheduledTaskPrincipal -UserId $currentIdentity.Name -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Write-Output 'Arranque al iniciar sesión registrado. No inicia antes del login.'
} else {
    if (-not $StartupCredential) { $StartupCredential=Get-Credential -UserName $currentIdentity.Name -Message 'Cuenta Windows del servidor: la contraseña se entrega al Programador de tareas, nunca a GitHub ni al chat.' }
    $account=New-Object System.Security.Principal.NTAccount($StartupCredential.UserName)
    if ($account.Translate([System.Security.Principal.SecurityIdentifier]).Value -ne $currentIdentity.User.Value) { throw 'Debe ser la identidad que instalará/conectará Gmail (DPAPI).' }
    $trigger=New-ScheduledTaskTrigger -AtStartup
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User $StartupCredential.UserName -Password $StartupCredential.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
    Write-Output 'Arranque con Windows registrado. Falta comprobar reinicio real y acceso DPAPI en esta computadora.'
}

$backupScript=Join-Path $InstallRoot 'Backup-Server.ps1'
$current=Get-Content -LiteralPath (Join-Path $InstallRoot 'private/current.json') -Raw | ConvertFrom-Json
Copy-Item -LiteralPath (Join-Path $current.release_dir 'Backup-Server.ps1') -Destination $backupScript -Force
$backupAction=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$backupScript+'" -InstallRoot "'+$InstallRoot+'"') -WorkingDirectory $InstallRoot
$backupTrigger=New-ScheduledTaskTrigger -Daily -At '03:00'
$backupSettings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
if ($AtLogon) {
    Register-ScheduledTask -TaskName ($taskName+'-Backup') -Action $backupAction -Trigger $backupTrigger -Settings $backupSettings -Principal $principal -Force | Out-Null
} else {
    Register-ScheduledTask -TaskName ($taskName+'-Backup') -Action $backupAction -Trigger $backupTrigger -Settings $backupSettings -User $StartupCredential.UserName -Password $StartupCredential.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
}
Write-Output 'Respaldo diario 03:00 registrado; pausa y reinicio breves. No borra respaldos anteriores. Comprobar espacio y copia externa.'
