#!/usr/bin/env pwsh
# Tab(caller) -> S10(callee) VoIP call setup for manual voice relay test
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000226",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$MonitorSec = 45
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "manual_retest_$Stamp"
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

function Wait-ForAuthReady([string]$Device, [int]$TimeoutSec = 180) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        if ($text -match 'VoIPPendingIncoming.*"token_summary":"len:\d+' -and $text -match '"user_id":\d+') { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
}

function Tap-ByResourceId {
    param([string]$Device, [string]$ResourceId, [string]$DumpPath)
    Get-UiDump -Device $Device -OutPath $DumpPath | Out-Null
    if (-not (Test-Path $DumpPath)) { return $false }
    [xml]$doc = Get-Content -Raw $DumpPath
    $node = $doc.SelectSingleNode("//node[contains(@resource-id,'$ResourceId')]")
    if (-not $node) { return $false }
    $bounds = [string]$node.GetAttribute("bounds")
    if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { return $false }
    $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
    $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
    Write-Step "Tap resource-id '$ResourceId' at ${cx},${cy} on $Device"
    Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
    return $true
}

function Accept-IncomingVoipCall {
    param([string]$Device)
    $null = Tap-ByResourceId -Device $Device -ResourceId "worldlinco-section-rail-voip-button" -DumpPath (Join-Path $RunDir "callee_voip_rail.xml")
    Start-Sleep -Seconds 2
    for ($scroll = 0; $scroll -lt 6; $scroll++) {
        Invoke-Adb $Device @("shell", "input", "swipe", "540", "1600", "540", "500", "350") | Out-Null
        Start-Sleep -Milliseconds 800
    }
    for ($i = 0; $i -lt 12; $i++) {
        $dump = Join-Path $RunDir "accept_$i.xml"
        if (Tap-UiLabel -Device $Device -Labels @("받기", "수신 보이스톡 받기", "Accept") -DumpPath $dump) {
            return $true
        }
        if (Tap-ByResourceId -Device $Device -ResourceId "worldlinco-voip-incoming-accept" -DumpPath $dump) {
            return $true
        }
        Invoke-Adb $Device @("shell", "input", "swipe", "540", "1600", "540", "500", "350") | Out-Null
        Start-Sleep -Seconds 2
    }
    return $false
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
                Write-Step "Tap '$label' on $Device at ${cx},${cy}"
                Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
                return $true
            }
        }
    }
    return $false
}

