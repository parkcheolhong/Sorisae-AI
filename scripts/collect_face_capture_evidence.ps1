#!/usr/bin/env pwsh
param(
    [string]$DeviceId = "R83W70QY11H",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$TapX = 400,
    [int]$TapY = 256,
    [int]$LaunchDelaySec = 3,
    [int]$CaptureSec = 18,
    [string]$EvidenceRoot = "docs/checklists/evidence",
    [string]$RunLabel = "face-capture",
    [string]$LoginEmail = "119cash@naver.com",
    [string]$LoginPasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [string]$DevClientUrl = "",
    [ValidateSet("auto", "skip")]
    [string]$LoginMode = "auto",
    [int]$LoginMaxWaitSec = 90,
    [int]$LoginProbeMaxSec = 25,
    [int]$SessionRestoreWaitSec = 15,
    [int]$SessionRestoreStableHits = 1
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $repoRoot (Join-Path $EvidenceRoot "$RunLabel-$runStamp")
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$rawLogPath = Join-Path $runDir "reactnative-logcat.txt"
$tracePath = Join-Path $runDir "face-capture-trace.txt"
$summaryPath = Join-Path $runDir "summary.json"
$lastDumpPath = Join-Path $runDir "last-window-dump.xml"

function Write-Step {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Output $line
}

function Run-Adb {
    param([string[]]$AdbArgs)

    & adb -s $DeviceId @AdbArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "adb command failed: $($AdbArgs -join ' ')"
    }
}

function Start-WorldlincoApp {
    if ([string]::IsNullOrWhiteSpace($DevClientUrl)) {
        Run-Adb @("shell", "am", "start", "-n", "$PackageName/.MainActivity")
        return
    }

    Run-Adb @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", $DevClientUrl)
}

function Get-ForegroundPackage {
    $raw = & adb -s $DeviceId shell dumpsys activity activities
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $text = ($raw -join "`n")
    if ($text -match 'mResumedActivity:.*?ActivityRecord\{[^\}]*?\s([a-zA-Z0-9\._]+)\/') {
        return $matches[1]
    }
    if ($text -match 'topResumedActivity=ActivityRecord\{[^\}]*?\s([a-zA-Z0-9\._]+)\/') {
        return $matches[1]
    }
    if ($text -match 'mFocusedApp.*?([a-zA-Z0-9\._]+)') {
        return $matches[1]
    }
    return $null
}

function Ensure-WorldlincoForeground {
    param([int]$Retries = 4)

    for ($i = 0; $i -lt $Retries; $i++) {
        $pkg = Get-ForegroundPackage
        if ($pkg -eq $PackageName) {
            return $true
        }
        Write-Step "foreground mismatch (current=$pkg); relaunching $PackageName"
        Start-WorldlincoApp
        Start-Sleep -Seconds 2
    }
    return $false
}

function Reset-AppProcessAndCaptureSession {
    param([int]$CooldownMs = 1400)

    # Prevent stale in-app capture state (e.g., capture_busy) from leaking across runs.
    Run-Adb @("shell", "am", "force-stop", $PackageName)
    Start-Sleep -Milliseconds $CooldownMs
    Run-Adb @("shell", "input", "keyevent", "3")
    Start-Sleep -Milliseconds 400
}

function Get-UiDump {
    param(
        [string]$OutPath,
        [int]$RetryCount = 2,
        [int]$RetryDelayMs = 300
    )

    [void](Ensure-WorldlincoForeground -Retries 1)
    $remote = "/sdcard/window_dump.xml"
    $attempts = [Math]::Max(1, $RetryCount + 1)
    $raw = $null
    $lastError = $null

    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        try {
            Run-Adb @("shell", "uiautomator", "dump", $remote)
            $xml = & adb -s $DeviceId shell cat $remote
            if ($LASTEXITCODE -ne 0) {
                throw "adb cat window_dump failed"
            }

            $candidate = ($xml -join "`n")
            if ([string]::IsNullOrWhiteSpace($candidate) -or $candidate -match '^ERROR:\s*null root node returned by UiTestAutomationBridge\.?$') {
                throw "uiautomator returned empty/null-root dump"
            }

            $raw = $candidate
            $lastError = $null
            break
        }
        catch {
            $lastError = $_
            if ($attempt -lt $attempts) {
                Start-Sleep -Milliseconds $RetryDelayMs
            }
        }
    }

    if (-not $raw) {
        throw "Get-UiDump failed after retries: $($lastError.Exception.Message)"
    }
    if ($raw -match 'package="com.android.chrome"|package="com.android.systemui"') {
        Write-Step "ui dump is not from worldlinco; re-ensuring foreground"
        [void](Ensure-WorldlincoForeground -Retries 2)
        Run-Adb @("shell", "uiautomator", "dump", $remote)
        $xml = & adb -s $DeviceId shell cat $remote
        if ($LASTEXITCODE -eq 0) {
            $raw = ($xml -join "`n")
        }
    }
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
    if (-not $nodes -or $nodes.Count -eq 0) {
        return $null
    }

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

