#!/usr/bin/env pwsh
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$MonitorSec = 75
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator\boundary_build63_monitor_$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $RunDir "run.log") -Value $line
}

function Invoke-Adb {
    param([string]$Device, [string[]]$AdbArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & adb -s $Device @AdbArgs 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" }
        }
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
}

function Wait-ForAuthReady([string]$Device, [int]$TimeoutSec = 120) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Wait-ForLogPattern([string]$Device, [string]$Pattern, [int]$TimeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-LogcatText $Device) -match $Pattern) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
}

function Tap-UiLabel {
    param([string]$Device, [string[]]$Labels, [string]$DumpPath)
    Get-UiDump -Device $Device -OutPath $DumpPath | Out-Null
    if (-not (Test-Path $DumpPath)) { return $false }
    [xml]$doc = Get-Content -Raw $DumpPath
    foreach ($n in $doc.SelectNodes("//node")) {
        $text = ([string]$n.GetAttribute("text")).Trim()
        $desc = ([string]$n.GetAttribute("content-desc")).Trim()
        $bounds = [string]$n.GetAttribute("bounds")
        if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { continue }
        foreach ($label in $Labels) {
            if ($text -like "*$label*" -or $desc -like "*$label*") {
                $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
                $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
                Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
                return $true
            }
        }
    }
    return $false
}

function Analyze-RelayBoundary([string]$Text, [string]$Label) {
    $deferReasons = [regex]::Matches($Text, '"defer_reason":"([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
    $flushReasons = [regex]::Matches($Text, 'VOIP_VOICE_RELAY_SEGMENT_FLUSH[^`]*"reason":"([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
    $segmentDurations = [regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END[^`]*"segment_duration_ms":(\d+)') | ForEach-Object { [int]$_.Groups[1].Value }
    $speechSpans = [regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END[^`]*"speech_span_ms":(\d+)') | ForEach-Object { [int]$_.Groups[1].Value }
    return [pscustomobject]@{
        device = $Label
        silero_end = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END')).Count
        flush_true = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END[^`]*"flush":true')).Count
        flush_false = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END[^`]*"flush":false')).Count
        defer_reasons = ($deferReasons | Group-Object | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ', '
        flush_reasons = ($flushReasons | Group-Object | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ', '
        segment_durations_ms = ($segmentDurations -join ', ')
        speech_span_ms = ($speechSpans -join ', ')
        relay_sent = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SENT')).Count
        playback = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_PLAYBACK')).Count
        fixed_interval_flush = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SEGMENT_FLUSH[^`]*fixed_interval')).Count
    }
}

Write-Step "Run dir: $RunDir"
foreach ($dev in @($CallerDevice, $CalleeDevice)) {
    Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $dev @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
    Invoke-Adb $dev @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
}
Start-Sleep -Seconds 5

if (-not (Wait-ForAuthReady $CallerDevice)) { throw "Tab auth timeout" }
if (-not (Wait-ForAuthReady $CalleeDevice)) { throw "S10 auth timeout" }

$connected = (Get-LogcatText $CallerDevice) -match 'Connection state: connected|VOIP_CONNECTION_STATE_CONNECTED'
if (-not $connected) {
    Write-Step "Starting VoIP call Tab -> S10"
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId'"
    Invoke-Adb $CallerDevice @("shell", $cmd) | Out-Null
    Start-Sleep -Seconds 6
    if (-not (Wait-ForLogPattern $CalleeDevice "VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED" 120)) {
        throw "Incoming timeout"
    }
    $accepted = $false
    for ($i = 0; $i -lt 12; $i++) {
        for ($s = 0; $s -lt 3; $s++) {
            Invoke-Adb $CalleeDevice @("shell", "input", "swipe", "540", "1600", "540", "500", "350") | Out-Null
            Start-Sleep -Milliseconds 700
        }
        if (Tap-UiLabel -Device $CalleeDevice -Labels @("받기", "Accept") -DumpPath (Join-Path $RunDir "accept_$i.xml")) {
            $accepted = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $accepted) { throw "Accept failed" }
    $null = Wait-ForLogPattern $CallerDevice "Connection state: connected|VOIP_CONNECTION_STATE_CONNECTED" 90
    $null = Wait-ForLogPattern $CalleeDevice "Connection state: connected|VOIP_CONNECTION_STATE_CONNECTED" 90
    Start-Sleep -Seconds 8
} else {
    Write-Step "Call already connected"
}

Write-Step "Clear logcat + monitor ${MonitorSec}s"
Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
Start-Sleep -Seconds $MonitorSec

$tabText = Get-LogcatText $CallerDevice
$s10Text = Get-LogcatText $CalleeDevice
$tabText | Out-File (Join-Path $RunDir "tab.log") -Encoding utf8
$s10Text | Out-File (Join-Path $RunDir "s10.log") -Encoding utf8

$tabA = Analyze-RelayBoundary $tabText "Tab"
$s10A = Analyze-RelayBoundary $s10Text "S10"

$summary = [pscustomobject]@{
    build = 63
    version = "1.0.38"
    monitor_sec = $MonitorSec
    run_dir = $RunDir
    tab = $tabA
    s10 = $s10A
    s10_to_tab = [bool]($s10A.relay_sent -gt 0 -and $tabA.playback -gt 0)
    defer_working = [bool]($s10A.flush_false -gt 0 -or $s10A.defer_reasons.Length -gt 0)
    no_fixed_interval_on_s10 = [bool]($s10A.fixed_interval_flush -eq 0)
}
$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

Write-Step "S10 silero_end=$($s10A.silero_end) flush_true=$($s10A.flush_true) flush_false=$($s10A.flush_false)"
Write-Step "S10 defer: $($s10A.defer_reasons)"
Write-Step "S10 flush: $($s10A.flush_reasons)"
Write-Step "S10 segment_ms: $($s10A.segment_durations_ms) speech_span_ms: $($s10A.speech_span_ms)"
Write-Step "S10 SENT=$($s10A.relay_sent) Tab PLAYBACK=$($tabA.playback) fixed_interval=$($s10A.fixed_interval_flush)"
Write-Step "defer_working=$($summary.defer_working) s10_to_tab=$($summary.s10_to_tab) no_fixed_interval=$($summary.no_fixed_interval_on_s10)"
