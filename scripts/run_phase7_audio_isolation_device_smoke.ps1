#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Phase 7.6 — 오디오 세션 격리 실기기 스모크 (로그 기반).

.DESCRIPTION
  단말에서 수동으로 시나리오를 수행한 뒤 logcat 에서 격리 이벤트를 확인한다.
  자동 통화/다이얼은 불가 — UI 조작은 테스터가 수행.

.PARAMETER Device
  adb -s 대상 (기본: 첫 번째 device)

.PARAMETER ExpectedBuild
  설치 기대 versionCode (기본: 317)

.EXAMPLE
  .\scripts\run_phase7_audio_isolation_device_smoke.ps1 -Device R83W70QY11H
#>
param(
    [string]$Device = "",
    [int]$ExpectedBuild = 317,
    [string]$PackageName = "com.parkcheolhong.worldlinco"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $RepoRoot "evidence\phase7-audio-isolation-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Invoke-Adb {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    if ($Device) {
        & adb -s $Device @Args
    } else {
        & adb @Args
    }
}

$devices = @(Invoke-Adb devices | Select-String "device$" | ForEach-Object { ($_ -split "\s+")[0] })
if ($devices.Count -eq 0) { throw "No adb device connected" }
if (-not $Device) { $Device = $devices[0] }

$dumpsys = (Invoke-Adb shell dumpsys package $PackageName 2>$null | Out-String)
$vcMatch = [regex]::Match($dumpsys, "versionCode=(\d+)")
$vnMatch = [regex]::Match($dumpsys, "versionName=([^\s]+)")
$installedCode = if ($vcMatch.Success) { [int]$vcMatch.Groups[1].Value } else { -1 }
$installedName = if ($vnMatch.Success) { $vnMatch.Groups[1].Value } else { "?" }

Write-Host "=== Phase 7.6 audio isolation smoke ===" -ForegroundColor Cyan
Write-Host "Device: $Device"
Write-Host "Installed: $installedName / build $installedCode (expected >= $ExpectedBuild)"

$scenarios = @(
    @{
        Id = "7.6-A"
        Title = "대면 ON → VoIP 친구 발신"
        Steps = @(
            "홈에서 대면 통역(대화) 켜기 — 마이크/TTS 동작 확인",
            "통화 탭 → 친구 VoIP 발신",
            "기대: 앱 마이크·TTS 즉시 정지, 에코 없음"
        )
        Patterns = @("quiesce_voip", "VOIP_SESSION_GUARD", "revoke_current", "VOICE_LEASE")
    },
    @{
        Id = "7.6-B"
        Title = "대면 ON → 일반전화(PSTN) 발신"
        Steps = @(
            "대면 통역 다시 켜기",
            "연락처/일반전화로 PSTN 발신",
            "기대: 앱 캡처 정지 후 시스템 다이얼러"
        )
        Patterns = @("quiesce_pstn", "pstn-assist", "revoke_current")
    },
    @{
        Id = "7.6-C"
        Title = "일반전화 종료 → 기능 재시작"
        Steps = @(
            "통화 종료 후 앱 복귀",
            "대면 통역 또는 VoIP 다시 시도",
            "기대: feature lock 없음, 정상 재시작"
        )
        Patterns = @("release", "deactivate", "pstn")
    },
    @{
        Id = "7.6-D"
        Title = "수신 VoIP 수락"
        Steps = @(
            "다른 단말에서 이 기기로 VoIP 수신",
            "수락",
            "기대: 수락 전 quiesce, 에코 없음"
        )
        Patterns = @("quiesce_voip", "incoming", "VOIP_SESSION_GUARD")
    }
)

foreach ($s in $scenarios) {
    Write-Host ""
    Write-Host "--- $($s.Id): $($s.Title) ---" -ForegroundColor Yellow
    $s.Steps | ForEach-Object { Write-Host "  • $_" }
    Read-Host "시나리오 완료 후 Enter"
    Invoke-Adb logcat -d -v time ReactNativeJS:I *:S | Out-File (Join-Path $LogDir "$($s.Id).log") -Encoding utf8
    $logText = Get-Content (Join-Path $LogDir "$($s.Id).log") -Raw
    $hits = @()
    foreach ($p in $s.Patterns) {
        if ($logText -match [regex]::Escape($p)) { $hits += $p }
    }
    if ($hits.Count -gt 0) {
        Write-Host "  PASS signals: $($hits -join ', ')" -ForegroundColor Green
    } else {
        Write-Host "  WARN: no expected log patterns — check $($s.Id).log" -ForegroundColor Red
    }
    Invoke-Adb logcat -c | Out-Null
}

$summary = @{
    device = $Device
    installedVersionName = $installedName
    installedVersionCode = $installedCode
    expectedBuild = $ExpectedBuild
    logDir = $LogDir
    scenarios = $scenarios.Id
    completedAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 4
$summaryPath = Join-Path $LogDir "summary.json"
[System.IO.File]::WriteAllText($summaryPath, $summary)
Write-Host ""
Write-Host "Evidence: $LogDir" -ForegroundColor Cyan
Write-Host "Summary: $summaryPath"

if ($installedCode -lt $ExpectedBuild) {
    Write-Host "NOTE: device build $installedCode < expected $ExpectedBuild — install build $ExpectedBuild first." -ForegroundColor Yellow
    exit 2
}
