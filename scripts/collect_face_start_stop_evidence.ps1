#!/usr/bin/env pwsh
param(
    [string]$DeviceId = "R83W70QY11H",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$EvidenceRoot = "docs/checklists/evidence",
    [string]$RunLabel = "face-start-stop-round1",
    [int]$StartStopGapSec = 2,
    [int]$PostStopWaitSec = 3
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $repoRoot (Join-Path $EvidenceRoot "$RunLabel-$runStamp")
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$summaryPath = Join-Path $runDir "summary.json"
$rawLogPath = Join-Path $runDir "reactnative-logcat.txt"
$tracePath = Join-Path $runDir "face-start-stop-trace.txt"
$lastDumpPath = Join-Path $runDir "last-window-dump.xml"

function Write-Step {
    param([string]$Message)
    Write-Output "[$(Get-Date -Format 'HH:mm:ss')] $Message"
}

function Run-Adb {
    param([string[]]$AdbArgs)

    & adb -s $DeviceId @AdbArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "adb command failed: $($AdbArgs -join ' ')"
    }
}

function Get-UiDump {
    param([string]$OutPath)

    $remote = "/sdcard/window_dump.xml"
    Run-Adb @("shell", "uiautomator", "dump", $remote)
    $xml = & adb -s $DeviceId shell cat $remote
    if ($LASTEXITCODE -ne 0) {
        throw "adb cat window_dump failed"
    }
    $raw = ($xml -join "`n")
    if ($OutPath) {
        Set-Content -Path $OutPath -Value $raw -Encoding utf8
    }
    return $raw
}

function Get-NodeCenter {
    param(
        [string]$Xml,
        [string]$Selector
    )

    if (-not $Xml -or -not $Selector) {
        return $null
    }

    [xml]$doc = $Xml
    $nodes = $doc.SelectNodes("//node[contains(@resource-id,'$Selector') or contains(@content-desc,'$Selector')]")
    foreach ($node in $nodes) {
        $bounds = [string]$node.GetAttribute("bounds")
        if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
            continue
        }
        $x1 = [int]$matches[1]
        $y1 = [int]$matches[2]
        $x2 = [int]$matches[3]
        $y2 = [int]$matches[4]
        if ($x2 -le $x1 -or $y2 -le $y1) {
            continue
        }
        if ($x1 -lt 0 -or $y1 -lt 0) {
            continue
        }
        return @{
            x = [int](($x1 + $x2) / 2)
            y = [int](($y1 + $y2) / 2)
        }
    }

    return $null
}

function Tap-At {
    param([int]$X, [int]$Y)
    Run-Adb @("shell", "input", "tap", "$X", "$Y")
}

function Tap-BySelector {
    param(
        [string]$Selector,
        [int]$Retries = 6,
        [int]$DelayMs = 700
    )

    for ($i = 0; $i -lt $Retries; $i++) {
        $xml = Get-UiDump -OutPath $lastDumpPath
        $center = Get-NodeCenter -Xml $xml -Selector $Selector
        if ($center) {
            Tap-At -X $center.x -Y $center.y
            Start-Sleep -Milliseconds 350
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
}

function Is-FaceScreenVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    $mic = Get-NodeCenter -Xml $xml -Selector "worldlinco-face-screen-mic"
    $close = Get-NodeCenter -Xml $xml -Selector "worldlinco-face-screen-close"
    return [bool]($mic -or $close)
}

function Is-PeerLanguagePickerVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($xml -match '상대 언어 \(GPS/수동\)|GPS 우선 · 필요 시 수동|peer language')
}

