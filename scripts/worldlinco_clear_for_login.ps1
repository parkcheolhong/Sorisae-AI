#!/usr/bin/env pwsh
# End stale VoIP UI so login/email keyboard is reachable (field testers).
param(
    [string]$Device = "",
    [string]$PackageName = "com.parkcheolhong.worldlinco"
)

$ErrorActionPreference = "Stop"

function Invoke-Adb([string]$Dev, [string[]]$Args) {
    & adb -s $Dev @Args 2>&1 | ForEach-Object { "$_" }
}

function Get-Devices {
    $lines = & adb devices | Select-Object -Skip 1
    $out = @()
    foreach ($line in $lines) {
        if ($line -match '^(\S+)\s+device\s*$') { $out += $matches[1] }
    }
    return $out
}

function Clear-DeviceForLogin([string]$Dev) {
    Write-Host "[clear] $Dev — force-stop + hangup taps + cold start"
    Invoke-Adb $Dev @("shell", "am", "force-stop", $PackageName) | Out-Null
    Start-Sleep -Seconds 2
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_HOME") | Out-Null
    Start-Sleep -Seconds 1
    Invoke-Adb $Dev @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 5
    $remote = "/sdcard/wl_clear_login.xml"
    Invoke-Adb $Dev @("shell", "uiautomator", "dump", $remote) | Out-Null
    $xml = (Invoke-Adb $Dev @("shell", "cat", $remote)) -join "`n"
    $hasLogin = $xml -match 'worldlinco-auth-email-input|상단 빠른 로그인|worldlinco-inline-auth-panel'
    $hasIncoming = $xml -match '수신 보이스톡|worldlinco-voip-incoming|받기'
    $hasActiveCall = $xml -match 'worldlinco-voip-hangup|통화 종료|End call'
    Write-Host "  login_panel=$hasLogin incoming_card=$hasIncoming active_call=$hasActiveCall"
    if ($hasIncoming -or $hasActiveCall) {
        Write-Host "  tip: VoIP 레일에서 [거절] 또는 [통화 종료] 후 채팅/홈으로 스크롤 → 상단 빠른 로그인"
    }
}

$targets = if ($Device) { @($Device) } else { Get-Devices }
if (-not $targets.Count) { throw "No adb devices in 'device' state" }
foreach ($dev in $targets) { Clear-DeviceForLogin -Dev $dev }
Write-Host "Done. Open app → scroll top → '상단 빠른 로그인' email/password fields."
