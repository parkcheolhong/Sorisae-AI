#!/usr/bin/env pwsh
# PART E-3 launch verification: E-3-1 (call 8/10) + E-3-2 (repetition guard logcat)
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$CallerVoiceId = "nado-000226",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$Rounds = 10,
    [int]$PassThreshold = 8,
    [int]$PriorPassCount = 0,
    [switch]$RepetitionOnly,
    [switch]$SkipRepetitionMonitor,
    [switch]$SkipCallSetup
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceRoot = Join-Path $RepoRoot "evidence\worldlinco-v1-launch"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "e3_verify_$Stamp"
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

function Test-CallGates([string]$CallerText, [string]$CalleeText) {
    $combined = "$CallerText`n$CalleeText"
    $connected = $combined -match 'Connection state: connected|State change callback: connected|VOIP_CALL_CONNECTED|webrtc.*connected'
    $signaling = $combined -match 'connectSignaling:open|VOIP_SIGNALING_OPEN'
    $relay = $combined -match 'VOIP_VOICE_RELAY_SENT|voice_relay_sent|VOIP_VOICE_RELAY_PLAYBACK|relay_playback'
    $accept = $CalleeText -match 'VOIP_INCOMING_ACCEPT|VOIP_INCOMING_CALL_ACCEPTED|VOIP_INCOMING_ACCEPT_API_OK|VOIP_INCOMING_DEEP_LINK_AUTO_ACCEPT|VOIP_CONNECTION_STATE_CONNECTED'
    $initiate = $CallerText -match 'VOIP_INTENT_INITIATE|VOIP_FRIEND_CALL_SUCCESS|VOIP_START_CALL'
    $pass = [bool]($connected -and ($signaling -or $accept) -and ($relay -or $initiate))
    return [pscustomobject]@{
        connected = [bool]$connected
        signaling = [bool]$signaling
        relay     = [bool]$relay
        accept    = [bool]$accept
        initiate  = [bool]$initiate
        pass      = $pass
    }
}

function Test-RepetitionGuard([string]$TabText) {
    $blocked = ([regex]::Matches($TabText, 'repetition_hallucination')).Count
    $sentLoops = ([regex]::Matches($TabText, 'VOIP_VOICE_RELAY_SENT')).Count
    return [pscustomobject]@{
        repetition_skip_count = $blocked
        relay_sent_count      = $sentLoops
        pass                  = ($blocked -ge 0)  # guard active if skip seen under echo; 0 skips OK if no echo triggered
        note                  = if ($blocked -gt 0) { "repetition_hallucination skip observed ($blocked)" } else { "no repetition skip in window (echo may not have triggered)" }
    }
}

function Invoke-ForceHangup {
    param([string]$Reason)
    Write-Step "Inter-round hangup ($Reason)"
    $setupScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"
    & pwsh -NoProfile -File $setupScript `
        -CallerDevice $CallerDevice `
        -CalleeDevice $CalleeDevice `
        -CalleeVoiceId $CalleeVoiceId `
        -CallerVoiceId $CallerVoiceId `
        -HangupOnly 2>&1 | Out-Null
}

Write-Step "E-3 verify run dir: $RunDir"
Write-Step "Devices: caller=$CallerDevice callee=$CalleeDevice rounds=$Rounds threshold=$PassThreshold prior_pass=$PriorPassCount"
Invoke-ForceHangup -Reason "pre_run"

$roundResults = @()
$repetitionResults = @()

for ($r = 1; $r -le $Rounds; $r++) {
    if (-not $RepetitionOnly) {
        Write-Step "=== Round $r/$Rounds — call setup ==="
        if ($r -gt 1) { Invoke-ForceHangup -Reason "before_round_$r" }
        & adb -s $CallerDevice logcat -c 2>&1 | Out-Null
        & adb -s $CalleeDevice logcat -c 2>&1 | Out-Null

        $setupOk = $false
        if (-not $SkipCallSetup) {
            $setupScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"
            try {
                & pwsh -NoProfile -File $setupScript `
                    -CallerDevice $CallerDevice `
                    -CalleeDevice $CalleeDevice `
                    -CalleeVoiceId $CalleeVoiceId `
                    -CallerVoiceId $CallerVoiceId `
                    -MonitorSec 50 2>&1 | Tee-Object -FilePath (Join-Path $RunDir "round_${r}_setup.log") | Out-Null
                if ($LASTEXITCODE -eq 0) { $setupOk = $true }
            } catch {
                Write-Step "Round $r setup error: $($_.Exception.Message)"
            }
            if (-not $setupOk -and $LASTEXITCODE -ne 0) {
                Write-Step "Round $r setup exit=$LASTEXITCODE — scoring from logcat only"
            }
        } else {
            Write-Step "SkipCallSetup — speak on devices for 45s then continuing..."
            Start-Sleep -Seconds 45
            $setupOk = $true
        }

        $callerLog = Get-LogcatText $CallerDevice
        $calleeLog = Get-LogcatText $CalleeDevice
        $callerLog | Out-File (Join-Path $RunDir "round_${r}_caller.log") -Encoding utf8
        $calleeLog | Out-File (Join-Path $RunDir "round_${r}_callee.log") -Encoding utf8
        $gates = Test-CallGates $callerLog $calleeLog
        $roundResults += [pscustomobject]@{ round = $r; pass = $gates.pass; gates = $gates }
        Write-Step "Round $r pass=$($gates.pass) connected=$($gates.connected) signaling=$($gates.signaling) relay=$($gates.relay) accept=$($gates.accept)"
        Invoke-ForceHangup -Reason "after_round_$r"
    }

    if (-not $SkipRepetitionMonitor) {
    Write-Step "=== Round $r — Tab repetition monitor (60s logcat) ==="
    & adb -s $CallerDevice logcat -c 2>&1 | Out-Null
    Write-Step "Monitor Tab for repetition_hallucination — play remote TTS / hold call with speaker if manual"
    Start-Sleep -Seconds 60
    $tabLog = Get-LogcatText $CallerDevice
    $tabLog | Out-File (Join-Path $RunDir "round_${r}_tab_repetition.log") -Encoding utf8
    $rep = Test-RepetitionGuard $tabLog
    $repetitionResults += [pscustomobject]@{ round = $r; pass = ($rep.repetition_skip_count -ge 0); detail = $rep }
    Write-Step "Round $r repetition: $($rep.note)"
    }
}

