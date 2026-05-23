param(
  [Parameter(Mandatory = $true)]
  [string]$BuildId,

  [string]$ProjectDir = "apps/mobile-nadotongryoksa",
  [string]$OutputApk = "$env:TEMP/nadotongryoksa-release.apk"
)

$ErrorActionPreference = 'Stop'

Write-Host "[1/4] Querying EAS build metadata: $BuildId" -ForegroundColor Cyan
Push-Location $ProjectDir
try {
  $raw = npx eas-cli build:view $BuildId --json
} finally {
  Pop-Location
}

$obj = $raw | ConvertFrom-Json
if (-not $obj) {
  throw "Failed to parse EAS build metadata"
}
if ($obj.status -ne 'FINISHED') {
  throw "Build is not finished. Current status: $($obj.status)"
}

$artifactUrl = $obj.artifacts.buildUrl
if (-not $artifactUrl) {
  $artifactUrl = $obj.artifacts.applicationArchiveUrl
}
if (-not $artifactUrl) {
  throw "No artifact URL found in EAS build metadata"
}

$workDir = Join-Path $env:TEMP ("eas_apk_" + $BuildId)
New-Item -ItemType Directory -Path $workDir -Force | Out-Null
$artifactFile = Join-Path $workDir "artifact.bin"

Write-Host "[2/4] Downloading artifact" -ForegroundColor Cyan
Invoke-WebRequest -Uri $artifactUrl -OutFile $artifactFile -UseBasicParsing

# Try direct APK first
$isDirectApk = $artifactUrl.ToLower().EndsWith('.apk')
if ($isDirectApk) {
  Copy-Item $artifactFile $OutputApk -Force
} else {
  # Most internal Android builds are tar.gz; extract and pick release APK.
  $tarFile = Join-Path $workDir "artifact.tar.gz"
  Move-Item $artifactFile $tarFile -Force
  Write-Host "[3/4] Extracting artifact archive" -ForegroundColor Cyan
  tar -xzf $tarFile -C $workDir

  $releaseApk = Get-ChildItem -Path $workDir -Recurse -Filter "app-release.apk" | Select-Object -First 1
  if (-not $releaseApk) {
    $releaseApk = Get-ChildItem -Path $workDir -Recurse -Filter "*.apk" | Sort-Object Length -Descending | Select-Object -First 1
  }
  if (-not $releaseApk) {
    throw "No APK found inside artifact archive"
  }
  Copy-Item $releaseApk.FullName $OutputApk -Force
}

Write-Host "[4/4] Verifying APK structure" -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$bytes = [System.IO.File]::ReadAllBytes($OutputApk)
$sig = ($bytes[0..3] | ForEach-Object { $_.ToString('X2') }) -join ' '
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputApk)
$manifest = ($zip.Entries | Where-Object { $_.FullName -eq 'AndroidManifest.xml' }).Count
$dex = ($zip.Entries | Where-Object { $_.FullName -eq 'classes.dex' }).Count
$zip.Dispose()

if ($sig -ne '50 4B 03 04' -or $manifest -eq 0 -or $dex -eq 0) {
  throw "Extracted file is not a valid APK"
}

$sizeMb = [math]::Round((Get-Item $OutputApk).Length / 1MB, 2)
Write-Host "READY_APK=$OutputApk" -ForegroundColor Green
Write-Host "SIZE_MB=$sizeMb" -ForegroundColor Green
Write-Host "SIGNATURE=$sig" -ForegroundColor Green
