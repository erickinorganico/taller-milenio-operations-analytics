function Assert-MilenioPrivateAddress([string]$Address) {
    $ip = $null
    if (-not [IPAddress]::TryParse($Address, [ref]$ip) -or $ip.ToString() -cne $Address) {
        throw 'Indica una IPv4 privada individual, como la que muestra el celular en el Wi-Fi.'
    }
    $bytes = $ip.GetAddressBytes()
    $private = $bytes[0] -eq 10 -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168) -or
        ($bytes[0] -eq 100 -and $bytes[1] -ge 64 -and $bytes[1] -le 127)
    if ($bytes.Length -ne 4 -or -not $private) { throw 'Cada cliente necesita su propia IPv4 privada.' }
}

function Get-MilenioPublicKey([string]$Line) {
    # Ed25519 wire encoding: algorithm name, key length (32), and public bytes.
    if ($Line.Trim() -cmatch '^ssh-ed25519[ \t]+(AAAAC3NzaC1lZDI1NTE5AAAAI[A-Za-z0-9+/]{43})(?:[ \t]+[^\r\n]*)?\z') {
        $blob = $Matches[1]
        $bytes = [Convert]::FromBase64String($blob)
        if ($bytes.Length -eq 51 -and $bytes[18] -eq 32) { return "ssh-ed25519 $blob" }
    }
    throw 'Se requiere una línea de llave pública Ed25519; exporta la llave pública desde el dispositivo.'
}

function Add-MilenioSshClients($AddressFilter, [string]$AuthorizedFile, [string[]]$Addresses, [string[]]$Keys) {
    $oldAddresses = @($AddressFilter.RemoteAddress)
    if (-not $oldAddresses.Count) { throw 'La regla del servidor carece de una lista privada verificable.' }
    foreach ($address in ($oldAddresses + $Addresses)) { Assert-MilenioPrivateAddress $address }
    $newAddresses = @($Addresses | Where-Object { $oldAddresses -notcontains $_ } | Select-Object -Unique)

    $lines = @([IO.File]::ReadAllLines($AuthorizedFile))
    # A manually restricted key must never gain an unrestricted duplicate.
    $existingKeys = @(foreach ($line in $lines) {
        if ($line.Trim() -and -not $line.Trim().StartsWith('#')) { Get-MilenioPublicKey $line }
    })
    $newKeys = @(foreach ($key in $Keys) {
        $plain = Get-MilenioPublicKey $key
        if ($existingKeys -cnotcontains $plain) { $existingKeys += $plain; $plain }
    })
    $temporary = $AuthorizedFile + '.' + [Guid]::NewGuid().ToString('N') + '.new'
    $previous = $temporary + '.previous'
    $filterChanged = $false
    try {
        if ($newKeys.Count) { [IO.File]::WriteAllLines($temporary, [string[]]($lines + $newKeys), [Text.Encoding]::ASCII) }
        if ($newAddresses.Count) {
            $AddressFilter | Set-NetFirewallAddressFilter -RemoteAddress ($oldAddresses + $newAddresses) -ErrorAction Stop | Out-Null
            $filterChanged = $true
        }
        if ($newKeys.Count) {
            # Windows ReplaceFile retains the protected DACL of authorized_keys.
            [IO.File]::Replace($temporary, $AuthorizedFile, $previous)
        }
    } catch {
        if (-not [IO.File]::Exists($AuthorizedFile) -and [IO.File]::Exists($previous)) {
            [IO.File]::Move($previous, $AuthorizedFile)
        }
        if ($filterChanged) {
            $AddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $oldAddresses -ErrorAction Stop | Out-Null
        }
        throw
    } finally {
        [IO.File]::Delete($temporary)
    }
    [IO.File]::Delete($previous)
}
