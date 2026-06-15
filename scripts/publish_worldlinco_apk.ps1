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

if (-not $SkipBuild) {
    Sync-AndroidVersionFromAppJson
    $env:GRADLE_USER_HOME = if ($env:GRADLE_USER_HOME) { $env:GRADLE_USER_HOME } else { "C:\gradle-cache" }
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
    Push-Location $AndroidDir
    try {
        & .\gradlew.bat assembleRelease "-PreactNativeArchitectures=arm64-v8a" --no-daemon
        if ($LASTEXITCODE -ne 0) { throw "Gradle build failed with exit code $LASTEXITCODE" }
    } finally {
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
Copy-Item -Force $ReleaseApk $canonicalPath

$manifestPath = Join-Path $PublishDir "nadotongryoksa-v1.manifest.json"
$manifest = @{
    package = "com.parkcheolhong.worldlinco"
    versionName = $version.VersionName
    versionCode = $version.VersionCode
    apkFilename = $canonicalName
    versionedFilename = $versionedName
    downloadPath = "/api/marketplace/apk/$canonicalName"
    publishedAt = (Get-Date).ToUniversalTime().ToString("o")
    sizeBytes = (Get-Item $canonicalPath).Length
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
    Write-Host "[install] adb -s $DeviceId install -r $canonicalPath"
    & adb -s $DeviceId install -r $canonicalPath
    if ($LASTEXITCODE -ne 0) { throw "adb install failed" }
}
