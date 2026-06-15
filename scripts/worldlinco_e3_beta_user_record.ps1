#!/usr/bin/env pwsh
# Append one E-3-4 beta user row (1+ successful WiFi call, build 74+)
param(
    [Parameter(Mandatory = $true)]
    [string]$DisplayName,
    [string]$Locale = "ko-KR",
    [string]$Device = "",
    [ValidateSet("yes", "no", "")]
    [string]$Wifi = "yes",
    [ValidateSet("yes", "no", "")]
    [string]$Connected = "yes",
    [ValidateSet("yes", "no", "")]
    [string]$Relay1Turn = "yes",
    [string]$Feedback = "",
    [string]$Notes = "",
    [int]$Build = 73,
    [string]$CsvPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $CsvPath) {
    $CsvPath = Join-Path $RepoRoot "evidence\worldlinco-v1-launch\E3-4_beta_users.csv"
}

if (-not (Test-Path $CsvPath)) {
    throw "CSV not found: $CsvPath"
}

$date = Get-Date -Format "yyyy-MM-dd"
$escaped = @(
    $DisplayName,
    $Locale,
    $Device,
    $Wifi,
    $Connected,
    $Relay1Turn,
    ($Feedback -replace '"', '""'),
    $date,
    ($Notes -replace '"', '""')
) | ForEach-Object { if ($_ -match '[,"\r\n#]') { """$_""" } else { $_ } }

$row = ($escaped -join ",") + ",$Build"
Add-Content -Path $CsvPath -Value $row -Encoding utf8

$dataRows = Get-Content $CsvPath | Where-Object { $_ -and -not $_.StartsWith("#") -and $_ -notmatch "^user_id," }
$count = @($dataRows).Count
Write-Host "[E-3-4] Recorded: $DisplayName ($date) — total rows: $count / 10"
if ($count -ge 10) {
    Write-Host "[E-3-4] DoD threshold reached (10 users)."
}
