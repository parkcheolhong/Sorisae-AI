#!/usr/bin/env pwsh
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$CalleeVoiceId = "nado-000001"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $RepoRoot "evidence\build89_bg_voip_$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content (Join-Path $RunDir "run.log") $line
}

function Invoke-Adb {
    param([string]$Device, [string[]]$AdbArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & adb -s $Device @AdbArgs 2>&1 | ForEach-Object { "$_" } }
    finally { $ErrorActionPreference = $prev }
}

function Get-LogcatText([string]$Device) {
    (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*", "MediaPlayer:*", "NuPlayer:*", "Ringtone:*", "Vibrator:*")) -join "`n"
}

Write-Step "Run dir: $RunDir"
Write-Step "Hangup + relaunch (preserve callee session: no force-stop on callee)"
Invoke-Adb $CallerDevice @("shell", "am", "force-stop", $PackageName) | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 12

$presenceOk = $false
for ($i = 0; $i -lt 20; $i++) {
    if ((Get-LogcatText $CalleeDevice) -match 'VOIP_PRESENCE_CONNECTED') { $presenceOk = $true; break }
    Start-Sleep -Seconds 3
}
Write-Step "callee_presence=$presenceOk"

Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_HOME") | Out-Null
Start-Sleep -Seconds 2

$runToken = Get-Date -Format "HHmmss"
Invoke-Adb $CallerDevice @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", "worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId&force=1&run=$runToken") | Out-Null
Write-Step "Tab auto-call deeplink sent"
Start-Sleep -Seconds 40

$calleeLog = Get-LogcatText $CalleeDevice
$callerLog = (Invoke-Adb $CallerDevice @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
$calleeLog | Out-File (Join-Path $RunDir "callee.log") -Encoding utf8
$callerLog | Out-File (Join-Path $RunDir "caller.log") -Encoding utf8

$summary = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    callee_presence = $presenceOk
    alert_started = [bool]($calleeLog -match 'VOIP_INCOMING_ALERT_STARTED|VOIP_INCOMING_ALERT_REASSERT')
    pending_or_fcm = [bool]($calleeLog -match 'VOIP_PENDING_CALL|incoming_call|fcm_')
    ring_evidence = [bool]($calleeLog -match 'NuPlayer|Ringtone|incoming_voip_alert')
    noti_disabled = [bool]($calleeLog -match 'VOIP_NOTIFICATION_PERMISSION_DISABLED|notifications_enabled.:false')
    caller_call_started = [bool]($callerLog -match 'call-|VOIP_FRIEND_CALL_SUCCESS')
}
$summary | ConvertTo-Json | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8
Write-Step "alert=$($summary.alert_started) pending=$($summary.pending_or_fcm) ring=$($summary.ring_evidence) caller=$($summary.caller_call_started)"
Write-Step "Open S10 notification settings"
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-a", "android.settings.APP_NOTIFICATION_SETTINGS", "-e", "android.provider.extra.APP_PACKAGE", $PackageName) | Out-Null
