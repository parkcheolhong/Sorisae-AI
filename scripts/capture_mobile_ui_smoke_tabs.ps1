#!/usr/bin/env pwsh
param(
    [string]$Device = "172.30.1.15:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$LoginEmail = "119cash@naver.com",
    [string]$LoginPasswordFile = ".runtime/secrets/fixed_admin_password.txt"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evidenceDir = Join-Path $repoRoot "docs/checklists/evidence/mobile-ui-smoke-$stamp"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

function Invoke-Adb {
    param([string[]]$Args)
    & adb -s $Device @Args 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" }
    }
}

function Get-UiDump {
    param([string]$OutPath)
    if (-not $OutPath) {
        return
    }
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb @("pull", $remote, $OutPath) | Out-Null
}

function Tap-At {
    param(
        [int]$X,
        [int]$Y
    )
    Invoke-Adb @("shell", "input", "tap", "$X", "$Y") | Out-Null
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

function Tap-BySelector {
    param(
        [string]$Selector,
        [string]$DumpPath
    )

    if (-not $Selector -or -not $DumpPath) {
        return $false
    }

    Get-UiDump -OutPath $DumpPath
    if (-not (Test-Path $DumpPath)) {
        return $false
    }

    [xml]$doc = Get-Content -Raw $DumpPath
    $node = $doc.SelectSingleNode("//node[contains(@resource-id,'$Selector') or contains(@content-desc,'$Selector')]")
    if (-not $node) {
        return $false
    }

    $bounds = [string]$node.GetAttribute("bounds")
    if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
        return $false
    }

    $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
    $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
    Tap-At -X $cx -Y $cy
    return $true
}

function Tap-ByText {
    param(
        [string[]]$Texts,
        [string]$DumpPath
    )

    if (-not $Texts -or -not $DumpPath) {
        return $false
    }

    Get-UiDump -OutPath $DumpPath
    if (-not (Test-Path $DumpPath)) {
        return $false
    }

    [xml]$doc = Get-Content -Raw $DumpPath
    foreach ($text in $Texts) {
        $node = $doc.SelectSingleNode("//node[contains(@text,'$text') or contains(@content-desc,'$text')]")
        if (-not $node) {
            continue
        }

        $bounds = [string]$node.GetAttribute("bounds")
        if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
            continue
        }

        $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
        $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
        Tap-At -X $cx -Y $cy
        return $true
    }

    return $false
}

function Ensure-LoginModalOpen {
    param(
        [string]$DumpPath
    )

    if (-not $LoginEmail) {
        return $false
    }

    $password = Get-LoginPassword
    if (-not $password) {
        return $false
    }

    if (-not $DumpPath) {
        return $false
    }

    Get-UiDump -OutPath $DumpPath
    if (-not (Test-Path $DumpPath)) {
        return $false
    }

    $xml = Get-Content -Raw $DumpPath
    $openedLogin = $false
    if ($xml -match 'worldlinco-inline-open-login-button|worldlinco-auth-open-login-modal-button|worldlinco-header-login-button') {
        $openedLogin = (Tap-BySelector -Selector "worldlinco-inline-open-login-button" -DumpPath $DumpPath) -or
        (Tap-BySelector -Selector "worldlinco-auth-open-login-modal-button" -DumpPath $DumpPath) -or
        (Tap-BySelector -Selector "worldlinco-header-login-button" -DumpPath $DumpPath)
    }
    if (-not $openedLogin) {
        $openedLogin = Tap-ByText -Texts @("로그인 / 회원가입", "로그인/회원가입", "Login / Sign up", "Login") -DumpPath $DumpPath
    }
    if (-not $openedLogin) {
        return $false
    }

    $emailNode = $null
    $passwordNode = $null
    $submitNode = $null
    for ($attempt = 0; $attempt -lt 6; $attempt++) {
        Start-Sleep -Seconds 1
        Get-UiDump -OutPath $DumpPath
        if (-not (Test-Path $DumpPath)) {
            continue
        }

        [xml]$doc = Get-Content -Raw $DumpPath
        $emailNode = $doc.SelectSingleNode("//node[contains(@resource-id,'worldlinco-auth-email-input')]")
        $passwordNode = $doc.SelectSingleNode("//node[contains(@resource-id,'worldlinco-auth-password-input')]")
        $submitNode = $doc.SelectSingleNode("//node[contains(@resource-id,'worldlinco-auth-login-submit-button')]")
        if ($emailNode -and $passwordNode -and $submitNode) {
            break
        }
    }

    if (-not $emailNode -or -not $passwordNode -or -not $submitNode) {
        return $false
    }

    $emailBounds = [string]$emailNode.GetAttribute("bounds")
    $passwordBounds = [string]$passwordNode.GetAttribute("bounds")
    $submitBounds = [string]$submitNode.GetAttribute("bounds")
    foreach ($entry in @(
            @{ Bounds = $emailBounds; Value = $LoginEmail },
            @{ Bounds = $passwordBounds; Value = $password }
        )) {
        if ($entry.Bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
            return $false
        }
        $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
        $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
        Tap-At -X $cx -Y $cy
        Start-Sleep -Milliseconds 300
        1..48 | ForEach-Object { Invoke-Adb @("shell", "input", "keyevent", "67") | Out-Null }
        $escaped = ($entry.Value -replace ' ', '%s')
        Invoke-Adb @("shell", "input", "text", $escaped) | Out-Null
        Start-Sleep -Milliseconds 300
    }

    if ($submitBounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
        return $false
    }

    $submitCx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
    $submitCy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
    Tap-At -X $submitCx -Y $submitCy
    Start-Sleep -Seconds 6
    return $true
}

