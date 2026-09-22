[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Workbook
)

$root = (Get-Location).Path
$inputPath = [IO.Path]::GetFullPath($Workbook)
$rootWithSlash = $root.TrimEnd('\') + '\'
if (-not $inputPath.StartsWith($rootWithSlash, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Workbook must be inside the current workspace.'
}
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) { throw 'Workbook does not exist.' }

$excel = $null; $book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AutomationSecurity = 3
    $book = $excel.Workbooks.Open($inputPath, 0, $false)
    $excel.CalculateFullRebuild()
    $book.Save()
    Write-Output (ConvertTo-Json @{ status = 'pass'; workbook = $Workbook } -Compress)
}
finally {
    if ($null -ne $book) { try { $book.Close($true) } catch {} }
    if ($null -ne $excel) { try { $excel.Quit() } catch {} }
    if ($null -ne $book) { [Runtime.InteropServices.Marshal]::ReleaseComObject($book) | Out-Null }
    if ($null -ne $excel) { [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null }
}