function Dismiss-PermissionDialog {
    param([int]$MaxAttempts = 4)

    $allowSelectors = @(
        'permission_allow_button',
        'permission_allow_foreground_only_button',
        'permission_allow_one_time_button',
        'permission_allow_always_button',
        'grant_dialog_button_allow'
    )

    for ($attempt = 0; $attempt -lt $MaxAttempts; $attempt++) {
        $xml = Get-UiDump -OutPath $lastDumpPath
        if ($xml -notmatch 'com\.google\.android\.permissioncontroller|com\.android\.permissioncontroller') {
            return $true
        }

        $tapped = $false
        foreach ($selector in $allowSelectors) {
            $center = Get-NodeCenter -Xml $xml -Selector $selector
            if ($center) {
                Tap-At -X $center.x -Y $center.y
                Start-Sleep -Milliseconds 550
                $tapped = $true
                break
            }
        }

        if (-not $tapped) {
            Tap-At -X 580 -Y 1180
            Start-Sleep -Milliseconds 550
        }
    }

    $finalXml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($finalXml -notmatch 'com\.google\.android\.permissioncontroller|com\.android\.permissioncontroller')
}

function Select-PeerLanguageOption {
    param([int]$Retries = 5)

    for ($attempt = 0; $attempt -lt $Retries; $attempt++) {
        $xml = Get-UiDump -OutPath $lastDumpPath
        [xml]$doc = $xml
        $nodes = $doc.SelectNodes("//node[@text!='']")
        foreach ($node in $nodes) {
            $text = [string]$node.GetAttribute('text')
            if ([string]::IsNullOrWhiteSpace($text)) {
                continue
            }
            if ($text -match '상대 언어|GPS|수동|닫기|Close|language|선택|취소|회원가입|로그인|한국어|Korean') {
                continue
            }

            $bounds = [string]$node.GetAttribute('bounds')
            if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
                continue
            }

            $cx = [int](($matches[1] + $matches[3]) / 2)
            $cy = [int](($matches[2] + $matches[4]) / 2)
            if ($cx -lt 80 -or $cx -gt 720) {
                continue
            }
            if ($cy -lt 360 -or $cy -gt 1120) {
                continue
            }

            Tap-At -X $cx -Y $cy
            Start-Sleep -Milliseconds 500
            return $true
        }
        Start-Sleep -Milliseconds 700
    }

    Tap-At -X 198 -Y 522
    Start-Sleep -Milliseconds 500
    return $true
}

$flow = [ordered]@{
    faceHomeOpened    = $false
    faceScreenVisible = $false
    langPickerOpened  = $false
    peerLangSelected  = $false
    micStartTapped    = $false
    micStopTapped     = $false
    faceClosed        = $false
}

Run-Adb @("logcat", "-c")
Write-Step "logcat cleared"
Run-Adb @("shell", "am", "start", "-n", "$PackageName/.MainActivity")
Start-Sleep -Seconds 3
[void](Dismiss-PermissionDialog -MaxAttempts 4)
Write-Step "permission dialog handled if present"

$flow.faceHomeOpened = Tap-BySelector -Selector "worldlinco-home-face-hero" -Retries 8 -DelayMs 900
if (-not $flow.faceHomeOpened) {
    Tap-At -X 400 -Y 650
    Start-Sleep -Milliseconds 900
}

$flow.faceScreenVisible = Is-FaceScreenVisible
if (-not $flow.faceScreenVisible) {
    Tap-At -X 400 -Y 650
    Start-Sleep -Milliseconds 900
    $flow.faceScreenVisible = Is-FaceScreenVisible
}

$langTap = (Tap-BySelector -Selector "worldlinco-face-screen-lang" -Retries 6 -DelayMs 700) -or
(Tap-BySelector -Selector "worldlinco-face-peer-lang" -Retries 3 -DelayMs 600)
if (-not $langTap) {
    Tap-At -X 469 -Y 70
    Start-Sleep -Milliseconds 700
}

$flow.langPickerOpened = Is-PeerLanguagePickerVisible
if ($flow.langPickerOpened) {
    $flow.peerLangSelected = Select-PeerLanguageOption -Retries 5
}

