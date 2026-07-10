#!/usr/bin/env pwsh
# Post-deploy: verify callee audit log on S10 + relay logcat while callee plays probe audio
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$ConnectedHoldSec = 12,
    [int]$MicHoldSec = 8
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "audit_relay_diag_$Stamp"
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

function Clear-DeviceLog([string]$Device) {
    Invoke-Adb $Device @("logcat", "-c") | Out-Null
}

function Launch-App([string]$Device) {
    Invoke-Adb $Device @(
        "shell", "am", "start", "-W", "-n",
        "$PackageName/.MainActivity",
        "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER"
    ) | Out-Null
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
    Write-Step "Tap testID '$ResourceId' at ${cx},${cy} on $Device"
    Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
    return $true
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
    param([string]$Device, [string]$Pattern, [int]$TimeoutSec = 90, [string]$LogPath)
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

function Wait-ForAuthReady([string]$Device, [int]$TimeoutSec = 180) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $text = Get-LogcatText $Device
        if ($text -match '"token_ready":true' -and $text -match '"user_ready":true') { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Dismiss-StaleVoipCall([string]$Device, [string]$DumpDir) {
    $dump = Join-Path $DumpDir "stale_hangup.xml"
    for ($i = 0; $i -lt 4; $i++) {
        $text = Get-LogcatText $Device
        $hasStale = $text -match "connectSignaling:open|Connection state: connected|State change callback: connected"
        if (-not $hasStale) { return $false }
        Write-Step "Stale VoIP on $Device — hangup attempt $($i + 1)"
        if (Tap-UiLabel -Device $Device -Labels @("통화 종료", "종료") -DumpPath $dump) {
            Start-Sleep -Seconds 5
            $after = Get-LogcatText $Device
            if ($after -notmatch "connectSignaling:open|Connection state: connected") { return $true }
        }
        Start-Sleep -Seconds 2
    }
    Write-Step "Force-stop $Device"
    Invoke-Adb $Device @("shell", "am", "force-stop", $PackageName) | Out-Null
    Start-Sleep -Seconds 2
    Launch-App $Device
    Start-Sleep -Seconds 8
    $null = Wait-ForAuthReady -Device $Device -TimeoutSec 120
    return $true
}

function Open-VoipValidationAutoCall([string]$Device) {
    $cmd = "am start -W -a android.intent.action.VIEW -d 'worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId'"
    Invoke-Adb $Device @("shell", $cmd) | Out-Null
}

function Ensure-ProbeAudio([string]$OutPath) {
    if (Test-Path $OutPath) { return $OutPath }
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $ffmpeg) { throw "ffmpeg required" }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" -af "volume=28dB" -ar 44100 -ac 1 $OutPath 2>$null | Out-Null
    } finally {
        $ErrorActionPreference = $prev
    }
    if (-not (Test-Path $OutPath)) { throw "probe audio generation failed" }
    return $OutPath
}

function Play-CalleeSpeechProbe {
    param([string]$Device, [string]$LocalWavPath, [int]$DurationSec)
    $remote = "/sdcard/Download/voip_callee_speech_probe.wav"
    Invoke-Adb $Device @("push", $LocalWavPath, $remote) | Out-Null
    for ($v = 0; $v -lt 5; $v++) {
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
    }
    Tap-UiLabel -Device $Device -Labels @("스피커", "Speaker") -DumpPath (Join-Path $RunDir "callee_speaker_on.xml") | Out-Null
    $loops = [Math]::Max(1, [int][Math]::Ceiling($DurationSec / 3.0))
    Write-Step "Playing callee speech probe ${DurationSec}s ($loops loops) on $Device"
    for ($i = 0; $i -lt $loops; $i++) {
        Invoke-Adb $Device @(
            "shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", "file://$remote", "-t", "audio/wav"
        ) | Out-Null
        Start-Sleep -Seconds 3
    }
}

function Get-UiTexts([string]$XmlPath) {
    if (-not (Test-Path $XmlPath)) { return @() }
    [xml]$doc = Get-Content -Raw $XmlPath
    return @($doc.SelectNodes("//node") | ForEach-Object { [string]$_.GetAttribute("text") } | Where-Object { $_ })
}

function Analyze-AuditUi([string]$XmlPath) {
    $texts = Get-UiTexts $XmlPath
    $joined = ($texts -join " | ")
    return [pscustomobject]@{
        has_audit_error_403 = [bool]($joined -match "403")
        has_audit_fetch_failed = [bool]($joined -match "audit fetch failed")
        has_call_initiated = [bool]($joined -match "call_initiated")
        has_call_accepted = [bool]($joined -match "call_accepted")
        has_empty_audit = [bool]($joined -match "아직 감사 로그가 없습니다")
        sample_texts = ($texts | Select-Object -First 40) -join "`n"
    }
}

