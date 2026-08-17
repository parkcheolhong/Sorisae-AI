param(
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$MainActivity = "com.parkcheolhong.worldlinco.MainActivity",
    [string]$DeviceSerial = "",
    [int]$WaitAfterLaunchSec = 4,
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

function Invoke-TapByContentDesc {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContentDesc
    )

    $bounds = Get-UiNodeBoundsByContentDesc -ContentDesc $ContentDesc
    if (-not $bounds) {
        return $false
    }

    $tapX = [int](($bounds.Left + $bounds.Right) / 2)
    $tapY = [int](($bounds.Top + $bounds.Bottom) / 2)
    Write-Host "[KWS-TRIGGER] Tap '$ContentDesc' at ($tapX,$tapY)"
    Invoke-Adb -Args @("shell", "input", "tap", "$tapX", "$tapY") | Out-Null
    return $true
}

Write-Host "[KWS-TRIGGER] Checking adb..."
$adbVersion = & adb version
if (-not $adbVersion) {
    throw "adb is not available."
}

$deviceLines = (& adb devices) -split "`n" | Where-Object { $_ -match "\tdevice$" }
if (-not $deviceLines -or $deviceLines.Count -eq 0) {
    throw "No online Android device found."
}

if ($DeviceSerial) {
    $matchedDevice = $deviceLines | Where-Object { $_ -match "^$([regex]::Escape($DeviceSerial))\tdevice$" }
    if (-not $matchedDevice) {
        throw "Requested device serial '$DeviceSerial' is not online."
    }
    Write-Host "[KWS-TRIGGER] Target device: $DeviceSerial"
}
elseif ($deviceLines.Count -gt 1) {
    throw "Multiple devices are online. Pass -DeviceSerial or set ANDROID_SERIAL."
}

Write-Host "[KWS-TRIGGER] Launch app..."
Invoke-Adb -Args @("shell", "am", "start", "-n", "$PackageName/$MainActivity") | Out-Null

if ($WaitAfterLaunchSec -gt 0) {
    Start-Sleep -Seconds $WaitAfterLaunchSec
}

Write-Host "[KWS-TRIGGER] Searching companion arm toggle node..."
if (-not (Invoke-TapByContentDesc -ContentDesc $CompanionToggleAccessibilityId)) {
    Write-Host "[KWS-TRIGGER] Companion toggle not visible. Opening the visible login trigger first."
    $loginOpened = $false
    foreach ($candidate in @(
        "worldlinco-header-login-button",
        "worldlinco-inline-open-login-button",
        "worldlinco-auth-open-login-modal-button"
    )) {
        if (Invoke-TapByContentDesc -ContentDesc $candidate) {
            $loginOpened = $true
            break
        }
    }

    if (-not $loginOpened) {
        Write-Host "[KWS-TRIGGER] Companion toggle not visible. Trying lobby fallback: demo session start."
        $demoTapped = (Invoke-TapByContentDesc -ContentDesc "worldlinco-demo-session-start-button-inline") -or (Invoke-TapByContentDesc -ContentDesc "worldlinco-demo-session-start-button")
        if (-not $demoTapped) {
            throw "Companion arm toggle not found and no visible login/demo trigger was available."
        }
    }

    Start-Sleep -Seconds 5
    if (-not (Invoke-TapByContentDesc -ContentDesc $CompanionToggleAccessibilityId)) {
        throw "Companion arm toggle node still not found after fallback flow: $CompanionToggleAccessibilityId"
    }
}

Write-Host "[KWS-TRIGGER] Companion arm trigger dispatched."
