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
    [switch]$PreserveCalleeSession,
    [string]$SetPreferredLanguage = "",
    [string]$ProfileEmail = "",
    [string]$CallerPreferredLanguage = "",
    [string]$CalleePreferredLanguage = "",
    [switch]$SkipUiLoginAutomation
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "manual_retest_$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$script:ReverseReadyByDevice = @{}

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
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
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

function Type-IntoFocusedField {
    param(
        [string]$Device,
        [string]$Value
    )

    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_MOVE_END") | Out-Null
    foreach ($i in 1..80) {
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_DEL") | Out-Null
    }
    $escaped = ($Value -replace ' ', '%s')
    Invoke-Adb $Device @("shell", "input", "text", $escaped) | Out-Null
    return $true
}

function Write-LatestAuthSubmitTrace {
    param([string]$Device)

    $text = Get-LogcatText $Device
    $lines = $text -split "`n"
    $patterns = @(
        'LOGIN_SUBMIT_PRESS',
        'LOGIN_API_REQUEST',
        'LOGIN_API_SUCCESS',
        'LOGIN_API_FAIL',
        'LOGIN_SUBMIT_SUCCESS',
        'LOGIN_SUBMIT_FAIL'
    )
    foreach ($pattern in $patterns) {
        $line = $lines | Where-Object { $_ -match $pattern } | Select-Object -Last 1
        if ($line) {
            Write-Step "AUTH_TRACE[$Device] $line"
        }
    }
}

function Try-UiLogin {
    param([string]$Device)

    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if (-not $password) {
        $passwordPath = Join-Path $RepoRoot $VoipApiPasswordFile
        if (Test-Path $passwordPath) {
            $password = (Get-Content -Raw $passwordPath).Trim()
        }
    }
    if (-not $password) { return $false }

    $safeDevice = $Device -replace '[:\\/]', '_'
    $dumpPath = Join-Path $RunDir "auth_login_$safeDevice.xml"
    $afterEmailPath = Join-Path $RunDir "auth_after_email_$safeDevice.xml"
    $postSubmitPath = Join-Path $RunDir "auth_post_submit_$safeDevice.xml"

    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Test-Path $dumpPath)) { return $false }
    $xml = Get-Content -Raw $dumpPath

    if ($xml -match 'worldlinco-header-login-button') {
        if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-header-login-button' -DumpPath $dumpPath) {
            Start-Sleep -Milliseconds 700
            Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
            $xml = Get-Content -Raw $dumpPath
        }
    }

    if ($xml -match 'worldlinco-inline-open-login-button') {
        if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-inline-open-login-button' -DumpPath $dumpPath) {
            Start-Sleep -Seconds 2
            Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
            $xml = Get-Content -Raw $dumpPath
        }
    }

    if ($xml -match '이미 사용 중인 이메일|이메일 인증 코드 받기') {
        if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-login-close' -DumpPath $dumpPath) {
            Start-Sleep -Milliseconds 700
            if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-header-login-button' -DumpPath $dumpPath) {
                Start-Sleep -Milliseconds 700
            }
            if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-inline-open-login-button' -DumpPath $dumpPath) {
                Start-Sleep -Seconds 2
                Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
                $xml = Get-Content -Raw $dumpPath
            }
        }
    }

    if ($xml -notmatch 'worldlinco-auth-email-input') {
        return $false
    }

    if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-email-input' -Value $VoipApiEmail -DumpPath $dumpPath)) {
        return $false
    }
    Start-Sleep -Milliseconds 400

    Get-UiDump -Device $Device -OutPath $afterEmailPath | Out-Null
    $afterEmailXml = if (Test-Path $afterEmailPath) { Get-Content -Raw $afterEmailPath } else { '' }

    # NOTE: worldlinco-auth-google-continue switches auth mode to signup.
    # For VoIP E2E we require login mode, so never tap it automatically.

    if ($afterEmailXml -match 'worldlinco-auth-password-input') {
        if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-password-input' -Value $password -DumpPath $afterEmailPath)) {
            return $false
        }
    }
    else {
        Write-Step "Password field hidden after email input on $Device; dismissing keyboard before fallback"
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
        Start-Sleep -Milliseconds 500
        Get-UiDump -Device $Device -OutPath $afterEmailPath | Out-Null
        $afterDismissXml = if (Test-Path $afterEmailPath) { Get-Content -Raw $afterEmailPath } else { '' }
        if ($afterDismissXml -match 'worldlinco-auth-password-input') {
            if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-password-input' -Value $password -DumpPath $afterEmailPath)) {
                return $false
            }
        }
        else {
            Write-Step "Password field still hidden after keyboard dismiss on $Device; using TAB fallback"
            Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_TAB") | Out-Null
            Start-Sleep -Milliseconds 400
            if (-not (Type-IntoFocusedField -Device $Device -Value $password)) {
                return $false
            }
        }
    }
    Start-Sleep -Milliseconds 400

    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-auth-login-submit-button' -DumpPath $dumpPath)) {
        if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-auth-signup-submit-button' -DumpPath $dumpPath) {
            # Signup submit visible means current modal mode is signup.
            # Toggle back to login and submit with login handler.
            if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-modal-auth-mode-toggle' -DumpPath $dumpPath) {
                Start-Sleep -Milliseconds 700
                Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
                if (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-auth-login-submit-button' -DumpPath $dumpPath) {
                    Write-Step "Login submit after auth mode toggle on $Device"
                }
                else {
                    Write-Step "Login submit button still missing after auth mode toggle on $Device"
                }
            }
            else {
                Write-Step "Signup submit visible but mode toggle not found on $Device"
            }
        }
        else {
            Write-Step "Login submit button not found on $Device; dismissing keyboard and retrying"
            Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
            Start-Sleep -Milliseconds 500
            if (-not (Tap-ByResourceId -Device $Device -ResourceId 'worldlinco-auth-login-submit-button' -DumpPath $dumpPath)) {
                Write-Step "Login submit retry not found on $Device; trying text-label fallback"
                if (-not (Tap-UiLabel -Device $Device -Labels @("로그인", "Login") -DumpPath $dumpPath)) {
                    Write-Step "Login text-label fallback not found on $Device; sending ENTER fallback"
                    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_ENTER") | Out-Null
                }
            }
        }
    }

    Write-Step "UI login submit attempted on $Device"
    Start-Sleep -Seconds 4
    Get-UiDump -Device $Device -OutPath $postSubmitPath | Out-Null
    Write-LatestAuthSubmitTrace -Device $Device
    return $true
}

