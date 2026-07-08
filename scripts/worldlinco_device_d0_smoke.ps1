#!/usr/bin/env pwsh
# D-0 device smoke: network diagnostics + friend folder hub + optional VoIP initiate audit
param(
    [string]$PrimaryDevice = "R83W70QY11H",
    [string]$SecondaryDevice = "172.30.1.19:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$ApiBaseUrl = "https://metanova1004.com",
    [switch]$SkipVoipCall,
    [int]$MonitorSec = 35
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RepoRoot "evidence\device-d0-smoke-$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $RunDir "run.log") -Value $line
}

function Invoke-Adb([string]$Device, [string[]]$AdbArgs) {
    & adb -s $Device @AdbArgs 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" }
    }
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump_d0.xml"
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
    Write-Step "Tap $ResourceId at ${cx},${cy} on $Device"
    Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
    return $true
}

function Wait-AuthReady([string]$Device, [int]$TimeoutSec = 180) {
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 8
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        if ($text -match 'VOIP_PRESENCE_CONNECTED' -and $text -match '"user_id":\d+') { return $true }
        if ($text -match 'AUTH_STORAGE_RESTORE_FOUND' -and $text -match '"user_id":\d+') { return $true }
        Start-Sleep -Seconds 4
    }
    return $false
}

Write-Step "D-0 device smoke -> $RunDir"
Write-Step "Devices: primary=$PrimaryDevice secondary=$SecondaryDevice"

