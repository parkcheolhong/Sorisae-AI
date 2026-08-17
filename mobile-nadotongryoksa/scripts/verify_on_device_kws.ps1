param(
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$MainActivity = "com.parkcheolhong.worldlinco.MainActivity",
    [string]$DeviceSerial = "",
    [int]$DurationSec = 120,
    [switch]$LaunchApp,
    [switch]$TriggerCompanionArm,
    [switch]$RunCompanionPreflow,
    [string]$LoginEmail = "",
    [string]$LoginPassword = "",
    [int]$TriggerDelaySec = 6,
    [int]$PreflowSettleSec = 4,
    [int]$PreflowMaxAttempts = 4,
    [int]$PreflowRetryDelaySec = 2,
    [int]$CompanionArmedVerifyRetries = 2,
    [string]$CompanionToggleAccessibilityId = "worldlinco-companion-voicecall-toggle"
)

$ErrorActionPreference = "Stop"

if (-not $DeviceSerial) {
    $DeviceSerial = $env:ANDROID_SERIAL
}

function Invoke-Adb {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    if ($DeviceSerial) {
        return & adb -s $DeviceSerial @Args
    }

    return & adb @Args
}

function Try-LaunchApp {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Pkg,
        [Parameter(Mandatory = $true)]
        [string]$Activity
    )

    $mainComponent = "$Pkg/$Activity"
    Write-Host "[KWS-VERIFY] Launch attempt #1: am start -n $mainComponent"
    $startResult = Invoke-Adb -Args @("shell", "am", "start", "-n", $mainComponent)
    $startText = ($startResult | Out-String)
    if ($startText -notmatch "does not exist|Error type 3") {
        return $true
    }

    Write-Host "[KWS-VERIFY] Launch attempt #2: resolve-activity fallback"
    $resolved = Invoke-Adb -Args @("shell", "cmd", "package", "resolve-activity", "--brief", $Pkg)
    $resolvedText = ($resolved | Out-String)
    $resolvedComponent = ($resolvedText -split "`r?`n" | Where-Object {
            $_ -and $_ -match "/" -and $_ -notmatch "No activity|Unable|Error"
        } | Select-Object -Last 1)

    if ($resolvedComponent) {
        Write-Host "[KWS-VERIFY] Resolved component: $resolvedComponent"
        $resolvedStart = Invoke-Adb -Args @("shell", "am", "start", "-n", $resolvedComponent)
        $resolvedStartText = ($resolvedStart | Out-String)
        if ($resolvedStartText -notmatch "does not exist|Error type 3") {
            return $true
        }
    }

    Write-Host "[KWS-VERIFY] Launch attempt #3: monkey launcher fallback"
    $monkeyResult = Invoke-Adb -Args @("shell", "monkey", "-p", $Pkg, "-c", "android.intent.category.LAUNCHER", "1")
    $monkeyText = ($monkeyResult | Out-String)
    if ($monkeyText -notmatch "No activities found to run") {
        return $true
    }

    Write-Host "[KWS-VERIFY] Launch failed after all fallback attempts."
    return $false
}

function Get-UiNodeBoundsByContentDesc {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContentDesc
    )

    Invoke-Adb -Args @("shell", "uiautomator", "dump", "/sdcard/kws_window_dump.xml") | Out-Null
    $xmlLines = Invoke-Adb -Args @("exec-out", "cat", "/sdcard/kws_window_dump.xml")
    $xmlText = ($xmlLines | Out-String)

    $nodeRegex = [regex]::new('<node\b[^>]*content-desc="' + [regex]::Escape($ContentDesc) + '"[^>]*>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $nodeMatch = $nodeRegex.Match($xmlText)
    if (-not $nodeMatch.Success) {
        return $null
    }

    $boundsRegex = [regex]::new('bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
    $boundsMatch = $boundsRegex.Match($nodeMatch.Value)
    if (-not $boundsMatch.Success) {
        return $null
    }

    return [PSCustomObject]@{
        Left   = [int]$boundsMatch.Groups[1].Value
        Top    = [int]$boundsMatch.Groups[2].Value
        Right  = [int]$boundsMatch.Groups[3].Value
        Bottom = [int]$boundsMatch.Groups[4].Value
    }
}

function Try-OpenLoginModal {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$TapByContentDesc
    )

    $loginTriggers = @(
        "worldlinco-header-login-button",
        "worldlinco-inline-open-login-button",
        "worldlinco-auth-open-login-modal-button"
    )

    foreach ($loginTrigger in $loginTriggers) {
        if (& $TapByContentDesc $loginTrigger) {
            return $true
        }
    }

    return $false
}

