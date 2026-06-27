#!/usr/bin/env pwsh
# Recover Android soft keyboard / dialer after VoIP ADB test sessions.
param(
    [string]$Device = "",
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"
$HoneyBoard = "com.samsung.android.honeyboard/.service.HoneyBoardService"

function Invoke-Adb([string]$Dev, [string[]]$AdbArgs) {
    & adb -s $Dev @AdbArgs 2>&1 | ForEach-Object { "$_" }
}

function Get-Devices {
    $lines = & adb devices | Select-Object -Skip 1
    @($lines | ForEach-Object { if ($_ -match '^(\S+)\s+device\s*$') { $matches[1] } })
}

function Repair-DeviceInput([string]$Dev) {
    Write-Host "=== Repair input/IME: $Dev ==="

    foreach ($pkg in @(
        "com.samsung.android.dialer",
        "com.samsung.android.incallui",
        "com.android.incallui",
        "com.skt.prod.dialer",
        "com.android.server.telecom",
        "io.appium.settings",
        "com.parkcheolhong.worldlinco"
    )) {
        Invoke-Adb $Dev @("shell", "am", "force-stop", $pkg) | Out-Null
    }

    Start-Sleep -Seconds 2
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
    Invoke-Adb $Dev @("shell", "input", "keyevent", "KEYCODE_HOME") | Out-Null

    Write-Host "[ime] Enable Samsung HoneyBoard default"
    Invoke-Adb $Dev @("shell", "ime", "enable", $HoneyBoard) | Out-Null
    Invoke-Adb $Dev @("shell", "ime", "set", $HoneyBoard) | Out-Null
    Invoke-Adb $Dev @("shell", "settings", "put", "secure", "default_input_method", $HoneyBoard) | Out-Null
    Invoke-Adb $Dev @("shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "1") | Out-Null

    $disableAppium = Invoke-Adb $Dev @("shell", "pm", "disable-user", "--user", "0", "io.appium.settings")
    if ($disableAppium -match "disabled|already") {
        Write-Host "[ime] Appium EmptyIME disabled (test leftover)"
    }

    $defaultIme = (Invoke-Adb $Dev @("shell", "settings", "get", "secure", "default_input_method")) -join ""
    Write-Host "[ime] default_input_method=$defaultIme"

    Invoke-Adb $Dev @("shell", "am", "start", "-n", "com.parkcheolhong.worldlinco/.MainActivity") | Out-Null
    Write-Host "[app] WorldLinco relaunched — scroll top → '상단 빠른 로그인' → tap email field"

    if ($Reboot) {
        Write-Host "[reboot] Device reboot in 3s..."
        Start-Sleep -Seconds 3
        Invoke-Adb $Dev @("reboot") | Out-Null
    }
}

$targets = if ($Device) { @($Device) } else { Get-Devices }
if (-not $targets.Count) { throw "No adb device online" }
foreach ($dev in $targets) { Repair-DeviceInput -Dev $dev }