function Save-Screenshot {
    param([string]$Name)
    if (-not $Name) {
        return $null
    }

    $target = Join-Path $evidenceDir $Name
    $remote = "/sdcard/$Name"
    & adb -s $Device shell screencap -p $remote | Out-Null
    & adb -s $Device pull $remote $target | Out-Null
    if (Test-Path $target) {
        return $target
    }
    return $null
}

$manifest = [ordered]@{
    run_id     = "mobile-ui-smoke-$stamp"
    device     = $Device
    package    = $PackageName
    started_at = (Get-Date).ToString("o")
    captures   = @()
}

Invoke-Adb @("shell", "am", "start", "-W", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 8

if (-not (Ensure-LoginModalOpen -DumpPath (Join-Path $evidenceDir "dump-login.xml"))) {
    # Fallback tap for known login lobby layout.
    Tap-At -X 120 -Y 252
}
Start-Sleep -Seconds 8

$steps = @(
    @{ name = "chat"; selector = "worldlinco-section-rail-chat-button"; file = "01_chat.png"; fallbackX = 85; fallbackY = 1240 },
    @{ name = "voip"; selector = "worldlinco-section-rail-voip-button"; file = "02_voip.png"; fallbackX = 240; fallbackY = 1240 },
    @{ name = "travel"; selector = "worldlinco-section-rail-travel-booking-button"; file = "03_travel.png"; fallbackX = 560; fallbackY = 1240 },
    @{ name = "settings"; selector = "worldlinco-bottom-tab-settings"; file = "04_settings.png"; fallbackX = 710; fallbackY = 1240 }
)

foreach ($step in $steps) {
    $dumpPath = Join-Path $evidenceDir ("dump-" + $step.name + ".xml")
    $selectorTapped = Tap-BySelector -Selector $step.selector -DumpPath $dumpPath
    $fallbackTapped = $false
    if (-not $selectorTapped) {
        Tap-At -X ([int]$step.fallbackX) -Y ([int]$step.fallbackY)
        $fallbackTapped = $true
    }
    Start-Sleep -Seconds 2

    $shot = Save-Screenshot -Name $step.file
    $manifest.captures += [ordered]@{
        section            = $step.name
        selector           = $step.selector
        tapped_by_selector = [bool]$selectorTapped
        tapped_by_fallback = [bool]$fallbackTapped
        screenshot         = if ($shot) { $step.file } else { "" }
    }
}

$manifest.completed_at = (Get-Date).ToString("o")
$manifestPath = Join-Path $evidenceDir "manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "EVIDENCE_DIR=$evidenceDir"
Write-Host "MANIFEST=$manifestPath"