function Invoke-CompanionArmTrigger {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContentDesc
    )

    $tapByContentDesc = {
        param([string]$Desc)
        $node = Get-UiNodeBoundsByContentDesc -ContentDesc $Desc
        if (-not $node) {
            return $false
        }
        $x = [int](($node.Left + $node.Right) / 2)
        $y = [int](($node.Top + $node.Bottom) / 2)
        Write-Host "[KWS-VERIFY] Tap '$Desc' at ($x,$y)"
        Invoke-Adb -Args @("shell", "input", "tap", "$x", "$y") | Out-Null
        return $true
    }

    Write-Host "[KWS-VERIFY] Triggering companion arm via accessibility id: $ContentDesc"
    if (& $tapByContentDesc $ContentDesc) {
        $armed = Confirm-CompanionArmedUiState -ToggleAccessibilityId $ContentDesc
        if ($armed) {
            return $true
        }
        Write-Host "[KWS-VERIFY] Trigger tap received but armed-state UI was not confirmed."
        return $false
    }

    Write-Host "[KWS-VERIFY] Companion toggle not visible. Opening auth modal via the currently visible login trigger."
    $loginOpened = Try-OpenLoginModal -TapByContentDesc $tapByContentDesc
    if ($loginOpened) {
        Start-Sleep -Seconds 2
    }

    if (& $tapByContentDesc $ContentDesc) {
        $armedAfterFallback = Confirm-CompanionArmedUiState -ToggleAccessibilityId $ContentDesc
        if ($armedAfterFallback) {
            return $true
        }
    }

    Write-Host "[KWS-VERIFY] Companion toggle not visible. Trying lobby fallback: demo session start."
    $demoTapped = (& $tapByContentDesc "worldlinco-demo-session-start-button-inline") -or (& $tapByContentDesc "worldlinco-demo-session-start-button")
    if ($demoTapped) {
        Start-Sleep -Seconds 5
        if (& $tapByContentDesc $ContentDesc) {
            $armedAfterFallback = Confirm-CompanionArmedUiState -ToggleAccessibilityId $ContentDesc
            if ($armedAfterFallback) {
                return $true
            }
        }
    }

    Write-Host "[KWS-VERIFY] Trigger FAILED: companion toggle not found after fallback flow."
    return $false
}

function Convert-ToAdbText {
    param([string]$Value)
    if (-not $Value) {
        return ""
    }
    return ($Value -replace ' ', '%s')
}

function Set-InputByContentDesc {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContentDesc,
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $node = Get-UiNodeBoundsByContentDesc -ContentDesc $ContentDesc
    if (-not $node) {
        return $false
    }

    $x = [int](($node.Left + $node.Right) / 2)
    $y = [int](($node.Top + $node.Bottom) / 2)
    Write-Host "[KWS-VERIFY] Focus '$ContentDesc' at ($x,$y)"
    Invoke-Adb -Args @("shell", "input", "tap", "$x", "$y") | Out-Null
    Start-Sleep -Milliseconds 350

    # Clear most existing text by repeated DEL events.
    1..48 | ForEach-Object { Invoke-Adb -Args @("shell", "input", "keyevent", "67") | Out-Null }

    $adbText = Convert-ToAdbText -Value $Text
    if ($adbText) {
        Invoke-Adb -Args @("shell", "input", "text", $adbText) | Out-Null
        return $true
    }

    return $false
}