$devices = & adb devices | Select-String "device$"
Write-Step "adb devices:`n$($devices -join "`n")"

foreach ($dev in @($PrimaryDevice, $SecondaryDevice)) {
    $version = Invoke-Adb $dev @("shell", "dumpsys", "package", $PackageName) | Select-String "versionCode="
    Write-Step "$dev package: $($version -join ', ')"
}

Invoke-Adb $PrimaryDevice @("logcat", "-c") | Out-Null
Invoke-Adb $SecondaryDevice @("logcat", "-c") | Out-Null

Write-Step "Launch + auth wait on $PrimaryDevice"
$authOk = Wait-AuthReady -Device $PrimaryDevice
Write-Step "Primary auth ready: $authOk"

Write-Step "Open friend folder via validation deeplink (build 76 hub)"
Invoke-Adb $PrimaryDevice @("logcat", "-c") | Out-Null
$runToken = Get-Date -Format "HHmmss"
Invoke-Adb $PrimaryDevice @(
    "shell", "am", "start", "-W", "-a", "android.intent.action.VIEW",
    "-d", "worldlingo://voip/open?action=validation&callee_voice_id=nado-000001&force=1&run=$runToken"
) | Out-Null
Start-Sleep -Seconds 10

$dumpPath = Join-Path $RunDir "friend_folder_open.xml"
Get-UiDump -Device $PrimaryDevice -OutPath $dumpPath | Out-Null
$opened = $false
if (Test-Path $dumpPath) {
    $xml = Get-Content -Raw $dumpPath
    $opened = $xml -match 'friend-add-mode-contacts|friend-pick-contact|친구 추가|연락처에서'
}
Write-Step "Friend hub visible in UI dump: $opened"

$primaryLog = Get-LogcatText $PrimaryDevice
$primaryLog | Set-Content -Path (Join-Path $RunDir "primary_logcat.txt") -Encoding UTF8

$networkHits = @(
    'VOIP_NETWORK_SNAPSHOT',
    'NETWORK_TRANSPORT_CHANGED',
    'FRIEND_FOLDER_DIAG',
    'friend-add-mode-contacts',
    'friend-pick-contact'
) | ForEach-Object {
    [pscustomobject]@{ pattern = $_; count = ([regex]::Matches($primaryLog, $_)).Count }
}

$connectivity = Invoke-Adb $PrimaryDevice @("shell", "dumpsys", "connectivity")
$connectivity | Set-Content -Path (Join-Path $RunDir "primary_connectivity.txt") -Encoding UTF8

try {
    $health = Invoke-RestMethod -Method GET -Uri "$ApiBaseUrl/api/v1/voip/health" -TimeoutSec 20
    $health | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $RunDir "voip_health.json") -Encoding UTF8
} catch {
    Write-Step "WARN: voip health fetch failed: $($_.Exception.Message)"
}

$voipResult = $null
if (-not $SkipVoipCall) {
    Write-Step "VoIP validation auto-call (wifi smoke)"
    $setupScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"
    & pwsh -NoProfile -File $setupScript `
        -CallerDevice $PrimaryDevice `
        -CalleeDevice $SecondaryDevice `
        -MonitorSec $MonitorSec 2>&1 | Tee-Object -FilePath (Join-Path $RunDir "voip_setup.log")
    $callerLog = Get-LogcatText $PrimaryDevice
    $calleeLog = Get-LogcatText $SecondaryDevice
    $callerLog | Set-Content -Path (Join-Path $RunDir "caller_post_voip_logcat.txt") -Encoding UTF8
    $calleeLog | Set-Content -Path (Join-Path $RunDir "callee_post_voip_logcat.txt") -Encoding UTF8

    $combined = "$callerLog`n$calleeLog"
    $callId = $null
    if ($combined -match 'VOIP_FRIEND_CALL_SUCCESS.*?"call_id":"(call-[a-f0-9]+)"') { $callId = $matches[1] }
    elseif ($combined -match '"call_id":"(call-[a-f0-9]+)"') { $callId = $matches[1] }

    $clientNetwork = $null
    if ($callId -and (Test-Path (Join-Path $RepoRoot ".runtime\secrets\fixed_admin_password.txt"))) {
        try {
            $tokenScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"
            # reuse login inside lte script path
            $loginBody = @{
                email = "119cash@naver.com"
                password = (Get-Content (Join-Path $RepoRoot ".runtime\secrets\fixed_admin_password.txt") -Raw).Trim()
            } | ConvertTo-Json
            $login = Invoke-RestMethod -Method POST -Uri "$ApiBaseUrl/api/auth/login" -ContentType "application/json" -Body $loginBody
            $jwt = $login.access_token
            $headers = @{ Authorization = "Bearer $jwt" }
            $audit = Invoke-RestMethod -Method GET -Uri "$ApiBaseUrl/api/v1/voip/calls/$callId/audit" -Headers $headers
            $initiated = @($audit) | Where-Object { $_.event_type -eq "call_initiated" } | Select-Object -First 1
            $clientNetwork = $initiated.metadata.client_network
            if ($callId) {
                & pwsh -NoProfile -File (Join-Path $RepoRoot "scripts\worldlinco_lte_matrix_verify.ps1") `
                    -BaseUrl $ApiBaseUrl `
                    -Token $jwt `
                    -CallId $callId `
                    -MatrixScenario "wifi_wifi" `
                    -DeviceRole "caller" `
                    -Notes "device_d0_smoke $Stamp" 2>&1 | Out-Null
            }
        } catch {
            Write-Step "WARN: audit/client_network fetch failed: $($_.Exception.Message)"
        }
    }

    $voipResult = [pscustomobject]@{
        call_id = $callId
        connected = [bool]($combined -match 'Connection state: connected|VOIP_CALL_CONNECTED|VOIP_CONNECTION_STATE_CONNECTED')
        client_network = $clientNetwork
    }
}

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    run_dir = $RunDir
    primary_device = $PrimaryDevice
    secondary_device = $SecondaryDevice
  auth_ready = $authOk
  friend_hub_visible = $opened
    network_probe_hits = $networkHits
    voip = $voipResult
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $RunDir "summary.json") -Encoding UTF8
Write-Step "Summary written: $(Join-Path $RunDir 'summary.json')"
$summary | ConvertTo-Json -Depth 6
