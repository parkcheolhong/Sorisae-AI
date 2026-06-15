#!/usr/bin/env pwsh
# Tab(caller) -> S10(callee) VoIP call setup for manual voice relay test
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$CallerVoiceId = "nado-000226",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$ApiBaseUrl = "https://metanova1004.com",
    [string]$VoipApiEmail = "119cash@naver.com",
    [string]$VoipApiPasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [int]$MonitorSec = 45,
    [switch]$HangupOnly,
    [switch]$SetupOnly,
    [string]$SetPreferredLanguage = "",
    [string]$ProfileEmail = "",
    [string]$CallerPreferredLanguage = "",
    [string]$CalleePreferredLanguage = ""
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

function Wait-ForAuthReady([string]$Device, [int]$TimeoutSec = 240) {
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 6
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        if ($text -match 'AUTH_STORAGE_RESTORE_FOUND' -and $text -match '"user_id":\d+') {
            Start-Sleep -Seconds 10
            $text = Get-LogcatText $Device
            if ($text -match '"token_ready":true' -or $text -match 'VOIP_PRESENCE_CONNECTED|FRIEND_FOLDER_DIAG|VOIP_PENDING_CALL') {
                return $true
            }
        }
        if ($text -match 'VoIPPendingIncoming.*"token_summary":"len:\d+' -and $text -match '"user_id":\d+') { return $true }
        if ($text -match 'VOIP_PRESENCE_CONNECTED' -and $text -match '"user_id":\d+') { return $true }
        Start-Sleep -Seconds 4
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

function Get-VoipApiAccessToken {
    param(
        [string]$Email = $VoipApiEmail,
        [string]$PasswordFile = $VoipApiPasswordFile
    )
    try {
        $password = $env:WORLDLINCO_VOIP_API_PASSWORD
        if (-not $password) {
            $passwordFile = Join-Path $RepoRoot $PasswordFile
            if (-not (Test-Path $passwordFile)) {
                Write-Step "WARN: VoIP API password missing (set WORLDLINCO_VOIP_API_PASSWORD or $PasswordFile) — skip API auth"
                return $null
            }
            $password = (Get-Content -Raw $passwordFile).Trim()
        }
        if (-not $password) { return $null }

        $loginJson = & curl.exe -s --max-time 20 -X POST "$ApiBaseUrl/api/auth/login" `
            -H "Content-Type: application/x-www-form-urlencoded" `
            --data-urlencode "username=$Email" `
            --data-urlencode "password=$password"
        if (-not $loginJson -or $loginJson.TrimStart() -notmatch '^\{') {
            Write-Step "WARN: VoIP API login returned non-JSON — skip API auth"
            return $null
        }
        $login = $loginJson | ConvertFrom-Json
        if (-not $login.access_token) { return $null }
        return [string]$login.access_token
    } catch {
        Write-Step "WARN: VoIP API login failed — skip API auth ($($_.Exception.Message))"
        return $null
    }
}

function Set-UserPreferredLanguageViaApi {
    param(
        [string]$Language,
        [string]$Email = $VoipApiEmail,
        [string]$PasswordFile = $VoipApiPasswordFile
    )
    $token = Get-VoipApiAccessToken -Email $Email -PasswordFile $PasswordFile
    if (-not $token) { return $false }
    $body = (@{ preferred_language = $Language } | ConvertTo-Json -Compress)
    $patchJson = & curl.exe -s --max-time 20 -X PATCH "$ApiBaseUrl/api/auth/me" `
        -H "Authorization: Bearer $token" `
        -H "Content-Type: application/json" `
        -d $body
    if ($patchJson -and $patchJson -match '"preferred_language"\s*:\s*"([^"]+)"') {
        Write-Step "API profile preferred_language=$($matches[1]) for $Email"
        return ($matches[1].ToLower() -eq $Language.ToLower())
    }
    Write-Step "WARN: API profile update failed for $Email -> $Language ($patchJson)"
    return $false
}

function Get-LatestIncomingCallFromLog {
    param(
        [string]$LogText,
        [string]$ExpectedCallerVoiceId = $CallerVoiceId
    )
    $lines = $LogText -split "`n"
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $line = $lines[$i]
        if ($line -notmatch 'VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_CALL_RECEIVED|VOIP_INCOMING_CALL_APPLIED|VOIP_INCOMING_ACCEPT_API_OK') {
            continue
        }
        if ($line -notmatch '"call_id":"(call-[a-f0-9]+)"') { continue }
        $callId = $matches[1]
        $callerVid = $null
        if ($line -match '"caller_voice_id":"([^"]+)"') { $callerVid = $matches[1] }
        if ($ExpectedCallerVoiceId -and $callerVid -and ($callerVid -ne $ExpectedCallerVoiceId)) { continue }
        $sig = $null
        if ($line -match '"signaling_server":"([^"]+)"') {
            $sig = ($matches[1] -replace '\\/', '/')
        }
        if (-not $sig) {
            $sig = "wss://metanova1004.com/api/v1/voip/signal?call_id=$callId&role=callee"
        }
        return @{
            call_id = $callId
            signaling_server = $sig
            caller_voice_id = $callerVid
        }
    }
    return $null
}

function Open-IncomingVoipDeepLinkAutoAccept {
    param(
        [string]$Device,
        [string]$CallId,
        [string]$SignalingServer,
        [string]$DisplayLanguage = ""
    )
    $encSig = [uri]::EscapeDataString($SignalingServer)
    $encLang = if ($DisplayLanguage) { [uri]::EscapeDataString($DisplayLanguage) } else { "" }
    $langQuery = if ($encLang) { "&display_language=$encLang" } else { "" }
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    foreach ($scheme in @('worldlingo', 'worldlinco')) {
        $deeplink = "${scheme}://voip/incoming?call_id=$CallId&signaling_server=$encSig&participant_role=callee&status=ringing&call_route=app_webrtc$langQuery"
        Write-Step "Launch incoming deeplink ($scheme) on $Device call_id=$CallId"
        $cmd = "am start -W -a android.intent.action.VIEW -d '$deeplink'"
        Invoke-Adb $Device @("shell", $cmd) | Out-Null
        Start-Sleep -Seconds 4
        if (Wait-ForLogPattern $Device "VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT|VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED" 20) {
            return $true
        }
    }
    return $false
}

function Find-CallerCallIdFromLog {
    param([string]$Text)
    foreach ($pattern in @(
        'VOIP_FRIEND_CALL_SUCCESS.*?"call_id":"(call-[a-f0-9]+)"',
        'VOIP_INTENT_INITIATE_SUCCESS.*?"call_id":"(call-[a-f0-9]+)"',
        '"call_id":"(call-[a-f0-9]+)".*?"callee_voice_id":"' + [regex]::Escape($CalleeVoiceId) + '"'
    )) {
        $matches = [regex]::Matches($Text, $pattern)
        if ($matches.Count -gt 0) {
            return $matches[$matches.Count - 1].Groups[1].Value
        }
    }
    return $null
}

function Wait-ForCallerCallId {
    param([string]$Device, [int]$TimeoutSec = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        $callId = Find-CallerCallIdFromLog $text
        if ($callId) { return $callId }
        Start-Sleep -Seconds 2
    }
    return $null
}

function Wait-ForIncomingCallId {
    param(
        [string]$Device,
        [string]$ExpectedCallId,
        [string]$ExpectedCallerVoiceId = $CallerVoiceId,
        [int]$TimeoutSec = 120
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match "VOIP_INCOMING_CALL_RECEIVED.*?`"call_id`":`"$ExpectedCallId`"") {
            return $true
        }
        if ($text -match "VOIP_PENDING_CALL_FETCHED.*?`"call_id`":`"$ExpectedCallId`"") {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Accept-IncomingVoipCall {
    param(
        [string]$Device,
        [string]$ExpectedCallId,
        [string]$ExpectedCallerVoiceId = $CallerVoiceId
    )
    Write-Step "S10 accept — incoming deeplink auto-accept call_id=$ExpectedCallId caller=$ExpectedCallerVoiceId"
    $payload = Get-LatestIncomingCallFromLog -LogText (Get-LogcatText $Device) -ExpectedCallerVoiceId $ExpectedCallerVoiceId
    $signaling = if ($payload -and $payload.call_id -eq $ExpectedCallId) {
        $payload.signaling_server
    } else {
        "wss://metanova1004.com/api/v1/voip/signal?call_id=$ExpectedCallId&role=callee"
    }

    if (Open-IncomingVoipDeepLinkAutoAccept -Device $Device -CallId $ExpectedCallId -SignalingServer $signaling -DisplayLanguage $CallerPreferredLanguage) {
        return $true
    }

    Write-Step "Deeplink accept not confirmed — UI fallback"
    Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 2
    for ($i = 0; $i -lt 8; $i++) {
        $dump = Join-Path $RunDir "accept_fallback_$i.xml"
        if (Tap-ByResourceId -Device $Device -ResourceId "worldlinco-voip-incoming-accept" -DumpPath $dump) { break }
        if (Tap-UiLabel -Device $Device -Labels @("받기", "수신 보이스톡 받기", "Accept", "Answer") -DumpPath $dump) { break }
        Start-Sleep -Seconds 2
    }
    return (Wait-ForLogPattern $Device "VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED|Connection state: connected" 30)
}

function End-StaleVoipCallsViaApi {
    param([string]$Reason = "cleanup")
    $token = Get-VoipApiAccessToken
    if (-not $token) { return }

    $callIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

    try {
        $pendingJson = & curl.exe -s --max-time 15 -H "Authorization: Bearer $token" "$ApiBaseUrl/api/v1/voip/calls/pending-incoming"
        if ($pendingJson -and $pendingJson.TrimStart() -match '^\{' ) {
            $pending = $pendingJson | ConvertFrom-Json
            if ($pending.call_id) { [void]$callIds.Add([string]$pending.call_id) }
        }
        $activeJson = & curl.exe -s --max-time 15 -H "Authorization: Bearer $token" "$ApiBaseUrl/api/v1/voip/calls/active-current"
        if ($activeJson -and $activeJson.TrimStart() -match '^\{' ) {
            $active = $activeJson | ConvertFrom-Json
            if ($active.call_id) { [void]$callIds.Add([string]$active.call_id) }
        }
    } catch {
        Write-Step "WARN: VoIP API query failed: $($_.Exception.Message)"
    }

    foreach ($callId in $callIds) {
        Write-Step "API end stale call $callId ($Reason)"
        & curl.exe -s --max-time 15 -X POST "$ApiBaseUrl/api/v1/voip/calls/$callId/end" `
            -H "Authorization: Bearer $token" `
            -H "Content-Type: application/json" `
            -d '{"duration_sec":0,"call_quality":"script_cleanup"}' | Out-Null
    }
    Start-Sleep -Seconds 2
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

function Force-HangupVoipDevices {
    param([string]$Reason = "cleanup")
    Write-Step "Force hangup ($Reason) on Tab + S10"
    End-StaleVoipCallsViaApi -Reason $Reason
    if ($Reason -like 'pre_*' -or $Reason -like 'before_*') {
        foreach ($dev in @($CallerDevice, $CalleeDevice)) {
            Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
            Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
        }
        Start-Sleep -Seconds 2
        return
    }
    foreach ($dev in @($CallerDevice, $CalleeDevice)) {
        Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
        Start-Sleep -Milliseconds 500
        for ($pass = 0; $pass -lt 2; $pass++) {
            if ($pass -eq 0) {
                Invoke-Adb $dev @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
                Start-Sleep -Seconds 2
            }
            $dump = Join-Path $RunDir "hangup_${Reason}_$($dev -replace '[:\\\\/]','_')_$pass.xml"
            $null = Tap-UiLabel -Device $dev -Labels @(
                "거절", "Decline", "통화 종료", "종료", "끊기", "End call", "Hang up", "전화 끊기"
            ) -DumpPath $dump
            $null = Tap-ByResourceId -Device $dev -ResourceId "worldlinco-voip-hangup" -DumpPath $dump
            $null = Tap-ByResourceId -Device $dev -ResourceId "worldlinco-voip-end-call" -DumpPath $dump
            Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
            Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
            Start-Sleep -Seconds 2
        }
    }
    Start-Sleep -Seconds 4
}

function Open-VoipValidationAutoCall([string]$Device) {
    if ($CalleeVoiceId -eq $CallerVoiceId) {
        throw "CalleeVoiceId must not equal CallerVoiceId (self-call): $CalleeVoiceId"
    }
    $runToken = Get-Date -Format "HHmmss"
    $calleeLangQuery = if ($CalleePreferredLanguage) { "&callee_preferred_language=$CalleePreferredLanguage" } else { "" }
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId&force=1&run=$runToken$calleeLangQuery'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Open-VoipValidationMode([string]$Device) {
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Set-DeviceVoipLanguageViaDeeplink {
    param([string]$Device, [string]$Language)
    if (-not $Language) { return }
    $runToken = Get-Date -Format "HHmmss"
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=open&preferred_language=$Language&force=1&run=$runToken'"
    Write-Step "Apply preferred_language=$Language via deeplink on $Device"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
    Start-Sleep -Seconds 4
    $text = Get-LogcatText $Device
    if ($text -notmatch 'VOIP_DEEPLINK_PREFERRED_LANGUAGE_APPLIED') {
        Write-Step "WARN: deeplink language apply not confirmed on $Device (build 69+ required)"
    }
}

function Start-CallerFriendVoipCall {
    param([string]$Device)
    Write-Step "Starting validation auto-call deeplink on Tab..."
    Open-VoipValidationAutoCall $Device
    Start-Sleep -Seconds 6

    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        $callId = Find-CallerCallIdFromLog (Get-LogcatText $Device)
        if ($callId) {
            Write-Step "Tab call started call_id=$callId (deeplink auto-call)"
            return $true
        }
        if ((Get-LogcatText $Device) -match 'VOIP_VALIDATION_AUTO_CALL_DEEPLINK|VOIP_FRIEND_SELECTED|VOIP_FRIEND_CALL_SUCCESS') {
            break
        }
        Start-Sleep -Seconds 2
    }

    Write-Step "Auto-call deeplink not confirmed — friend folder UI fallback"
    Open-VoipValidationMode $Device
    Start-Sleep -Seconds 3
    $dump = Join-Path $RunDir "caller_friend_folder_open.xml"
    foreach ($rid in @("worldlinco-voip-lobby-friend-folder-open", "worldlinco-chat-friend-folder-open")) {
        if (Tap-ByResourceId -Device $Device -ResourceId $rid -DumpPath $dump) { break }
    }
    Start-Sleep -Seconds 4
    Wait-ForLogPattern $Device "nado-000001|119cash@naver.com|$CalleeVoiceId" 45 | Out-Null
    for ($i = 0; $i -lt 8; $i++) {
        Invoke-Adb $Device @("shell", "input", "swipe", "400", "1400", "400", "500", "350") | Out-Null
        Start-Sleep -Milliseconds 800
        if (Tap-ByResourceId -Device $Device -ResourceId "worldlinco-friend-voice-call-$CalleeVoiceId" -DumpPath (Join-Path $RunDir "caller_friend_call_tap_$i.xml")) {
            $waitDeadline = (Get-Date).AddSeconds(20)
            while ((Get-Date) -lt $waitDeadline) {
                if (Find-CallerCallIdFromLog (Get-LogcatText $Device)) { return $true }
                Start-Sleep -Seconds 2
            }
        }
        if (Tap-UiLabel -Device $Device -Labels @("보이스톡 걸기, 119cash@naver.com", "119cash@naver.com") -DumpPath (Join-Path $RunDir "caller_s10_tap_$i.xml")) {
            $waitDeadline = (Get-Date).AddSeconds(20)
            while ((Get-Date) -lt $waitDeadline) {
                if (Find-CallerCallIdFromLog (Get-LogcatText $Device)) { return $true }
                Start-Sleep -Seconds 2
            }
        }
    }
    return [bool](Find-CallerCallIdFromLog (Get-LogcatText $Device))
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
if ($SetPreferredLanguage) {
    $email = if ($ProfileEmail) { $ProfileEmail } else { $VoipApiEmail }
    $ok = Set-UserPreferredLanguageViaApi -Language $SetPreferredLanguage -Email $email
    if (-not $ok) { exit 1 }
    exit 0
}
if ($HangupOnly) {
    Force-HangupVoipDevices -Reason "hangup_only"
    exit 0
}
Write-Step "Grant mic + force-stop apps (reset deeplink consume)"
foreach ($dev in @($CallerDevice, $CalleeDevice)) {
    Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $dev @("shell", "am", "force-stop", $PackageName) | Out-Null
}
Start-Sleep -Seconds 2
Invoke-Adb $CallerDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 8

Write-Step "Waiting auth..."
if (-not (Wait-ForAuthReady $CallerDevice)) { throw "Tab auth timeout" }
if (-not (Wait-ForAuthReady $CalleeDevice)) { throw "S10 auth timeout" }

if ($CallerPreferredLanguage) {
    Set-DeviceVoipLanguageViaDeeplink -Device $CallerDevice -Language $CallerPreferredLanguage
}
if ($CalleePreferredLanguage) {
    Set-DeviceVoipLanguageViaDeeplink -Device $CalleeDevice -Language $CalleePreferredLanguage
}

Write-Step "Dismiss stale calls (force hangup)"
Force-HangupVoipDevices -Reason "pre_call"

Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null

Write-Step "Tab placing call to $CalleeVoiceId"
if (-not (Start-CallerFriendVoipCall $CallerDevice)) {
    throw "Tab did not start call"
}

$callerCallId = Wait-ForCallerCallId $CallerDevice 180
if (-not $callerCallId) {
    throw "Tab call_id not found in logcat"
}
Write-Step "Tab call_id=$callerCallId — waiting matching incoming on S10..."
if (-not (Wait-ForIncomingCallId -Device $CalleeDevice -ExpectedCallId $callerCallId)) {
    throw "S10 incoming timeout for $callerCallId"
}

$accepted = Accept-IncomingVoipCall -Device $CalleeDevice -ExpectedCallId $callerCallId
if (-not $accepted) {
    Write-Step "WARN: Accept tap not confirmed — checking connected anyway"
}

Write-Step "Waiting connected..."
$tabConn = Wait-ForLogPattern $CallerDevice "Connection state: connected|State change callback: connected" 120
$s10Conn = Wait-ForLogPattern $CalleeDevice "Connection state: connected|State change callback: connected" 120
if (-not ($tabConn -and $s10Conn)) { throw "Connection timeout" }

Write-Step "Enable speaker on Tab (TTS playback)"
for ($v = 0; $v -lt 5; $v++) {
    Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
}
$null = Tap-UiLabel $CallerDevice @("스피커", "Speaker") (Join-Path $RunDir "tab_speaker.xml")
Start-Sleep -Seconds 3

if (-not $SetupOnly) {
    Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
    Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
}

if ($SetupOnly) {
    Write-Step "=== SETUP ONLY: connected call_id=$callerCallId ==="
    exit 0
}

Write-Step "=== READY: S10에서 6초 이상 말씀해 주세요 (ko↔ja: こんにちは。よろしくお願いします。) ==="
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
Force-HangupVoipDevices -Reason "post_call"
