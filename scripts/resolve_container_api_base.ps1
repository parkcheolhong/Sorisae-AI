#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Docker 백엔드에 실기기(폰/탭)가 붙을 LAN API URL을 반환한다.

.DESCRIPTION
  - 호스트 PC의 사설 IPv4(172.x / 10.x)를 고른 뒤 http://{ip}:8000 형태로 출력.
  - .env 의 MOBILE_CONTAINER_API_BASE_URL 이 있으면 우선 사용.
  - 127.0.0.1 / localhost 는 실기기에서 접근 불가이므로 사용하지 않는다.
#>
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env"

if (Test-Path $EnvFile) {
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*MOBILE_CONTAINER_API_BASE_URL\s*=\s*(.+)\s*$') {
            $fromEnv = $Matches[1].Trim().Trim('"').Trim("'")
            if ($fromEnv -and $fromEnv -notmatch '127\.0\.0\.1|localhost') {
                Write-Output $fromEnv
                return
            }
        }
    }
}

$candidates = @(Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '127.*'
        -and $_.PrefixOrigin -ne 'WellKnown'
        -and ($_.IPAddress -like '172.*' -or $_.IPAddress -like '10.*' -or $_.IPAddress -like '192.168.*')
    } |
    Sort-Object -Property @{
        Expression = {
            if ($_.IPAddress -like '172.30.*') { 0 }
            elseif ($_.IPAddress -like '172.*') { 1 }
            elseif ($_.IPAddress -like '10.*') { 2 }
            else { 3 }
        }
    }, IPAddress)

if ($candidates.Count -eq 0) {
    throw "LAN IPv4 not found. Set MOBILE_CONTAINER_API_BASE_URL in .env"
}

$ip = $candidates[0].IPAddress
Write-Output "http://${ip}:$Port"
