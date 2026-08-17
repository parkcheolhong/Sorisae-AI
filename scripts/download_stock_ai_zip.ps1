param(
    [string]$OutputDir = $(if ($env:CODEAI_DEFAULT_OUTPUT_DIR) { $env:CODEAI_DEFAULT_OUTPUT_DIR } else { 'E:\AI주식 자동매매' }),
    [string]$BaseUrl = 'https://metanova1004.com',
    [string]$Product = 'stock-ai-autotrader',
    [string]$FileName = 'intraday_lgbm_live.zip'
)

$ErrorActionPreference = 'Stop'

$normalizedBaseUrl = $BaseUrl.TrimEnd('/')
$downloadUrl = "$normalizedBaseUrl/api/marketplace/download-product?product=$([Uri]::EscapeDataString($Product))"

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$destinationPath = Join-Path $OutputDir $FileName

& curl.exe -L $downloadUrl -o $destinationPath

if (-not (Test-Path -LiteralPath $destinationPath)) {
    throw "Download failed: file was not created at $destinationPath"
}

$file = Get-Item -LiteralPath $destinationPath
Write-Output ("saved=" + $file.FullName)
Write-Output ("size=" + $file.Length)
Write-Output ("updated=" + $file.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))
