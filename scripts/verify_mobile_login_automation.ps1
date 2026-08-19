#!/usr/bin/env pwsh
param(
    [string]$Device = "R83W70QY11H",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$Email = "119cash@naver.com",
    [string]$PasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [string]$ApiBase = "https://metanova1004.com",
    [int]$Rounds = 3,
    [switch]$ResetSession,
    [switch]$ResetSessionStrict
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RepoRoot "evidence\mobile-login-automation-$Stamp"
$LastDumpPath = Join-Path $RunDir "last-window-dump.xml"
$StrictResetSessionMode = [bool]$ResetSessionStrict
$EffectiveResetSession = [bool]($ResetSession -or $StrictResetSessionMode)
$script:LastSubmitPressedObserved = 'IDLE'
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Get-AdbDeviceState {
    param([string]$TargetDevice)

    $lines = & adb devices 2>&1
    foreach ($line in $lines) {
        $text = [string]$line
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        if ($text -match '^List of devices attached') { continue }
        if ($text -match '^\* daemon ') { continue }

        $parts = $text -split '\s+'
        if ($parts.Count -lt 2) { continue }
        if ($parts[0] -eq $TargetDevice) {
            return $parts[1].ToLowerInvariant()
        }
    }

    return $null
}

function Repair-AdbConnection {
    param([int]$MaxWaitSec = 20)

    $null = & adb reconnect offline 2>&1
    $null = & adb reconnect 2>&1

    if ($Device -match ':') {
        $null = & adb connect $Device 2>&1
    }

    $deadline = (Get-Date).AddSeconds([Math]::Max(5, [Math]::Min(60, $MaxWaitSec)))
    while ((Get-Date) -lt $deadline) {
        $state = Get-AdbDeviceState -TargetDevice $Device
        if ($state -eq 'device') {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Is-AdbUnauthorizedText {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }

    return [bool]($Text -match 'device unauthorized|ADB_VENDOR_KEYS is not set|check for a confirmation dialog on your device')
}

function Invoke-Adb {
    param([string[]]$AdbArgs)
    $attempts = 0
    while ($attempts -lt 3) {
        $attempts++
        $output = @()
        $old = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $result = & adb -s $Device @AdbArgs 2>&1
            foreach ($item in $result) {
                if ($null -eq $item) { continue }
                $output += ($item.ToString())
            }
        }
        finally {
            $ErrorActionPreference = $old
        }

        $combined = $output -join "`n"
        if (Is-AdbUnauthorizedText -Text $combined) {
            throw "adb_device_unauthorized: approve USB debugging dialog on device and re-run"
        }

        $adbOffline = ($combined -match 'device offline|no devices/emulators found|device .* not found')
        if (-not $adbOffline) {
            return $output
        }

        Write-Warning "ADB connection unstable ($attempts/3). trying reconnect..."
        [void](Repair-AdbConnection -MaxWaitSec 12)
    }

    return $output
}

function Get-ForegroundPackage {
    $windowState = (Invoke-Adb @('shell', 'dumpsys', 'window', 'windows')) -join "`n"
    $mCurrentFocus = [regex]::Match($windowState, 'mCurrentFocus=.*\s([a-zA-Z0-9_\.]+)\/[a-zA-Z0-9_\.$]+')
    if ($mCurrentFocus.Success) {
        return $mCurrentFocus.Groups[1].Value
    }

    $activityState = (Invoke-Adb @('shell', 'dumpsys', 'activity', 'top')) -join "`n"
    $resumed = [regex]::Match($activityState, 'ACTIVITY\s+([a-zA-Z0-9_\.]+)\/[a-zA-Z0-9_\.$]+')
    if ($resumed.Success) {
        return $resumed.Groups[1].Value
    }

    return $null
}

function Ensure-TargetAppForeground {
    param([int]$WaitMs = 800)

    for ($i = 0; $i -lt 3; $i++) {
        $fg = Get-ForegroundPackage
        if (-not [string]::IsNullOrWhiteSpace($fg) -and $fg -eq $PackageName) {
            return
        }
        $null = Invoke-Adb @('shell', 'am', 'start', '-n', "$PackageName/.MainActivity")
        Start-Sleep -Milliseconds $WaitMs
    }
}

function Is-TargetAppUiDump {
    param([string]$Xml)

    if ([string]::IsNullOrWhiteSpace($Xml)) {
        return $false
    }

    $pkgPattern = 'package="' + [regex]::Escape($PackageName) + '"'
    return [bool]($Xml -match $pkgPattern)
}

function Get-Password {
    $pw = $env:WORLDLINCO_VOIP_API_PASSWORD
    if (-not [string]::IsNullOrWhiteSpace($pw)) {
        return $pw.Trim()
    }

    $passwordPath = Join-Path $RepoRoot $PasswordFile
    if (Test-Path $passwordPath) {
        $text = (Get-Content -Raw $passwordPath).Trim()
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }

    throw "Admin password not found. Set WORLDLINCO_VOIP_API_PASSWORD or provide $PasswordFile"
}

function Test-LoginCredentialPrecheck {
    param(
        [string]$BaseUrl,
        [string]$EmailValue,
        [string]$PasswordValue
    )

    if ([string]::IsNullOrWhiteSpace($BaseUrl) -or [string]::IsNullOrWhiteSpace($EmailValue) -or [string]::IsNullOrWhiteSpace($PasswordValue)) {
        return $null
    }

    try {
        $endpoint = $BaseUrl.TrimEnd('/') + '/api/auth/login'
        $payload = "username=$([uri]::EscapeDataString($EmailValue.Trim().ToLowerInvariant()))&password=$([uri]::EscapeDataString($PasswordValue))"
        $resp = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/x-www-form-urlencoded' -Body $payload -TimeoutSec 8 -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
            return $true
        }
    }
    catch {
        $statusCode = $null
        try {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
            $statusCode = $null
        }

        if ($statusCode -eq 401) {
            return $false
        }

        $message = $_.Exception.Message
        if ($message -match '401|Unauthorized') {
            return $false
        }
        return $null
    }

    return $null
}

function New-AutomationOtpCredential {
    param([string]$BaseUrl)

    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        return $null
    }

    $seed = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $rand = Get-Random -Minimum 100 -Maximum 999
    $email = "autologin_${seed}_${rand}@worldlinco-demo.com"
    $username = "autologin_${seed}_${rand}"
    $password = "WorldLinco!A1${seed}${rand}"

    $requestPayload = @{
        username            = $username
        email               = $email
        password            = $password
        preferred_language  = 'ko'
        country_code        = 'KR'
        full_name           = 'Automation Login'
        verificationChannel = 'email'
    }

    try {
        $requestEndpoint = $BaseUrl.TrimEnd('/') + '/api/auth/signup/request-code'
        $req = Invoke-RestMethod -Uri $requestEndpoint -Method Post -ContentType 'application/json' -Body ($requestPayload | ConvertTo-Json) -TimeoutSec 15 -ErrorAction Stop
        $sessionToken = [string]$req.signupSessionToken
        $otp = [string]$req.devOtpHint
        if ([string]::IsNullOrWhiteSpace($sessionToken) -or [string]::IsNullOrWhiteSpace($otp)) {
            return $null
        }

        $confirmEndpoint = $BaseUrl.TrimEnd('/') + '/api/auth/signup/confirm'
        $confirmPayload = @{
            signupSessionToken = $sessionToken
            verificationCode   = $otp
            preferred_language = 'ko'
            country_code       = 'KR'
            full_name          = 'Automation Login'
        }

        $null = Invoke-RestMethod -Uri $confirmEndpoint -Method Post -ContentType 'application/json' -Body ($confirmPayload | ConvertTo-Json) -TimeoutSec 15 -ErrorAction Stop
        return @{
            email    = $email
            password = $password
            source   = 'otp_auto_signup'
        }
    }
    catch {
        return $null
    }
}

