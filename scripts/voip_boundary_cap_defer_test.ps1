#!/usr/bin/env pwsh
# Build 64+: reproduce Silero defer gates + verify 14s safety cap (not 12s max_duration)
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$CalleeVoiceId = "nado-000001",
    [int]$DeferWindowSec = 40,
    [int]$CapWindowSec = 90,
    [switch]$SkipCallSetup,
    [switch]$SkipProbeAudio,
    [switch]$ForceFreshCall,
    [switch]$DeferOnly,
    [switch]$CapOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AppJson = Get-Content (Join-Path $RepoRoot "apps\mobile-nadotongryoksa\app.json") -Raw | ConvertFrom-Json
$RunDir = Join-Path $RepoRoot "evidence\voip-voice-relay-orchestrator\cap_defer_test_$(Get-Date -Format 'yyyyMMdd-HHmmss')"
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

function Get-LogcatLines([string]$Device, [int]$Tail = 400) {
    $lines = @(Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*"))
    if ($lines.Count -le $Tail) { return ($lines -join "`n") }
    return ($lines[($lines.Count - $Tail)..($lines.Count - 1)] -join "`n")
}

function Get-LogcatText([string]$Device) {
    return Get-LogcatLines -Device $Device -Tail 2000
}

function Test-CallConnected {
    param([int]$Tail = 400)
    $pattern = 'Connection state: connected|VOIP_CONNECTION_STATE_CONNECTED|connection_state":"connected"|connectionState":"connected"'
    $tabText = Get-LogcatLines $CallerDevice $Tail
    $s10Text = Get-LogcatLines $CalleeDevice $Tail
    $tab = $tabText -match $pattern
    $s10 = $s10Text -match $pattern
    # Stale "connected" in old buffer while app shows no active call.
    if ($tabText -match '"has_active_call":false' -and $tabText -notmatch '"has_active_call":true') { $tab = $false }
    if ($s10Text -match '"has_active_call":false' -and $s10Text -notmatch '"has_active_call":true') { $s10 = $false }
    return [bool]($tab -and $s10)
}

function Ensure-AppsForeground {
    foreach ($dev in @($CallerDevice, $CalleeDevice)) {
        Invoke-Adb $dev @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
        Invoke-Adb $dev @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    }
    Start-Sleep -Seconds 2
}

function Ensure-VoiceRelayReady {
    param([int]$TimeoutSec = 35)
    Ensure-AppsForeground
    if (Wait-ForRelaySegment $CalleeDevice $TimeoutSec) {
        Write-Step "S10 voice relay segment ready"
        return $true
    }
    Write-Step "WARN: relay segment not started within ${TimeoutSec}s"
    return $false
}

function Invoke-CallSetup {
    Write-Step "Running voip_manual_call_setup (Tab -> S10)"
    $setupScript = Join-Path $RepoRoot "scripts\voip_manual_call_setup.ps1"
    & $setupScript -CallerDevice $CallerDevice -CalleeDevice $CalleeDevice -CalleeVoiceId $CalleeVoiceId -MonitorSec 1
    Start-Sleep -Seconds 2
    if (Test-CallConnected) {
        Write-Step "Call connected after setup"
        return $true
    }
    Write-Step "WARN: call setup script exit=$LASTEXITCODE and connection not confirmed"
    return $false
}

function Ensure-ConnectedCall {
    if ((Test-CallConnected) -and -not $ForceFreshCall) {
        Write-Step "Call already connected (recent logcat)"
        return
    }
    if ($SkipCallSetup) {
        throw "No connected call on both devices. Re-run without -SkipCallSetup or place call manually first."
    }
    if ($ForceFreshCall) {
        Write-Step "Force-stop apps before call setup"
        foreach ($dev in @($CallerDevice, $CalleeDevice)) {
            Invoke-Adb $dev @("shell", "am", "force-stop", $PackageName) | Out-Null
        }
        Start-Sleep -Seconds 2
    }
    if (-not (Invoke-CallSetup)) {
        throw "Could not establish Tab+S10 connected call"
    }
}

function Ensure-ProbeWav {
    param([string]$OutPath, [double]$DurationSec, [int]$Frequency = 880)
    if (Test-Path $OutPath) { return $OutPath }
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $ffmpeg) { throw "ffmpeg required for probe audio" }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & ffmpeg -y -f lavfi -i "sine=frequency=${Frequency}:duration=$DurationSec" -af "volume=32dB" -ar 44100 -ac 1 $OutPath 2>$null | Out-Null
    } finally {
        $ErrorActionPreference = $prev
    }
    if (-not (Test-Path $OutPath)) { throw "Failed to generate probe wav at $OutPath" }
    return $OutPath
}

