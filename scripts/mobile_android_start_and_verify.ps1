param(
    [string]$AvdName = '',
    [int]$ExpoPort = 19017,
    [switch]$SkipEmulator
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
    Write-Output 'FAIL: SDK root not found'
    exit 1
}

$adb = Join-Path $sdkRoot 'platform-tools\adb.exe'
$emulator = Join-Path $sdkRoot 'emulator\emulator.exe'

if (-not (Test-Path $adb)) {
    Write-Output 'FAIL: adb not found'
    exit 1
}

if (-not $SkipEmulator) {
    if (-not (Test-Path $emulator)) {
        Write-Output 'FAIL: emulator binary not found'
        exit 1
    }

    if (-not $AvdName) {
        $avdIniDir = "$env:USERPROFILE\.android\avd"
        $avdList = @()
        if (Test-Path $avdIniDir) {
            $avdList = Get-ChildItem $avdIniDir -Filter *.ini | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_.Name) }
        }
        if ($avdList.Count -eq 0) {
            Write-Output 'FAIL: no AVD found'
            exit 1
        }
        $AvdName = $avdList[0]
    }

    Write-Output "Starting AVD: $AvdName"
    Start-Process -FilePath $emulator -ArgumentList "-avd $AvdName -netdelay none -netspeed full" | Out-Null

    $booted = $false
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 2
        $state = & $adb shell getprop sys.boot_completed 2>$null
        if (($state | Out-String).Trim() -eq '1') {
            $booted = $true
            break
        }
    }

    if (-not $booted) {
        Write-Output 'FAIL: emulator boot timeout'
        exit 1
    }
}

$projectDir = 'C:\Users\WORK\source\repos\parkcheolhong\codeAI\apps\mobile-nadotongryoksa'
Push-Location $projectDir
try {
    $env:CI = '1'
    $env:EXPO_NO_TELEMETRY = '1'
    Write-Output "Starting Expo Web on port $ExpoPort"
    npx expo start --web --port $ExpoPort
}
finally {
    Pop-Location
}