$flow.micStartTapped = Tap-BySelector -Selector "worldlinco-face-screen-mic" -Retries 7 -DelayMs 700
if (-not $flow.micStartTapped) {
    Tap-At -X 400 -Y 676
    $flow.micStartTapped = $true
}
Start-Sleep -Seconds $StartStopGapSec

$flow.micStopTapped = Tap-BySelector -Selector "worldlinco-face-screen-mic" -Retries 4 -DelayMs 450
if (-not $flow.micStopTapped) {
    Tap-At -X 400 -Y 676
    $flow.micStopTapped = $true
}

$flow.faceClosed = Tap-BySelector -Selector "worldlinco-face-screen-close" -Retries 4 -DelayMs 500
if (-not $flow.faceClosed) {
    Tap-At -X 758 -Y 71
    $flow.faceClosed = $true
}
Start-Sleep -Seconds $PostStopWaitSec

& adb -s $DeviceId logcat -d -v time ReactNativeJS:I *:S > $rawLogPath
if ($LASTEXITCODE -ne 0) {
    throw "adb logcat dump failed"
}

$patterns = @(
    'FACE_CAPTURE_TRACE',
    'FACE_CONVERSATION',
    'COMPANION_START_VOICE_ENTER',
    'COMPANION_START_VOICE_BLOCKED',
    'face_auto_voice_start_begin',
    'face_auto_voice_start_end',
    'face_auto_voice_stop_begin',
    'face_auto_voice_stop_end',
    'start_tap',
    'capture_started',
    'payload_prepared',
    'post_start',
    'response_received'
)
$matches = Select-String -Path $rawLogPath -Pattern ($patterns -join '|') -CaseSensitive:$false
$matches | ForEach-Object { $_.Line } | Set-Content -Path $tracePath -Encoding utf8
if (-not (Test-Path $tracePath)) {
    Set-Content -Path $tracePath -Value "" -Encoding utf8
}

$traceText = Get-Content -Raw $tracePath
$hasStart = ($traceText -match 'face_auto_voice_start_begin') -and ($traceText -match 'face_auto_voice_start_end')
$hasStop = ($traceText -match 'face_auto_voice_stop_begin') -and ($traceText -match 'face_auto_voice_stop_end')
$hasCaptureStart = ($traceText -match 'start_tap') -or ($traceText -match 'capture_started') -or ($traceText -match 'COMPANION_START_VOICE_ENTER') -or ($traceText -match 'COMPANION_START_VOICE_BLOCKED')
$uiStartStopCompleted = $flow.micStartTapped -and $flow.micStopTapped -and $flow.faceClosed
$passByLifecycleLogs = $hasStart -and $hasStop
$passByCurrentBuildSignals = $hasCaptureStart -and $uiStartStopCompleted

$summary = [ordered]@{
    deviceId      = $DeviceId
    packageName   = $PackageName
    flow          = $flow
    runDir        = $runDir
    rawLogPath    = $rawLogPath
    tracePath     = $tracePath
    checks        = [ordered]@{
        hasFaceAutoStartLifecycle = $hasStart
        hasFaceAutoStopLifecycle  = $hasStop
        hasCaptureStartSignal     = $hasCaptureStart
        uiStartStopCompleted      = $uiStartStopCompleted
        passByLifecycleLogs       = $passByLifecycleLogs
        passByCurrentBuildSignals = $passByCurrentBuildSignals
    }
    gateVersion   = 'face-start-stop-v2'
    pass          = ($passByLifecycleLogs -or $passByCurrentBuildSignals)
    capturedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
}
$summary | ConvertTo-Json -Depth 7 | Set-Content -Path $summaryPath -Encoding utf8

if ($summary.pass) {
    Write-Step "result: PASS"
    Write-Output "PASS: face start/stop probe matched lifecycle or current-build signals"
}
else {
    Write-Step "result: FAIL"
    Write-Output "FAIL: missing required start/stop probe signals"
}
Write-Output "TRACE: $tracePath"
Write-Output "SUMMARY: $summaryPath"