function Analyze-RelayLog([string]$Text) {
    return [pscustomobject]@{
        relay_sent = [bool]($Text -match "VOIP_VOICE_RELAY_SENT")
        relay_sent_meta = [bool]($Text -match "VOIP_VOICE_RELAY_SENT.*utterance_id")
        translate_request = [bool]($Text -match "VOIP_VOICE_TRANSLATE_REQUEST")
        translate_result = [bool]($Text -match "VOIP_VOICE_TRANSLATE_RESULT")
        relay_start_blocked = [bool]($Text -match "VOIP_VOICE_RELAY_START_BLOCKED")
        relay_error = [bool]($Text -match "voiceRelayError|Failed to stop voice relay")
        audit_loaded = [bool]($Text -match "VOIP_CALL_MODE_AUDIT_LOADED")
        audit_failed = [bool]($Text -match "VOIP_CALL_MODE_AUDIT_FAILED")
        audit_fetch_403 = [bool]($Text -match "audit fetch failed: HTTP 403|VOIP_CALL_MODE_AUDIT_FAILED.*403")
        incoming_suppressed = [bool]($Text -match "VOIP_INCOMING_CALL_SUPPRESSED_ACTIVE_SESSION")
        signaling_open = [bool]($Text -match "connectSignaling:open")
        connected = [bool]($Text -match "Connection state: connected|State change callback: connected")
        accept_api_ok = [bool]($Text -match "VOIP_INCOMING_ACCEPT_API_OK")
    }
}

function Grant-MicPermission([string]$Device) {
    Invoke-Adb $Device @("shell", "pm", "grant", $PackageName, "android.permission.RECORD_AUDIO") | Out-Null
}

Write-Step "Audit+Relay diag dir: $RunDir"
Write-Step "Backend restarted with callee audit fix — starting dual-device call"

Grant-MicPermission $CallerDevice
Grant-MicPermission $CalleeDevice
Launch-App $CallerDevice
Launch-App $CalleeDevice
Start-Sleep -Seconds 5

Write-Step "Waiting auth on both devices..."
if (-not (Wait-ForAuthReady $CallerDevice)) { throw "Caller auth timeout" }
if (-not (Wait-ForAuthReady $CalleeDevice)) { throw "Callee auth timeout" }

$null = Dismiss-StaleVoipCall $CallerDevice $RunDir
$null = Dismiss-StaleVoipCall $CalleeDevice $RunDir
Start-Sleep -Seconds 2

Clear-DeviceLog $CallerDevice
Clear-DeviceLog $CalleeDevice

Write-Step "Starting auto-call from caller..."
Open-VoipValidationAutoCall $CallerDevice
Start-Sleep -Seconds 6
$callOk = Wait-ForLogPattern $CallerDevice "VOIP_FRIEND_CALL_SUCCESS|VOIP_VALIDATION_AUTO_CALL_DEEPLINK|VOIP_START_CALL" 120 (Join-Path $RunDir "call_start.log")
if (-not $callOk) { throw "Caller did not start call" }

Write-Step "Waiting incoming on callee..."
if (-not (Wait-ForLogPattern $CalleeDevice "VOIP_INCOMING_CALL_RECEIVED|VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_RING" 120 (Join-Path $RunDir "incoming.log"))) {
    throw "Callee incoming timeout"
}