function Play-ProbeWav {
    param([string]$Device, [string]$LocalWavPath, [string]$RemoteName, [switch]$ReturnToApp)
    $remote = "/sdcard/Download/$RemoteName"
    Invoke-Adb $Device @("push", $LocalWavPath, $remote) | Out-Null
    for ($v = 0; $v -lt 5; $v++) {
        Invoke-Adb $Device @("shell", "input", "keyevent", "KEYCODE_VOLUME_UP") | Out-Null
    }
    Invoke-Adb $Device @(
        "shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", "file://$remote", "-t", "audio/wav"
    ) | Out-Null
    if ($ReturnToApp) {
        Start-Sleep -Milliseconds 400
        Invoke-Adb $Device @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
    }
}

function Wait-ForRelaySegment([string]$Device, [int]$TimeoutSec = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-LogcatText $Device) -match 'VOIP_VOICE_RELAY_SEGMENT_STARTED') { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-ForLogPattern {
    param([string]$Device, [string]$Pattern, [int]$TimeoutSec = 45)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-LogcatText $Device) -match $Pattern) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Run-DeferProbeBursts {
    param([string]$Device, [int]$WindowSec)
    $shortWav = Ensure-ProbeWav -OutPath (Join-Path $RunDir "defer_short_0.35s.wav") -DurationSec 0.35
    $mediumWav = Ensure-ProbeWav -OutPath (Join-Path $RunDir "defer_medium_5s.wav") -DurationSec 5
    Write-Step "Defer: 5s probe -> wait silence flush -> 0.35s burst within cooldown"
    Play-ProbeWav -Device $Device -LocalWavPath $mediumWav -RemoteName "voip_defer_medium.wav" -ReturnToApp
    if (Wait-ForLogPattern $Device "SEGMENT_FLUSH.*reason.:.(silence|max_duration)" 20) {
        Start-Sleep -Milliseconds 600
        Play-ProbeWav -Device $Device -LocalWavPath $shortWav -RemoteName "voip_defer_short.wav" -ReturnToApp
        Start-Sleep -Seconds 2
    } else {
        Write-Step "WARN: no flush observed after medium probe"
    }
    $deadline = (Get-Date).AddSeconds($WindowSec)
    $burst = 0
    while ((Get-Date) -lt $deadline) {
        $burst++
        Write-Step "Defer short burst #$burst"
        Play-ProbeWav -Device $Device -LocalWavPath $shortWav -RemoteName "voip_defer_short.wav" -ReturnToApp
        Start-Sleep -Seconds 8
    }
}

function Run-CapProbeContinuous {
    param([string]$Device, [int]$WindowSec)
    $longWav = Ensure-ProbeWav -OutPath (Join-Path $RunDir "cap_long_22s.wav") -DurationSec 22
    Write-Step "Cap phase: loop 22s probe on S10 until ${WindowSec}s (need max_duration >= 14s)"
    $deadline = (Get-Date).AddSeconds($WindowSec)
    $loop = 0
    while ((Get-Date) -lt $deadline) {
        $loop++
        Write-Step "Cap probe loop #$loop"
        Play-ProbeWav -Device $Device -LocalWavPath $longWav -RemoteName "voip_cap_long.wav" -ReturnToApp
        if (Wait-ForLogPattern $Device 'SEGMENT_FLUSH[^`]*"reason":"max_duration"' 8) {
            Write-Step "max_duration observed during cap probe"
            break
        }
        Start-Sleep -Seconds 2
    }
}

function Parse-ProbeTimestamp([string]$Value) {
    if (-not $Value) { return $null }
    try { return [DateTimeOffset]::Parse($Value).UtcDateTime } catch { }
    try { return [datetime]::Parse($Value) } catch { }
    return $null
}

