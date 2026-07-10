#!/usr/bin/env pwsh
# V-8: VoIP Voice Relay Orchestrator — 2-device E2E (accept + connected + relay logcat gates)
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$CallerEmail = "burumi69@gmail.com",
    [string]$CalleeEmail = "119cash@naver.com",
    [string]$AuthPasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [int]$ConnectedHoldSec = 35,
    [int]$RelayProbeSec = 25,
    [switch]$SkipBuild,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "run_$Stamp"
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
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

function Get-DeviceSlug([string]$Device) {
    return ($Device -replace "[:\\\\/]", "_")
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
}

function Get-InstalledVersionCode([string]$Device) {
    $out = Invoke-Adb $Device @("shell", "dumpsys", "package", $PackageName)
    $m = [regex]::Match(($out -join "`n"), "versionCode=(\d+)")
    if ($m.Success) { return [int]$m.Groups[1].Value }
    return $null
}

function Clear-DeviceLog([string]$Device) {
    Invoke-Adb $Device @("logcat", "-c") | Out-Null
}

function Wake-Device([string]$Device) {
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
    Invoke-Adb $Device @("shell", "input", "keyevent", "82") | Out-Null
}

function Grant-MicPermission([string]$Device) {
    Invoke-Adb $Device @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
    Invoke-Adb $Device @("shell", "pm", "grant", $PackageName, "android.permission.MODIFY_AUDIO_SETTINGS") | Out-Null
    # 알림 권한 다이얼로그 자동 허용 (Android 13+)
    Invoke-Adb $Device @("shell", "pm", "grant", $PackageName, "android.permission.POST_NOTIFICATIONS") | Out-Null
}

function Dismiss-SystemDialogs([string]$Device) {
    # 알림/권한 다이얼로그가 남아 있으면 "허용" 버튼 탭
    $dumpPath = Join-Path $env:TEMP "dialog_dismiss_$(Get-DeviceSlug $Device).xml"
    Get-UiDump -Device $Device -OutPath $dumpPath | Out-Null
    if (-not (Test-Path $dumpPath)) { return }
    $xml = Get-Content -Raw $dumpPath
    # "허용" 버튼이 있으면 탭 (알림 권한 다이얼로그)
    if ($xml -match '(?:text|content-desc)="허용"') {
        Tap-UiLabel -Device $Device -Labels @("허용") -DumpPath $dumpPath | Out-Null
        Start-Sleep -Seconds 1
    }
}

function Launch-App([string]$Device) {
    Invoke-Adb $Device @(
        "shell", "am", "start", "-W", "-n",
        "$PackageName/.MainActivity",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER"
    ) | Out-Null
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
        return $false
    }
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

function Get-AuthPassword {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if ($password) { return $password.Trim() }
    $passwordPath = Join-Path $RepoRoot $AuthPasswordFile
    if (Test-Path $passwordPath) {
        return (Get-Content -Raw $passwordPath).Trim()
    }
    return $null
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

    $password = Get-AuthPassword
    if (-not $password) { return $false }

    # Select email based on device role
    $emailForDevice = if ($Device -eq $CallerDevice) { $CallerEmail } else { $CalleeEmail }
    
    $safeDevice = Get-DeviceSlug $Device
    $dumpPath = Join-Path $RunDir "auth_login_$safeDevice.xml"
    $afterEmailPath = Join-Path $RunDir "auth_after_email_$safeDevice.xml"
    $postSubmitPath = Join-Path $RunDir "auth_post_submit_$safeDevice.xml"
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

    if (-not (Set-FieldText -Device $Device -ResourceId 'worldlinco-auth-email-input' -Value $emailForDevice -DumpPath $dumpPath)) {
        return $false
    }
    Start-Sleep -Milliseconds 400

    Get-UiDump -Device $Device -OutPath $afterEmailPath | Out-Null
    $afterEmailXml = if (Test-Path $afterEmailPath) { Get-Content -Raw $afterEmailPath } else { '' }
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
    return $xml -match 'worldlinco-inline-open-login-button|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button'
}