$tapped = $false
for ($i = 0; $i -lt 12; $i++) {
    if (Tap-UiLabel $CalleeDevice @("받기", "수신 보이스톡 받기", "Accept") (Join-Path $RunDir "accept.xml")) {
        $tapped = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $tapped) { throw "Accept tap failed" }

Write-Step "Waiting accept + signaling..."
$acceptOk = Wait-ForLogPattern $CalleeDevice "VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_CALL_ACCEPTED" 60
$signalingOk = Wait-ForLogPattern $CalleeDevice "connectSignaling:open" 60
Write-Step "Accept=$acceptOk Signaling=$signalingOk"

Write-Step "Connected hold ${ConnectedHoldSec}s..."
Start-Sleep -Seconds $ConnectedHoldSec

Write-Step "Scrolling callee to VoIPCallScreen audit section + refresh"
for ($s = 0; $s -lt 8; $s++) {
    Invoke-Adb $CalleeDevice @("shell", "input", "swipe", "400", "1700", "400", "300", "500") | Out-Null
    Start-Sleep -Milliseconds 600
}
$auditRefreshDump = Join-Path $RunDir "callee_audit_refresh_tap.xml"
$auditTapped = Tap-ByResourceId $CalleeDevice "worldlinco-voip-audit-refresh" $auditRefreshDump
if (-not $auditTapped) {
    Tap-UiLabel $CalleeDevice @("새로고침", "통화 모드 감사 로그") (Join-Path $RunDir "callee_audit_refresh_label.xml") | Out-Null
}
$auditLoadedOk = Wait-ForLogPattern $CalleeDevice "VOIP_CALL_MODE_AUDIT_LOADED" 15 (Join-Path $RunDir "callee_audit_loaded.log")
Start-Sleep -Seconds 2
$auditDumpAfter = Join-Path $RunDir "callee_audit_after_refresh.xml"
Get-UiDump $CalleeDevice $auditDumpAfter | Out-Null
$auditUi = Analyze-AuditUi $auditDumpAfter

Write-Step "Audit logcat loaded=$auditLoadedOk initiated=$($auditUi.has_call_initiated) accepted=$($auditUi.has_call_accepted) 403=$($auditUi.has_audit_error_403)"

Write-Step "Mic relay window ${MicHoldSec}s — speak 2-3s on S10 microphone now"
Clear-DeviceLog $CalleeDevice
Start-Sleep -Seconds $MicHoldSec

$calleeRelayLog = Join-Path $RunDir "callee_relay_probe.log"
$calleeText = (Invoke-Adb $CalleeDevice @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*")) -join "`n"
$calleeText | Out-File $calleeRelayLog -Encoding utf8
$callerText = Get-LogcatText $CallerDevice
$relayCallee = Analyze-RelayLog $calleeText
$relayCaller = Analyze-RelayLog $callerText

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    accept_ok = $acceptOk
    signaling_ok = $signalingOk
    audit_logcat_loaded = $auditLoadedOk
    audit_ui = $auditUi
    callee_relay = $relayCallee
    caller_relay = $relayCaller
}
$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

$report = @"
# Audit + Relay Diagnosis $Stamp

## Backend
- ``devanalysis114-backend`` restarted with callee audit ACL fix

## Call flow
- Accept API: ``$acceptOk``
- Signaling open (callee): ``$signalingOk``

## S10 audit (after 새로고침)
- logcat VOIP_CALL_MODE_AUDIT_LOADED: ``$auditLoadedOk``
- call_initiated visible: ``$($auditUi.has_call_initiated)``
- call_accepted visible: ``$($auditUi.has_call_accepted)``
- HTTP 403 error text: ``$($auditUi.has_audit_error_403)``

## Callee relay logcat (${MicHoldSec}s mic window on S10)
- VOIP_VOICE_RELAY_SENT: ``$($relayCallee.relay_sent)``
- relay + utterance_id: ``$($relayCallee.relay_sent_meta)``
- VOIP_VOICE_TRANSLATE_REQUEST: ``$($relayCallee.translate_request)``
- VOIP_VOICE_TRANSLATE_RESULT: ``$($relayCallee.translate_result)``
- VOIP_VOICE_RELAY_START_BLOCKED: ``$($relayCallee.relay_start_blocked)``
- VOIP_CALL_MODE_AUDIT_LOADED: ``$($relayCallee.audit_loaded)``
- VOIP_INCOMING_CALL_SUPPRESSED_ACTIVE_SESSION: ``$($relayCallee.incoming_suppressed)``

## Caller relay logcat (same window)
- VOIP_VOICE_RELAY_SENT: ``$($relayCaller.relay_sent)``
- VOIP_VOICE_TRANSLATE_REQUEST: ``$($relayCaller.translate_request)``

## Verdict
- Audit fix on S10: $(if ($auditLoadedOk -and -not $auditUi.has_audit_error_403) { 'PASS' } else { 'FAIL / INCONCLUSIVE' })
- Relay on callee speech probe: $(if ($relayCallee.relay_sent) { 'PASS' } else { 'FAIL' })
"@
$report | Out-File (Join-Path $RunDir "DIAG_REPORT.md") -Encoding utf8
Write-Step "Report: $(Join-Path $RunDir 'DIAG_REPORT.md')"
Write-Step "Audit pass: $auditLoadedOk | Relay pass: $($relayCallee.relay_sent)"

if (-not ($auditLoadedOk -and -not $auditUi.has_audit_error_403)) { exit 4 }
if (-not $relayCallee.relay_sent) { exit 5 }
exit 0
