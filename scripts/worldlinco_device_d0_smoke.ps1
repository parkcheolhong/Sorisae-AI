#!/usr/bin/env pwsh
# D-0 device smoke: network diagnostics + friend folder hub + optional VoIP initiate audit
param(
    [string]$PrimaryDevice = "R83W70QY11H",
    [string]$SecondaryDevice = "172.30.1.19:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$ApiBaseUrl = "https://metanova1004.com",
    [string]$AuthEmail = "119cash@naver.com",
    [string]$AuthPasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [switch]$SkipVoipCall,
    [int]$MonitorSec = 35
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
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
    $oldEap = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & adb -s $Device @AdbArgs 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" }
        }
    }
    finally {
        $ErrorActionPreference = $oldEap
    }
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
}

function Write-DeviceText([string]$Device, [string[]]$AdbArgs, [string]$OutPath) {
    (Invoke-Adb $Device $AdbArgs) | Set-Content -Path $OutPath -Encoding UTF8
}

function Get-AuthStateSnapshot {
    param(
        [string]$Device,
        [string]$LogText
    )

    $restoreFound = $LogText -match 'AUTH_STORAGE_RESTORE_FOUND'
    $restoreApplied = $LogText -match 'AUTH_STORAGE_RESTORE_APPLIED'
    $restoreInvalid = $LogText -match 'restore invalid, clearing stored auth'
    $tokenReady = $LogText -match '"token_ready":true'
    $userReady = $LogText -match '"user_ready":true'
    $presenceConnected = $LogText -match 'VOIP_PRESENCE_CONNECTED'
    $pendingCallPollOk = $LogText -match '"source":"pending_call_poll".*"status":200,"ok":true'
    $loginInvalid = $LogText -match '이메일 또는 비밀번호가 올바르지 않습니다'
    $sessionPresent = ($LogText -match 'token_summary":"len:' -and $LogText -match '"user_id":\d+') -or ($LogText -match 'AUTH_STORAGE_RESTORE_FOUND' -and $LogText -match '"user_id":\d+')
    $uiProbeSeen = $LogText -match 'UI_PRESS_PROBE|AUTH_FLOW|NETWORK_TRANSPORT_CHANGED|VOIP_PENDING|VoIPPendingIncoming'
    $reactLogSilent = [string]::IsNullOrWhiteSpace($LogText)
    # Treat a live pending-call poll with token/user context as an authenticated session
    # even when restore markers are absent on warm launches.
    $authReady = ($tokenReady -and $userReady) -or $presenceConnected -or ($restoreApplied -and -not $restoreInvalid) -or ($sessionPresent -and $pendingCallPollOk)
    $blocker = $null

    if (-not $authReady) {
        if ($reactLogSilent) {
            $blocker = 'react_log_silent'
        }
        elseif ($restoreInvalid) {
            $blocker = 'restore_invalid'
        }
        elseif ($loginInvalid) {
            $blocker = 'login_invalid'
        }
        elseif ($sessionPresent -and -not $uiProbeSeen) {
            $blocker = 'session_present_probe_missing'
        }
        elseif ($sessionPresent) {
            $blocker = 'session_present_auth_probe_incomplete'
        }
        elseif ($restoreFound -and -not $restoreApplied) {
            $blocker = 'restore_not_applied'
        }
        else {
            $blocker = 'auth_not_ready'
        }
    }

    return [pscustomobject]@{
        device             = $Device
        auth_ready         = $authReady
        blocker            = $blocker
        restore_found      = $restoreFound
        restore_applied    = $restoreApplied
        restore_invalid    = $restoreInvalid
        token_ready        = $tokenReady
        user_ready         = $userReady
        presence_connected = $presenceConnected
        login_invalid      = $loginInvalid
        session_present    = $sessionPresent
        ui_probe_seen      = $uiProbeSeen
        react_log_silent   = $reactLogSilent
    }
}