function Open-VoipValidationAutoCall([string]$Device) {
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Open-VoipValidationMode([string]$Device) {
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Start-CallerFriendVoipCall {
    param([string]$Device)
    Write-Step "Starting validation auto-call deeplink on Tab..."
    Open-VoipValidationAutoCall $Device
    Start-Sleep -Seconds 6

    if (Wait-ForLogPattern $Device "VOIP_VALIDATION_AUTO_CALL_DEEPLINK|VOIP_FRIEND_CALL_SUCCESS|VOIP_START_CALL" 45) {
        return $true
    }

    Write-Step "Auto-call deeplink not confirmed — friend folder UI fallback"
    Open-VoipValidationMode $Device
    Start-Sleep -Seconds 3
    $dump = Join-Path $RunDir "caller_friend_folder_open.xml"
    foreach ($rid in @("worldlinco-voip-lobby-friend-folder-open", "worldlinco-chat-friend-folder-open")) {
        if (Tap-ByResourceId -Device $Device -ResourceId $rid -DumpPath $dump) { break }
    }
    Start-Sleep -Seconds 4
    Wait-ForLogPattern $Device "nado-000226|burumi69" 45 | Out-Null
    for ($i = 0; $i -lt 8; $i++) {
        Invoke-Adb $Device @("shell", "input", "swipe", "400", "1400", "400", "500", "350") | Out-Null
        Start-Sleep -Milliseconds 800
        if (Tap-UiLabel -Device $Device -Labels @("보이스톡 걸기, burumi69@gmail.com", "burumi69@gmail.com") -DumpPath (Join-Path $RunDir "caller_burumi_tap_$i.xml")) {
            return $true
        }
        if (Tap-ByResourceId -Device $Device -ResourceId "worldlinco-friend-voice-call-$CalleeVoiceId" -DumpPath (Join-Path $RunDir "caller_friend_call_tap_$i.xml")) {
            return $true
        }
    }
    return $false
}

function Wait-ForLogPattern {
    param([string]$Device, [string]$Pattern, [int]$TimeoutSec = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match $Pattern) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Step "Run dir: $RunDir"
Write-Step "Grant mic + launch apps"
Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CallerDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 5

Write-Step "Waiting auth..."
if (-not (Wait-ForAuthReady $CallerDevice)) { throw "Tab auth timeout" }
if (-not (Wait-ForAuthReady $CalleeDevice)) { throw "S10 auth timeout" }

Write-Step "Dismiss stale calls"
$null = Tap-UiLabel $CallerDevice @("통화 종료", "종료") (Join-Path $RunDir "tab_hangup.xml")
Start-Sleep -Seconds 2
$null = Tap-UiLabel $CalleeDevice @("통화 종료", "종료") (Join-Path $RunDir "s10_hangup.xml")
Start-Sleep -Seconds 2

Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null

Write-Step "Tab placing call to $CalleeVoiceId"
if (-not (Start-CallerFriendVoipCall $CallerDevice)) {
    throw "Tab did not start call"
}
if (-not (Wait-ForLogPattern $CallerDevice "VOIP_FRIEND_CALL_SUCCESS|VOIP_START_CALL|connectSignaling" 90)) {
    throw "Tab call initiation not confirmed in logcat"
}

Write-Step "Waiting incoming on S10..."
if (-not (Wait-ForLogPattern $CalleeDevice "VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_RING" 120)) {
    throw "S10 incoming timeout"
}

$accepted = Accept-IncomingVoipCall -Device $CalleeDevice
if (-not $accepted) { throw "Accept tap failed" }

Write-Step "Waiting connected..."
$tabConn = Wait-ForLogPattern $CallerDevice "Connection state: connected|State change callback: connected" 90
$s10Conn = Wait-ForLogPattern $CalleeDevice "Connection state: connected|State change callback: connected" 90
if (-not ($tabConn -and $s10Conn)) { throw "Connection timeout" }

Write-Step "Enable speaker on Tab (TTS playback)"
for ($v = 0; $v -lt 5; $v++) {
    Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
}
$null = Tap-UiLabel $CallerDevice @("스피커", "Speaker") (Join-Path $RunDir "tab_speaker.xml")
Start-Sleep -Seconds 3

Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null

Write-Step "=== READY: S10에서 한국어 6초 이상 말씀해 주세요. Tab은 영어 TTS 수신 예상 ==="
Write-Step "Monitoring ${MonitorSec}s..."
Start-Sleep -Seconds $MonitorSec

$tabLog = Get-LogcatText $CallerDevice
$s10Log = Get-LogcatText $CalleeDevice
$tabLog | Out-File (Join-Path $RunDir "tab.log") -Encoding utf8
$s10Log | Out-File (Join-Path $RunDir "s10.log") -Encoding utf8

$s10Seg = [bool]($s10Log -match "VOIP_VOICE_RELAY_SEGMENT_STARTED")
$s10Sent = [bool]($s10Log -match "VOIP_VOICE_RELAY_SENT")
$tabPlay = [bool]($tabLog -match "VOIP_VOICE_RELAY_PLAYBACK")
$tabSent = [bool]($tabLog -match "VOIP_VOICE_RELAY_SENT")
$s10Play = [bool]($s10Log -match "VOIP_VOICE_RELAY_PLAYBACK")

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    s10_segment_started = $s10Seg
    s10_relay_sent = $s10Sent
    tab_playback = $tabPlay
    tab_relay_sent = $tabSent
    s10_playback = $s10Play
    verdict = if ($s10Sent -and $tabPlay -and -not $tabSent) { "PASS" } else { "FAIL" }
}
$summary | ConvertTo-Json -Depth 4 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

Write-Step "S10 SEGMENT=$s10Seg S10 SENT=$s10Sent S10 PLAYBACK=$s10Play"
Write-Step "TAB PLAYBACK=$tabPlay TAB SENT=$tabSent"
Write-Step "Verdict: $($summary.verdict)"
Write-Step "Logs: $RunDir"
