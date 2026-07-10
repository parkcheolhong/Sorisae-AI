#!/usr/bin/env pwsh
# ko↔ja VoIP smoke: Tab(caller/ko) -> S10, S10 speaks Japanese, Tab expects relay playback
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$CallerVoiceId = "nado-000226",
    [string]$CalleeApiEmail = "119cash@naver.com",
    [Alias("BaseUrl")]
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$CalleePreferredLanguage = "ja",
    [string]$RestoreCalleeLanguage = "ko",
    [int]$MonitorSec = 70,
    [int]$StableSec = 8
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\worldlinco-v1-launch"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "ko_ja_smoke_$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $RunDir "run.log") -Value $line
}

function Get-LogcatText([string]$Device) {
    $out = & adb -s $Device logcat -d -v time -s ReactNativeJS:* 2>&1
    return ($out | ForEach-Object { if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" } }) -join "`n"
}

function Test-CallSessionConnected {
    param([string]$LogText, [string]$ExpectedCallId)
    if (-not $ExpectedCallId) { return $false }
    if ($LogText -notmatch [regex]::Escape($ExpectedCallId)) { return $false }
    if ($LogText -match "VOIP_CONNECTION_STATE_UPDATE.*$([regex]::Escape($ExpectedCallId)).*disconnected") {
        if ($LogText -notmatch 'Connection state: connected|State change callback: connected') { return $false }
    }
    return ($LogText -match 'Connection state: connected|State change callback: connected')
}

function Get-ApiAuthToken {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if (-not $password) {
        $passwordPath = Join-Path $RepoRoot ".runtime/secrets/fixed_admin_password.txt"
        if (Test-Path $passwordPath) {
            $password = (Get-Content -Raw $passwordPath).Trim()
        }
    }
    if (-not $password) { return $null }

    try {
        $loginJson = & curl.exe -s --max-time 15 -X POST "$ApiBaseUrl/api/auth/login" `
            -H "Content-Type: application/x-www-form-urlencoded" `
            --data-urlencode "username=$CalleeApiEmail" `
            --data-urlencode "password=$password"
        if (-not $loginJson -or $loginJson.TrimStart() -notmatch '^\{') { return $null }
        $login = $loginJson | ConvertFrom-Json
        return [string]$login.access_token
    }
    catch {
        return $null
    }
}

function Test-CallStatusActiveByApi {
    param([string]$ExpectedCallId, [string]$Token)
    if (-not $ExpectedCallId -or -not $Token) { return $false }
    try {
        $json = & curl.exe -s --max-time 10 -H "Authorization: Bearer $Token" "$ApiBaseUrl/api/v1/voip/calls/$ExpectedCallId"
        if (-not $json -or $json.TrimStart() -notmatch '^\{') { return $false }
        return ($json -match '"status"\s*:\s*"(active|connecting|ringing)"')
    }
    catch {
        return $false
    }
}

function Test-CalleeAcceptedOrIncomingPipeline {
    param([string]$LogText, [string]$ExpectedCallId)
    if (-not $ExpectedCallId) { return $false }
    if ($LogText -notmatch [regex]::Escape($ExpectedCallId)) { return $false }
    return ($LogText -match 'VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED|VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_CALL_APPLIED')
}

function Wait-ForStableCallSession {
    param([string]$ExpectedCallId, [int]$StableSeconds = 8, [int]$TimeoutSec = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $stableSince = $null
    $apiToken = Get-ApiAuthToken
    while ((Get-Date) -lt $deadline) {
        $tabLog = Get-LogcatText $CallerDevice
        $s10Log = Get-LogcatText $CalleeDevice
        $tabOk = Test-CallSessionConnected -LogText $tabLog -ExpectedCallId $ExpectedCallId
        $s10Ok = Test-CallSessionConnected -LogText $s10Log -ExpectedCallId $ExpectedCallId
        $s10PipelineOk = Test-CalleeAcceptedOrIncomingPipeline -LogText $s10Log -ExpectedCallId $ExpectedCallId
        $apiOk = Test-CallStatusActiveByApi -ExpectedCallId $ExpectedCallId -Token $apiToken

        if ($tabOk -and ($s10Ok -or $s10PipelineOk -or $apiOk)) {
            if (-not $stableSince) { $stableSince = Get-Date }
            if (((Get-Date) - $stableSince).TotalSeconds -ge $StableSeconds) {
                Write-Step "Call stable ${StableSeconds}s call_id=$ExpectedCallId (tab=$tabOk s10=$s10Ok pipeline=$s10PipelineOk api=$apiOk)"
                return $true
            }
        } else {
            $stableSince = $null
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Filter-LogByCallId {
    param([string]$LogText, [string]$ExpectedCallId)
    if (-not $ExpectedCallId) { return $LogText }
    return (($LogText -split "`n") | Where-Object { $_ -match [regex]::Escape($ExpectedCallId) }) -join "`n"
}

Write-Step "ko↔ja VoIP smoke -> $RunDir"
$setupScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"

Write-Step "Set S10 ($CalleeApiEmail) preferred_language=$CalleePreferredLanguage via API"
& pwsh -NoProfile -File $setupScript -SetPreferredLanguage $CalleePreferredLanguage -ProfileEmail $CalleeApiEmail 2>&1 | Tee-Object (Join-Path $RunDir "profile_set.log")
if ($LASTEXITCODE -ne 0) {
    Write-Step "WARN: S10 profile API update failed — app will use cached profile until /me refresh"
}

Write-Step "Pre-call hangup + stale call purge"
& pwsh -NoProfile -File $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice `
    -CalleeVoiceId $CalleeVoiceId -CallerVoiceId $CallerVoiceId -ApiBaseUrl $ApiBaseUrl -HangupOnly 2>&1 | Out-Null

Write-Step "Call setup (SetupOnly)"
$setupLogPath = Join-Path $RunDir "setup.log"
& pwsh -NoProfile -File $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice `
    -CalleeVoiceId $CalleeVoiceId -CallerVoiceId $CallerVoiceId `
    -CallerPreferredLanguage "ko" -CalleePreferredLanguage $CalleePreferredLanguage `
    -ApiBaseUrl $ApiBaseUrl -PreserveCalleeSession -SetupOnly 2>&1 | Tee-Object $setupLogPath

$setupLog = if (Test-Path $setupLogPath) { Get-Content -Raw $setupLogPath } else { "" }
$callId = $null
if ($setupLog -match 'SETUP ONLY: connected call_id=(call-[a-f0-9]+)') {
    $callId = $Matches[1]
} elseif ($setupLog -match 'call_id=(call-[a-f0-9]+)') {
    $callId = $Matches[1]
}

if (-not $callId) {
    Write-Step "FAIL: setup did not reach connected call_id"
    & pwsh -NoProfile -File $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice `
        -CalleeVoiceId $CalleeVoiceId -CallerVoiceId $CallerVoiceId -ApiBaseUrl $ApiBaseUrl -HangupOnly 2>&1 | Out-Null
    exit 1
}

Write-Step "Connected call_id=$callId — waiting stable ${StableSec}s..."
if (-not (Wait-ForStableCallSession -ExpectedCallId $callId -StableSeconds $StableSec)) {
    Write-Step "FAIL: call session not stable for $StableSec s"
    Get-LogcatText $CallerDevice | Out-File (Join-Path $RunDir "tab_unstable.log") -Encoding utf8
    Get-LogcatText $CalleeDevice | Out-File (Join-Path $RunDir "s10_unstable.log") -Encoding utf8
    & pwsh -NoProfile -File $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice `
        -CalleeVoiceId $CalleeVoiceId -CallerVoiceId $CallerVoiceId -ApiBaseUrl $ApiBaseUrl -HangupOnly 2>&1 | Out-Null
    exit 1
}

& adb -s $CallerDevice logcat -c 2>&1 | Out-Null
& adb -s $CalleeDevice logcat -c 2>&1 | Out-Null
Write-Step "=== S10 ONLY: Japanese 6+ sec (e.g. こんにちは。よろしくお願いします。) ==="
Start-Sleep -Seconds $MonitorSec

$tabLog = Filter-LogByCallId (Get-LogcatText $CallerDevice) $callId
$s10Log = Filter-LogByCallId (Get-LogcatText $CalleeDevice) $callId
$tabLog | Out-File (Join-Path $RunDir "tab.log") -Encoding utf8
$s10Log | Out-File (Join-Path $RunDir "s10.log") -Encoding utf8

$s10Sent = [bool]($s10Log -match 'VOIP_VOICE_RELAY_SENT')
$tabPlay = [bool]($tabLog -match 'VOIP_VOICE_RELAY_PLAYBACK')
$jaDetected = [bool]($s10Log -match 'VOIP_VOICE_TRANSLATE_RESULT.*detected_lang":"ja' -or $s10Log -match '"detected_lang":"ja"')
$targetLangKo = [bool]($s10Log -match 'VOIP_VOICE_TRANSLATE_RESULT.*target_lang":"ko' -or $s10Log -match 'VOIP_VOICE_RELAY_SENT.*target_lang":"ko')
$koOnTab = [bool]($tabLog -match 'VOIP_VOICE_RELAY_PLAYBACK.*(?:안녕|반갑|부탁|잘|만나)' -or $tabLog -match 'translated_text.*(?:안녕|반갑|부탁|잘|만나)')
$koJaTranslate = [bool]($s10Log -match 'VOIP_VOICE_TRANSLATE_RESULT.*detected_lang":"ja' -or $tabLog -match 'voice_translation.*source_lang":"ja')
$jaSegment = [bool]($s10Log -match 'VOIP_VOICE_RELAY_SEGMENT_STARTED.*source_lang":"ja')
$deeplinkLang = [bool]($s10Log -match 'VOIP_DEEPLINK_PREFERRED_LANGUAGE_APPLIED.*preferred_language":"ja"')
$repetition = ([regex]::Matches($tabLog, 'repetition_hallucination')).Count

$pass = $jaDetected -and $targetLangKo -and ($tabPlay -or $koOnTab)

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    call_id = $callId
    callee_preferred_language = $CalleePreferredLanguage
    s10_relay_sent = $s10Sent
    s10_ja_segment = $jaSegment
    s10_deeplink_ja = $deeplinkLang
    s10_target_lang_ko = $targetLangKo
    tab_playback = $tabPlay
    ja_detected = $jaDetected
    tab_ko_playback = $koOnTab
    ko_ja_translate = $koJaTranslate
    repetition_skip = $repetition
    pass = $pass
}
$summary | ConvertTo-Json -Depth 4 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8
Write-Step "PASS=$pass call_id=$callId s10_sent=$s10Sent target_ko=$targetLangKo ja_seg=$jaSegment tab_play=$tabPlay ja=$jaDetected ko_tts=$koOnTab repetition=$repetition"
Write-Step "Evidence: $RunDir"

Write-Step "Post-call hangup"
& pwsh -NoProfile -File $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice `
    -CalleeVoiceId $CalleeVoiceId -CallerVoiceId $CallerVoiceId -ApiBaseUrl $ApiBaseUrl -HangupOnly 2>&1 | Out-Null

if ($RestoreCalleeLanguage) {
    Write-Step "Restore S10 preferred_language=$RestoreCalleeLanguage"
    & pwsh -NoProfile -File $setupScript -SetPreferredLanguage $RestoreCalleeLanguage -ProfileEmail $CalleeApiEmail 2>&1 | Out-Null
}

if (-not $pass) { exit 1 }