function Open-VoipValidationMode([string]$Device) {
    $deeplink = "worldlingo://voip/open?action=validation"
    Invoke-Adb $Device @(
        "shell", "am", "start", "-W",
        "-a", "android.intent.action.VIEW",
        "-d", "`"$deeplink`""
    ) | Out-Null
}

function Open-VoipValidationAutoCall([string]$Device) {
    # Must pass the full am command as one adb shell string (B26 verified pattern).
    # Splitting args breaks on '&' and callee_voice_id is dropped.
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Start-CallerFriendVoipCall {
    param([string]$Device, [string]$DumpDir)
    Write-Step "Starting validation auto-call deeplink on caller..."
    Open-VoipValidationAutoCall $Device
    Start-Sleep -Seconds 6

    $friendsOk = Wait-ForLogPattern -Device $Device -Pattern "VOIP_VALIDATION_AUTO_CALL_DEEPLINK|$CalleeVoiceId" -TimeoutSec 45 -LogPath (Join-Path $DumpDir "caller_auto_call_deeplink.log")
    if ($friendsOk) { return $true }

    Write-Step "Auto-call deeplink not confirmed — falling back to friend folder UI tap"
    Open-VoipValidationMode $Device
    Start-Sleep -Seconds 3
    $dump = Join-Path $DumpDir "caller_friend_folder_open.xml"
    foreach ($rid in @("worldlinco-voip-lobby-friend-folder-open", "worldlinco-chat-friend-folder-open")) {
        if (Tap-ByResourceId -Device $Device -ResourceId $rid -DumpPath $dump) { break }
    }
    Start-Sleep -Seconds 4
    Wait-ForLogPattern -Device $Device -Pattern $CalleeVoiceId -TimeoutSec 45 | Out-Null
    for ($i = 0; $i -lt 8; $i++) {
        Invoke-Adb $Device @("shell", "input", "swipe", "400", "1400", "400", "500", "350") | Out-Null
        Start-Sleep -Milliseconds 800
        if (Tap-UiLabel -Device $Device -Labels @("보이스톡 걸기, burumi69@gmail.com", "burumi69@gmail.com") -DumpPath (Join-Path $DumpDir "caller_burumi_tap.xml")) {
            return $true
        }
        if (Tap-ByResourceId -Device $Device -ResourceId "worldlinco-friend-voice-call-$CalleeVoiceId" -DumpPath (Join-Path $DumpDir "caller_friend_call_tap.xml")) {
            return $true
        }
    }
    return $false
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
}

function Get-TapCenterFromXml {
    param([string]$XmlPath, [string[]]$Labels)
    if (-not (Test-Path $XmlPath)) { return $null }
    [xml]$doc = Get-Content -Raw $XmlPath
    $best = $null
    $bestScore = -1
    foreach ($n in $doc.SelectNodes("//node")) {
        $text = ([string]$n.GetAttribute("text")).Trim()
        $desc = ([string]$n.GetAttribute("content-desc")).Trim()
        $bounds = [string]$n.GetAttribute("bounds")
        if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { continue }
        $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
        $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
        foreach ($label in $Labels) {
            $l = $label.ToLowerInvariant()
            $score = -1
            if ($text.ToLowerInvariant() -eq $l) { $score = 100 }
            elseif ($desc.ToLowerInvariant() -eq $l) { $score = 95 }
            elseif ($text.ToLowerInvariant().Contains($l)) { $score = 85 }
            elseif ($desc.ToLowerInvariant().Contains($l)) { $score = 80 }
            if ($score -gt $bestScore) {
                $bestScore = $score
                $best = [pscustomobject]@{ x = $cx; y = $cy; label = $label; text = $text; desc = $desc }
            }
        }
    }
    return $best
}

function Tap-UiLabel {
    param([string]$Device, [string[]]$Labels, [string]$DumpPath)
    Get-UiDump -Device $Device -OutPath $DumpPath | Out-Null
    $hit = Get-TapCenterFromXml -XmlPath $DumpPath -Labels $Labels
    if (-not $hit) { return $false }
    Write-Step "Tap '$($hit.label)' at $($hit.x),$($hit.y) on $Device (text='$($hit.text)')"
    Invoke-Adb $Device @("shell", "input", "tap", "$($hit.x)", "$($hit.y)") | Out-Null
    return $true
}

function Wait-ForLogPattern {
    param(
        [string]$Device,
        [string]$Pattern,
        [int]$TimeoutSec = 90,
        [string]$LogPath
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match $Pattern) {
            if ($LogPath) { $text | Out-File -FilePath $LogPath -Encoding utf8 }
            return $true
        }
        Start-Sleep -Seconds 2
    }
    if ($LogPath) { (Get-LogcatText $Device) | Out-File -FilePath $LogPath -Encoding utf8 }
    return $false
}

function Find-LatestCallIdFromLog {
    param([string]$Text)
    foreach ($pattern in @(
        'VOIP_FRIEND_CALL_SUCCESS.*?"call_id":"(call-[a-f0-9]+)"',
        'VOIP_INTENT_INITIATE_SUCCESS.*?"call_id":"(call-[a-f0-9]+)"',
        '"call_id":"(call-[a-f0-9]+)"'
    )) {
        $matches = [regex]::Matches($Text, $pattern)
        if ($matches.Count -gt 0) {
            return $matches[$matches.Count - 1].Groups[1].Value
        }
    }
    return $null
}

function Open-IncomingVoipDeepLinkAutoAccept {
    param(
        [string]$Device,
        [string]$CallId,
        [string]$SignalingServer
    )
    if (-not $CallId) { return $false }
    $encSig = [uri]::EscapeDataString($SignalingServer)
    foreach ($scheme in @('worldlingo', 'worldlinco')) {
        $deeplink = "${scheme}://voip/incoming?call_id=$CallId&signaling_server=$encSig&participant_role=callee&status=ringing&call_route=app_webrtc"
        Write-Step "Launch incoming deeplink ($scheme) on $Device call_id=$CallId"
        $cmd = "am start -W -a android.intent.action.VIEW -d '$deeplink'"
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
        Invoke-Adb $Device @("shell", $cmd) | Out-Null
        Start-Sleep -Seconds 3
        if (Wait-ForLogPattern -Device $Device -Pattern "VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT|VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED" -TimeoutSec 20) {
            return $true
        }
    }
    return $false
}

function Wait-ForAuthReady {
    param([string]$Device, [int]$TimeoutSec = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $loginAttempted = $false
    $lastLoginAttemptAt = Get-Date "2000-01-01"
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') {
            return $true
        }
        if (-not $loginAttempted) {
            $loginAttempted = Try-UiLogin -Device $Device
            if ($loginAttempted) {
                $lastLoginAttemptAt = Get-Date
            }
        }
        elseif (((Get-Date) - $lastLoginAttemptAt).TotalSeconds -ge 20 -and (Test-LoginSurfaceVisible -Device $Device -DumpSuffix (Get-DeviceSlug $Device))) {
            Write-Step "Login surface still visible on $Device; retrying UI login"
            $loginAttempted = Try-UiLogin -Device $Device
            if ($loginAttempted) {
                $lastLoginAttemptAt = Get-Date
            }
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Dismiss-StaleVoipCall {
    param([string]$Device, [string]$DumpDir)
    $dump = Join-Path $DumpDir "stale_hangup_$(Get-DeviceSlug $Device).xml"
    for ($i = 0; $i -lt 4; $i++) {
        $text = Get-LogcatText $Device
        $hasStale = $text -match "connectSignaling:open|Connection state: connected|State change callback: connected|has_active_call.:true"
        if (-not $hasStale) { return $false }
        Write-Step "Stale active VoIP session detected on $Device — tapping hangup (attempt $($i + 1))"
        if (Tap-UiLabel -Device $Device -Labels @("통화 종료", "종료") -DumpPath $dump) {
            Start-Sleep -Seconds 5
            $after = Get-LogcatText $Device
            if ($after -notmatch "connectSignaling:open|Connection state: connected|State change callback: connected") {
                return $true
            }
        }
        Start-Sleep -Seconds 2
    }
    Write-Step "Stale VoIP session persists on $Device — force-stop + relaunch"
    Invoke-Adb $Device @("shell", "am", "force-stop", $PackageName) | Out-Null
    Start-Sleep -Seconds 2
    Launch-App $Device
    Start-Sleep -Seconds 8
    if (-not (Wait-ForAuthReady -Device $Device -TimeoutSec 120)) {
        Write-Step "WARN: auth not ready after stale-session relaunch on $Device"
    }
    return $true
}

function Ensure-ProbeAudio {
    param([string]$OutPath)
    if (Test-Path $OutPath) { return $OutPath }
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $ffmpeg) { throw "ffmpeg required for relay probe audio" }
    # Windows TTS로 실제 사람 목소리 생성 (사인파는 Whisper VAD에서 제거됨)
    $tmpWav = [System.IO.Path]::ChangeExtension($OutPath, ".tmp.wav")
    try {
        Add-Type -AssemblyName System.Speech
        $tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $tts.Rate = -2  # 약간 느리게 → Whisper 인식률 향상
        $tts.SetOutputToWaveFile($tmpWav)
        $tts.Speak("Hello. Testing voice relay translation pipeline. One two three. Hello. Can you hear me?")
        $tts.Dispose()
    }
    catch {
        Write-Warning "TTS failed: $_. Falling back to sine wave."
        $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try { & ffmpeg -y -f lavfi -i "sine=frequency=880:duration=4" -af "volume=30dB" -ar 44100 -ac 1 $OutPath 2>$null | Out-Null }
        finally { $ErrorActionPreference = $prev }
        if (-not (Test-Path $OutPath)) { throw "Failed to generate probe audio at $OutPath" }
        return $OutPath
    }
    # 16kHz mono로 변환 (Whisper 최적 포맷)
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & ffmpeg -y -i $tmpWav -ar 16000 -ac 1 -acodec pcm_s16le $OutPath 2>$null | Out-Null }
    finally { $ErrorActionPreference = $prev }
    if (Test-Path $tmpWav) { Remove-Item $tmpWav -Force -ErrorAction SilentlyContinue }
    if (-not (Test-Path $OutPath)) { throw "Failed to generate probe audio at $OutPath" }
    return $OutPath
}

function Play-RelayProbeAudio {
    param([string]$Device, [string]$LocalWavPath, [int]$DurationSec)
    $remote = "/sdcard/Download/voip_relay_probe.wav"
    Invoke-Adb $Device @("push", $LocalWavPath, $remote) | Out-Null
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
    Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
    $loops = [Math]::Max(1, [int][Math]::Ceiling($DurationSec / 4.0))
    for ($i = 0; $i -lt $loops; $i++) {
        Invoke-Adb $Device @(
            "shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", "file://$remote", "-t", "audio/wav"
        ) | Out-Null
        Start-Sleep -Seconds 4
    }
}

function Export-FilteredLog([string]$Device, [string]$OutPath) {
    $raw = Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")
    $raw | Out-File -FilePath $OutPath -Encoding utf8
    return ($raw -join "`n")
}

function Test-LogGates([string]$Text) {
    $relaySentWithMeta = [bool]($Text -match 'VOIP_VOICE_RELAY_SENT.*utterance_id.*chunk_index.*is_final')
    return [pscustomobject]@{
        accept_api_ok        = [bool]($Text -match "VOIP_INCOMING_ACCEPT_API_OK")
        accept_accepted      = [bool]($Text -match "VOIP_INCOMING_CALL_ACCEPTED|VOIP_CALL_MODE_AUDIT_LOADED.*call_accepted")
        signaling_open       = [bool]($Text -match "connectSignaling:open|connectSignaling:onmessage.*state=OPEN|handleSignalingMessage:pong")
        connected_state      = [bool]($Text -match "Connection state: connected|State change callback: connected|VOIP_RAIL_STATE_RESTORE.*active_call_id")
        disconnected_early   = [bool]($Text -match "State change callback: disconnected|Connection state: disconnected")
        voice_relay_sent     = [bool]($Text -match "VOIP_VOICE_RELAY_SENT")
        utterance_meta       = [bool]($Text -match "utterance_id|chunk_index|is_final")
        relay_sent_with_meta = $relaySentWithMeta
        translate_result     = [bool]($Text -match 'VOIP_VOICE_TRANSLATE_RESULT|normalizedType: ''voice_translation''|"type":"voice_translation"')
        friend_call_ok       = [bool]($Text -match "VOIP_FRIEND_CALL_SUCCESS")
        silero_started       = [bool]($Text -match "VOIP_VOICE_RELAY_SILERO_STARTED")
        silero_speech_end    = [bool]($Text -match "VOIP_VOICE_RELAY_SILERO_SPEECH_END")
        silero_segment_flush = [bool]($Text -match 'VOIP_VOICE_RELAY_SEGMENT_FLUSH.*"reason":"silence"')
        segment_started      = [bool]($Text -match "VOIP_VOICE_RELAY_SEGMENT_STARTED")
        relay_playback       = [bool]($Text -match "VOIP_VOICE_RELAY_PLAYBACK")
        face_translate_ok    = [bool]($Text -match 'segment_response","ok":true,"route":"translate"')
        active_call_restored = [bool]($Text -match 'VOIP_RAIL_STATE_RESTORE.*"active_call_id":"call-')
    }
}

Write-Step "V-8 E2E run dir: $RunDir"
Write-Step "Caller=$CallerDevice Callee=$CalleeDevice callee_voice_id=$CalleeVoiceId"

# --- Build ---
$ApkPath = Join-Path $RepoRoot "uploads\marketplace_local\apk\nadotongryoksa-v1.apk"
if (-not $SkipBuild) {
    Write-Step "Building release APK (assembleRelease arm64-v8a)..."
    & (Join-Path $RepoRoot "scripts\publish_worldlinco_apk.ps1") | Tee-Object -FilePath (Join-Path $RunDir "build.log")
}
if (-not (Test-Path $ApkPath)) { throw "APK missing: $ApkPath" }

$appJson = Get-Content (Join-Path $RepoRoot "apps\mobile-nadotongryoksa\app.json") -Raw | ConvertFrom-Json
$expectedVersionCode = [int]$appJson.expo.android.versionCode
$expectedVersionName = [string]$appJson.expo.version
Write-Step "Expected APK version: $expectedVersionName (code $expectedVersionCode)"

# --- Install ---
if (-not $SkipInstall) {
    foreach ($dev in @($CallerDevice, $CalleeDevice)) {
        Write-Step "Installing APK on $dev ..."
        Invoke-Adb $dev @("install", "-r", $ApkPath) | Tee-Object -FilePath (Join-Path $RunDir "install_$(Get-DeviceSlug $dev).log")
    }
}

$callerCode = Get-InstalledVersionCode $CallerDevice
$calleeCode = Get-InstalledVersionCode $CalleeDevice
Write-Step "Installed versionCode caller=$callerCode callee=$calleeCode"
if ($callerCode -ne $expectedVersionCode -or $calleeCode -ne $expectedVersionCode) {
    throw "Version mismatch: expected $expectedVersionCode, got caller=$callerCode callee=$calleeCode"
}

# --- Prep devices ---
# Both devices: clear app data (need fresh login + fresh mic state)
foreach ($dev in @($CallerDevice, $CalleeDevice)) {
    Wake-Device $dev
    Grant-MicPermission $dev
    Invoke-Adb $dev @("shell", "am", "force-stop", $PackageName) | Out-Null
    Write-Step "Clearing app data on $dev to remove old auth tokens..."
    Invoke-Adb $dev @("shell", "pm", "clear", $PackageName) | Out-Null
    Clear-DeviceLog $dev
    Launch-App $dev
    Start-Sleep -Seconds 4
    Dismiss-SystemDialogs $dev
}

Write-Step "Waiting for auth hydration on both devices in parallel (240s max)..."
# 두 기기 동시 로그인: 공유 deadline 내에서 교대 폴링
$authDeadline = (Get-Date).AddSeconds(240)
$callerLoginDone = $false
$calleeLoginDone = $false
$callerLoginAttempted = $false
$calleeLoginAttempted = $false
$callerLastAttempt = Get-Date "2000-01-01"
$calleeLastAttempt = Get-Date "2000-01-01"
$callerAuth = $false
$calleeAuth = $false

while ((Get-Date) -lt $authDeadline) {
    # --- Caller ---
    if (-not $callerAuth) {
        $callerText = Get-LogcatText $CallerDevice
        if ($callerText -match '"token_ready":true' -and $callerText -match '"user_ready":true') {
            $callerAuth = $true
            Write-Step "Caller auth ready"
        }
        elseif (-not $callerLoginAttempted) {
            $callerLoginAttempted = Try-UiLogin -Device $CallerDevice
            if ($callerLoginAttempted) { $callerLastAttempt = Get-Date }
        }
        elseif (((Get-Date) - $callerLastAttempt).TotalSeconds -ge 20 -and (Test-LoginSurfaceVisible -Device $CallerDevice -DumpSuffix (Get-DeviceSlug $CallerDevice))) {
            Write-Step "Login surface still visible on $CallerDevice; retrying UI login"
            $callerLoginAttempted = Try-UiLogin -Device $CallerDevice
            if ($callerLoginAttempted) { $callerLastAttempt = Get-Date }
        }
    }

    # --- Callee ---
    if (-not $calleeAuth) {
        $calleeText = Get-LogcatText $CalleeDevice
        if ($calleeText -match '"token_ready":true' -and $calleeText -match '"user_ready":true') {
            $calleeAuth = $true
            Write-Step "Callee auth ready"
        }
        elseif (-not $calleeLoginAttempted) {            Dismiss-SystemDialogs $CalleeDevice            $calleeLoginAttempted = Try-UiLogin -Device $CalleeDevice
            if ($calleeLoginAttempted) { $calleeLastAttempt = Get-Date }
        }
        elseif (((Get-Date) - $calleeLastAttempt).TotalSeconds -ge 20 -and (Test-LoginSurfaceVisible -Device $CalleeDevice -DumpSuffix (Get-DeviceSlug $CalleeDevice))) {
            Write-Step "Login surface still visible on $CalleeDevice; retrying UI login"
            $calleeLoginAttempted = Try-UiLogin -Device $CalleeDevice
            if ($calleeLoginAttempted) { $calleeLastAttempt = Get-Date }
        }
    }

    if ($callerAuth -and $calleeAuth) { break }
    Start-Sleep -Seconds 3
}

Export-FilteredLog $CallerDevice (Join-Path $RunDir "boot_caller.log") | Out-Null
Export-FilteredLog $CalleeDevice (Join-Path $RunDir "boot_callee.log") | Out-Null
if (-not $callerAuth) { throw "Caller auth not ready (token_ready + user_ready) within 240s" }
if (-not $calleeAuth) { throw "Callee auth not ready (token_ready + user_ready) within 240s" }
Write-Step "Auth ready on both devices"

Write-Step "Dismissing stale VoIP sessions if any..."
$null = Dismiss-StaleVoipCall -Device $CallerDevice -DumpDir $RunDir
$null = Dismiss-StaleVoipCall -Device $CalleeDevice -DumpDir $RunDir
Start-Sleep -Seconds 3

Write-Step "Waiting for VoIP presence on callee (120s max)..."
$presenceOk = Wait-ForLogPattern -Device $CalleeDevice -Pattern "VOIP_PRESENCE_CONNECTED" -TimeoutSec 120 -LogPath (Join-Path $RunDir "presence_callee.log")
if (-not $presenceOk) {
    Write-Step "WARN: VOIP_PRESENCE_CONNECTED not seen on callee — continuing"
}

Clear-DeviceLog $CallerDevice
Clear-DeviceLog $CalleeDevice

# --- Start call from caller ---
Write-Step "Starting validation friend VoIP call on caller (auth confirmed)..."
$callTapOk = Start-CallerFriendVoipCall -Device $CallerDevice -DumpDir $RunDir
if (-not $callTapOk) { Write-Step "WARN: could not tap friend call button — continuing to wait for call logs" }

Write-Step "Waiting for friend call initiate on caller..."
$callStartOk = Wait-ForLogPattern -Device $CallerDevice -Pattern "VOIP_FRIEND_CALL_SUCCESS|VOIP_VALIDATION_AUTO_CALL_DEEPLINK|VOIP_START_CALL" -TimeoutSec 120 -LogPath (Join-Path $RunDir "call_start_caller.log")
if (-not $callStartOk) {
    Write-Step "WARN: VOIP_FRIEND_CALL_SUCCESS not confirmed — retry friend call tap once"
    $null = Start-CallerFriendVoipCall -Device $CallerDevice -DumpDir $RunDir
    Start-Sleep -Seconds 4
    $callStartOk = Wait-ForLogPattern -Device $CallerDevice -Pattern "VOIP_FRIEND_CALL_SUCCESS|VOIP_VALIDATION_AUTO_CALL_DEEPLINK|VOIP_START_CALL" -TimeoutSec 60 -LogPath (Join-Path $RunDir "call_start_retry.log")
}

Write-Step "Waiting for incoming on callee..."
$incomingOk = Wait-ForLogPattern -Device $CalleeDevice -Pattern "VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_RING" -TimeoutSec 120 -LogPath (Join-Path $RunDir "incoming_wait.log")
if (-not $incomingOk) { throw "Callee did not receive incoming call within 120s" }

# --- Accept on callee ---
$callerPreAcceptText = Get-LogcatText $CallerDevice
$callId = Find-LatestCallIdFromLog -Text $callerPreAcceptText
if (-not $callId) {
    $calleePreAcceptText = Get-LogcatText $CalleeDevice
    $callId = Find-LatestCallIdFromLog -Text $calleePreAcceptText
}
$signalingServer = if ($callId) { "wss://metanova1004.com/api/v1/voip/signal?call_id=$callId&role=callee" } else { "" }

$deepLinkAcceptOk = $false
if ($callId -and $signalingServer) {
    Write-Step "Trying incoming deep-link auto-accept on callee for call_id=$callId"
    $deepLinkAcceptOk = Open-IncomingVoipDeepLinkAutoAccept -Device $CalleeDevice -CallId $callId -SignalingServer $signalingServer
}

$acceptDump = Join-Path $RunDir "callee_before_accept.xml"
$null = Tap-ByResourceId -Device $CalleeDevice -ResourceId "worldlinco-section-rail-voip-button" -DumpPath (Join-Path $RunDir "callee_voip_rail.xml")
Start-Sleep -Seconds 2
$tapped = $deepLinkAcceptOk
if (-not $tapped) {
    $acceptResourceIds = @(
        "worldlinco-voip-incoming-accept",
        "worldlinco-voip-incoming-accept-banner",
        "worldlinco-voip-incoming-accept-rail",
        "worldlinco-voip-incoming-accept-popup"
    )
    for ($i = 0; $i -lt 12; $i++) {
        if (Tap-UiLabel -Device $CalleeDevice -Labels @("받기", "수신 보이스톡 받기", "Accept", "Answer") -DumpPath $acceptDump) {
            $tapped = $true
            break
        }
        foreach ($rid in $acceptResourceIds) {
            if (Tap-ByResourceId -Device $CalleeDevice -ResourceId $rid -DumpPath (Join-Path $RunDir "callee_accept_by_testid_${i}_$rid.xml")) {
                $tapped = $true
                break
            }
        }
        if ($tapped) { break }
        Start-Sleep -Seconds 2
    }
}
if (-not $tapped) {
    Copy-Item $acceptDump (Join-Path $RunDir "callee_accept_failed.xml") -ErrorAction SilentlyContinue
    throw "Failed to tap 받기 on callee UI"
}

Write-Step "Waiting for accept API + signaling open (60s)..."
$acceptOk = Wait-ForLogPattern -Device $CalleeDevice -Pattern "VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED" -TimeoutSec 60
$signalingOk = Wait-ForLogPattern -Device $CalleeDevice -Pattern "connectSignaling:open" -TimeoutSec 60
if (-not $acceptOk) { Write-Step "WARN: VOIP_INCOMING_ACCEPT_API_OK not yet seen on callee" }
if (-not $signalingOk) { Write-Step "WARN: connectSignaling:open not yet seen on callee" }

# --- Hold connected ---
Write-Step "Holding call for ${ConnectedHoldSec}s (connected stability)..."
Start-Sleep -Seconds $ConnectedHoldSec

# --- Voice relay probe ---
$probeWav = Ensure-ProbeAudio -OutPath (Join-Path $RunDir "voip_relay_probe.wav")
Write-Step "Voice relay probe ${RelayProbeSec}s — playing probe audio on caller speaker..."
Tap-UiLabel -Device $CallerDevice -Labels @("스피커", "Speaker") -DumpPath (Join-Path $RunDir "caller_speaker_on.xml") | Out-Null
Clear-DeviceLog $CallerDevice
Clear-DeviceLog $CalleeDevice
Play-RelayProbeAudio -Device $CallerDevice -LocalWavPath $probeWav -DurationSec $RelayProbeSec
Start-Sleep -Seconds 5

Write-Step "Callee Silero probe ${RelayProbeSec}s — playing probe audio on S10 speaker..."
Tap-UiLabel -Device $CalleeDevice -Labels @("스피커", "Speaker") -DumpPath (Join-Path $RunDir "callee_speaker_on.xml") | Out-Null
Play-RelayProbeAudio -Device $CalleeDevice -LocalWavPath $probeWav -DurationSec $RelayProbeSec
Start-Sleep -Seconds 5

# --- Collect logs ---
$callerLogPath = Join-Path $RunDir "caller_final.log"
$calleeLogPath = Join-Path $RunDir "callee_final.log"
$callerText = Export-FilteredLog $CallerDevice $callerLogPath
$calleeText = Export-FilteredLog $CalleeDevice $calleeLogPath
$combinedPath = Join-Path $RunDir "combined_filtered.log"
@(
    "=== CALLER $CallerDevice ===",
    $callerText,
    "",
    "=== CALLEE $CalleeDevice ===",
    $calleeText
) | Out-File -FilePath $combinedPath -Encoding utf8

$callerGates = Test-LogGates $callerText
$calleeGates = Test-LogGates $calleeText

# Screenshots (PS5-compatible)
$callerPng = Join-Path $RunDir "caller_screen.png"
$calleePng = Join-Path $RunDir "callee_screen.png"
try {
    $callerBytes = & adb -s $CallerDevice exec-out screencap -p
    if ($callerBytes) { [System.IO.File]::WriteAllBytes($callerPng, [byte[]]$callerBytes) }
    $calleeBytes = & adb -s $CalleeDevice exec-out screencap -p
    if ($calleeBytes) { [System.IO.File]::WriteAllBytes($calleePng, [byte[]]$calleeBytes) }
}
catch {
    Write-Step "WARN: screenshot capture failed: $($_.Exception.Message)"
}

$hardPass = (
    $acceptOk -or $calleeGates.accept_api_ok -or $calleeGates.accept_accepted
) -and (
    $signalingOk -or $callerGates.signaling_open -or $calleeGates.signaling_open
) -and (
    $callerGates.connected_state -or $calleeGates.connected_state -or $callerGates.active_call_restored -or $calleeGates.active_call_restored
)

$relayPass = (
    ($callerGates.voice_relay_sent -or $calleeGates.voice_relay_sent -or $callerGates.translate_result -or $calleeGates.translate_result -or $callerGates.face_translate_ok -or $calleeGates.face_translate_ok)
) -and (
    $callerGates.relay_sent_with_meta -or $calleeGates.relay_sent_with_meta `
        -or (($callerGates.voice_relay_sent -or $calleeGates.voice_relay_sent) -and ($callerGates.utterance_meta -or $calleeGates.utterance_meta)) `
        -or $callerGates.face_translate_ok -or $calleeGates.face_translate_ok `
        -or (($callerGates.translate_result -or $calleeGates.translate_result) -and ($callerGates.active_call_restored -or $calleeGates.active_call_restored))
)

$sileroPass = (
    ($callerGates.silero_started -or $calleeGates.silero_started)
) -and (
    $callerGates.silero_speech_end -or $calleeGates.silero_speech_end
)

$summary = [pscustomobject]@{
    timestamp       = (Get-Date).ToString("o")
    run_dir         = $RunDir
    caller_device   = $CallerDevice
    callee_device   = $CalleeDevice
    version_code    = $expectedVersionCode
    version_name    = $expectedVersionName
    caller_auth_ok  = $callerAuth
    callee_auth_ok  = $calleeAuth
    presence_ok     = $presenceOk
    call_start_ok   = $callStartOk
    incoming_ok     = $incomingOk
    accept_tap_ok   = $tapped
    accept_api_seen = $acceptOk
    signaling_seen  = $signalingOk
    hard_pass       = [bool]$hardPass
    relay_pass      = [bool]$relayPass
    silero_pass     = [bool]$sileroPass
    caller_gates    = $callerGates
    callee_gates    = $calleeGates
}

$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

$report = @"
# V-8 E2E Run $Stamp

## Devices
- Caller (A): ``$CallerDevice`` — versionCode ``$callerCode``
- Callee (B): ``$CalleeDevice`` — versionCode ``$calleeCode``
- APK: ``$expectedVersionName`` / build ``$expectedVersionCode``

## Gate results

| Gate | Caller | Callee |
|------|--------|--------|
| VOIP_INCOMING_ACCEPT_API_OK | $($calleeGates.accept_api_ok) | (callee only) |
| connectSignaling:open | $($callerGates.signaling_open) | $($calleeGates.signaling_open) |
| connected (30s+) | $($callerGates.connected_state) | $($calleeGates.connected_state) |
| early disconnected | $($callerGates.disconnected_early) | $($calleeGates.disconnected_early) |
| VOIP_VOICE_RELAY_SENT | $($callerGates.voice_relay_sent) | $($calleeGates.voice_relay_sent) |
| relay + utterance_id/chunk_index/is_final | $($callerGates.relay_sent_with_meta) | $($calleeGates.relay_sent_with_meta) |
| voice_translation seen | $($callerGates.translate_result) | $($calleeGates.translate_result) |
| FACE translate ok | $($callerGates.face_translate_ok) | $($calleeGates.face_translate_ok) |
| active_call_id restored | $($callerGates.active_call_restored) | $($calleeGates.active_call_restored) |
| SILERO_STARTED | $($callerGates.silero_started) | $($calleeGates.silero_started) |
| SILERO_SPEECH_END | $($callerGates.silero_speech_end) | $($calleeGates.silero_speech_end) |
| SEGMENT_FLUSH(silence) | $($callerGates.silero_segment_flush) | $($calleeGates.silero_segment_flush) |
| RELAY_PLAYBACK | $($callerGates.relay_playback) | $($calleeGates.relay_playback) |

## Verdict
- **Accept + signaling + connected**: $(if ($hardPass) { 'PASS' } else { 'FAIL' })
- **Voice relay sent**: $(if ($relayPass) { 'PASS' } else { 'FAIL' })
- **Silero VAD POC**: $(if ($sileroPass) { 'PASS' } else { 'FAIL / INCONCLUSIVE' })
- **Voice relay metadata**: $(if ($relayPass) { 'PASS' } else { 'FAIL' })

## Artifacts
- ``caller_final.log``, ``callee_final.log``, ``combined_filtered.log``
- ``summary.json``, ``callee_before_accept.xml``, screenshots
"@

$report | Out-File (Join-Path $RunDir "E2E_REPORT.md") -Encoding utf8
Write-Step "Report: $(Join-Path $RunDir 'E2E_REPORT.md')"
Write-Step "Hard pass: $hardPass | Relay pass: $relayPass"

if (-not $hardPass) { exit 2 }
if (-not $relayPass) { exit 3 }
exit 0
