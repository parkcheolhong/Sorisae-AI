param(
    [switch]$ShowDetails
)

$ErrorActionPreference = 'Stop'

$sdkCandidates = @(
    "$env:LOCALAPPDATA\Android\Sdk",
    'C:\Android\Sdk'
)

$sdkRoot = $null
foreach ($candidate in $sdkCandidates) {
    if (Test-Path $candidate) {
        $sdkRoot = $candidate
        break
    }
}

if (-not $sdkRoot) {
    Write-Output 'STATUS=FAIL'
    Write-Output 'REASON=SDK_ROOT_NOT_FOUND'
    Write-Output "HINT=Open Android Studio once and finish SDK setup, then retry."
    exit 1
}

$adb = Join-Path $sdkRoot 'platform-tools\adb.exe'
$emulator = Join-Path $sdkRoot 'emulator\emulator.exe'
$avdIniDir = "$env:USERPROFILE\.android\avd"

$hasAdb = Test-Path $adb
$hasEmu = Test-Path $emulator
$avdList = @()
if (Test-Path $avdIniDir) {
    $avdList = Get-ChildItem $avdIniDir -Filter *.ini | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_.Name) }
}

Write-Output "SDK_ROOT=$sdkRoot"
Write-Output "ADB=$hasAdb"
Write-Output "EMULATOR=$hasEmu"
Write-Output "AVD_COUNT=$($avdList.Count)"
if ($ShowDetails -and $avdList.Count -gt 0) {
    Write-Output ('AVDS=' + ($avdList -join ','))
}

if (-not $hasAdb -or -not $hasEmu) {
    Write-Output 'STATUS=FAIL'
    Write-Output 'REASON=SDK_COMPONENT_MISSING'
    exit 1
}

Write-Output 'STATUS=OK'
exit 0