function Test-LoginSurfaceVisible([string]$Device, [string]$DumpSuffix) {
    $dumpPath = Join-Path $RunDir "login_surface_$DumpSuffix.xml"
    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Test-Path $dumpPath)) { return $false }
    $xml = Get-Content -Raw $dumpPath
    return $xml -match 'worldlinco-header-login-button|worldlinco-inline-open-login-button|worldlinco-inline-auth-panel|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-auth-signup-submit-button|worldlinco-auth-google-continue'
}

function Test-ManualSessionReady([string]$Device, [string]$DumpSuffix) {
    $dumpPath = Join-Path $RunDir "manual_session_$DumpSuffix.xml"
    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Test-Path $dumpPath)) { return $false }
    $xml = Get-Content -Raw $dumpPath

    $hasLoginSurface = $xml -match 'worldlinco-header-login-button|worldlinco-inline-open-login-button|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-auth-signup-submit-button|worldlinco-auth-google-continue'
    if ($hasLoginSurface) { return $false }

    $hasLoggedInSurface = $xml -match 'worldlinco-my-info-toggle|worldlinco-translate-home-button|worldlinco-voip-lobby-friend-folder-open|worldlinco-chat-friend-folder-open|worldlinco-voip-lobby-button|worldlinco-voip-open'
    return $hasLoggedInSurface
}

