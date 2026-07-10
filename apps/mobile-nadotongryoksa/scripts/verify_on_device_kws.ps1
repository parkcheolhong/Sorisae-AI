param(
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$MainActivity = "com.parkcheolhong.worldlinco.MainActivity",
    [int]$DurationSec = 120,
    [switch]$LaunchApp
)

$ErrorActionPreference = "Stop"

Write-Host "[KWS-VERIFY] Checking adb availability..."
$adbVersion = & adb version
if (-not $adbVersion) {
    throw "adb is not available. Please install Android platform-tools."
}

$deviceLines = (& adb devices) -split "`n" | Where-Object { $_ -match "\tdevice$" }
if (-not $deviceLines -or $deviceLines.Count -eq 0) {
    throw "No online Android device found. Connect a device and enable USB debugging."
}

Write-Host "[KWS-VERIFY] Online devices:"
$deviceLines | ForEach-Object { Write-Host "  $_" }

if ($LaunchApp.IsPresent) {
    Write-Host "[KWS-VERIFY] Launching app..."
    & adb shell am start -n "$PackageName/$MainActivity" | Out-Null
}

Write-Host "[KWS-VERIFY] Clearing old logs..."
& adb logcat -c

Write-Host "[KWS-VERIFY] Capturing logs for $DurationSec seconds"
Write-Host "[KWS-VERIFY] Watch for: native_started, native_wake, native_error, scan_idle"

$deadline = (Get-Date).AddSeconds($DurationSec)

$process = Start-Process -FilePath "adb" -ArgumentList "logcat", "-v", "time", "ReactNativeJS:V", "OnDeviceKws:V", "*:S" -NoNewWindow -RedirectStandardOutput "$env:TEMP\kws_verify_log.txt" -PassThru
try {
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 300
        if ($process.HasExited) {
            break
        }
    }
}
finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}

$logPath = Join-Path $env:TEMP "kws_verify_log.txt"
if (-not (Test-Path $logPath)) {
    throw "Failed to capture logcat output."
}

$interesting = Select-String -Path $logPath -Pattern "COMPANION_KWS|COMPANION_VOICE_CALL|OnDeviceKwsEvent|native_started|native_wake|native_error|scan_idle"

Write-Host "[KWS-VERIFY] ---- filtered output ----"
if ($interesting) {
    $interesting | ForEach-Object { Write-Host $_.Line }
}
else {
    Write-Host "[KWS-VERIFY] No KWS markers found."
}

Write-Host "[KWS-VERIFY] Raw log saved: $logPath"
Write-Host "[KWS-VERIFY] PASS condition example: native_started -> native_wake sequence appears."
