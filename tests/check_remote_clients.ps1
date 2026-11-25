# Isolated enrollment rehearsal. The firewall is an in-memory stand-in.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../infra/Clientes-SSH.ps1')

function Set-NetFirewallAddressFilter {
    [CmdletBinding()]
    param([Parameter(ValueFromPipeline)]$InputObject, [string[]]$RemoteAddress)
    process {
        if ($script:failFirewall) { throw 'Simulated firewall failure' }
        $InputObject.RemoteAddress = [string[]]$RemoteAddress
        $script:updates++
    }
}

function Assert-True($Condition, $Message) { if (-not $Condition) { throw $Message } }
function Test-Key([byte]$LastByte) {
    $blob = New-Object byte[] 51
    $blob[3] = 11
    [Text.Encoding]::ASCII.GetBytes('ssh-ed25519').CopyTo($blob, 4)
    $blob[18] = 32
    $blob[50] = $LastByte
    'ssh-ed25519 ' + [Convert]::ToBase64String($blob)
}

$work = Join-Path ([IO.Path]::GetTempPath()) ('milenio-remote-test-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($work) | Out-Null
$file = Join-Path $work 'authorized_keys'
try {
    $first = Test-Key 1
    $second = Test-Key 2
    $filter = [pscustomobject]@{ RemoteAddress = [string[]]@('192.168.1.10') }
    $script:updates = 0
    [IO.File]::WriteAllLines($file, [string[]]@('# PC', "$first PC"), [Text.Encoding]::ASCII)
    Add-MilenioSshClients $filter $file @('192.168.1.20') @("$second phone", $second)
    Assert-True (($filter.RemoteAddress -join ',') -eq '192.168.1.10,192.168.1.20') 'Lost original PC or missing mobile address'
    $expected = @('# PC', "$first PC", $second) -join ','
    Assert-True (([IO.File]::ReadAllLines($file) -join ',') -ceq $expected) 'Existing key lost or mobile key duplicated'
    Add-MilenioSshClients $filter $file @('192.168.1.20') @($second)
    Assert-True ($script:updates -eq 1) 'Repeat enrollment changed the firewall'
    Assert-True (([IO.File]::ReadAllLines($file) -join ',') -ceq $expected) 'Repeat enrollment changed keys'

    foreach ($address in @('0.0.0.0','198.51.100.1','192.168.1.0/24','*','::1','10.1')) {
        $rejected = $false
        try { Assert-MilenioPrivateAddress $address } catch { $rejected = $true }
        Assert-True $rejected 'Accepted a public, broad or ambiguous address'
    }
    $script:failFirewall = $true
    $rejected = $false
    try { Add-MilenioSshClients $filter $file @('10.0.0.5') @((Test-Key 3)) } catch { $rejected = $true }
    Assert-True $rejected 'Expected firewall error'
    Assert-True (([IO.File]::ReadAllLines($file) -join ',') -ceq $expected) 'Firewall failure changed keys'
    Assert-True (@(Get-ChildItem -LiteralPath $work).Count -eq 1) 'Temporary keys left behind'
    $script:failFirewall = $false
    if ($env:OS -eq 'Windows_NT') {
        $hold = [IO.File]::Open($file, 'Open', 'Read', 'Read')
        $rejected = $false
        try { Add-MilenioSshClients $filter $file @('10.0.0.5') @((Test-Key 3)) } catch { $rejected = $true } finally { $hold.Dispose() }
        Assert-True $rejected 'Expected locked authorization file to prevent enrollment'
        Assert-True (($filter.RemoteAddress -join ',') -ceq '192.168.1.10,192.168.1.20') 'Key update failure left new address active'
        Assert-True (([IO.File]::ReadAllLines($file) -join ',') -ceq $expected) 'Key update failure changed original file'
    }
    $priorUpdates = $script:updates
    [IO.File]::WriteAllText($file, "restrict $first")
    $rejected = $false
    try { Add-MilenioSshClients $filter $file @('10.0.0.5') @($first) } catch { $rejected = $true }
    Assert-True $rejected 'A manually restricted key was silently broadened'
    Assert-True ($script:updates -eq $priorUpdates) 'Invalid input changed the firewall'
    Write-Output 'PASS: preserve clients, idempotent enrollment, private addresses, restricted key, failed admission.'
} finally {
    [IO.File]::Delete($file)
    [IO.Directory]::Delete($work)
}
