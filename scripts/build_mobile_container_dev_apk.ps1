#!/usr/bin/env pwsh
<#
.SYNOPSIS
  실기기 실험용 APK — Docker 컨테이너 백엔드(LAN)에 연결.

.EXAMPLE
  .\scripts\build_mobile_container_dev_apk.ps1
  .\scripts\build_mobile_container_dev_apk.ps1 -InstallDevices R83W70QY11H,172.30.1.19:5555
#>
param(
    [string[]]$InstallDevices = @(),
    [switch]$SkipDockerPrep
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $SkipDockerPrep) {
    & (Join-Path $PSScriptRoot "ensure_docker_backend_lan.ps1")
}

$apiBase = & (Join-Path $PSScriptRoot "resolve_container_api_base.ps1")
Write-Host "EAS container-dev API: $apiBase"

$env:EXPO_PUBLIC_API_BASE_URL = $apiBase
$env:EXPO_PUBLIC_RELEASE_CHANNEL = "container-dev"

$mobileDir = (Resolve-Path (Join-Path $RepoRoot "apps\mobile-nadotongryoksa")).Path
Set-Location $mobileDir

# 모노레포 전체 업로드(2GB+) 방지 — mobile 앱 디렉터리만 아카이브
$env:EAS_NO_VCS = "1"
$env:EAS_PROJECT_ROOT = $mobileDir

npx eas-cli build --profile container-dev --platform android --non-interactive

if ($InstallDevices.Count -gt 0) {
    Write-Host "After build completes, download APK and run:"
    foreach ($d in $InstallDevices) {
        Write-Host "  adb -s $d install -r <apk-path>"
    }
}
