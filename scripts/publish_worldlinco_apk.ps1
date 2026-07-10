#!/usr/bin/env pwsh
param(
    [switch]$SkipBuild,
    [string]$DeviceId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$MobileDir = Join-Path $RepoRoot "apps\mobile-nadotongryoksa"
$AndroidDir = Join-Path $MobileDir "android"
$AppJsonPath = Join-Path $MobileDir "app.json"
$ReleaseApk = Join-Path $AndroidDir "app\build\outputs\apk\release\app-release.apk"
$PublishDir = Join-Path $RepoRoot "uploads\marketplace_local\apk"

function Read-AppVersion {
    $json = Get-Content $AppJsonPath -Raw | ConvertFrom-Json
    return @{
        VersionName = [string]$json.expo.version
        VersionCode = [int]$json.expo.android.versionCode
    }
}

function Sync-AndroidVersionFromAppJson {
    $version = Read-AppVersion
    $gradlePath = Join-Path $AndroidDir "app\build.gradle"
    $gradle = Get-Content $gradlePath -Raw
    $gradle = [regex]::Replace($gradle, 'versionCode\s+\d+', "versionCode $($version.VersionCode)")
    $gradle = [regex]::Replace($gradle, 'versionName\s+"[^"]+"', "versionName `"$($version.VersionName)`"")
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($gradlePath, $gradle, $utf8NoBom)
    Write-Host "[sync] android/app/build.gradle -> versionCode=$($version.VersionCode) versionName=$($version.VersionName)"
}

function Get-InstalledVersionCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DeviceId,
        [string]$PackageName = "com.parkcheolhong.worldlinco"
    )

    $output = & adb -s $DeviceId shell dumpsys package $PackageName 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $match = [regex]::Match(($output -join "`n"), "versionCode=(\d+)")
    if (-not $match.Success) {
        return $null
    }
    return [int]$match.Groups[1].Value
}

if (-not $SkipBuild) {
    # 출시 SSOT: LAN/container-dev env 가 섞이지 않도록 production 고정
    Remove-Item Env:MOBILE_CONTAINER_API_BASE_URL -ErrorAction SilentlyContinue
    $env:EXPO_PUBLIC_API_BASE_URL = "https://metanova1004.com"
    $env:EXPO_PUBLIC_RELEASE_CHANNEL = "production"
    $env:NODE_ENV = "production"
    Write-Host "[publish] production API: $($env:EXPO_PUBLIC_API_BASE_URL)"
    $syncScript = Join-Path $RepoRoot "scripts\sync_android_version.py"
    if (Test-Path $syncScript) {
        & python $syncScript
        if ($LASTEXITCODE -ne 0) { throw "sync_android_version.py failed" }
    }
    Sync-AndroidVersionFromAppJson
    $env:GRADLE_USER_HOME = "C:\gradle-cache"
    $env:NODE_ENV = "production"
    $env:GRADLE_OPTS = "-Dorg.gradle.caching=true"
    $gradleRoot = $AndroidDir
    # Windows 경로 260자 제한: C:\wlnc junction 이 있으면 짧은 경로로 빌드한다.
    if (Test-Path "C:\wlnc\android\gradlew.bat") {
        $gradleRoot = "C:\wlnc\android"
        Write-Host "[build] Using short path gradle root: $gradleRoot"
    }
    $bundleDirs = @(
        "android\app\build\generated\assets\react\release",
        "android\app\build\generated\res\react\release",
        "android\app\build\intermediates\sourcemaps\react\release"
    )
    foreach ($dir in $bundleDirs) {
        New-Item -ItemType Directory -Force -Path (Join-Path $MobileDir $dir) | Out-Null
    }
    Write-Host "[build] Cleaning embedded React release bundle"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $MobileDir "android\app\build\generated\assets\react\release\*")
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $MobileDir "android\app\build\generated\res\react\release\*")
    Write-Host "[build] Gradle assembleRelease (arm64-v8a)"
    Push-Location $gradleRoot
    try {
        & .\gradlew.bat assembleRelease "-PreactNativeArchitectures=arm64-v8a" --no-daemon
        if ($LASTEXITCODE -ne 0) { throw "Gradle build failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $ReleaseApk)) {
    throw "Release APK not found: $ReleaseApk"
}

$version = Read-AppVersion
$versionedName = "nadotongryoksa-v$($version.VersionName)-build$($version.VersionCode)-current.apk"
$canonicalName = "nadotongryoksa-v1.apk"

New-Item -ItemType Directory -Force -Path $PublishDir | Out-Null
$versionedPath = Join-Path $PublishDir $versionedName
$canonicalPath = Join-Path $PublishDir $canonicalName

Copy-Item -Force $ReleaseApk $versionedPath
# canonical APK 는 nginx/백엔드가 mmap 중일 수 있어 .new 경유로 교체한다.
$tmpCanonical = "$canonicalPath.new"
[System.IO.File]::Copy($ReleaseApk, $tmpCanonical, $true)
if (Test-Path $canonicalPath) {
    Remove-Item -Force $canonicalPath -ErrorAction SilentlyContinue
}
Move-Item -Force $tmpCanonical $canonicalPath

$manifestPath = Join-Path $PublishDir "nadotongryoksa-v1.manifest.json"
$manifest = @{
    package           = "com.parkcheolhong.worldlinco"
    versionName       = $version.VersionName
    versionCode       = $version.VersionCode
    apkFilename       = $canonicalName
    versionedFilename = $versionedName
    downloadPath      = "/api/marketplace/apk/$canonicalName"
    publishedAt       = (Get-Date).ToUniversalTime().ToString("o")
    sizeBytes         = (Get-Item $canonicalPath).Length
} | ConvertTo-Json -Depth 3
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($manifestPath, $manifest, $utf8NoBom)

$sizeMb = [math]::Round((Get-Item $canonicalPath).Length / 1MB, 2)
Write-Host "[publish] $canonicalPath ($sizeMb MB)"
Write-Host "[publish] $versionedPath"
Write-Host "[publish] $manifestPath (v$($version.VersionName) build $($version.VersionCode))"
Write-Host "[marketplace] /api/marketplace/apk/$canonicalName"
Write-Host "[marketplace] /api/marketplace/apk/worldlinco/manifest"

if ($DeviceId) {
    $installedVersionCode = Get-InstalledVersionCode -DeviceId $DeviceId
    if ($installedVersionCode -eq $version.VersionCode) {
        Write-Host "[install] skipped: device $DeviceId already has build $installedVersionCode"
    }
    else {
        Write-Host "[install] adb -s $DeviceId install -r $canonicalPath"
        & adb -s $DeviceId install -r $canonicalPath
        if ($LASTEXITCODE -ne 0) { throw "adb install failed" }
    }
}