function Analyze-Boundary([string]$Text, [string]$Label) {
    $deferReasons = [regex]::Matches($Text, '"defer_reason":"([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
    $flushFalse = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END.*?"flush":false')).Count
    $flushTrue = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SILERO_SPEECH_END.*?"flush":true')).Count
    $maxDurMs = @()
    $segStarts = [regex]::Matches($Text, 'VOIP_VOICE_RELAY_SEGMENT_STARTED.*?"timestamp":"([^"]+)"')
    $maxFlushes = [regex]::Matches($Text, 'VOIP_VOICE_RELAY_SEGMENT_FLUSH.*?"reason":"max_duration".*?"timestamp":"([^"]+)"')
    $segIdx = 0
    $segStartTimes = @()
    foreach ($m in $segStarts) {
        $parsed = Parse-ProbeTimestamp $m.Groups[1].Value
        if ($parsed) { $segStartTimes += $parsed }
    }
    foreach ($mf in $maxFlushes) {
        $flushTime = Parse-ProbeTimestamp $mf.Groups[1].Value
        if (-not $flushTime) { continue }
        while ($segIdx -lt ($segStartTimes.Count - 1) -and $segStartTimes[$segIdx + 1] -le $flushTime) {
            $segIdx++
        }
        if ($segStartTimes.Count -gt $segIdx) {
            $elapsed = [int]($flushTime - $segStartTimes[$segIdx]).TotalMilliseconds
            if ($elapsed -ge 0) { $maxDurMs += $elapsed }
        }
    }
    return [pscustomobject]@{
        device = $Label
        silero_end = ([regex]::Matches($Text, 'SILERO_SPEECH_END')).Count
        flush_true = $flushTrue
        flush_false = $flushFalse
        defer_reasons = ($deferReasons | Where-Object { $_ -and $_ -ne 'null' } | Group-Object | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ', '
        max_duration_count = $maxFlushes.Count
        max_duration_elapsed_ms = ($maxDurMs -join ', ')
        fixed_interval = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SEGMENT_FLUSH.*?"reason":"fixed_interval"')).Count
        relay_sent = ([regex]::Matches($Text, 'VOIP_VOICE_RELAY_SENT')).Count
    }
}

function Test-DeferReproduced {
    param([object[]]$Analyses)
    foreach ($a in $Analyses) {
        if ($a.flush_false -gt 0) { return $true }
        if ($a.defer_reasons -and $a.defer_reasons.Length -gt 0) { return $true }
    }
    return $false
}

function Write-DeferPhaseSummary {
    param([object]$S10, [object]$Tab)
    Write-Step "S10 defer: flush_false=$($S10.flush_false) silero_end=$($S10.silero_end) defer=$($S10.defer_reasons)"
    Write-Step "Tab defer: flush_false=$($Tab.flush_false) silero_end=$($Tab.silero_end) defer=$($Tab.defer_reasons)"
}

Write-Step "Cap/defer test dir: $RunDir"
Write-Step "Expected build $($AppJson.expo.version) code $($AppJson.expo.android.versionCode)"
if ($DeferOnly -and $CapOnly) { throw "Use either -DeferOnly or -CapOnly, not both" }
Ensure-ConnectedCall
$relayReady = Ensure-VoiceRelayReady -TimeoutSec 35
if (-not $relayReady) {
    Write-Step "WARN: continuing without confirmed relay segment — results may be empty"
}

if (-not $CapOnly) {
Write-Step "=== Phase A (${DeferWindowSec}s): Tab/S10 짧은 1~2음절 2~3회 (defer 유도) ==="
if ($SkipProbeAudio) {
    Write-Step ">>> Tab: 영어 0.5초 ('hi') 2~3회 권장 / S10: defer 어려움 (span 2.4s+) <<<"
}
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
if ($SkipProbeAudio) {
    Start-Sleep -Seconds $DeferWindowSec
} else {
    Run-DeferProbeBursts -Device $CalleeDevice -WindowSec $DeferWindowSec
}
$deferLogS10 = Get-LogcatText $CalleeDevice
$deferLogTab = Get-LogcatText $CallerDevice
$deferLogS10 | Out-File (Join-Path $RunDir "s10_defer_phase.log") -Encoding utf8
$deferLogTab | Out-File (Join-Path $RunDir "tab_defer_phase.log") -Encoding utf8
$deferS10 = Analyze-Boundary $deferLogS10 "S10-defer"
$deferTab = Analyze-Boundary $deferLogTab "Tab-defer"
$deferPass = Test-DeferReproduced @($deferS10, $deferTab)

if ($DeferOnly) {
    $summary = [pscustomobject]@{
        timestamp = (Get-Date).ToString("o")
        run_dir = $RunDir
        version = [string]$AppJson.expo.version
        version_code = [int]$AppJson.expo.android.versionCode
        mode = "defer_only"
        defer_phase_sec = $DeferWindowSec
        defer_phase_s10 = $deferS10
        defer_phase_tab = $deferTab
        defer_repro_pass = [bool]$deferPass
    }
    $summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8
    Write-DeferPhaseSummary -S10 $deferS10 -Tab $deferTab
    Write-Step "Defer combined PASS=$deferPass"
    Write-Step "Artifacts: $RunDir"
    if (-not $deferPass) { exit 2 }
    exit 0
}
}

if ($CapOnly) {
    Write-Step "=== Cap only (${CapWindowSec}s): S10 15초+ 연속 발화 (14s cap 확인) ==="
} else {
Write-Step "=== Phase B (${CapWindowSec}s): S10 15초+ 연속 발화 (14s cap 확인) ==="
}
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
$useCapProbe = -not $CapManualSpeech
if ($CapManualSpeech) {
    Write-Step ">>> Cap manual: S10에서 15초+ 연속 발화 <<<"
    Start-Sleep -Seconds $CapWindowSec
} elseif ($useCapProbe) {
    Run-CapProbeContinuous -Device $CalleeDevice -WindowSec $CapWindowSec
} else {
    Start-Sleep -Seconds $CapWindowSec
}
$capLog = Get-LogcatText $CalleeDevice
$capLog | Out-File (Join-Path $RunDir "s10_cap_phase.log") -Encoding utf8
$capA = Analyze-Boundary $capLog "S10-cap"

$capPass = $false
if ($capA.max_duration_elapsed_ms) {
    foreach ($part in ($capA.max_duration_elapsed_ms -split ',\s*')) {
        if ($part -and [int]$part -ge 13500) { $capPass = $true; break }
    }
}
if (-not $CapOnly -and -not $capPass -and $deferS10.max_duration_elapsed_ms) {
    foreach ($part in ($deferS10.max_duration_elapsed_ms -split ',\s*')) {
        if ($part -and [int]$part -ge 13500) { $capPass = $true; break }
    }
}
if (-not $capPass -and $capA.max_duration_count -eq 0 -and $capA.relay_sent -gt 0) {
    Write-Step "WARN: no max_duration in cap window — utterance may have ended via silence before 14s"
}

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    version = [string]$AppJson.expo.version
    version_code = [int]$AppJson.expo.android.versionCode
    safety_cap_ms = 14000
    mode = if ($CapOnly) { "cap_only" } else { "cap_defer" }
    defer_phase_sec = if ($CapOnly) { 0 } else { $DeferWindowSec }
    cap_phase_sec = $CapWindowSec
    defer_phase_s10 = if ($CapOnly) { $null } else { $deferS10 }
    defer_phase_tab = if ($CapOnly) { $null } else { $deferTab }
    cap_phase = $capA
    defer_repro_pass = if ($CapOnly) { $null } else { [bool](Test-DeferReproduced @($deferS10, $deferTab)) }
    cap_14s_pass = [bool]$capPass
}
$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8

if (-not $CapOnly) {
    Write-DeferPhaseSummary -S10 $deferS10 -Tab $deferTab
    $deferPass = Test-DeferReproduced @($deferS10, $deferTab)
    Write-Step "Defer combined PASS=$deferPass"
}
Write-Step "Cap phase: max_duration=$($capA.max_duration_count) elapsed_ms=$($capA.max_duration_elapsed_ms) PASS=$capPass"
Write-Step "Artifacts: $RunDir"

if (-not $CapOnly -and -not $deferPass) { exit 2 }
if (-not $capPass) { exit 3 }
exit 0