function Capture-AuthFailureEvidence {
    param(
        [string]$Device,
        [string]$Prefix
    )

    $safePrefix = $Prefix -replace '[:\\/]','_'
    Get-UiDump -Device $Device -OutPath (Join-Path $RunDir "auth_failure_${safePrefix}_ui.xml") | Out-Null
    Write-DeviceText -Device $Device -AdbArgs @("shell", "dumpsys", "window", "windows") -OutPath (Join-Path $RunDir "auth_failure_${safePrefix}_window.txt")
    Write-DeviceText -Device $Device -AdbArgs @("shell", "dumpsys", "activity", "top") -OutPath (Join-Path $RunDir "auth_failure_${safePrefix}_activity_top.txt")
    Write-DeviceText -Device $Device -AdbArgs @("shell", "pidof", $PackageName) -OutPath (Join-Path $RunDir "auth_failure_${safePrefix}_pid.txt")
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump_d0.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
}

function Get-AuthPassword {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if ($password) { return $password.Trim() }
    $passwordPath = Join-Path $RepoRoot $AuthPasswordFile
    if (Test-Path $passwordPath) {
        return (Get-Content -Raw $passwordPath).Trim()
    }
    return $null
}

function Test-AuthApiCredential {
    $password = Get-AuthPassword
    if (-not $password) {
        return [pscustomobject]@{ ok = $false; blocker = 'credential_missing' }
    }
    try {
        $loginBody = "username=$([uri]::EscapeDataString($AuthEmail))&password=$([uri]::EscapeDataString($password))"
        $login = Invoke-RestMethod -Method POST -Uri "$ApiBaseUrl/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body $loginBody
        if ($login.access_token) {
            return [pscustomobject]@{ ok = $true; blocker = $null }
        }
        return [pscustomobject]@{ ok = $false; blocker = 'login_api_token_missing' }
    }
    catch {
        if ($_.Exception.Message -match '401') {
            return [pscustomobject]@{ ok = $false; blocker = 'login_api_unauthorized' }
        }
        return [pscustomobject]@{ ok = $false; blocker = 'login_api_error' }
    }
}

function Get-ConnectedDevices {
    return @((& adb devices) | Select-String "device$" | ForEach-Object {
            (($_.ToString() -split "\s+")[0]).Trim()
        })
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

function Set-FieldText {
    param(
        [string]$Device,
        [string]$ResourceId,
        [string]$Value,
        [string]$DumpPath
    )

    if (-not (Tap-ByResourceId -Device $Device -ResourceId $ResourceId -DumpPath $DumpPath)) {
        return $false
    }
    Start-Sleep -Milliseconds 400
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_MOVE_END") | Out-Null
    foreach ($i in 1..80) {
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_DEL") | Out-Null
    }
    $escaped = ($Value -replace ' ', '%s')
    Invoke-Adb $Device @("shell", "input", "text", $escaped) | Out-Null
    return $true
}

function Try-UiLogin {
    param([string]$Device)

    $password = Get-AuthPassword
    if (-not $password) { return $false }

    $dumpPath = Join-Path $RunDir "auth_login_$($Device -replace '[:\\/]','_').xml"
    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Test-Path $dumpPath)) { return $false }
    $xml = Get-Content -Raw $dumpPath

    if ($xml -match 'worldlinco-inline-open-login-button') {
        if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-inline-open-login-button' -DumpPath $dumpPath) {
            Start-Sleep -Seconds 2
            Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
            $xml = Get-Content -Raw $dumpPath
        }
    }

    if ($xml -notmatch 'worldlinco-auth-email-input' -or $xml -notmatch 'worldlinco-auth-password-input') {
        return $false
    }

    if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-email-input' -Value $AuthEmail -DumpPath $dumpPath)) {
        return $false
    }
    Start-Sleep -Milliseconds 400
    if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-password-input' -Value $password -DumpPath $dumpPath)) {
        return $false
    }
    Start-Sleep -Milliseconds 400
    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-auth-login-submit-button' -DumpPath $dumpPath)) {
        return $false
    }
    Write-Step "UI login submit attempted on $Device"
    Start-Sleep -Seconds 4
    return $true
}