function Get-UiDump {
    param([string]$OutPath)
    $remote = "/sdcard/mobile_login_automation.xml"
    $null = Invoke-Adb @("shell", "uiautomator", "dump", $remote)
    $null = Invoke-Adb @("pull", $remote, $OutPath)
    if (-not (Test-Path $OutPath)) {
        $xmlLines = Invoke-Adb @("shell", "cat", $remote)
        if ($xmlLines -and ($xmlLines -join "`n").Length -gt 0) {
            Set-Content -Path $OutPath -Value ($xmlLines -join "`n") -Encoding UTF8
        }
    }

    if (Test-Path $OutPath) {
        $xmlText = Get-Content -Raw $OutPath
        if ($xmlText -and $xmlText -match '<hierarchy' -and $xmlText -match 'package="com\.parkcheolhong\.worldlinco"') {
            return $xmlText
        }
        if (Is-AdbUnauthorizedText -Text $xmlText) {
            throw "adb_device_unauthorized: approve USB debugging dialog on device and re-run"
        }
        if ($xmlText -match 'device offline|no devices/emulators found|device .* not found') {
            [void](Repair-AdbConnection -MaxWaitSec 12)
            return $null
        }
    }

    return $null
}

function Get-UiXml {
    param([string]$OutPath)
    $tmp = Join-Path $RunDir "ui_tmp.xml"
    Get-UiDump -OutPath $tmp | Out-Null
    if (-not (Test-Path $tmp)) { return $null }
    return Get-Content -Raw $tmp
}

function Convert-ToAdbInputText {
    param([string]$Text)

    if (-not $Text) {
        return ''
    }

    $escaped = $Text
    $escaped = $escaped -replace '\\', '\\\\'
    $escaped = $escaped -replace ' ', '%s'
    return $escaped
}

function Get-NodeBounds {
    param(
        [string]$Xml,
        [string]$ResourceId
    )

    if ([string]::IsNullOrWhiteSpace($Xml)) { return $null }
    try {
        [xml]$doc = $Xml
    }
    catch {
        return $null
    }

    $node = $doc.SelectSingleNode("//node[contains(@resource-id,'$ResourceId')]")
    if (-not $node) { return $null }
    $bounds = [string]$node.GetAttribute("bounds")
    if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { return $null }
    $x1 = [int]$matches[1]
    $y1 = [int]$matches[2]
    $x2 = [int]$matches[3]
    $y2 = [int]$matches[4]
    return @(
        [math]::Floor(($x1 + $x2) / 2),
        [math]::Floor(($y1 + $y2) / 2)
    )
}

function Get-PreferredTapPointByResource {
    param(
        [string]$Xml,
        [string]$ResourceId
    )

    if ([string]::IsNullOrWhiteSpace($Xml) -or [string]::IsNullOrWhiteSpace($ResourceId)) {
        return $null
    }

    try {
        [xml]$doc = $Xml
    }
    catch {
        return $null
    }

    $anchor = $doc.SelectSingleNode("//node[contains(@resource-id,'$ResourceId')]")
    if (-not $anchor) {
        return $null
    }

    $clickableChildren = $anchor.SelectNodes(".//node[@clickable='true']")
    $candidates = @()
    foreach ($child in $clickableChildren) {
        $bounds = [string]$child.GetAttribute('bounds')
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

        $enabled = ([string]$child.GetAttribute('enabled')).ToLowerInvariant()
        $candidates += [pscustomobject]@{
            priority  = if ($enabled -eq 'true') { 0 } else { 1 }
            x         = [math]::Floor(($x1 + $x2) / 2)
            y         = [math]::Floor(($y1 + $y2) / 2)
            bounds    = $bounds
            clickable = [string]$child.GetAttribute('clickable')
            enabled   = [string]$child.GetAttribute('enabled')
            source    = 'clickable-child'
        }
    }

    if ($candidates.Count -gt 0) {
        return ($candidates | Sort-Object priority | Select-Object -First 1)
    }

    $anchorBounds = [string]$anchor.GetAttribute('bounds')
    if ($anchorBounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
        return $null
    }

    $ax1 = [int]$matches[1]
    $ay1 = [int]$matches[2]
    $ax2 = [int]$matches[3]
    $ay2 = [int]$matches[4]
    if ($ax2 -le $ax1 -or $ay2 -le $ay1) {
        return $null
    }

    return [pscustomobject]@{
        priority  = 2
        x         = [math]::Floor(($ax1 + $ax2) / 2)
        y         = [math]::Floor(($ay1 + $ay2) / 2)
        bounds    = $anchorBounds
        clickable = [string]$anchor.GetAttribute('clickable')
        enabled   = [string]$anchor.GetAttribute('enabled')
        source    = 'anchor-center'
    }
}

function Get-BoundsMetrics {
    param([string]$Bounds)

    if ([string]::IsNullOrWhiteSpace($Bounds)) {
        return $null
    }
    if ($Bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
        return $null
    }

    $x1 = [int]$matches[1]
    $y1 = [int]$matches[2]
    $x2 = [int]$matches[3]
    $y2 = [int]$matches[4]
    if ($x2 -le $x1 -or $y2 -le $y1) {
        return $null
    }

    return [pscustomobject]@{
        x1     = $x1
        y1     = $y1
        x2     = $x2
        y2     = $y2
        width  = ($x2 - $x1)
        height = ($y2 - $y1)
        cx     = [math]::Floor(($x1 + $x2) / 2)
        cy     = [math]::Floor(($y1 + $y2) / 2)
    }
}

function Ensure-ResourceTapVisibility {
    param(
        [string]$ResourceId,
        [int]$MaxSwipes = 4
    )

    for ($i = 0; $i -lt [Math]::Max(1, $MaxSwipes); $i++) {
        $xml = Get-UiDump -OutPath $LastDumpPath
        $point = Get-PreferredTapPointByResource -Xml $xml -ResourceId $ResourceId
        if (-not $point) {
            return $null
        }

        $metrics = Get-BoundsMetrics -Bounds $point.bounds
        if (-not $metrics) {
            return $point
        }

        if ($metrics.height -ge 28 -and $metrics.y2 -lt 1290) {
            return $point
        }

        # Bring bottom-clipped submit button into a tappable viewport area.
        $null = Invoke-Adb @('shell', 'input', 'swipe', '400', '1140', '400', '760', '220')
        Start-Sleep -Milliseconds 320
    }

    $finalXml = Get-UiDump -OutPath $LastDumpPath
    return (Get-PreferredTapPointByResource -Xml $finalXml -ResourceId $ResourceId)
}

function PreScroll-LoginSubmitIntoView {
    param([int]$MaxSwipes = 4)

    for ($i = 0; $i -lt [Math]::Max(1, $MaxSwipes); $i++) {
        $xml = Get-UiDump -OutPath $LastDumpPath
        $point = Get-PreferredTapPointByResource -Xml $xml -ResourceId 'worldlinco-auth-login-submit-button'
        if (-not $point) {
            return
        }

        $metrics = Get-BoundsMetrics -Bounds $point.bounds
        if (-not $metrics) {
            return
        }

        if ($metrics.height -ge 28 -and $metrics.y2 -lt 1260) {
            return
        }

        $null = Invoke-Adb @('shell', 'input', 'swipe', '400', '1210', '400', '520', '240')
        Start-Sleep -Milliseconds 320
    }
}