function Wait-ForAuthReady([string]$Device, [int]$TimeoutSec = 240, [bool]$AllowUiLogin = $true) {
    if ($AllowUiLogin) {
        Invoke-Adb $Device @("logcat", "-c") | Out-Null
    }
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    Start-Sleep -Seconds 6
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $loginAttempted = $false
    $lastLoginAttemptAt = Get-Date "2000-01-01"
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        # LOGIN_SUBMIT_SUCCESS alone is not sufficient; require token/session readiness signals.
        if ($text -match 'LOGIN_SUBMIT_SUCCESS' -and $text -match '"user_id":\d+' -and $text -match '"token_ready":true|VOIP_PRESENCE_CONNECTED|FRIEND_FOLDER_DIAG') {
            return $true
        }
        if ($text -match 'AUTH_STORAGE_RESTORE_FOUND' -and $text -match '"user_id":\d+') {
            Start-Sleep -Seconds 10
            $text = Get-LogcatText $Device
            if ($text -match '"token_ready":true' -or $text -match 'VOIP_PRESENCE_CONNECTED|FRIEND_FOLDER_DIAG|VOIP_PENDING_CALL') {
                return $true
            }
        }
        if ($text -match 'VoIPPendingIncoming.*"token_summary":"len:\d+' -and $text -match '"user_id":\d+') { return $true }
        if ($text -match 'VOIP_PRESENCE_CONNECTED' -and $text -match '"user_id":\d+') { return $true }
        if (-not $AllowUiLogin) {
            if (Test-ManualSessionReady -Device $Device -DumpSuffix ($Device -replace '[:\\/]','_')) {
                return $true
            }
            Start-Sleep -Seconds 4
            continue
        }
        if (-not $loginAttempted) {
            $loginAttempted = Try-UiLogin -Device $Device
            if ($loginAttempted) {
                $lastLoginAttemptAt = Get-Date
            }
        }
        elseif (((Get-Date) - $lastLoginAttemptAt).TotalSeconds -ge 20 -and (Test-LoginSurfaceVisible -Device $Device -DumpSuffix ($Device -replace '[:\\/]', '_'))) {
            Write-Step "Login surface still visible on $Device; retrying UI login"
            $loginAttempted = Try-UiLogin -Device $Device
            if ($loginAttempted) {
                $lastLoginAttemptAt = Get-Date
            }
        }
        Start-Sleep -Seconds 4
    }
    return $false
}

function Tap-ByResourceId {
    param([string]$Device, [string]$ResourceId, [string]$DumpPath)
    Get-UiDump -Device $Device -OutPath $DumpPath | Out-Null
    if (-not (Test-Path $DumpPath)) { return $false }
    $rawDump = Get-Content -Raw $DumpPath
    if ([string]::IsNullOrWhiteSpace($rawDump)) { return $false }
    try {
        [xml]$doc = $rawDump
    }
    catch {
        Write-Step "WARN: invalid UI dump XML for $Device at $DumpPath"
        return $false
    }
    if (-not $doc) { return $false }
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
    }
    catch {
        Write-Step "WARN: VoIP API login failed — skip API auth ($($_.Exception.Message))"
        return $null
    }
}

function Test-VoipApiCredential {
    try {
        $token = Get-VoipApiAccessToken
        if ($token) {
            return [pscustomobject]@{ ok = $true; blocker = $null }
        }

        $password = $env:WORLDLINCO_VOIP_API_PASSWORD
        if (-not $password) {
            $passwordPath = Join-Path $RepoRoot $VoipApiPasswordFile
            if (Test-Path $passwordPath) {
                $password = (Get-Content -Raw $passwordPath).Trim()
            }
        }
        if (-not $password) {
            return [pscustomobject]@{ ok = $false; blocker = 'login_api_token_missing' }
        }

        $statusCode = & curl.exe -s -o NUL -w "%{http_code}" -X POST "$ApiBaseUrl/api/auth/login" `
            -H "Content-Type: application/x-www-form-urlencoded" `
            --data-urlencode "username=$VoipApiEmail" `
            --data-urlencode "password=$password"
        if ("$statusCode" -eq '401') {
            return [pscustomobject]@{ ok = $false; blocker = 'login_api_unauthorized' }
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
            call_id          = $callId
            signaling_server = $sig
            caller_voice_id  = $callerVid
        }
    }
    return $null
}

function Get-SignalingServerFallback {
    param([string]$CallId)
    $base = [string]$ApiBaseUrl
    if (-not $base) {
        return "wss://metanova1004.com/api/v1/voip/signal?call_id=$CallId&role=callee"
    }
    try {
        $uri = [System.Uri]$base
        $wsScheme = if ($uri.Scheme -eq "https") { "wss" } else { "ws" }
        $host = $uri.Host
        $portPart = ""
        if (-not $uri.IsDefaultPort) {
            $portPart = ":$($uri.Port)"
        }
        return "${wsScheme}://${host}${portPart}/api/v1/voip/signal?call_id=$CallId&role=callee"
    }
    catch {
        return "wss://metanova1004.com/api/v1/voip/signal?call_id=$CallId&role=callee"
    }
}

function Ensure-AdbReverseForLocalApi {
    param(
        [string]$Device,
        [int]$Port = 8000
    )

    if ($script:ReverseReadyByDevice.ContainsKey($Device)) {
        return [bool]$script:ReverseReadyByDevice[$Device]
    }

    $ok = $false
    try {
        $out = Invoke-Adb $Device @("reverse", "tcp:$Port", "tcp:$Port")
        $txt = ($out -join "`n")
        if ($txt -notmatch 'error|cannot|failed|unknown') {
            $ok = $true
        }
    }
    catch {
        $ok = $false
    }

    $script:ReverseReadyByDevice[$Device] = $ok
    if ($ok) {
        Write-Step "ADB reverse ready on $Device tcp:$Port -> tcp:$Port"
    }
    else {
        Write-Step "WARN: ADB reverse failed on $Device tcp:$Port"
    }
    return $ok
}

