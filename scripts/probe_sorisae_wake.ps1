param(
    [string]$DeviceId = "",
    [int]$CaptureSeconds = 20,
    [string]$OutputDir = "artifacts/sorisae-probe"
)

$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) {
    Write-Host "[SORISAE-PROBE] $msg"
}

function Get-AdbDevices {
    $raw = adb devices 2>$null
    if (-not $raw) { return @() }
    return ($raw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -match "\tdevice$" } | ForEach-Object { ($_ -split "\t")[0] })
}

$devices = Get-AdbDevices
if ($devices.Count -eq 0) {
    throw "ADB device not found. Connect a phone and ensure 'adb devices' shows at least one device."
}

$selected = $DeviceId
if ([string]::IsNullOrWhiteSpace($selected)) {
    if ($devices.Count -eq 1) {
        $selected = $devices[0]
    } else {
        throw "Multiple devices found: $($devices -join ', '). Pass -DeviceId explicitly."
    }
}

if (-not ($devices -contains $selected)) {
    throw "Device '$selected' is not online. Online devices: $($devices -join ', ')"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$probeDir = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $probeDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$safeDeviceName = ($selected -replace '[^a-zA-Z0-9._-]', '_')
$logFile = Join-Path $probeDir "wake-probe-$safeDeviceName-$ts.log"

Write-Info "device=$selected"
Write-Info "log_file=$logFile"
Write-Info "step1: clearing old logs"
adb -s $selected logcat -c | Out-Null

Write-Info "step2: capturing ReactNativeJS logs for $CaptureSeconds sec"
Write-Info "now say wake phrase several times: '소리새야'"

$adbArgs = @("-s", $selected, "logcat", "ReactNativeJS:I", "*:S")
$proc = Start-Process -FilePath "adb" -ArgumentList $adbArgs -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err" -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds $CaptureSeconds
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}

if (-not (Test-Path $logFile)) {
    throw "Log capture failed: $logFile"
}

$logText = Get-Content -Raw -Path $logFile
$wakeHit = $logText -match '\[COMPANION_VOICE_CALL\].*"event":"wake"'
$recoverHit = $logText -match '\[COMPANION_VOICE_CALL\].*"event":"dormant_watchdog_recover"'
$lowTrustHit = $logText -match '\[FACE_CONVERSATION\].*"event":"segment_skip_low_trust"'

Write-Info "result_summary"
Write-Info "wake_event=$wakeHit"
Write-Info "watchdog_recover_event=$recoverHit"
Write-Info "segment_skip_low_trust=$lowTrustHit"

if ($wakeHit) {
    Write-Host "PASS: wake event detected."
    exit 0
}

Write-Host "FAIL: wake event not detected."
Write-Host "CHECK: $logFile"
if ($recoverHit) {
    Write-Host "HINT: dormant watchdog is active, but wake phrase did not match transcript."
}
if ($lowTrustHit) {
    Write-Host "HINT: STT low-trust segments were observed during probe window."
}
exit 2