function Wait-AuthReady([string]$Device, [int]$TimeoutSec = 180) {
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 8
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $loginAttempted = $false
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        $state = Get-AuthStateSnapshot -Device $Device -LogText $text
        if ($state.auth_ready) { return $true }
        if ($state.restore_invalid -or $state.login_invalid) { return $false }
        if (-not $loginAttempted) {
            $loginAttempted = Try-UiLogin -Device $Device
        }
        Start-Sleep -Seconds 4
    }
    return $false
}

Write-Step "D-0 device smoke -> $RunDir"
Write-Step "Devices: primary=$PrimaryDevice secondary=$SecondaryDevice"

$connectedDevices = Get-ConnectedDevices
Write-Step "adb devices:`n$($connectedDevices -join "`n")"

$missingDevices = @($PrimaryDevice, $SecondaryDevice) | Where-Object { $_ -notin $connectedDevices }
if ($missingDevices.Count -gt 0) {
    $summary = [pscustomobject]@{
        timestamp          = (Get-Date).ToUniversalTime().ToString("o")
        run_dir            = $RunDir
        primary_device     = $PrimaryDevice
        secondary_device   = $SecondaryDevice
        auth_ready         = $false
        primary_auth       = [pscustomobject]@{ device = $PrimaryDevice; auth_ready = $false; blocker = if ($PrimaryDevice -in $missingDevices) { 'device_missing' } else { $null } }
        secondary_auth     = [pscustomobject]@{ device = $SecondaryDevice; auth_ready = $false; blocker = if ($SecondaryDevice -in $missingDevices) { 'device_missing' } else { $null } }
        friend_hub_visible = $false
        network_probe_hits = @()
        voip               = $null
        blocker            = "missing_device:$($missingDevices -join ',')"
    }
    $summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $RunDir "summary.json") -Encoding UTF8
    Write-Step "Missing required adb device(s): $($missingDevices -join ', ')"
    Write-Step "Summary written: $(Join-Path $RunDir 'summary.json')"
    $summary | ConvertTo-Json -Depth 6
    exit 1
}

foreach ($dev in @($PrimaryDevice, $SecondaryDevice)) {
    $version = Invoke-Adb $dev @("shell", "dumpsys", "package", $PackageName) | Select-String "versionCode="
    Write-Step "$dev package: $($version -join ', ')"
}

Invoke-Adb $PrimaryDevice @("logcat", "-c") | Out-Null
Invoke-Adb $SecondaryDevice @("logcat", "-c") | Out-Null

Write-Step "Launch + auth wait on $PrimaryDevice"
$authOk = Wait-AuthReady -Device $PrimaryDevice
Write-Step "Primary auth ready: $authOk"

$primaryAuthLog = Get-LogcatText $PrimaryDevice
$primaryAuthState = Get-AuthStateSnapshot -Device $PrimaryDevice -LogText $primaryAuthLog
$secondaryAuthLog = Get-LogcatText $SecondaryDevice
$secondaryAuthState = Get-AuthStateSnapshot -Device $SecondaryDevice -LogText $secondaryAuthLog
$authApiCredential = Test-AuthApiCredential

if (-not $secondaryAuthState.auth_ready -and -not $secondaryAuthState.session_present -and -not $secondaryAuthState.restore_found -and -not $authApiCredential.ok) {
    $secondaryAuthState.blocker = $authApiCredential.blocker
}

$primaryAuthLog | Set-Content -Path (Join-Path $RunDir "primary_auth_logcat.txt") -Encoding UTF8
$secondaryAuthLog | Set-Content -Path (Join-Path $RunDir "secondary_auth_logcat.txt") -Encoding UTF8
$primaryAuthState | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $RunDir "primary_auth_state.json") -Encoding UTF8
$secondaryAuthState | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $RunDir "secondary_auth_state.json") -Encoding UTF8

if (-not $primaryAuthState.auth_ready) {
    Capture-AuthFailureEvidence -Device $PrimaryDevice -Prefix "primary"
}
if (-not $secondaryAuthState.auth_ready) {
    Capture-AuthFailureEvidence -Device $SecondaryDevice -Prefix "secondary"
}

Write-Step "Primary auth state: ready=$($primaryAuthState.auth_ready) blocker=$($primaryAuthState.blocker) restore_applied=$($primaryAuthState.restore_applied) restore_invalid=$($primaryAuthState.restore_invalid) token_ready=$($primaryAuthState.token_ready) user_ready=$($primaryAuthState.user_ready) presence_connected=$($primaryAuthState.presence_connected) session_present=$($primaryAuthState.session_present) ui_probe_seen=$($primaryAuthState.ui_probe_seen) react_log_silent=$($primaryAuthState.react_log_silent)"
Write-Step "Secondary auth state: ready=$($secondaryAuthState.auth_ready) blocker=$($secondaryAuthState.blocker) restore_applied=$($secondaryAuthState.restore_applied) restore_invalid=$($secondaryAuthState.restore_invalid) token_ready=$($secondaryAuthState.token_ready) user_ready=$($secondaryAuthState.user_ready) presence_connected=$($secondaryAuthState.presence_connected) session_present=$($secondaryAuthState.session_present) ui_probe_seen=$($secondaryAuthState.ui_probe_seen) react_log_silent=$($secondaryAuthState.react_log_silent)"

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

$friendHubBlocker = $null
if (-not $opened) {
    if ($primaryLog -match 'VOIP_VALIDATION_DEEPLINK_AUTH_REQUIRED') {
        $friendHubBlocker = 'auth_required'
    }
    elseif ($primaryLog -match 'APP_ENTRY_DEEP_LINK_VOIP_OPEN') {
        $friendHubBlocker = 'deeplink_opened_without_friend_folder'
    }
    else {
        $friendHubBlocker = 'friend_folder_not_detected'
    }
}

if ($friendHubBlocker) {
    Write-Step "Friend hub blocker: $friendHubBlocker"
}

$networkHits = @(
    'VOIP_NETWORK_SNAPSHOT',
    'NETWORK_TRANSPORT_CHANGED',
    'FRIEND_FOLDER_DIAG',
    'VOIP_VALIDATION_DEEPLINK_AUTH_REQUIRED',
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
}
catch {
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
            $loginUsername = "119cash@naver.com"
            $loginPassword = (Get-Content (Join-Path $RepoRoot ".runtime\secrets\fixed_admin_password.txt") -Raw).Trim()
            $loginBody = "username=$([uri]::EscapeDataString($loginUsername))&password=$([uri]::EscapeDataString($loginPassword))"
            $login = Invoke-RestMethod -Method POST -Uri "$ApiBaseUrl/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body $loginBody
            if (-not $login.access_token) {
                throw "login token missing"
            }
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
        }
        catch {
            Write-Step "WARN: audit/client_network fetch failed: $($_.Exception.Message)"
        }
    }

    $voipResult = [pscustomobject]@{
        call_id        = $callId
        connected      = [bool]($combined -match 'Connection state: connected|VOIP_CALL_CONNECTED|VOIP_CONNECTION_STATE_CONNECTED')
        client_network = $clientNetwork
    }
}

$summary = [pscustomobject]@{
    timestamp          = (Get-Date).ToUniversalTime().ToString("o")
    run_dir            = $RunDir
    primary_device     = $PrimaryDevice
    secondary_device   = $SecondaryDevice
    auth_ready         = $authOk
    primary_auth       = $primaryAuthState
    secondary_auth     = $secondaryAuthState
    auth_api_credential = $authApiCredential
    friend_hub_visible = $opened
    friend_hub_blocker = $friendHubBlocker
    network_probe_hits = $networkHits
    voip               = $voipResult
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $RunDir "summary.json") -Encoding UTF8
Write-Step "Summary written: $(Join-Path $RunDir 'summary.json')"
$summary | ConvertTo-Json -Depth 6