function Invoke-CompanionPreflow {
    $tapByContentDesc = {
        param([string]$Desc)
        $node = Get-UiNodeBoundsByContentDesc -ContentDesc $Desc
        if (-not $node) {
            return $false
        }
        $x = [int](($node.Left + $node.Right) / 2)
        $y = [int](($node.Top + $node.Bottom) / 2)
        Write-Host "[KWS-VERIFY] Tap '$Desc' at ($x,$y)"
        Invoke-Adb -Args @("shell", "input", "tap", "$x", "$y") | Out-Null
        return $true
    }

    Write-Host "[KWS-VERIFY] Running companion preflow (login/session entry)..."

    $openedLogin = Try-OpenLoginModal -TapByContentDesc $tapByContentDesc
    if ($openedLogin -and $PreflowSettleSec -gt 0) {
        Start-Sleep -Seconds $PreflowSettleSec
    }

    if ($LoginEmail -and $LoginPassword) {
        $emailSet = Set-InputByContentDesc -ContentDesc "worldlinco-auth-email-input" -Text $LoginEmail
        $pwSet = Set-InputByContentDesc -ContentDesc "worldlinco-auth-password-input" -Text $LoginPassword
        if ($emailSet -and $pwSet) {
            Write-Host "[KWS-VERIFY] Login form filled. Submitting..."
            $submitted = (& $tapByContentDesc "worldlinco-auth-login-submit-button")
            if ($submitted -and $PreflowSettleSec -gt 0) {
                Start-Sleep -Seconds $PreflowSettleSec
            }
        }
        else {
            Write-Host "[KWS-VERIFY] Login fields not fully visible. Continuing with session fallback."
        }
    }

    # Session entry fallback: demo session button is expected in lobby/inline auth panel.
    $demoTapped = (& $tapByContentDesc "worldlinco-demo-session-start-button-inline") -or (& $tapByContentDesc "worldlinco-demo-session-start-button")
    if ($demoTapped -and $PreflowSettleSec -gt 0) {
        Start-Sleep -Seconds $PreflowSettleSec
    }

    # Forced navigation step: route through Settings tab once to stabilize tab/surface state.
    $settingsTapped = (& $tapByContentDesc "worldlinco-bottom-tab-settings")
    if ($settingsTapped -and $PreflowSettleSec -gt 0) {
        Start-Sleep -Seconds ([Math]::Max(1, [int]($PreflowSettleSec / 2)))
    }

    # Optional state settle taps (best effort, ignore if absent).
    $null = (& $tapByContentDesc "worldlinco-my-info-toggle")
    $null = (& $tapByContentDesc "worldlinco-translate-home-button")

    Write-Host "[KWS-VERIFY] Companion preflow complete."
}

function Test-UiContentDescVisible {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContentDesc
    )

    $node = Get-UiNodeBoundsByContentDesc -ContentDesc $ContentDesc
    return ($null -ne $node)
}

function Test-UiTextVisible {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    Invoke-Adb -Args @("shell", "uiautomator", "dump", "/sdcard/kws_window_dump.xml") | Out-Null
    $xmlLines = Invoke-Adb -Args @("exec-out", "cat", "/sdcard/kws_window_dump.xml")
    $xmlText = ($xmlLines | Out-String)
    return ($xmlText -match [regex]::Escape($Text))
}