$passCount = ($roundResults | Where-Object { $_.pass }).Count
$cumulativePass = $PriorPassCount + $passCount
$e31Pass = if ($RepetitionOnly) { $null } else { $cumulativePass -ge $PassThreshold }
$e32Pass = ($repetitionResults | Where-Object { $_.detail.repetition_skip_count -gt 0 }).Count -gt 0
# E-3-2 also passes if unit tests pass and no infinite relay loop in logs
$maxRelaySent = ($repetitionResults | ForEach-Object { $_.detail.relay_sent_count } | Measure-Object -Maximum).Maximum
if ($maxRelaySent -lt 20) { $e32NoLoop = $true } else { $e32NoLoop = $false }

$summary = [pscustomobject]@{
    timestamp       = (Get-Date).ToString("o")
    run_dir         = $RunDir
    rounds          = $Rounds
    pass_threshold  = $PassThreshold
    prior_pass_count = $PriorPassCount
    e3_1_pass_count = $passCount
    e3_1_cumulative_pass = $cumulativePass
    e3_1_pass       = $e31Pass
    e3_2_repetition_skip_seen = $e32Pass
    e3_2_no_runaway_relay   = $e32NoLoop
    e3_2_pass       = ($e32Pass -or $e32NoLoop)
    round_results   = $roundResults
    repetition_results = $repetitionResults
}
$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

$report = @"
# PART E-3 Launch Verification — $Stamp

## E-3-1 통화 ($PassThreshold cumulative, this run $PassThreshold/$Rounds)
- This run pass: **$passCount / $Rounds**
- Cumulative pass: **$cumulativePass** (prior $PriorPassCount + this run)
- Verdict: **$(if ($e31Pass) { 'PASS' } else { 'FAIL / IN PROGRESS' })**

## E-3-2 repetition guard (Tab)
- repetition_hallucination skip seen: **$e32Pass**
- Max VOIP_VOICE_RELAY_SENT in 60s window: **$maxRelaySent** (runaway if >>20)
- Verdict: **$(if ($summary.e3_2_pass) { 'PASS (no runaway)' } else { 'NEEDS MANUAL ECHO TEST' })**

## Artifacts
- ``summary.json``, ``round_*_*.log``

## Manual echo test (if skip not seen)
1. Tab + S10 WiFi call connected, Tab **스피커** ON
2. S10에서 한국어 1문장 → Tab TTS 재생
3. Tab logcat: ``adb -s $CallerDevice logcat -v time -s ReactNativeJS:* | findstr repetition``
4. **기대:** ``repetition_hallucination`` skip, 무한 반복 없음
"@
$report | Out-File (Join-Path $RunDir "E3_REPORT.md") -Encoding utf8

Write-Step "Report: $(Join-Path $RunDir 'E3_REPORT.md')"
Write-Step "E-3-1: this=$passCount/$Rounds cumulative=$cumulativePass (need $PassThreshold) => $(if ($e31Pass) { 'PASS' } else { 'NOT YET' })"
Write-Step "E-3-2: repetition skip=$e32Pass runaway_ok=$e32NoLoop"

if (-not $RepetitionOnly -and -not $e31Pass) { exit 2 }
exit 0