function Should-PreferLocalSignaling {
    try {
        $uri = [System.Uri][string]$ApiBaseUrl
        $host = $uri.Host.ToLowerInvariant()
        if ($host -eq 'localhost' -or $host -eq '127.0.0.1' -or $host -eq '0.0.0.0') { return $true }
        if ($host -like '172.*' -or $host -like '10.*' -or $host -like '192.168.*') { return $true }
        return $false
    }
    catch {
        return $false
    }
}

function Resolve-SignalingServer {
    param(
        [string]$CallId,
        [string]$Candidate,
        [string]$Device = ""
    )

    if (Should-PreferLocalSignaling) {
        if ($Device -and (Ensure-AdbReverseForLocalApi -Device $Device -Port 8000)) {
            return Get-SignalingServerFallback -CallId $CallId
        }
        if ($Candidate) {
            Write-Step "Local signaling bridge unavailable; using candidate signaling for $Device"
            return $Candidate
        }
        return Get-SignalingServerFallback -CallId $CallId
    }

    if ($Candidate) {
        return $Candidate
    }
    return Get-SignalingServerFallback -CallId $CallId
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

    function Test-PendingIncomingApi {
        param(
            [string]$CallId,
            [string]$CallerVoiceId
        )

        $token = Get-VoipApiAccessToken
        if (-not $token) { return $false }
        try {
            $pendingJson = & curl.exe -s --max-time 15 -H "Authorization: Bearer $token" "$ApiBaseUrl/api/v1/voip/calls/pending-incoming"
            if (-not $pendingJson -or $pendingJson.TrimStart() -notmatch '^\{') { return $false }
            $pending = $pendingJson | ConvertFrom-Json
            if ($pending.call_id -ne $CallId) { return $false }
            if ($CallerVoiceId -and $pending.caller_voice_id -and $pending.caller_voice_id -ne $CallerVoiceId) { return $false }
            Write-Step "Pending-incoming API confirmed call_id=$CallId caller=$($pending.caller_voice_id)"
            return $true
        }
        catch {
            Write-Step "WARN: pending-incoming API probe failed: $($_.Exception.Message)"
            return $false
        }
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $deepLinkInjected = $false
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match "VOIP_INCOMING_CALL_RECEIVED.*?`"call_id`":`"$ExpectedCallId`"") {
            return $true
        }
        if ($text -match "VOIP_PENDING_CALL_FETCHED.*?`"call_id`":`"$ExpectedCallId`"") {
            return $true
        }
        if ($text -match "VOIP_INCOMING_CALL_APPLIED.*?`"call_id`":`"$ExpectedCallId`"") {
            return $true
        }
        if (Test-PendingIncomingApi -CallId $ExpectedCallId -CallerVoiceId $ExpectedCallerVoiceId) {
            return $true
        }
        if (-not $deepLinkInjected) {
            $payload = Get-LatestIncomingCallFromLog -LogText $text -ExpectedCallerVoiceId $ExpectedCallerVoiceId
            $candidateSignaling = if ($payload -and $payload.call_id -eq $ExpectedCallId) {
                $payload.signaling_server
            }
            else {
                $null
            }
            $signaling = Resolve-SignalingServer -CallId $ExpectedCallId -Candidate $candidateSignaling -Device $Device
            if (Open-IncomingVoipDeepLinkAutoAccept -Device $Device -CallId $ExpectedCallId -SignalingServer $signaling -DisplayLanguage $CallerPreferredLanguage) {
                Write-Step "Incoming deeplink injected while waiting for call_id=$ExpectedCallId"
                return $true
            }
            $deepLinkInjected = $true
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
    $candidateSignaling = if ($payload -and $payload.call_id -eq $ExpectedCallId) {
        $payload.signaling_server
    }
    else {
        $null
    }
    $signaling = Resolve-SignalingServer -CallId $ExpectedCallId -Candidate $candidateSignaling -Device $Device

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
    }
    catch {
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

function Ensure-CalleePresenceConnected {
    param(
        [string]$Device,
        [int]$TotalTimeoutSec = 120
    )

    $deadline = (Get-Date).AddSeconds($TotalTimeoutSec)
    $attempt = 0
    while ((Get-Date) -lt $deadline) {
        $attempt += 1
        Write-Step "Presence warmup attempt #$attempt on $Device"

        # Bring app to foreground and open VoIP validation lobby to trigger presence websocket.
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
        Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
        Start-Sleep -Seconds 2
        Open-VoipValidationMode $Device
        Start-Sleep -Seconds 3

        if (Wait-ForLogPattern $Device "VOIP_PRESENCE_CONNECTED" 20) {
            return $true
        }

        # Secondary hints: if pending incoming pipeline is alive, keep progressing.
        if (Wait-ForLogPattern $Device "VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_CALL_APPLIED" 8) {
            Write-Step "Presence fallback: incoming pipeline active on $Device"
            return $true
        }

        Start-Sleep -Seconds 2
    }

    return $false
}

function Wait-ForConnectedCallState {
    param(
        [string]$Device,
        [string]$CallId,
        [int]$TimeoutSec = 120
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $connectedPattern = 'Connection state: connected|State change callback: connected|VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED|peer answered \(bridge\)|VOIP_CONNECTION_STATE_UPDATE.*"state":"connected"'
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        $hasCall = $false
        if ($CallId) {
            $hasCall = ($text -match [regex]::Escape($CallId))
        }
        $hasConnectedSignal = ($text -match $connectedPattern)
        if ($hasCall -and $hasConnectedSignal) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-ForCalleeRelayReady {
    param(
        [string]$Device,
        [string]$CallId,
        [int]$TimeoutSec = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($CallId -and ($text -notmatch [regex]::Escape($CallId))) {
            Start-Sleep -Seconds 2
            continue
        }

        if ($text -match 'VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED|Connection state: connected|State change callback: connected|VOIP_CONNECTION_STATE_UPDATE.*"state":"connected"') {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Test-CallStateConnectedByApi {
    param([string]$CallId)
    if (-not $CallId) { return $false }
    try {
        $token = Get-VoipApiAccessToken
        if (-not $token) { return $false }
        $json = & curl.exe -s --max-time 10 -H "Authorization: Bearer $token" "$ApiBaseUrl/api/v1/voip/calls/$CallId"
        if (-not $json -or $json.TrimStart() -notmatch '^\{') { return $false }
        return ($json -match '"status"\s*:\s*"(active|connecting)"')
    }
    catch {
        return $false
    }
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
if (Should-PreferLocalSignaling) {
    $null = Ensure-AdbReverseForLocalApi -Device $CallerDevice -Port 8000
    $null = Ensure-AdbReverseForLocalApi -Device $CalleeDevice -Port 8000
}
Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "force-stop", $PackageName) | Out-Null
if (-not $PreserveCalleeSession) {
    Invoke-Adb $CalleeDevice @("shell", "am", "force-stop", $PackageName) | Out-Null
}
else {
    Write-Step "PreserveCalleeSession: callee app left running for FCM/presence incoming path"
}
Start-Sleep -Seconds 2
Invoke-Adb $CallerDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 8

$calleeWarmLog = Get-LogcatText $CalleeDevice
$calleeHasWarmSession = $calleeWarmLog -match 'AUTH_STORAGE_RESTORE_FOUND|"token_ready":true|"user_ready":true|VOIP_PRESENCE_CONNECTED|token_summary":"len:'
if (-not $calleeHasWarmSession) {
    if ($PreserveCalleeSession) {
        $preserveDump = Join-Path $RunDir "callee_preserve_session_probe.xml"
        Get-UiDump -Device $CalleeDevice -OutPath $preserveDump | Out-Null
        $preserveXml = if (Test-Path $preserveDump) { Get-Content -Raw $preserveDump } else { '' }
        if ($preserveXml -match 'worldlinco-inline-open-login-button|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button') {
            Write-Step "PreserveCalleeSession fallback: callee login surface detected; switching to normal auth flow"
        }
        else {
            Write-Step "PreserveCalleeSession fallback: no warm-session evidence; switching to normal auth flow"
        }
    }

    Write-Step "Checking VoIP API credential preflight..."
    $credential = Test-VoipApiCredential
    if (-not $credential.ok) {
        throw "VoIP API credential preflight failed ($($credential.blocker))"
    }
}
else {
    Write-Step "Skipping VoIP API credential preflight because callee session evidence is already present"
}

Write-Step "Waiting auth..."
$allowUiLogin = -not $SkipUiLoginAutomation
if ($SkipUiLoginAutomation) {
    Write-Step "Manual login mode enabled: UI login automation is disabled"
}
if (-not (Wait-ForAuthReady $CallerDevice 240 $allowUiLogin)) {
    if ($SkipUiLoginAutomation) {
        Write-Step "WARN: Tab auth timeout in manual login mode; continuing to call flow checks"
    }
    else {
        throw "Tab auth timeout"
    }
}
if (-not (Wait-ForAuthReady $CalleeDevice 75 $allowUiLogin)) {
    if ($PreserveCalleeSession) {
        Write-Step "Callee auth probe timeout; retrying strict auth flow"
        if (-not (Wait-ForAuthReady $CalleeDevice 90 $allowUiLogin)) {
            if ($SkipUiLoginAutomation) {
                Write-Step "WARN: Callee auth timeout in manual login mode; continuing to presence checks"
            }
            else {
                throw "Callee auth timeout"
            }
        }
    }
    else {
        if ($SkipUiLoginAutomation) {
            Write-Step "WARN: Callee auth timeout in manual login mode; continuing to presence checks"
        }
        else {
            throw "Callee auth timeout"
        }
    }
}

if ($PreserveCalleeSession) {
    Write-Step "Waiting callee VOIP_PRESENCE_CONNECTED before placing call..."
    if (-not (Ensure-CalleePresenceConnected -Device $CalleeDevice -TotalTimeoutSec 120)) {
        if ($SkipUiLoginAutomation) {
            Write-Step "WARN: Callee presence not confirmed; continuing with incoming fallback path"
        }
        else {
            throw "Callee presence not connected"
        }
    }
}

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
$tabConn = Wait-ForConnectedCallState -Device $CallerDevice -CallId $callerCallId -TimeoutSec 120
$s10Conn = Wait-ForConnectedCallState -Device $CalleeDevice -CallId $callerCallId -TimeoutSec 120
if (-not ($tabConn -and $s10Conn)) {
    if ($tabConn -or $s10Conn) {
        Write-Step "Connected partial accepted: tab=$tabConn s10=$s10Conn (one-sided log visibility)"
    }
    elseif (Test-CallStateConnectedByApi -CallId $callerCallId) {
        Write-Step "Connected fallback: server call state is active/connecting for $callerCallId"
    }
    else {
        throw "Connection timeout"
    }
}

if (-not (Wait-ForCalleeRelayReady -Device $CalleeDevice -CallId $callerCallId -TimeoutSec 30)) {
    Write-Step "Callee relay-ready signal missing; retrying incoming deep-link accept"
    $null = Accept-IncomingVoipCall -Device $CalleeDevice -ExpectedCallId $callerCallId
    if (-not (Wait-ForCalleeRelayReady -Device $CalleeDevice -CallId $callerCallId -TimeoutSec 25)) {
        if ($SkipUiLoginAutomation) {
            Write-Step "WARN: Callee relay-ready not confirmed; proceeding with best-effort media path"
        }
        else {
            throw "Callee relay-ready timeout"
        }
    }
}

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
    timestamp           = (Get-Date).ToString("o")
    run_dir             = $RunDir
    s10_segment_started = $s10Seg
    s10_relay_sent      = $s10Sent
    tab_playback        = $tabPlay
    tab_relay_sent      = $tabSent
    s10_playback        = $s10Play
    verdict             = if ($s10Sent -and $tabPlay -and -not $tabSent) { "PASS" } else { "FAIL" }
}
$summary | ConvertTo-Json -Depth 4 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

Write-Step "S10 SEGMENT=$s10Seg S10 SENT=$s10Sent S10 PLAYBACK=$s10Play"
Write-Step "TAB PLAYBACK=$tabPlay TAB SENT=$tabSent"
Write-Step "Verdict: $($summary.verdict)"
Write-Step "Logs: $RunDir"
Force-HangupVoipDevices -Reason "post_call"