function Confirm-CompanionArmedUiState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ToggleAccessibilityId
    )

    $tapByContentDesc = {
        param([string]$Desc)
        $node = Get-UiNodeBoundsByContentDesc -ContentDesc $Desc
        if (-not $node) {
            return $false
        }
        $x = [int](($node.Left + $node.Right) / 2)
        $y = [int](($node.Top + $node.Bottom) / 2)
        Write-Host "[KWS-VERIFY] Re-tap '$Desc' at ($x,$y)"
        Invoke-Adb -Args @("shell", "input", "tap", "$x", "$y") | Out-Null
        return $true
    }

    # Armed state label should switch from "대기 켜기" to "대기 끄기" (or English equivalent).
    $offTextKo = "대기 끄기"
    $onTextKo = "대기 켜기"
    $offTextEn = "turn off"
    $onTextEn = "Turn on voice-call wake"

    $tries = [Math]::Max(0, $CompanionArmedVerifyRetries)
    for ($i = 0; $i -le $tries; $i++) {
        $hasOffKo = Test-UiTextVisible -Text $offTextKo
        $hasOffEn = Test-UiTextVisible -Text $offTextEn
        $hasOnKo = Test-UiTextVisible -Text $onTextKo
        $hasOnEn = Test-UiTextVisible -Text $onTextEn

        if ($hasOffKo -or $hasOffEn) {
            Write-Host "[KWS-VERIFY] Armed-state UI confirmed after tap (off-label visible)."
            return $true
        }

        if (-not $hasOnKo -and -not $hasOnEn) {
            # If neither label is found, keep retrying because surface may still be transitioning.
            Write-Host "[KWS-VERIFY] Armed-state label not yet stable; retry check ($($i+1)/$($tries+1))."
        }
        else {
            Write-Host "[KWS-VERIFY] Unarmed label still visible after tap; retrying tap/check ($($i+1)/$($tries+1))."
        }

        if ($i -lt $tries) {
            $retapped = (& $tapByContentDesc $ToggleAccessibilityId)
            if (-not $retapped) {
                Write-Host "[KWS-VERIFY] Re-tap skipped: toggle not visible during armed-state retry."
            }
            Start-Sleep -Milliseconds 800
        }
    }

    Write-Host "[KWS-VERIFY] Armed-state UI not confirmed after retries."
    return $false
}

function Ensure-CompanionToggleVisible {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ToggleAccessibilityId
    )

    $attempts = [Math]::Max(1, $PreflowMaxAttempts)
    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        if (Test-UiContentDescVisible -ContentDesc $ToggleAccessibilityId) {
            Write-Host "[KWS-VERIFY] Preflow loop success: '$ToggleAccessibilityId' visible before trigger (attempt=$attempt)."
            return $true
        }

        Write-Host "[KWS-VERIFY] Preflow loop attempt ${attempt}/${attempts}: '$ToggleAccessibilityId' not visible. Re-entering preflow..."
        Invoke-CompanionPreflow

        if (Test-UiContentDescVisible -ContentDesc $ToggleAccessibilityId) {
            Write-Host "[KWS-VERIFY] Preflow loop success: '$ToggleAccessibilityId' became visible (attempt=$attempt)."
            return $true
        }

        if ($attempt -lt $attempts -and $PreflowRetryDelaySec -gt 0) {
            Start-Sleep -Seconds $PreflowRetryDelaySec
        }
    }

    Write-Host "[KWS-VERIFY] Preflow loop exhausted: '$ToggleAccessibilityId' is still not visible."
    return $false
}

Write-Host "[KWS-VERIFY] Checking adb availability..."
$adbVersion = & adb version
if (-not $adbVersion) {
    throw "adb is not available. Please install Android platform-tools."
}

$deviceLines = (& adb devices) -split "`n" | Where-Object { $_ -match "\tdevice$" }
if (-not $deviceLines -or $deviceLines.Count -eq 0) {
    throw "No online Android device found. Connect a device and enable USB debugging."
}

Write-Host "[KWS-VERIFY] Online devices:"
$deviceLines | ForEach-Object { Write-Host "  $_" }

if ($DeviceSerial) {
    $matchedDevice = $deviceLines | Where-Object { $_ -match "^$([regex]::Escape($DeviceSerial))\tdevice$" }
    if (-not $matchedDevice) {
        throw "Requested device serial '$DeviceSerial' is not online."
    }
    Write-Host "[KWS-VERIFY] Target device: $DeviceSerial"
}
elseif ($deviceLines.Count -gt 1) {
    throw "Multiple devices are online. Pass -DeviceSerial or set ANDROID_SERIAL."
}

if ($LaunchApp.IsPresent) {
    Write-Host "[KWS-VERIFY] Launching app..."
    $launchOk = Try-LaunchApp -Pkg $PackageName -Activity $MainActivity
    if (-not $launchOk) {
        throw "App launch failed. Verify package/activity and installation on the target device."
    }
}

