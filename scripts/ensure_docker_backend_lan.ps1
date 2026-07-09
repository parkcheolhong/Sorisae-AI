#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Docker 백엔드를 LAN(0.0.0.0:8000)에 노출하고 health 를 확인한다.
#>
param(
    [switch]$SkipRecreate
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$apiBase = & (Join-Path $PSScriptRoot "resolve_container_api_base.ps1")
Write-Host "Container API (devices): $apiBase"

$envFile = Join-Path $RepoRoot ".env"
$lanIp = ([uri]$apiBase).Host
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    if ($content -match '(?m)^MOBILE_CONTAINER_API_BASE_URL=') {
        $content = $content -replace '(?m)^MOBILE_CONTAINER_API_BASE_URL=.*$', "MOBILE_CONTAINER_API_BASE_URL=$apiBase"
    } else {
        $content = $content.TrimEnd() + "`nMOBILE_CONTAINER_API_BASE_URL=$apiBase`n"
    }
    if ($content -notmatch '(?m)^BACKEND_PUBLISH_HOST=') {
        $content = $content.TrimEnd() + "`nBACKEND_PUBLISH_HOST=0.0.0.0`n"
    } else {
        $content = $content -replace '(?m)^BACKEND_PUBLISH_HOST=.*$', 'BACKEND_PUBLISH_HOST=0.0.0.0'
    }
    Set-Content -Path $envFile -Value $content -NoNewline
}

$env:BACKEND_PUBLISH_HOST = "0.0.0.0"
$env:BACKEND_PUBLISH_PORT = "8000"

if ($SkipRecreate) {
    docker compose up -d backend
} else {
    docker compose up -d --force-recreate backend
}

$deadline = (Get-Date).AddMinutes(3)
do {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 5
        Write-Host "Docker backend healthy: $($health | ConvertTo-Json -Compress)"
        break
    } catch {
        if ((Get-Date) -gt $deadline) {
            throw "Docker backend health check failed on http://127.0.0.1:8000/api/health"
        }
        Start-Sleep -Seconds 3
    }
} while ($true)

try {
    $lanHealth = Invoke-RestMethod -Uri "$apiBase/api/health" -TimeoutSec 5
    Write-Host "LAN health OK: $apiBase/api/health"
} catch {
    Write-Warning "LAN health from host failed ($apiBase). Check Windows Firewall for port 8000."
}

docker ps --filter "name=devanalysis114-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