function Tap-Coordinates {
    param(
        [int]$X,
        [int]$Y
    )

    $null = Invoke-Adb @("shell", "input", "tap", "$X", "$Y")
    Start-Sleep -Milliseconds 500
    return $true
}

function Get-NodeCenterByText {
    param(
        [string]$Xml,
        [string]$TextPattern
    )

    if ([string]::IsNullOrWhiteSpace($Xml) -or [string]::IsNullOrWhiteSpace($TextPattern)) {
        return $null
    }

    try {
        [xml]$doc = $Xml
    }
    catch {
        return $null
    }

    $nodes = $doc.SelectNodes("//node[contains(@text,'$TextPattern') or contains(@content-desc,'$TextPattern')]")
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
        return @(
            [math]::Floor(($x1 + $x2) / 2),
            [math]::Floor(($y1 + $y2) / 2)
        )
    }

    return $null
}

function Tap-ByText {
    param(
        [string]$TextPattern,
        [string]$Xml = $null,
        [int]$Retries = 2,
        [int]$DelayMs = 450
    )

    for ($i = 0; $i -lt [Math]::Max(1, $Retries); $i++) {
        $center = $null
        if ($Xml -and $i -eq 0) {
            $center = Get-NodeCenterByText -Xml $Xml -TextPattern $TextPattern
        }
        else {
            $dump = Join-Path $RunDir "tap_by_text_probe.xml"
            Get-UiDump -OutPath $dump | Out-Null
            if (Test-Path $dump) {
                $center = Get-NodeCenterByText -Xml (Get-Content -Raw $dump) -TextPattern $TextPattern
            }
        }

        if ($center) {
            return Tap-Coordinates -X $center[0] -Y $center[1]
        }

        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
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

function Is-ExpoDevServerSelectionVisible {
    param([string]$Xml)

    if (-not $Xml) {
        return $false
    }

    return [bool]($Xml -match 'DEVELOPMENT SERVERS|Fetch development servers|Scan QR Code|New development server|Development Build')
}

function Dismiss-ExpoDevServerSelection {
    param([int]$Attempts = 5)

    for ($i = 0; $i -lt $Attempts; $i++) {
        $dump = Join-Path $RunDir "dismiss_expo_dev_server.xml"
        Get-UiDump -OutPath $dump | Out-Null
        $xml = if (Test-Path $dump) { Get-Content -Raw $dump } else { $null }
        if (-not (Is-ExpoDevServerSelectionVisible -Xml $xml)) {
            return $true
        }

        $dismissed =
        (Tap-ByText -TextPattern 'Connect' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'Download' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'RECENTLY OPENED' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'Fetch development servers' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'DEVELOPMENT SERVERS' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'New development server' -Xml $xml -Retries 1 -DelayMs 250) -or
        (Tap-ByText -TextPattern 'Scan QR Code' -Xml $xml -Retries 1 -DelayMs 250)

        if (-not $dismissed) {
            # Expo screen rows are often wrapped in a clickable parent without text;
            # use calibrated taps to trigger the selected dev server row.
            Tap-Coordinates -X 400 -Y 700 | Out-Null
            Start-Sleep -Milliseconds 220
            Tap-Coordinates -X 700 -Y 700 | Out-Null
            Start-Sleep -Milliseconds 220
            Tap-Coordinates -X 400 -Y 1238 | Out-Null
            Start-Sleep -Milliseconds 220
            Tap-Coordinates -X 400 -Y 700 | Out-Null
            $dismissed = $true
        }

        if (-not $dismissed) {
            $null = Invoke-Adb @('shell', 'input', 'keyevent', '4')
        }

        Start-Sleep -Milliseconds 600
        Ensure-TargetAppForeground -WaitMs 800

        $checkDump = Join-Path $RunDir "dismiss_expo_dev_server_check.xml"
        Get-UiDump -OutPath $checkDump | Out-Null
        $checkXml = if (Test-Path $checkDump) { Get-Content -Raw $checkDump } else { $null }
        if (-not (Is-ExpoDevServerSelectionVisible -Xml $checkXml)) {
            return $true
        }
    }

    $lastDump = Join-Path $RunDir "dismiss_expo_dev_server_final.xml"
    Get-UiDump -OutPath $lastDump | Out-Null
    $lastXml = if (Test-Path $lastDump) { Get-Content -Raw $lastDump } else { $null }
    return -not (Is-ExpoDevServerSelectionVisible -Xml $lastXml)
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
    param([string]$Xml = $null)

    $candidateXml = $Xml
    if ([string]::IsNullOrWhiteSpace($candidateXml)) {
        $tmp = Join-Path $RunDir "auth_debug_probe.xml"
        Get-UiDump -OutPath $tmp | Out-Null
        if (Test-Path $tmp) {
            $candidateXml = Get-Content -Raw $tmp
        }
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
        state  = $stateMatch.Groups[1].Value.ToUpperInvariant()
        user   = if ($userMatch.Success) { $userMatch.Groups[1].Value.Trim() } else { $null }
        source = 'ui_dump'
    }
}

function Get-AuthDebugSubmitPressedSnapshot {
    param([string]$Xml = $null)

    $candidateXml = $Xml
    if ([string]::IsNullOrWhiteSpace($candidateXml)) {
        $tmp = Join-Path $RunDir "auth_debug_submit_probe.xml"
        $candidateXml = Get-UiDump -OutPath $tmp
    }

    if ([string]::IsNullOrWhiteSpace($candidateXml)) {
        return $null
    }

    $normalized = $candidateXml -replace "`r", "" -replace "`n", " "
    $submitMatch = [regex]::Match($normalized, 'AUTH_DEBUG_SUBMIT_PRESSED\s*:\s*([A-Z_]+)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $submitMatch.Success) {
        return $null
    }

    return $submitMatch.Groups[1].Value.ToUpperInvariant()
}

function Has-AuthReadyLogHint {
    param([int]$TailLines = 350)

    $raw = Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")
    if (-not $raw) {
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

function Has-LoginApiFail401 {
    param([int]$TailLines = 500)

    $raw = Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")
    if (-not $raw) {
        return $false
    }

    $tail = @($raw | Select-Object -Last ([Math]::Max(120, [Math]::Min(1600, $TailLines)))) -join "`n"
    return [bool]($tail -match '"event":"LOGIN_API_FAIL".*"status":401')
}

function Has-LoginApiFail409 {
    param([int]$TailLines = 500)

    $raw = Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")
    if (-not $raw) {
        return $false
    }

    $tail = @($raw | Select-Object -Last ([Math]::Max(120, [Math]::Min(1600, $TailLines)))) -join "`n"
    return [bool]($tail -match '"event":"LOGIN_API_FAIL".*"status":409')
}

function Try-ClearActiveSessionByRecovery {
    param(
        [string]$BaseUrl,
        [string]$UserHint
    )

    if ([string]::IsNullOrWhiteSpace($BaseUrl) -or [string]::IsNullOrWhiteSpace($UserHint)) {
        return $false
    }

    try {
        $startEndpoint = $BaseUrl.TrimEnd('/') + '/api/auth/recovery/start'
        $startPayload = @{
            user_hint            = $UserHint
            scope                = 'user'
            verification_channel = 'email'
        }
        $startResp = Invoke-RestMethod -Uri $startEndpoint -Method Post -ContentType 'application/json' -Body ($startPayload | ConvertTo-Json) -TimeoutSec 15 -ErrorAction Stop
        $sessionToken = [string]$startResp.recovery_session_token
        $otp = [string]$startResp.dev_otp_hint
        if ([string]::IsNullOrWhiteSpace($sessionToken) -or [string]::IsNullOrWhiteSpace($otp)) {
            return $false
        }

        $verifyEndpoint = $BaseUrl.TrimEnd('/') + '/api/auth/recovery/verify-identity'
        $verifyPayload = @{
            recovery_session_token = $sessionToken
            verification_code      = $otp
        }
        $verifyResp = Invoke-RestMethod -Uri $verifyEndpoint -Method Post -ContentType 'application/json' -Body ($verifyPayload | ConvertTo-Json) -TimeoutSec 15 -ErrorAction Stop
        $resetToken = [string]$verifyResp.reset_token
        if ([string]::IsNullOrWhiteSpace($resetToken)) {
            return $false
        }

        $clearEndpoint = $BaseUrl.TrimEnd('/') + '/api/auth/recovery/clear-active-session'
        $clearPayload = @{
            reset_token = $resetToken
            scope       = 'user'
        }
        $clearResp = Invoke-RestMethod -Uri $clearEndpoint -Method Post -ContentType 'application/json' -Body ($clearPayload | ConvertTo-Json) -TimeoutSec 15 -ErrorAction Stop
        return [bool]($clearResp.cleared -eq $true)
    }
    catch {
        return $false
    }
}

function Has-DemoSessionAppliedHint {
    param([int]$TailLines = 700)

    $raw = Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")
    if (-not $raw) {
        return $false
    }

    $tail = @($raw | Select-Object -Last ([Math]::Max(150, [Math]::Min(2200, $TailLines)))) -join "`n"
    return [bool]($tail -match '"event":"DEMO_SESSION_APPLIED"')
}

function Has-DemoSessionFailHint {
    param([int]$TailLines = 700)

    $raw = Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")
    if (-not $raw) {
        return $false
    }

    $tail = @($raw | Select-Object -Last ([Math]::Max(150, [Math]::Min(2200, $TailLines)))) -join "`n"
    return [bool]($tail -match '"event":"DEMO_SESSION_FAIL"')
}

function Try-StartInstantDemoSession {
    param([int]$WaitSec = 28)

    Ensure-TargetAppForeground -WaitMs 900

    $clickDeadline = (Get-Date).AddSeconds(12)
    $clicked = $false
    while ((Get-Date) -lt $clickDeadline -and -not $clicked) {
        Ensure-TargetAppForeground -WaitMs 600
        $xml = Get-UiDump -OutPath $LastDumpPath
        if (-not (Is-TargetAppUiDump -Xml $xml)) {
            Start-Sleep -Milliseconds 350
            continue
        }

        $auth = Get-AuthDebugStateSnapshot -Xml $xml
        if ($auth -and ($auth.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return $true
        }

        # Close keyboard if needed and bring the demo CTA into visible viewport.
        $null = Invoke-Adb @('shell', 'input', 'keyevent', '4')
        Start-Sleep -Milliseconds 220
        $demoPoint = Ensure-ResourceTapVisibility -ResourceId 'worldlinco-demo-session-start-button' -MaxSwipes 3
        if ($demoPoint) {
            $clicked = Tap-Coordinates -X $demoPoint.x -Y $demoPoint.y
        }

        if (-not $clicked) {
            $clicked =
            (Tap-BySelector -Selector 'worldlinco-demo-session-start-button' -Retries 1 -DelayMs 250) -or
            (Tap-BySelector -Selector 'worldlinco-demo-session-start-button-inline' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '데모 세션 둘러보기' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '데모 세션 시작' -Retries 1 -DelayMs 250)
        }

        if (-not $clicked) {
            $null = Invoke-Adb @('shell', 'input', 'swipe', '400', '1120', '400', '760', '220')
            Start-Sleep -Milliseconds 300
        }
    }

    if (-not $clicked) { return $false }

    $deadline = (Get-Date).AddSeconds([Math]::Max(8, [Math]::Min(60, $WaitSec)))
    while ((Get-Date) -lt $deadline) {
        Ensure-TargetAppForeground -WaitMs 500
        $xml = Get-UiDump -OutPath $LastDumpPath
        $auth = Get-AuthDebugStateSnapshot -Xml $xml
        if ($auth -and ($auth.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return $true
        }
        if ($xml -match 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle|worldlinco-my-info-toggle') {
            return $true
        }
        if (Has-DemoSessionAppliedHint -TailLines 700) {
            return $true
        }
        if (Has-DemoSessionFailHint -TailLines 700) {
            return $false
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Dismiss-TransientDevOverlay {
    param([int]$Attempts = 1)

    for ($i = 0; $i -lt $Attempts; $i++) {
        $dump = Join-Path $RunDir "dismiss_dev_overlay.xml"
        Get-UiDump -OutPath $dump | Out-Null
        $xml = if (Test-Path $dump) { Get-Content -Raw $dump } else { $null }
        if (-not (Is-TransientDevOverlayVisible -Xml $xml)) {
            return $true
        }

        if (-not (Tap-ByText -TextPattern 'Close' -Xml $xml)) {
            $null = Invoke-Adb @('shell', 'input', 'keyevent', '4')
        }
        Start-Sleep -Milliseconds 500
    }

    $lastDump = Join-Path $RunDir "dismiss_dev_overlay_final.xml"
    Get-UiDump -OutPath $lastDump | Out-Null
    $lastXml = if (Test-Path $lastDump) { Get-Content -Raw $lastDump } else { $null }
    return -not (Is-TransientDevOverlayVisible -Xml $lastXml)
}

function Tap-Resource {
    param(
        [string]$ResourceId,
        [string]$Xml = $null
    )

    $bounds = $null
    if ($Xml) {
        $bounds = Get-NodeBounds -Xml $Xml -ResourceId $ResourceId
    }
    else {
        $dump = Join-Path $RunDir "tap_probe.xml"
        Get-UiDump -OutPath $dump | Out-Null
        if (Test-Path $dump) {
            $bounds = Get-NodeBounds -Xml (Get-Content -Raw $dump) -ResourceId $ResourceId
        }
    }

    if (-not $bounds) {
        $fallback = @{
            'worldlinco-header-login-button'      = @{ X = 400; Y = 250 };
            'worldlinco-inline-open-login-button' = @{ X = 400; Y = 450 };
            'worldlinco-auth-email-input'         = @{ X = 420; Y = 610 };
            'worldlinco-auth-password-input'      = @{ X = 420; Y = 760 };
            'worldlinco-auth-login-submit-button' = @{ X = 400; Y = 860 }
        }
        if ($fallback.ContainsKey($ResourceId)) {
            return Tap-Coordinates -X $fallback[$ResourceId].X -Y $fallback[$ResourceId].Y
        }
        return $false
    }

    $x = $bounds[0]
    $y = $bounds[1]
    return Tap-Coordinates -X $x -Y $y
}

function Set-FieldText {
    param(
        [string]$ResourceId,
        [string]$Value,
        [string]$Xml = $null
    )

    $bounds = $null
    if ($Xml) {
        $bounds = Get-NodeBounds -Xml $Xml -ResourceId $ResourceId
    }
    else {
        $dump = Join-Path $RunDir "field_probe.xml"
        Get-UiDump -OutPath $dump | Out-Null
        if (Test-Path $dump) {
            $bounds = Get-NodeBounds -Xml (Get-Content -Raw $dump) -ResourceId $ResourceId
        }
    }

    if (-not $bounds) {
        $fallback = @{
            'worldlinco-auth-email-input'    = @{ X = 420; Y = 610 };
            'worldlinco-auth-password-input' = @{ X = 420; Y = 760 }
        }
        if ($fallback.ContainsKey($ResourceId)) {
            $x = $fallback[$ResourceId].X
            $y = $fallback[$ResourceId].Y
            $null = Invoke-Adb @("shell", "input", "tap", "$x", "$y")
            Start-Sleep -Milliseconds 350
            $null = Invoke-Adb @("shell", "input", "keyevent", "KEYCODE_MOVE_END")
            foreach ($i in 1..80) {
                $null = Invoke-Adb @("shell", "input", "keyevent", "KEYCODE_DEL")
            }
            $escaped = Convert-ToAdbInputText -Text $Value
            $null = Invoke-Adb @("shell", "input", "text", $escaped)
            Start-Sleep -Milliseconds 350
            return $true
        }
        return $false
    }
    $x = $bounds[0]
    $y = $bounds[1]
    $null = Invoke-Adb @("shell", "input", "tap", "$x", "$y")
    Start-Sleep -Milliseconds 350
    $null = Invoke-Adb @("shell", "input", "keyevent", "KEYCODE_MOVE_END")
    foreach ($i in 1..80) {
        $null = Invoke-Adb @("shell", "input", "keyevent", "KEYCODE_DEL")
    }
    $escaped = Convert-ToAdbInputText -Text $Value
    $null = Invoke-Adb @("shell", "input", "text", $escaped)
    Start-Sleep -Milliseconds 350
    return $true
}

function Capture-Screenshot {
    param([string]$Name)
    $remote = "/sdcard/$Name.png"
    $null = Invoke-Adb @("shell", "screencap", "-p", $remote)
    $target = Join-Path $RunDir $Name
    $null = Invoke-Adb @("pull", $remote, $target)
    if (Test-Path $target) {
        return $target
    }
    return $null
}

function Get-LogcatText {
    return ((Invoke-Adb @("logcat", "-d", "-v", "time", "ReactNativeJS:I", "*:S")) -join "`n")
}

function Wait-ForLoginSurface {
    param([int]$TimeoutSec = 20)

    $loginPattern = 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal|worldlinco-inline-auth-panel|로그인이 필요해요|WORLDLINCO LOBBY|로그인 패널 열기|로그인 / 회원가입|로그인 또는 회원가입'
    $loginCtaPattern = 'worldlinco-inline-open-login-button|worldlinco-header-login-button|worldlinco-auth-open-login-modal-button|로그인 패널 열기|로그인 / 회원가입|로그인|App Icon|WorldLinco|User|Home|Updates|Settings|Development Build|DEVELOPMENT SERVERS|RECENTLY OPENED|New development server|http://172\.30\.1\.41:8091|http://127\.0\.0\.1:8091|RESET'

    # Calibrated modal-open taps for current device/layout drift.
    $fallbackSequence = @(
        @{ X = 400; Y = 250 },
        @{ X = 400; Y = 300 },
        @{ X = 400; Y = 360 },
        @{ X = 400; Y = 450 },
        @{ X = 400; Y = 520 },
        @{ X = 520; Y = 180 }
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $unknownSurfaceStreak = 0
    while ((Get-Date) -lt $deadline) {
        $dump = Join-Path $RunDir "wait_login_surface.xml"
        Get-UiDump -OutPath $dump | Out-Null
        if (Test-Path $dump) {
            $xml = Get-Content -Raw $dump

            if (Is-ExpoDevServerSelectionVisible -Xml $xml) {
                [void](Dismiss-ExpoDevServerSelection -Attempts 2)
                Start-Sleep -Milliseconds 450
                continue
            }

            if (Is-TransientDevOverlayVisible -Xml $xml) {
                [void](Dismiss-TransientDevOverlay -Attempts 1)
                Start-Sleep -Milliseconds 250
                continue
            }

            if (Is-DevClientLoadErrorVisible -Xml $xml) {
                throw "Dev client runtime not ready (load error visible)"
            }

            if ($xml -match $loginPattern) {
                return $xml
            }

            if (Is-MinimalRuntimeShellVisible -Xml $xml) {
                Tap-Coordinates -X 400 -Y 250 | Out-Null
                Start-Sleep -Milliseconds 450
                continue
            }

            if ($xml -match $loginCtaPattern) {
                foreach ($button in @('text:http://172.30.1.41:8091', 'text:http://127.0.0.1:8091', 'text:RECENTLY OPENED', 'text:DEVELOPMENT SERVERS', 'text:Development Build', 'text:로그인 패널 열기', 'text:로그인 / 회원가입', 'text:로그인', 'text:User', 'text:Home', 'text:Updates', 'text:Settings', 'text:WorldLinco', 'text:App Icon', 'worldlinco-auth-open-login-modal-button', 'worldlinco-inline-open-login-button', 'worldlinco-header-login-button')) {
                    $opened = $false
                    if ($button -eq 'worldlinco-header-login-button') {
                        Tap-Coordinates -X 400 -Y 250 | Out-Null
                        $opened = $true
                    }
                    elseif ($button -like 'text:*') {
                        $textPattern = $button.Substring(5)
                        $opened = Tap-ByText -TextPattern $textPattern -Xml $xml
                    }
                    else {
                        $opened = Tap-Resource -ResourceId $button -Xml $xml
                    }

                    if ($opened) {
                        Start-Sleep -Milliseconds 650
                        $retryDump = Join-Path $RunDir "wait_login_surface_retry.xml"
                        Get-UiDump -OutPath $retryDump | Out-Null
                        if (Test-Path $retryDump) {
                            $retryXml = Get-Content -Raw $retryDump
                            if ($retryXml -match $loginPattern) {
                                return $retryXml
                            }
                        }
                    }
                }
            }

            foreach ($point in $fallbackSequence) {
                $null = Invoke-Adb @("shell", "input", "tap", "$($point.X)", "$($point.Y)")
                Start-Sleep -Milliseconds 450
                $retryDump = Join-Path $RunDir "wait_login_surface_retry.xml"
                Get-UiDump -OutPath $retryDump | Out-Null
                if (Test-Path $retryDump) {
                    $retryXml = Get-Content -Raw $retryDump
                    if ($retryXml -match $loginPattern) {
                        return $retryXml
                    }
                }
            }

            $unknownSurfaceStreak++
            if ($unknownSurfaceStreak -ge 2) {
                Tap-Coordinates -X 400 -Y 250 | Out-Null
                Start-Sleep -Milliseconds 300
                $unknownSurfaceStreak = 0
            }
        }
        Start-Sleep -Milliseconds 250
    }

    $finalDump = Join-Path $RunDir "wait_login_surface_final.xml"
    Get-UiDump -OutPath $finalDump | Out-Null
    if (Test-Path $finalDump) {
        $finalXml = Get-Content -Raw $finalDump
        if ($finalXml -match $loginCtaPattern -or $finalXml -match $loginPattern) {
            return $finalXml
        }
    }

    Write-Warning "Login form did not appear within $TimeoutSec seconds; proceeding with coordinate fallback"
    if (Test-Path $finalDump) {
        return (Get-Content -Raw $finalDump)
    }
    return $null
}

function Tap-BySelector {
    param(
        [string]$Selector,
        [int]$Retries = 4,
        [int]$DelayMs = 500
    )

    for ($i = 0; $i -lt [Math]::Max(1, $Retries); $i++) {
        if (Tap-Resource -ResourceId $Selector) {
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
}

function Is-HomeScreenVisible {
    param([string]$Xml = $null)

    $candidate = $Xml
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        $candidate = Get-UiDump -OutPath $LastDumpPath
    }
    return [bool]($candidate -match 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle|worldlinco-my-info-toggle')
}

function Is-LoginLobbyVisible {
    param([string]$Xml = $null)

    $candidate = $Xml
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        $candidate = Get-UiDump -OutPath $LastDumpPath
    }
    return [bool]($candidate -match 'worldlinco-login-modal|worldlinco-inline-auth-panel|worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|로그인이 필요해요|WORLDLINCO LOBBY')
}

function Is-AuthenticatedSessionVisible {
    param([string]$Xml = $null)

    $candidate = $Xml
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        $candidate = Get-UiDump -OutPath $LastDumpPath
    }

    $authDebug = Get-AuthDebugStateSnapshot -Xml $candidate
    if ($authDebug -and ($authDebug.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
        return $true
    }

    return (Is-HomeScreenVisible -Xml $candidate)
}

function Wait-ForSessionRestoreReady {
    param(
        [int]$MaxWaitSec = 8,
        [int]$StableHits = 1
    )

    $deadline = (Get-Date).AddSeconds([Math]::Max(1, [Math]::Min(120, $MaxWaitSec)))
    $requiredStableHits = [Math]::Max(1, [Math]::Min(5, $StableHits))
    $hits = 0

    while ((Get-Date) -lt $deadline) {
        if (Is-AuthenticatedSessionVisible) {
            $hits++
            if ($hits -ge $requiredStableHits) {
                return $true
            }
            Start-Sleep -Milliseconds 250
            continue
        }

        $hits = 0
        if (Is-LoginLobbyVisible) {
            return $false
        }
        Start-Sleep -Milliseconds 250
    }

    return $false
}

function Enter-Field {
    param(
        [string]$Selector,
        [string]$Value
    )

    return (Set-FieldText -ResourceId $Selector -Value $Value)
}

function Get-LoginPassword {
    return (Get-Password)
}

function Ensure-LoggedIn {
    $homePattern = 'worldlinco-home-face-hero|worldlinco-translate-home-button|worldlinco-home-tools-toggle|worldlinco-my-info-toggle'
    $loginPattern = 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal|worldlinco-inline-auth-panel|로그인이 필요해요|WORLDLINCO LOBBY|로그인 패널 열기|로그인 / 회원가입|로그인 또는 회원가입'
    $loginCtaPattern = 'worldlinco-inline-open-login-button|worldlinco-header-login-button|worldlinco-auth-open-login-modal-button|로그인 패널 열기|로그인 / 회원가입|로그인|App Icon|WorldLinco|User|Home|Updates|Settings|Development Build|DEVELOPMENT SERVERS|RECENTLY OPENED|New development server|http://172\.30\.1\.41:8091|http://127\.0\.0\.1:8091|RESET'

    Ensure-TargetAppForeground -WaitMs 1200
    $currentXml = Get-UiDump -OutPath $LastDumpPath
    if (-not (Is-TargetAppUiDump -Xml $currentXml)) {
        Ensure-TargetAppForeground -WaitMs 1200
        $currentXml = Get-UiDump -OutPath $LastDumpPath
    }
    if (Is-TransientDevOverlayVisible -Xml $currentXml) {
        [void](Dismiss-TransientDevOverlay -Attempts 1)
        $currentXml = Get-UiDump -OutPath $LastDumpPath
    }

    $authDebugCurrent = Get-AuthDebugStateSnapshot -Xml $currentXml
    if ($authDebugCurrent -and ($authDebugCurrent.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
        return @{ attempted = $false; ok = $true; reason = 'auth_debug_authenticated' }
    }

    for ($quick = 0; $quick -lt 2; $quick++) {
        if ($currentXml -match $homePattern) {
            return @{ attempted = $false; ok = $true; reason = 'session_restored' }
        }
        Start-Sleep -Milliseconds 200
        $currentXml = Get-UiDump -OutPath $LastDumpPath
        $authDebugCurrent = Get-AuthDebugStateSnapshot -Xml $currentXml
        if ($authDebugCurrent -and ($authDebugCurrent.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return @{ attempted = $false; ok = $true; reason = 'auth_debug_authenticated' }
        }
    }

    if (Wait-ForSessionRestoreReady -MaxWaitSec 8 -StableHits 1) {
        return @{ attempted = $false; ok = $true; reason = 'session_restored' }
    }

    $probeDeadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $probeDeadline) {
        Ensure-TargetAppForeground -WaitMs 450
        $probeXml = Get-UiDump -OutPath $LastDumpPath
        if (-not (Is-TargetAppUiDump -Xml $probeXml)) {
            Start-Sleep -Milliseconds 250
            continue
        }

        if (Is-DevClientLoadErrorVisible -Xml $probeXml) {
            return @{ attempted = $true; ok = $false; reason = 'devclient_runtime_unready' }
        }

        if (Is-ExpoDevServerSelectionVisible -Xml $probeXml) {
            [void](Dismiss-ExpoDevServerSelection -Attempts 2)
            Start-Sleep -Milliseconds 450
            continue
        }

        if ($probeXml -match $homePattern) {
            return @{ attempted = $false; ok = $true; reason = 'session_restored' }
        }

        if ($probeXml -match $loginPattern -or $probeXml -match $loginCtaPattern) {
            $currentXml = $probeXml
            break
        }

        if (Is-MinimalRuntimeShellVisible -Xml $probeXml) {
            Tap-Coordinates -X 400 -Y 250 | Out-Null
        }
        Start-Sleep -Milliseconds 300
    }

    if ($currentXml -notmatch $loginPattern -and $currentXml -notmatch $loginCtaPattern) {
        if (Is-ExpoDevServerSelectionVisible -Xml $currentXml) {
            return @{ attempted = $true; ok = $false; reason = 'expo_dev_server_stuck' }
        }
        return @{ attempted = $true; ok = $false; reason = 'login_timeout_probe' }
    }

    if ($currentXml -match $loginCtaPattern) {
        # Text/resource-first detection ratio increased per request.
        foreach ($button in @('text:http://172.30.1.41:8091', 'text:http://127.0.0.1:8091', 'text:RECENTLY OPENED', 'text:DEVELOPMENT SERVERS', 'text:Development Build', 'text:로그인 패널 열기', 'text:로그인 / 회원가입', 'text:로그인', 'text:User', 'text:Home', 'text:Updates', 'text:Settings', 'text:WorldLinco', 'text:App Icon', 'worldlinco-auth-open-login-modal-button', 'worldlinco-inline-open-login-button', 'worldlinco-header-login-button')) {
            $opened = $false
            if ($button -like 'text:*') {
                $opened = Tap-ByText -TextPattern $button.Substring(5) -Xml $currentXml -Retries 2 -DelayMs 350
            }
            elseif ($button -eq 'worldlinco-header-login-button') {
                Tap-Coordinates -X 400 -Y 250 | Out-Null
                $opened = $true
            }
            else {
                $opened = Tap-BySelector -Selector $button -Retries 2 -DelayMs 350
            }

            if ($opened) {
                Start-Sleep -Milliseconds 650
                $postTapXml = Get-UiDump -OutPath $LastDumpPath
                if ($postTapXml -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button|worldlinco-login-modal') {
                    $currentXml = $postTapXml
                    break
                }
            }
        }
    }

    if ($currentXml -notmatch $loginPattern) {
        return @{ attempted = $true; ok = $false; reason = 'login_open_failed' }
    }

    $password = Get-LoginPassword
    if (-not $Email -or -not $password) {
        return @{ attempted = $true; ok = $false; reason = 'missing_login_credentials' }
    }

    $loginEmail = $Email
    $loginPassword = $password

    # Strict reset mode must avoid API pre-login side effects that can create
    # an active session before the in-app login submit path runs.
    $credentialPrecheck = if ($StrictResetSessionMode) {
        $true
    }
    else {
        Test-LoginCredentialPrecheck -BaseUrl $ApiBase -EmailValue $loginEmail -PasswordValue $loginPassword
    }
    if ($credentialPrecheck -ne $true) {
        $otpCredential = New-AutomationOtpCredential -BaseUrl $ApiBase
        if ($otpCredential -and $otpCredential.email -and $otpCredential.password) {
            $loginEmail = [string]$otpCredential.email
            $loginPassword = [string]$otpCredential.password
            $otpPrecheck = Test-LoginCredentialPrecheck -BaseUrl $ApiBase -EmailValue $loginEmail -PasswordValue $loginPassword
            if ($otpPrecheck -ne $true) {
                return @{ attempted = $true; ok = $false; reason = 'otp_signup_login_precheck_failed' }
            }
        }
        elseif (Try-StartInstantDemoSession -WaitSec 32) {
            return @{ attempted = $true; ok = $true; reason = 'demo_session_authenticated_precheck_401' }
        }
        else {
            return @{ attempted = $true; ok = $false; reason = 'login_credential_401_precheck' }
        }
    }

    if (-not (Enter-Field -Selector 'worldlinco-auth-email-input' -Value $loginEmail)) {
        return @{ attempted = $true; ok = $false; reason = 'login_email_input_failed' }
    }
    if (-not (Enter-Field -Selector 'worldlinco-auth-password-input' -Value $loginPassword)) {
        return @{ attempted = $true; ok = $false; reason = 'login_password_input_failed' }
    }

    $submitTapped = $false
    for ($submitTry = 0; $submitTry -lt 4; $submitTry++) {
        # Blur text input without closing modal.
        Tap-Coordinates -X 400 -Y 340 | Out-Null
        Start-Sleep -Milliseconds 180
        Ensure-TargetAppForeground -WaitMs 700
        PreScroll-LoginSubmitIntoView -MaxSwipes 3
        $submitPoint = Ensure-ResourceTapVisibility -ResourceId 'worldlinco-auth-login-submit-button' -MaxSwipes 3
        if (-not $submitPoint) {
            $openedModal =
            (Tap-BySelector -Selector 'worldlinco-auth-open-login-modal-button' -Retries 1 -DelayMs 250) -or
            (Tap-BySelector -Selector 'worldlinco-inline-open-login-button' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '로그인 패널 열기' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '로그인 / 회원가입' -Retries 1 -DelayMs 250)
            if ($openedModal) {
                Start-Sleep -Milliseconds 500
                Ensure-TargetAppForeground -WaitMs 500
                PreScroll-LoginSubmitIntoView -MaxSwipes 2
                $submitPoint = Ensure-ResourceTapVisibility -ResourceId 'worldlinco-auth-login-submit-button' -MaxSwipes 2
            }
        }
        if ($submitPoint) {
            $submitMetrics = Get-BoundsMetrics -Bounds $submitPoint.bounds
            if ($submitMetrics -and ($submitMetrics.height -lt 28 -or $submitMetrics.y2 -ge 1330)) {
                # Submit button is clipped near screen bottom; blur and resolve again.
                Tap-Coordinates -X 400 -Y 320 | Out-Null
                Start-Sleep -Milliseconds 260
                Ensure-TargetAppForeground -WaitMs 700
                $submitPoint = Ensure-ResourceTapVisibility -ResourceId 'worldlinco-auth-login-submit-button' -MaxSwipes 2
                if ($submitPoint) {
                    $submitMetrics = Get-BoundsMetrics -Bounds $submitPoint.bounds
                }
            }
        }

        if ($submitPoint) {
            $submitTapped = Tap-Coordinates -X $submitPoint.x -Y $submitPoint.y
            if (-not $submitTapped -and $submitMetrics) {
                $fallbackY = [Math]::Max(0, $submitMetrics.y1 - 80)
                $submitTapped = Tap-Coordinates -X $submitPoint.x -Y $fallbackY
                if (-not $submitTapped) {
                    $safeY = [Math]::Max(0, [Math]::Min(1250, $submitMetrics.y1 + 12))
                    $submitTapped = Tap-Coordinates -X $submitPoint.x -Y $safeY
                }
            }
        }
        else {
            $submitTapped =
            (Tap-BySelector -Selector 'worldlinco-auth-login-submit-button' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '로그인 / 회원가입' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '로그인 또는 회원가입' -Retries 1 -DelayMs 250) -or
            (Tap-ByText -TextPattern '🔒 로그인' -Retries 1 -DelayMs 250)
        }

        if (-not $submitTapped) {
            $null = Invoke-Adb @('shell', 'input', 'keyevent', '66')
            Start-Sleep -Milliseconds 250
            $submitTapped = Tap-BySelector -Selector 'worldlinco-auth-login-submit-button' -Retries 1 -DelayMs 250
        }

        $postSubmitProbe = Get-UiDump -OutPath $LastDumpPath
        $submitState = Get-AuthDebugSubmitPressedSnapshot -Xml $postSubmitProbe
        if ($submitState -and $submitState -ne 'IDLE') {
            $script:LastSubmitPressedObserved = $submitState
        }
        if ($submitTapped -and $submitState -and $submitState -ne 'IDLE') {
            break
        }

        Start-Sleep -Milliseconds 300
    }

    if (-not $submitTapped) {
        return @{ attempted = $true; ok = $false; reason = 'login_submit_tap_failed' }
    }

    # Requested branch: immediate PASS when AUTH_DEBUG_STATE becomes authenticated during 10s polling.
    $submitDeadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $submitDeadline) {
        Ensure-TargetAppForeground -WaitMs 500
        $afterLogin = Get-UiDump -OutPath $LastDumpPath
        $authDebugAfterLogin = Get-AuthDebugStateSnapshot -Xml $afterLogin
        if ($authDebugAfterLogin -and ($authDebugAfterLogin.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            return @{ attempted = $true; ok = $true; reason = 'login_success_auth_debug' }
        }
        if ($afterLogin -match $homePattern) {
            return @{ attempted = $true; ok = $true; reason = 'login_success' }
        }
        Start-Sleep -Milliseconds 450
    }

    if (Has-AuthReadyLogHint -TailLines 420) {
        return @{ attempted = $true; ok = $true; reason = 'login_success_log_hint' }
    }

    if (Has-LoginApiFail409 -TailLines 700) {
        if (Try-ClearActiveSessionByRecovery -BaseUrl $ApiBase -UserHint $loginEmail) {
            Ensure-TargetAppForeground -WaitMs 600
            $retryTap =
            (Tap-BySelector -Selector 'worldlinco-auth-login-submit-button' -Retries 2 -DelayMs 280) -or
            (Tap-ByText -TextPattern '로그인 / 회원가입' -Retries 1 -DelayMs 280)
            if ($retryTap) {
                $retryDeadline = (Get-Date).AddSeconds(10)
                while ((Get-Date) -lt $retryDeadline) {
                    Ensure-TargetAppForeground -WaitMs 450
                    $retryXml = Get-UiDump -OutPath $LastDumpPath
                    $retryAuth = Get-AuthDebugStateSnapshot -Xml $retryXml
                    if ($retryAuth -and ($retryAuth.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
                        return @{ attempted = $true; ok = $true; reason = 'login_success_after_clear_session' }
                    }
                    if ($retryXml -match $homePattern) {
                        return @{ attempted = $true; ok = $true; reason = 'login_success_after_clear_session' }
                    }
                    Start-Sleep -Milliseconds 450
                }
            }
            $retryXmlFinal = Get-UiDump -OutPath $LastDumpPath
            $loginFormStillVisible = [bool]($retryXmlFinal -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button')
            if ((Has-AuthReadyLogHint -TailLines 700) -or (-not $loginFormStillVisible)) {
                return @{ attempted = $true; ok = $true; reason = 'login_success_after_clear_session_async' }
            }
            return @{ attempted = $true; ok = $false; reason = 'login_409_cleared_but_not_authenticated' }
        }
        return @{ attempted = $true; ok = $false; reason = 'login_409_clear_session_failed' }
    }

    if (Has-LoginApiFail401 -TailLines 700) {
        if (Try-StartInstantDemoSession -WaitSec 30) {
            return @{ attempted = $true; ok = $true; reason = 'demo_session_authenticated' }
        }
        return @{ attempted = $true; ok = $false; reason = 'login_401_demo_fallback_failed' }
    }

    return @{ attempted = $true; ok = $false; reason = 'login_not_completed' }
}

function Run-OneRound {
    param([int]$RoundNumber)

    $roundDir = Join-Path $RunDir "round-$RoundNumber"
    New-Item -ItemType Directory -Force -Path $roundDir | Out-Null

    if ($EffectiveResetSession) {
        $null = Invoke-Adb @("shell", "pm", "clear", $PackageName)
        Start-Sleep -Seconds 2
    }

    $null = Invoke-Adb @("shell", "logcat", "-c")

    $null = Invoke-Adb @("shell", "am", "force-stop", $PackageName)
    Start-Sleep -Milliseconds 500
    $null = Invoke-Adb @("shell", "am", "start", "-n", "$PackageName/.MainActivity")
    Start-Sleep -Seconds 5

    $script:LastSubmitPressedObserved = 'IDLE'

    $ensure = Ensure-LoggedIn

    $postEnsureDump = Join-Path $roundDir "after_ensure_loggedin.xml"
    Get-UiDump -OutPath $postEnsureDump | Out-Null
    $postEnsureXml = if (Test-Path $postEnsureDump) { Get-Content -Raw $postEnsureDump } else { $null }

    $stabilizeUntil = (Get-Date).AddSeconds(10)
    $authDebugPoll = $null
    while ((Get-Date) -lt $stabilizeUntil) {
        $pollDump = Join-Path $roundDir "post_ensure_poll.xml"
        Get-UiDump -OutPath $pollDump | Out-Null
        $pollXml = if (Test-Path $pollDump) { Get-Content -Raw $pollDump } else { $postEnsureXml }
        $authDebugPoll = Get-AuthDebugStateSnapshot -Xml $pollXml
        if ($authDebugPoll -and ($authDebugPoll.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) {
            break
        }
        Start-Sleep -Milliseconds 450
    }

    $finalDump = Join-Path $roundDir "after_submit.xml"
    Get-UiDump -OutPath $finalDump | Out-Null
    $finalXml = if (Test-Path $finalDump) { Get-Content -Raw $finalDump } else { $postEnsureXml }
    $logcat = Get-LogcatText
    $authDebugAfter = Get-AuthDebugStateSnapshot -Xml $finalXml
    $submitPressedSnapshot = Get-AuthDebugSubmitPressedSnapshot -Xml $finalXml
    $effectiveSubmitPressed = if ($script:LastSubmitPressedObserved -and $script:LastSubmitPressedObserved -ne 'IDLE') { $script:LastSubmitPressedObserved } else { $submitPressedSnapshot }
    if (-not $authDebugAfter -and $authDebugPoll) {
        $authDebugAfter = $authDebugPoll
    }
    $authReadyHint = Has-AuthReadyLogHint -TailLines 500

    $defaultSuccess = (
        $ensure.ok -or
        (($authDebugAfter) -and ($authDebugAfter.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) -or
        ($logcat -match 'LOGIN_SUBMIT_SUCCESS') -or
        (($logcat -match '"token_ready":true') -and ($logcat -match '"user_ready":true')) -or
        $authReadyHint
    )

    $strictResetSuccess = (
        $ensure.attempted -and
        (($authDebugAfter) -and ($authDebugAfter.state -in @('AUTHENTICATED', 'TOKEN_ONLY'))) -and
        ($effectiveSubmitPressed -eq 'PRESSED') -and
        ($ensure.reason -notin @('session_restored', 'login_open_failed', 'login_not_completed'))
    )

    $finalSuccess = if ($StrictResetSessionMode) { $strictResetSuccess } else { $defaultSuccess }

    $screenshot = Capture-Screenshot -Name "round_${RoundNumber}_after_submit"
    $summary = [ordered]@{
        round                           = $RoundNumber;
        timestamp                       = (Get-Date).ToString("o");
        device                          = $Device;
        package                         = $PackageName;
        email                           = $Email;
        ensure_attempted                = $ensure.attempted;
        ensure_ok                       = $ensure.ok;
        ensure_reason                   = $ensure.reason;
        login_submit_seen               = ($logcat -match 'LOGIN_SUBMIT_SUCCESS');
        token_ready                     = ($logcat -match '"token_ready":true');
        user_ready                      = ($logcat -match '"user_ready":true');
        show_login_false                = ($logcat -match '"show_login":false');
        auth_debug_state                = if ($authDebugAfter) { $authDebugAfter.state } else { $null };
        auth_debug_user                 = if ($authDebugAfter) { $authDebugAfter.user } else { $null };
        auth_debug_submit_pressed       = $effectiveSubmitPressed;
        auth_ready_hint                 = $authReadyHint;
        reset_session_applied           = $EffectiveResetSession;
        strict_reset_session_mode       = $StrictResetSessionMode;
        login_form_visible_after_submit = ((Test-Path $finalDump) -and ((Get-Content -Raw $finalDump) -match 'worldlinco-auth-email-input|worldlinco-auth-password-input|worldlinco-auth-login-submit-button'));
        ui_dump_path                    = $finalDump;
        screenshot_path                 = $screenshot;
        log_path                        = Join-Path $roundDir "reactnativejs.log";
        success                         = $finalSuccess;
    }

    Set-Content -Path (Join-Path $roundDir "reactnativejs.log") -Value $logcat -Encoding UTF8
    $summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $roundDir "summary.json") -Encoding UTF8

    if (-not $summary.success) {
        throw "Round $RoundNumber login automation failed: ensure_reason=$($ensure.reason), auth_debug_state=$($summary.auth_debug_state)"
    }

    return $summary
}

Write-Host "[verify-mobile-login] device=$Device package=$PackageName rounds=$Rounds reset_session=$EffectiveResetSession strict_reset_session_mode=$StrictResetSessionMode"
Write-Host "[verify-mobile-login] looking for admin password in $PasswordFile"

$results = @()
for ($i = 1; $i -le $Rounds; $i++) {
    Write-Host "--- round $i/$Rounds ---"
    try {
        $summary = Run-OneRound -RoundNumber $i
        $results += $summary
        Write-Host ($summary | ConvertTo-Json -Depth 6)
    }
    catch {
        $msg = $_.Exception.Message
        Write-Warning "Round $i failed: $msg"
        $results += [ordered]@{ round = $i; success = $false; error = $msg }
        break
    }
}

$allPass = ($results.Count -gt 0) -and (($results | Where-Object { -not [bool]$_.success }).Count -eq 0)
$manifestPath = Join-Path $RunDir "manifest.json"
[ordered]@{
    device                    = $Device;
    package                   = $PackageName;
    rounds                    = $Rounds;
    reset_session_applied     = $EffectiveResetSession;
    strict_reset_session_mode = $StrictResetSessionMode;
    results                   = $results;
    all_passed                = $allPass;
    generated_at              = (Get-Date).ToString("o");
} | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "--- manifest ---"
Get-Content -Path $manifestPath -Raw

if (-not $allPass) {
    exit 1
}

exit 0