Write-Host "[KWS-VERIFY] Clearing old logs..."
Invoke-Adb -Args @("logcat", "-c") | Out-Null

Write-Host "[KWS-VERIFY] Capturing logs for $DurationSec seconds"
Write-Host "[KWS-VERIFY] Watch for: native_started, native_wake, native_error, scan_idle, companion handler markers, kws_init markers"

$deadline = (Get-Date).AddSeconds($DurationSec)

$logcatArgs = @("logcat", "-v", "time", "ReactNativeJS:V", "OnDeviceKws:V", "*:S")
if ($DeviceSerial) {
    $logcatArgs = @("-s", $DeviceSerial) + $logcatArgs
}

$process = Start-Process -FilePath "adb" -ArgumentList $logcatArgs -NoNewWindow -RedirectStandardOutput "$env:TEMP\kws_verify_log.txt" -PassThru
try {
    if ($RunCompanionPreflow.IsPresent) {
        $toggleVisible = Ensure-CompanionToggleVisible -ToggleAccessibilityId $CompanionToggleAccessibilityId
        if (-not $toggleVisible) {
            Write-Host "[KWS-VERIFY] Continuing trigger even though toggle visibility loop did not satisfy the precondition."
        }
    }

    if ($TriggerCompanionArm.IsPresent) {
        if ($TriggerDelaySec -gt 0) {
            Start-Sleep -Seconds $TriggerDelaySec
        }
        $triggered = Invoke-CompanionArmTrigger -ContentDesc $CompanionToggleAccessibilityId
        if (-not $triggered) {
            Write-Host "[KWS-VERIFY] Trigger scenario could not toggle companion arm."
        }
    }

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 300
        if ($process.HasExited) {
            break
        }
    }
}
finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}

$logPath = Join-Path $env:TEMP "kws_verify_log.txt"
if (-not (Test-Path $logPath)) {
    throw "Failed to capture logcat output."
}

$interesting = Select-String -Path $logPath -Pattern "COMPANION_KWS|COMPANION_VOICE_CALL|OnDeviceKwsEvent|native_started|native_wake|native_error|scan_idle|COMPANION_HANDLER|COMPANION_TOGGLE_TAP|COMPANION_ARMED_ON|COMPANION_ARMED_OFF|COMPANION_START_VOICE_REQUEST|COMPANION_KWS_INIT_BEGIN|COMPANION_KWS_INIT_END|COMPANION_KWS_INIT_ERROR"

$kwsPattern = "COMPANION_KWS"
$voicePattern = "COMPANION_VOICE_CALL"
$hasNativeStarted = [bool](Select-String -Path $logPath -Pattern 'native_started' -Quiet)
$hasNativeSkip = [bool](Select-String -Path $logPath -Pattern 'native_skip' -Quiet)
$hasNativeWake = [bool](Select-String -Path $logPath -Pattern 'native_wake' -Quiet)
$hasNativeError = [bool](Select-String -Path $logPath -Pattern 'native_error' -Quiet)
$hasScanIdle = [bool](Select-String -Path $logPath -Pattern 'scan_idle' -Quiet)
$hasCompanionKws = [bool](Select-String -Path $logPath -Pattern $kwsPattern -Quiet)
$hasCompanionVoice = [bool](Select-String -Path $logPath -Pattern $voicePattern -Quiet)
$hasCompanionTapMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_TOGGLE_TAP|COMPANION_HANDLER.*COMPANION_TOGGLE_TAP' -Quiet)
$hasCompanionArmedOnMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_ARMED_ON|COMPANION_HANDLER.*COMPANION_ARMED_ON' -Quiet)
$hasCompanionStartVoiceMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_START_VOICE_REQUEST|COMPANION_HANDLER.*COMPANION_START_VOICE_REQUEST' -Quiet)
$hasCompanionStartVoiceEnterMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_START_VOICE_ENTER|COMPANION_HANDLER.*COMPANION_START_VOICE_ENTER' -Quiet)
$hasCompanionKwsInitSkipMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_KWS_INIT_SKIP|COMPANION_HANDLER.*COMPANION_KWS_INIT_SKIP' -Quiet)
$hasCompanionKwsInitBeginMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_KWS_INIT_BEGIN|COMPANION_HANDLER.*COMPANION_KWS_INIT_BEGIN' -Quiet)
$hasCompanionKwsInitEndMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_KWS_INIT_END|COMPANION_HANDLER.*COMPANION_KWS_INIT_END' -Quiet)
$hasCompanionKwsInitErrorMarker = [bool](Select-String -Path $logPath -Pattern 'COMPANION_KWS_INIT_ERROR|COMPANION_HANDLER.*COMPANION_KWS_INIT_ERROR' -Quiet)

