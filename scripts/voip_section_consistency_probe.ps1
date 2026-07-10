#!/usr/bin/env pwsh
# VoIP 섹션 정합성 프로브 — Tab+S10 ADB, 백엔드 통화 이력, 오디오·세션 충돌 마커
param(
    [string]$TabDevice = "R83W70QY11H",
    [string]$S10Device = "172.30.1.19:5555",
    [string]$Since = "24h",
    [int]$LogTail = 8000,
    [string]$Container = "devanalysis114-backend"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RepoRoot "evidence\voip-section-consistency\$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Get-VoiceCallVolumeIndex([string]$Device) {
    $raw = adb -s $Device shell dumpsys audio 2>&1 | Out-String
    $m = [regex]::Match($raw, 'STREAM_VOICE_CALL:\s*\r?\n\s*-?\s*Current:.*?2 \(speaker\):\s*(\d+)')
    if ($m.Success) { return [int]$m.Groups[1].Value }
    $m2 = [regex]::Match($raw, 'STREAM_VOICE_CALL:[\s\S]*?2 \(speaker\):\s*(\d+)')
    if ($m2.Success) { return [int]$m2.Groups[1].Value }
    return $null
}

function Get-AudioMode([string]$Device) {
    $raw = adb -s $Device shell dumpsys audio 2>&1 | Out-String
    if ($raw -match 'mode\s*=\s*MODE_IN_COMMUNICATION') { return 'MODE_IN_COMMUNICATION' }
    if ($raw -match 'mode\s*=\s*MODE_NORMAL') { return 'MODE_NORMAL' }
    return 'unknown'
}

function Get-LogMarkers([string]$Device) {
    $log = adb -s $Device logcat -d -t $LogTail 2>&1 | Out-String
    return [ordered]@{
        voice_lease_face_acquire = ([regex]::Matches($log, 'VOICE_LEASE.*acquire.*owner.:face')).Count
        companion_dormant_recover = ([regex]::Matches($log, 'dormant_watchdog_recover')).Count
        voip_session_quiesce = ([regex]::Matches($log, 'VOIP_SESSION_GUARD.*quiesce')).Count
        voip_blocked_voice_input = ([regex]::Matches($log, 'blocked_voip_session')).Count
        native_tts_delivered = ([regex]::Matches($log, 'server_audio_voicecall_native')).Count
        expo_av_tts_delivered = ([regex]::Matches($log, 'tts_delivery.:server_audio[^"]')).Count
        ice_restart = ([regex]::Matches($log, 'ICE restart')).Count
        voip_connected = ([regex]::Matches($log, 'Connection state: connected|State change callback: connected')).Count
        companion_arm_suspended_true = ([regex]::Matches($log, 'companion_arm_suspended.:true')).Count
    }
}

Write-Host "VoIP section consistency probe -> $RunDir"

$devices = @(
    @{ id = $TabDevice; role = 'tab' },
    @{ id = $S10Device; role = 's10' }
)

$deviceReport = @{}
foreach ($d in $devices) {
    $devList = adb devices 2>&1 | Out-String
    $online = $devList -match [regex]::Escape($d.id)
    if (-not $online) {
        $deviceReport[$d.role] = @{ online = $false }
        continue
    }
    $pkg = adb -s $d.id shell dumpsys package com.parkcheolhong.worldlinco 2>&1 | Out-String
    $ver = if ($pkg -match 'versionCode=(\d+)') { $Matches[1] } else { $null }
    $deviceReport[$d.role] = @{
        online = $true
        device_id = $d.id
        version_code = $ver
        audio_mode_idle = Get-AudioMode $d.id
        stream_voice_call_speaker_index = Get-VoiceCallVolumeIndex $d.id
        log_markers = Get-LogMarkers $d.id
    }
}

$backendTrace = & pwsh -NoProfile -File (Join-Path $RepoRoot "scripts\voip_call_trace.ps1") -Since $Since -TailLines 4000 2>&1 | Out-String
$backendTrace | Set-Content (Join-Path $RunDir "backend_trace.txt") -Encoding UTF8

$voiceEvents = ([regex]::Matches($backendTrace, '\[음성\]')).Count
$signalEvents = ([regex]::Matches($backendTrace, '\[신호\]')).Count
$lastCall = $null
if ($backendTrace -match 'Call ended \| call_id=([^\s|]+)') {
    $lastCall = $Matches[1]
}

$collisionRisk = $false
foreach ($role in @('tab', 's10')) {
    $m = $deviceReport[$role].log_markers
    if ($m -and $m.voip_connected -gt 0 -and ($m.voice_lease_face_acquire -gt 0 -or $m.companion_dormant_recover -gt 0)) {
        $collisionRisk = $true
    }
}

$lowVolumeRisk = $false
foreach ($role in @('tab', 's10')) {
    $idx = $deviceReport[$role].stream_voice_call_speaker_index
    if ($null -ne $idx -and $idx -lt 12) { $lowVolumeRisk = $true }
}

$verdict = 'PASS'
$issues = @()
if ($collisionRisk) { $verdict = 'FAIL'; $issues += 'section_collision:companion_mic_during_voip' }
if ($lowVolumeRisk) { if ($verdict -eq 'PASS') { $verdict = 'WARN' }; $issues += 'stream_voice_call_below_12_idle' }
if ($voiceEvents -eq 0) { if ($verdict -eq 'PASS') { $verdict = 'WARN' }; $issues += 'no_backend_voice_translation_24h' }

$summary = [ordered]@{
    timestamp = (Get-Date).ToString('o')
    run_dir = $RunDir
    verdict = $verdict
    issues = $issues
    backend = @{
        voice_translation_events = $voiceEvents
        signal_events = $signalEvents
        last_call_id = $lastCall
    }
    devices = $deviceReport
}

$summary | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $RunDir "summary.json") -Encoding UTF8
Write-Host ($summary | ConvertTo-Json -Depth 6)
Write-Host "verdict=$verdict issues=$($issues -join ',')"