function Get-NodeCenterByText {
    param(
        [string]$Xml,
        [string]$TextPattern
    )

    if (-not $Xml -or -not $TextPattern) {
        return $null
    }

    [xml]$doc = $Xml
    $nodes = $doc.SelectNodes("//node[contains(@text,'$TextPattern')]")
    if (-not $nodes -or $nodes.Count -eq 0) {
        return $null
    }

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

function Convert-ToAdbInputText {
    param([string]$Text)

    if (-not $Text) {
        return ''
    }

    $escaped = $Text
    $escaped = $escaped -replace '\\', '\\\\'
    $escaped = $escaped -replace ' ', '%s'
    $escaped = $escaped -replace '@', '\\@'
    $escaped = $escaped -replace '\.', '\\.'
    $escaped = $escaped -replace '%', '\%'
    return $escaped
}

function Tap-BySelector {
    param(
        [string]$Selector,
        [int]$Retries = 6,
        [int]$DelayMs = 800
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

function Tap-ByText {
    param(
        [string]$TextPattern,
        [int]$Retries = 6,
        [int]$DelayMs = 800
    )

    for ($i = 0; $i -lt $Retries; $i++) {
        $xml = Get-UiDump -OutPath $lastDumpPath
        $center = Get-NodeCenterByText -Xml $xml -TextPattern $TextPattern
        if ($center) {
            Tap-At -X $center.x -Y $center.y
            Start-Sleep -Milliseconds 350
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
}

function Is-HomeScreenVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($xml -match 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle')
}

function Is-AuthenticatedSessionVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    $authDebug = Get-AuthDebugStateSnapshot -Xml $xml
    if ($authDebug -and ($authDebug.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
        return $true
    }
    return Is-HomeScreenVisible -or ($xml -match 'worldlinco-my-info-toggle|worldlinco-header-login-button.*logout|로그아웃')
}

function Wait-ForSessionRestoreReady {
    param(
        [int]$MaxWaitSec = 15,
        [int]$StableHits = 1
    )

    $deadline = (Get-Date).AddSeconds([Math]::Max(1, [Math]::Min(180, $MaxWaitSec)))
    $requiredStableHits = [Math]::Max(1, [Math]::Min(5, $StableHits))
    $hits = 0

    while ((Get-Date) -lt $deadline) {
        if (Is-AuthenticatedSessionVisible) {
            $hits++
            if ($hits -ge $requiredStableHits) {
                return $true
            }
            Start-Sleep -Milliseconds 300
            continue
        }

        $hits = 0
        if (Is-LoginLobbyVisible) {
            return $false
        }
        Start-Sleep -Milliseconds 300
    }

    return $false
}

function Is-LoginLobbyVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($xml -match 'worldlinco-login-modal|worldlinco-inline-auth-panel|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|로그인이 필요해요|WORLDLINCO LOBBY')
}

function Is-TransientDevOverlayVisible {
    param([string]$Xml)

    if (-not $Xml) {
        return $false
    }
    return [bool]($Xml -match 'developer menu|Runtime version:|This is the developer menu|long press anywhere on the screen with three fingers|content-desc="Close"')
}

function Is-DevClientLoadErrorVisible {
    param([string]$Xml)

    if (-not $Xml) {
        return $false
    }

    return [bool]($Xml -match 'There was a problem loading the project|This development build encountered the following error|java\.net\.ConnectException|Failed to connect to /')
}

function Is-MinimalRuntimeShellVisible {
    param([string]$Xml)

    if (-not $Xml) {
        return $false
    }

    if ($Xml -notmatch 'package="com\.parkcheolhong\.worldlinco"') {
        return $false
    }

    if ($Xml -match 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle|worldlinco-my-info-toggle|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-inline-open-login-button|worldlinco-header-login-button|worldlinco-login-modal|worldlinco-inline-auth-panel') {
        return $false
    }

    $resourceIds = [regex]::Matches($Xml, 'resource-id="([^"]*)"') |
    ForEach-Object { $_.Groups[1].Value } |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Unique

    if (-not $resourceIds -or $resourceIds.Count -eq 0) {
        return $false
    }

    $allowedIds = @(
        'com.parkcheolhong.worldlinco:id/action_bar_root',
        'android:id/content',
        'android:id/navigationBarBackground'
    )

    foreach ($rid in $resourceIds) {
        if ($allowedIds -notcontains $rid) {
            return $false
        }
    }

    return $true
}

function Get-AuthDebugStateSnapshot {
    param(
        [string]$Xml = $null,
        [switch]$AllowFallbackToUiDump
    )

    $candidateXml = $Xml
    if ([string]::IsNullOrWhiteSpace($candidateXml)) {
        $candidateXml = Get-UiDump -OutPath $lastDumpPath
    }

    if ([string]::IsNullOrWhiteSpace($candidateXml)) {
        return $null
    }

    $normalized = $candidateXml -replace "`r", "" -replace "`n", " "
    $stateMatch = [regex]::Match($normalized, 'AUTH_DEBUG_STATE\s*:\s*(AUTHENTICATED|TOKEN_ONLY|HYDRATING|ANONYMOUS)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $stateMatch.Success) {
        return $null
    }

    $userMatch = [regex]::Match($normalized, 'AUTH_DEBUG_USER\s*:\s*([^\s<>"'']+)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    return [ordered]@{
        state = $stateMatch.Groups[1].Value.ToUpperInvariant()
        user  = if ($userMatch.Success) { $userMatch.Groups[1].Value.Trim() } else { $null }
        source = 'ui_dump'
    }
}

function Has-AuthReadyLogHint {
    param([int]$TailLines = 350)

    $raw = & adb -s $DeviceId logcat -d -v time ReactNativeJS:I *:S
    if ($LASTEXITCODE -ne 0 -or -not $raw) {
        return $false
    }

    $tail = @($raw | Select-Object -Last ([Math]::Max(80, [Math]::Min(1200, $TailLines)))) -join "`n"
    $patterns = @(
        '"event":"VOIP_PRESENCE_CONNECTED".*"token_ready":true.*"user_ready":true.*"show_login":false',
        '"event":"LOGIN_SESSION_APPLIED"',
        '"event":"PASSKEY_LOGIN_CALLBACK_SUCCESS"',
        'LOGIN_SUBMIT_SUCCESS',
        'AUTH_DEBUG_STATE:AUTHENTICATED',
        'AUTH_DEBUG_STATE:TOKEN_ONLY'
    )

    foreach ($pattern in $patterns) {
        if ($tail -match $pattern) {
            return $true
        }
    }

    return $false
}

function Dismiss-TransientDevOverlay {
    param([int]$Attempts = 1)

    for ($i = 0; $i -lt $Attempts; $i++) {
        $xml = Get-UiDump -OutPath $lastDumpPath
        if (-not (Is-TransientDevOverlayVisible -Xml $xml)) {
            return $true
        }

        if (-not (Tap-BySelector -Selector 'Close' -Retries 1 -DelayMs 250)) {
            Run-Adb @('shell', 'input', 'keyevent', '4')
        }
        Start-Sleep -Milliseconds 500
    }

    $last = Get-UiDump -OutPath $lastDumpPath
    return -not (Is-TransientDevOverlayVisible -Xml $last)
}

function Is-FaceScreenVisible {
    $xml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($xml -match 'worldlinco-face-screen-mic|worldlinco-face-screen-close|worldlinco-face-screen-lang|worldlinco-face-peer-lang|worldlinco-face-peer-lang-quick-open')
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
        $hasSystemPermissionDialog = [bool]($xml -match 'com\.google\.android\.permissioncontroller|com\.android\.permissioncontroller')
        $hasLocationPrompt = [bool]($xml -match '위치 정보에 액세스하도록 허용하시겠습니까|앱 사용 중에만 허용|이번만 허용|허용 안함|Allow while using the app|Only this time|Don''t allow')

        if (-not $hasSystemPermissionDialog -and -not $hasLocationPrompt) {
            return $true
        }

        $tapped = $false
        if ($hasLocationPrompt) {
            foreach ($text in @('앱 사용 중에만 허용', '이번만 허용', 'Allow while using the app', 'While using the app', 'Only this time', '허용')) {
                $centerByText = Get-NodeCenterByText -Xml $xml -TextPattern $text
                if ($centerByText) {
                    Tap-At -X $centerByText.x -Y $centerByText.y
                    Start-Sleep -Milliseconds 600
                    $tapped = $true
                    break
                }
            }
        }

        foreach ($selector in $allowSelectors) {
            if ($tapped) {
                break
            }
            $center = Get-NodeCenter -Xml $xml -Selector $selector
            if ($center) {
                Tap-At -X $center.x -Y $center.y
                Start-Sleep -Milliseconds 550
                $tapped = $true
                break
            }
        }

        if (-not $tapped) {
            # Fallback around the common lower-right allow CTA area.
            Tap-At -X 580 -Y 1180
            Start-Sleep -Milliseconds 550
        }
    }

    $finalXml = Get-UiDump -OutPath $lastDumpPath
    return [bool]($finalXml -notmatch 'com\.google\.android\.permissioncontroller|com\.android\.permissioncontroller|위치 정보에 액세스하도록 허용하시겠습니까|앱 사용 중에만 허용|이번만 허용|허용 안함|Allow while using the app|Only this time|Don''t allow')
}

function Enter-Field {
    param(
        [string]$Selector,
        [string]$Value
    )

    $tapped = Tap-BySelector -Selector $Selector -Retries 4 -DelayMs 600
    if (-not $tapped) {
        switch ($Selector) {
            'worldlinco-auth-email-input' { Tap-At -X 422 -Y 605; $tapped = $true }
            'worldlinco-auth-password-input' { Tap-At -X 398 -Y 890; $tapped = $true }
        }
    }
    if (-not $tapped) {
        return $false
    }

    if ($Selector -eq 'worldlinco-auth-password-input') {
        # Layout drift fallback: move focus from email to password row using Tab.
        Run-Adb @('shell', 'input', 'keyevent', '61')
        Start-Sleep -Milliseconds 220
    }

    1..24 | ForEach-Object { Run-Adb @("shell", "input", "keyevent", "67") }
    $escaped = Convert-ToAdbInputText -Text $Value
    Run-Adb @("shell", "input", "text", $escaped)
    return $true
}

function Get-LoginPassword {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if ($password) {
        return $password.Trim()
    }

    $passwordPath = Join-Path $repoRoot $LoginPasswordFile
    if (Test-Path $passwordPath) {
        return (Get-Content -Raw $passwordPath).Trim()
    }

    return $null
}

function Ensure-LoggedIn {
    $homePattern = 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle|worldlinco-my-info-toggle'
    $loginPattern = 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal|worldlinco-inline-auth-panel|로그인이 필요해요|WORLDLINCO LOBBY|로그인 패널 열기|로그인 / 회원가입|로그인 또는 회원가입'
    $loginCtaPattern = 'worldlinco-inline-open-login-button|worldlinco-header-login-button|worldlinco-auth-open-login-modal-button|로그인 패널 열기|로그인 / 회원가입|로그인'
    $currentXml = Get-UiDump -OutPath $lastDumpPath
    if (Is-TransientDevOverlayVisible -Xml $currentXml) {
        Write-Step "transient dev overlay detected; dismissing before login surface detection"
        [void](Dismiss-TransientDevOverlay -Attempts 1)
        $currentXml = Get-UiDump -OutPath $lastDumpPath
    }

    $authDebugCurrent = Get-AuthDebugStateSnapshot -Xml $currentXml
    if ($authDebugCurrent -and ($authDebugCurrent.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
        return @{ attempted = $false; ok = $true; reason = 'auth_debug_authenticated' }
    }

    # Fast-path: when home markers appear across quick probes, skip deeper recovery/login flow.
    for ($quick = 0; $quick -lt 3; $quick++) {
        if ($currentXml -match $homePattern) {
            return @{ attempted = $false; ok = $true; reason = 'session_restored' }
        }
        Start-Sleep -Milliseconds 200
        $currentXml = Get-UiDump -OutPath $lastDumpPath
        $authDebugCurrent = Get-AuthDebugStateSnapshot -Xml $currentXml
        if ($authDebugCurrent -and ($authDebugCurrent.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return @{ attempted = $false; ok = $true; reason = 'auth_debug_authenticated' }
        }
    }
    if ($currentXml -match $homePattern) {
        return @{ attempted = $false; ok = $true; reason = 'session_restored' }
    }

    if ($LoginMode -eq 'skip') {
        if ($currentXml -match $loginPattern) {
            Write-Step "login mode skip: current UI still shows login flow; continuing to real login entry"
        }
        else {
            return @{ attempted = $false; ok = $false; reason = 'login_skipped_without_visible_session' }
        }
    }

    if (Wait-ForSessionRestoreReady -MaxWaitSec $SessionRestoreWaitSec -StableHits $SessionRestoreStableHits) {
        return @{ attempted = $false; ok = $true; reason = 'session_restored' }
    }

    $loginDeadline = (Get-Date).AddSeconds([Math]::Max(1, [Math]::Min(240, $LoginMaxWaitSec)))
    $probeDeadline = (Get-Date).AddSeconds([Math]::Max(6, [Math]::Min(60, $LoginProbeMaxSec)))

    $probeRecoveryUsed = $false
    $devLoadRecoveryUsed = $false
    $unknownSurfaceStreak = 0
    $minimalShellStreak = 0
    $probe = 0
    while ((Get-Date) -lt $probeDeadline) {
        $probe++
        try {
            $probeXml = Get-UiDump -OutPath $lastDumpPath
        }
        catch {
            if (-not $probeRecoveryUsed) {
                $probeRecoveryUsed = $true
                Write-Step "login probe ui dump failed; fast-recovery relaunch once"
                Start-WorldlincoApp
                [void](Ensure-WorldlincoForeground -Retries 1)
                Start-Sleep -Milliseconds 900
                continue
            }

            Write-Step "login probe ui dump failed after fast-recovery"
            if ((Get-Date) -gt $probeDeadline) {
                return @{ attempted = $true; ok = $false; reason = 'login_timeout_probe' }
            }
            Start-Sleep -Milliseconds 300
            continue
        }

        if (Is-DevClientLoadErrorVisible -Xml $probeXml) {
            if (-not $devLoadRecoveryUsed) {
                $devLoadRecoveryUsed = $true
                Write-Step "dev-client load error detected; fast-recovery relaunch once"
                Start-WorldlincoApp
                [void](Ensure-WorldlincoForeground -Retries 1)
                Start-Sleep -Milliseconds 650
                continue
            }
            return @{ attempted = $true; ok = $false; reason = 'devclient_runtime_unready' }
        }

        if (Is-MinimalRuntimeShellVisible -Xml $probeXml) {
            $minimalShellStreak++
            if ($minimalShellStreak -ge 3) {
                if (-not $devLoadRecoveryUsed) {
                    $devLoadRecoveryUsed = $true
                    Write-Step "minimal runtime shell detected repeatedly; fast-recovery relaunch once"
                    Start-WorldlincoApp
                    [void](Ensure-WorldlincoForeground -Retries 1)
                    Start-Sleep -Milliseconds 700
                    $minimalShellStreak = 0
                    continue
                }
                return @{ attempted = $true; ok = $false; reason = 'devclient_runtime_unready' }
            }
        }
        else {
            $minimalShellStreak = 0
        }

        if ($probeXml -match $homePattern) {
            return @{ attempted = $false; ok = $true; reason = 'session_restored' }
        }
        if ($probeXml -match $loginPattern -or $probeXml -match $loginCtaPattern) {
            break
        }

        $unknownSurfaceStreak++
        if ($unknownSurfaceStreak -ge 4) {
            Tap-At -X 400 -Y 250
            Start-Sleep -Milliseconds 450
            $unknownSurfaceStreak = 0
        }

        if (Is-TransientDevOverlayVisible -Xml $probeXml) {
            [void](Dismiss-TransientDevOverlay -Attempts 1)
            continue
        }
        Start-Sleep -Milliseconds 250
    }

    if ((Get-Date) -ge $probeDeadline) {
        return @{ attempted = $true; ok = $false; reason = 'login_timeout_probe' }
    }

    $xml = Get-UiDump -OutPath $lastDumpPath
    if (Is-TransientDevOverlayVisible -Xml $xml) {
        [void](Dismiss-TransientDevOverlay -Attempts 1)
        $xml = Get-UiDump -OutPath $lastDumpPath
    }
    if ($xml -match $homePattern) {
        return @{ attempted = $false; ok = $true; reason = 'session_restored' }
    }

    if ($xml -match $loginCtaPattern) {
        foreach ($button in @('worldlinco-header-login-button', 'worldlinco-auth-open-login-modal-button', 'worldlinco-inline-open-login-button', 'text:로그인 패널 열기', 'text:로그인 / 회원가입', 'text:로그인')) {
            if ($button -eq 'worldlinco-header-login-button') {
                Tap-At -X 400 -Y 250
                Start-Sleep -Milliseconds 900
            }
            elseif ($button -like 'text:*') {
                $textPattern = $button.Substring(5)
                [void](Tap-ByText -TextPattern $textPattern -Retries 2 -DelayMs 450)
                Start-Sleep -Milliseconds 700
            }
            else {
                [void](Tap-BySelector -Selector $button -Retries 2 -DelayMs 450)
                Start-Sleep -Milliseconds 700
            }
            $postTapXml = Get-UiDump -OutPath $lastDumpPath
            if ($postTapXml -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal') {
                $xml = $postTapXml
                break
            }
        }
    }

    if ($xml -notmatch $loginPattern) {
        return @{ attempted = $false; ok = $false; reason = 'ui_surface_unrecognized' }
    }

    $password = Get-LoginPassword
    if (-not $LoginEmail -or -not $password) {
        return @{ attempted = $false; ok = $false; reason = 'missing_login_credentials' }
    }

    $opened = $false
    foreach ($button in @('worldlinco-header-login-button', 'worldlinco-auth-open-login-modal-button', 'worldlinco-inline-open-login-button', 'text:로그인 패널 열기', 'text:로그인 / 회원가입', 'text:로그인')) {
        if ((Get-Date) -gt $loginDeadline) {
            return @{ attempted = $true; ok = $false; reason = 'login_timeout_open' }
        }
        if ($button -eq 'worldlinco-header-login-button') {
            Tap-At -X 400 -Y 250
            Write-Step "login CTA direct tap: $button @ 400,250"
            $modalDeadline = (Get-Date).AddSeconds(5)
            while ((Get-Date) -lt $modalDeadline) {
                Start-Sleep -Milliseconds 650
                $postTapXml = Get-UiDump -OutPath $lastDumpPath
                if ($postTapXml -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal') {
                    $opened = $true
                    break
                }
            }
            if ($opened) {
                break
            }
            Write-Step "login CTA direct tap did not open modal: $button"
        }
        elseif ($button -like 'text:*') {
            $textPattern = $button.Substring(5)
            if (Tap-ByText -TextPattern $textPattern -Retries 3 -DelayMs 500) {
                Write-Step "login CTA tapped by text: $textPattern"
                $modalDeadline = (Get-Date).AddSeconds(5)
                while ((Get-Date) -lt $modalDeadline) {
                    Start-Sleep -Milliseconds 650
                    $postTapXml = Get-UiDump -OutPath $lastDumpPath
                    if ($postTapXml -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal') {
                        $opened = $true
                        break
                    }
                }
                if ($opened) {
                    break
                }
                Write-Step "login CTA text tap did not open modal: $textPattern"
            }
        }
        elseif (Tap-BySelector -Selector $button -Retries 3 -DelayMs 500) {
            Write-Step "login CTA tapped: $button"
            $modalDeadline = (Get-Date).AddSeconds(5)
            while ((Get-Date) -lt $modalDeadline) {
                Start-Sleep -Milliseconds 650
                $postTapXml = Get-UiDump -OutPath $lastDumpPath
                if ($postTapXml -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal') {
                    $opened = $true
                    break
                }
            }
            if ($opened) {
                break
            }
            Write-Step "login CTA did not open modal: $button"
        }
    }
    if (-not $opened) {
        return @{ attempted = $true; ok = $false; reason = 'login_open_failed' }
    }
    Start-Sleep -Milliseconds 1200

    $formReady = $false
    while ((Get-Date) -lt $loginDeadline) {
        $formXml = Get-UiDump -OutPath $lastDumpPath
        if ($formXml -match 'worldlinco-auth-email-input' -and $formXml -match 'worldlinco-auth-password-input' -and $formXml -match 'worldlinco-auth-login-submit-button') {
            $formReady = $true
            break
        }
        Start-Sleep -Milliseconds 600
    }
    if (-not $formReady) {
        return @{ attempted = $true; ok = $false; reason = 'login_form_timeout' }
    }

    if (-not (Enter-Field -Selector 'worldlinco-auth-email-input' -Value $LoginEmail)) {
        return @{ attempted = $true; ok = $false; reason = 'login_email_input_failed' }
    }
    if (-not (Enter-Field -Selector 'worldlinco-auth-password-input' -Value $password)) {
        return @{ attempted = $true; ok = $false; reason = 'login_password_input_failed' }
    }

    $submitTapped =
    (Tap-ByText -TextPattern '로그인 / 회원가입' -Retries 2 -DelayMs 500) -or
    (Tap-ByText -TextPattern '로그인' -Retries 2 -DelayMs 500) -or
    (Tap-BySelector -Selector 'worldlinco-auth-login-submit-button' -Retries 6 -DelayMs 750)

    if (-not $submitTapped) {
        return @{ attempted = $true; ok = $false; reason = 'login_submit_tap_failed' }
    }
    Write-Step "login submit tapped: worldlinco-auth-login-submit-button"

    $submitDeadline = (Get-Date).AddSeconds([Math]::Max(12, [Math]::Min(35, [int]([Math]::Round($LoginMaxWaitSec / 3.0)))))
    while ((Get-Date) -lt $submitDeadline) {
        $afterLogin = Get-UiDump -OutPath $lastDumpPath
        $authDebugAfterLogin = Get-AuthDebugStateSnapshot -Xml $afterLogin
        if ($authDebugAfterLogin -and ($authDebugAfterLogin.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return @{ attempted = $true; ok = $true; reason = 'login_success_auth_debug' }
        }
        if ($afterLogin -match $homePattern) {
            return @{ attempted = $true; ok = $true; reason = 'login_success' }
        }
        if ($afterLogin -match 'worldlinco-my-info-toggle|worldlinco-translate-home-button') {
            return @{ attempted = $true; ok = $true; reason = 'login_success' }
        }
        Start-Sleep -Milliseconds 800
    }

    if (Has-AuthReadyLogHint -TailLines 420) {
        return @{ attempted = $true; ok = $true; reason = 'login_success_log_hint' }
    }

    return @{ attempted = $true; ok = $false; reason = 'login_not_completed' }
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
            if ($text -match '상대 언어|GPS|수동|닫기|Close|language|선택|취소|회원가입|로그인') {
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

    # Device-proven fallback: first list option (English) center around x=198,y=522.
    Tap-At -X 198 -Y 522
    Start-Sleep -Milliseconds 500
    return $true
}

$flow = [ordered]@{
    faceHomeOpened   = $false
    langPickerOpened = $false
    peerLangSelected = $false
    faceMicTapped    = $false
}

Run-Adb @("logcat", "-c")
Write-Step "logcat cleared"
$sessionAlreadyReady = $false
try {
    $sessionAlreadyReady = Is-AuthenticatedSessionVisible
}
catch {
    $sessionAlreadyReady = $false
}
if ($sessionAlreadyReady) {
    Write-Step "existing live session detected; preserving current login state"
}
else {
    Reset-AppProcessAndCaptureSession
    Write-Step "pre-reset complete: force-stop + cooldown + home"
    Start-WorldlincoApp
    Write-Step "app launch requested: $PackageName"
    Start-Sleep -Seconds $LaunchDelaySec
}
Ensure-WorldlincoForeground | Out-Null
Write-Step "foreground confirmed: $PackageName"
[void](Dismiss-PermissionDialog -MaxAttempts 4)
Write-Step "permission dialog handled if present"

$loginState = Ensure-LoggedIn
Write-Step "login state: ok=$($loginState.ok) attempted=$($loginState.attempted) reason=$($loginState.reason)"

if (-not $loginState.ok) {
    & adb -s $DeviceId logcat -d -v time ReactNativeJS:I DevLauncher*:V Expo*:V *:S > $rawLogPath
    if ($LASTEXITCODE -ne 0) {
        Set-Content -Path $rawLogPath -Value "" -Encoding utf8
    }

    $loginDiagPatterns = @(
        'There was a problem loading the project',
        'This development build encountered the following error',
        'ConnectException',
        'Failed to connect to /',
        'null root node returned by UiTestAutomationBridge',
        'ReactNativeJS'
    )
    $diagMatches = Select-String -Path $rawLogPath -Pattern ($loginDiagPatterns -join '|') -CaseSensitive:$false
    $diagMatches | ForEach-Object { $_.Line } | Set-Content -Path $tracePath -Encoding utf8
    if (-not (Test-Path $tracePath)) {
        Set-Content -Path $tracePath -Value "" -Encoding utf8
    }

    $summary = [ordered]@{
        deviceId       = $DeviceId
        packageName    = $PackageName
        tap            = @{ x = $TapX; y = $TapY }
        login          = $loginState
        flow           = $flow
        runDir         = $runDir
        lastDumpPath   = $lastDumpPath
        rawLogPath     = $rawLogPath
        tracePath      = $tracePath
        requiredEvents = @('start_tap', 'capture_started', 'payload_prepared', 'post_start', 'response_received')
        missingEvents  = @('start_tap', 'capture_started', 'payload_prepared', 'post_start', 'response_received')
        pass           = $false
        blocked        = 'login_not_ready'
        capturedAtUtc  = (Get-Date).ToUniversalTime().ToString('o')
    }
    $summary | ConvertTo-Json -Depth 7 | Set-Content -Path $summaryPath -Encoding utf8
    Write-Step "blocked early: login not ready"
    Write-Output "FAIL: login not ready (reason=$($loginState.reason))"
    Write-Output "TRACE: $tracePath"
    Write-Output "SUMMARY: $summaryPath"
    return
}

$flow.faceHomeOpened = Tap-BySelector -Selector 'worldlinco-home-face-hero' -Retries 8 -DelayMs 900
Write-Step "face home open: $($flow.faceHomeOpened)"
if (-not $flow.faceHomeOpened) {
    $homeXml = Get-UiDump -OutPath $lastDumpPath
    if (Is-LoginLobbyVisible) {
        Write-Step "blocked before face home: login lobby still active; no worldlinco home hero visible"
        $summary = [ordered]@{
            deviceId       = $DeviceId
            packageName    = $PackageName
            tap            = @{ x = $TapX; y = $TapY }
            login          = $loginState
            flow           = $flow
            runDir         = $runDir
            lastDumpPath   = $lastDumpPath
            rawLogPath     = $rawLogPath
            tracePath      = $tracePath
            requiredEvents = @('start_tap', 'capture_started', 'payload_prepared', 'post_start', 'response_received')
            missingEvents  = @('start_tap', 'capture_started', 'payload_prepared', 'post_start', 'response_received')
            pass           = $false
            blocked        = 'login_lobby_not_home'
            capturedAtUtc  = (Get-Date).ToUniversalTime().ToString('o')
        }
        $summary | ConvertTo-Json -Depth 7 | Set-Content -Path $summaryPath -Encoding utf8
        Write-Output "FAIL: home hero blocked by unauthenticated lobby"
        return
    }
    Tap-At -X 400 -Y 650
    Start-Sleep -Milliseconds 800
}

if (-not (Is-FaceScreenVisible)) {
    # Retry with proven hero center once more when selector tap did not open modal.
    Tap-At -X 400 -Y 650
    Start-Sleep -Milliseconds 900
}

$langTap = (Tap-BySelector -Selector 'worldlinco-face-screen-lang' -Retries 6 -DelayMs 700) -or
(Tap-BySelector -Selector 'worldlinco-face-peer-lang' -Retries 3 -DelayMs 600) -or
(Tap-BySelector -Selector 'worldlinco-face-peer-lang-quick-open' -Retries 2 -DelayMs 500)
if (-not $langTap) {
    # Device-proven fallback coordinates on face screen.
    Tap-At -X 469 -Y 70
    Start-Sleep -Milliseconds 700
}
$flow.langPickerOpened = Is-PeerLanguagePickerVisible
if (-not $flow.langPickerOpened) {
    # Single stabilization retry: re-resolve selector after screen settle, then fallback once more.
    Start-Sleep -Milliseconds 450
    $langTapRetry = (Tap-BySelector -Selector 'worldlinco-face-screen-lang' -Retries 2 -DelayMs 450) -or
    (Tap-BySelector -Selector 'worldlinco-face-peer-lang' -Retries 2 -DelayMs 450)
    if (-not $langTapRetry) {
        Tap-At -X 469 -Y 70
        Start-Sleep -Milliseconds 500
    }
    $flow.langPickerOpened = Is-PeerLanguagePickerVisible
}
Write-Step "peer lang picker open: $($flow.langPickerOpened)"

if ($flow.langPickerOpened) {
    $flow.peerLangSelected = Select-PeerLanguageOption -Retries 5
}
Write-Step "peer lang selected: $($flow.peerLangSelected)"

$flow.faceMicTapped = Tap-BySelector -Selector 'worldlinco-face-screen-mic' -Retries 7 -DelayMs 700
if (-not $flow.faceMicTapped) {
    Tap-At -X 400 -Y 676
    $flow.faceMicTapped = $true
}
Write-Step "face mic tapped: $($flow.faceMicTapped)"

Start-Sleep -Seconds $CaptureSec
Write-Step "capture wait complete (${CaptureSec}s)"

& adb -s $DeviceId logcat -d -v time ReactNativeJS:I *:S > $rawLogPath
if ($LASTEXITCODE -ne 0) {
    throw "adb logcat dump failed"
}

$patterns = @(
    'FACE_CAPTURE_TRACE',
    'FACE_CAPTURE_BLOCK',
    'FACE_CONVERSATION',
    'COMPANION_HANDLER',
    'COMPANION_START_VOICE_ENTER',
    'COMPANION_START_VOICE_BLOCKED',
    'start_tap',
    'capture_started',
    'payload_prepared',
    'post_start',
    'response_received',
    'face_auto_voice_start_begin',
    'face_auto_voice_start_end',
    'peer_language_required',
    'capture_permission_denied',
    'segment_error'
)

$matches = Select-String -Path $rawLogPath -Pattern ($patterns -join '|') -CaseSensitive:$false
$matches | ForEach-Object { $_.Line } | Set-Content -Path $tracePath -Encoding utf8
if (-not (Test-Path $tracePath)) {
    Set-Content -Path $tracePath -Value "" -Encoding utf8
}

$traceText = Get-Content -Raw $tracePath
$requiredLegacy = @('start_tap', 'capture_started', 'payload_prepared', 'post_start', 'response_received')
$missingLegacy = @()
foreach ($event in $requiredLegacy) {
    if ($traceText -notmatch [regex]::Escape($event)) {
        $missingLegacy += $event
    }
}

$startSignalKeys = @(
    'start_tap',
    'capture_started',
    'face_auto_voice_start_begin',
    'face_auto_voice_start_end',
    'COMPANION_START_VOICE_ENTER',
    'COMPANION_START_VOICE_BLOCKED',
    'blocked_peer_language_required',
    'capture_blocked_speaking'
)
$networkSignalKeys = @(
    'payload_prepared',
    'post_start',
    'response_received',
    'segment_response',
    'segment_error'
)

$hasStartSignal = $false
foreach ($key in $startSignalKeys) {
    if ($traceText -match [regex]::Escape($key)) {
        $hasStartSignal = $true
        break
    }
}

$hasNetworkSignal = $false
foreach ($key in $networkSignalKeys) {
    if ($traceText -match [regex]::Escape($key)) {
        $hasNetworkSignal = $true
        break
    }
}

$passLegacy = ($missingLegacy.Count -eq 0)
$passLatest = $hasStartSignal -and $hasNetworkSignal
$pass = $passLegacy -or $passLatest

$summary = [ordered]@{
    deviceId       = $DeviceId
    packageName    = $PackageName
    tap            = @{ x = $TapX; y = $TapY }
    login          = $loginState
    flow           = $flow
    runDir         = $runDir
    lastDumpPath   = $lastDumpPath
    rawLogPath     = $rawLogPath
    tracePath      = $tracePath
    gateVersion    = 'face-events-v2'
    requiredLegacy = $requiredLegacy
    missingLegacy  = $missingLegacy
    checks         = [ordered]@{
        hasStartSignal   = $hasStartSignal
        hasNetworkSignal = $hasNetworkSignal
        passLegacy       = $passLegacy
        passLatest       = $passLatest
    }
    pass           = $pass
    capturedAtUtc  = (Get-Date).ToUniversalTime().ToString('o')
}
$summary | ConvertTo-Json -Depth 7 | Set-Content -Path $summaryPath -Encoding utf8

if ($pass) {
    Write-Step "result: PASS"
    Write-Output "PASS: face-capture events matched (legacy or latest gate)"
}
else {
    Write-Step "result: FAIL missingLegacy=$($missingLegacy -join ',')"
    Write-Output "FAIL: missing legacy events -> $($missingLegacy -join ', ')"
}
Write-Output "TRACE: $tracePath"
Write-Output "SUMMARY: $summaryPath"