$expandedInteresting = Select-String -Path $logPath -Pattern "COMPANION_KWS|COMPANION_VOICE_CALL|OnDeviceKwsEvent|COMPANION_HANDLER|COMPANION_TOGGLE_TAP|COMPANION_ARMED_ON|COMPANION_ARMED_OFF|COMPANION_START_VOICE_REQUEST|COMPANION_KWS_INIT_BEGIN|COMPANION_KWS_INIT_END|COMPANION_KWS_INIT_ERROR|native_started|native_skip|native_start_failed|native_unavailable|missing_vosk_model_path|missing_porcupine_credentials|probe_unsupported|native_wake|native_wake_ignored_face_screen_open|native_error|scan_idle|scan_guard_after_close|dormant_silence_backoff"

Write-Host "[KWS-VERIFY] ---- filtered output ----"
if ($expandedInteresting) {
    $expandedInteresting | ForEach-Object { Write-Host $_.Line }
}
else {
    Write-Host "[KWS-VERIFY] No KWS markers found."
}

Write-Host "[KWS-VERIFY] ---- gate summary ----"
Write-Host "[KWS-VERIFY] has_companion_kws=$hasCompanionKws has_companion_voice_call=$hasCompanionVoice has_native_started=$hasNativeStarted has_native_skip=$hasNativeSkip has_native_wake=$hasNativeWake has_native_error=$hasNativeError has_scan_idle=$hasScanIdle"
Write-Host "[KWS-VERIFY] has_companion_tap_marker=$hasCompanionTapMarker has_companion_armed_on_marker=$hasCompanionArmedOnMarker has_companion_start_voice_marker=$hasCompanionStartVoiceMarker has_companion_start_voice_enter_marker=$hasCompanionStartVoiceEnterMarker"
Write-Host "[KWS-VERIFY] has_companion_kws_init_skip_marker=$hasCompanionKwsInitSkipMarker has_companion_kws_init_begin_marker=$hasCompanionKwsInitBeginMarker has_companion_kws_init_end_marker=$hasCompanionKwsInitEndMarker has_companion_kws_init_error_marker=$hasCompanionKwsInitErrorMarker"

if ($hasNativeStarted) {
    Write-Host "[KWS-VERIFY] GATE: PASS (native_started observed)"
}
elseif ($hasCompanionStartVoiceEnterMarker -and $hasCompanionKwsInitBeginMarker -and $hasCompanionKwsInitEndMarker) {
    Write-Host "[KWS-VERIFY] GATE: PASS (companion start voice + KWS init sequence observed)"
}
elseif ($hasNativeSkip) {
    Write-Host "[KWS-VERIFY] GATE: FAIL (native_skip observed before start)"
}
elseif (-not $hasCompanionKws -and -not $hasCompanionVoice) {
    Write-Host "[KWS-VERIFY] GATE: FAIL (no companion marker observed - trigger path may not be reached)"
}
else {
    Write-Host "[KWS-VERIFY] GATE: FAIL (companion start voice or KWS init sequence incomplete)"
}

Write-Host "[KWS-VERIFY] Raw log saved: $logPath"
Write-Host "[KWS-VERIFY] PASS condition example: native_started -> native_wake sequence appears."
