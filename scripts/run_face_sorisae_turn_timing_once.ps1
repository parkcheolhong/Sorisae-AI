param(
    [string]$Serial = "",
    [string]$Label = "",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$FaceP95MaxMs = 9000,
    [int]$SorisaeP95MaxMs = 12000,
    [int]$MaxCutSignals = 4
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$evidenceRoot = Join-Path $repoRoot "evidence/turn-timing"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $evidenceRoot $timestamp

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$adbArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Serial)) {
    $adbArgs += @("-s", $Serial)
}

Write-Host "[timing] clear logcat buffer"
& adb @adbArgs logcat -c

Write-Host "[timing] 실기기에서 아래 순서로 1회씩 수행하세요:"
Write-Host "  1) 대면통역 1턴 발화 후 결과 대기"
Write-Host "  2) 소리새 대화 1턴 발화 후 결과 대기"
Write-Host "완료되면 Enter"
Read-Host | Out-Null

$logPath = Join-Path $outDir "device.log"
$jsonPath = Join-Path $outDir "report.json"
$mdPath = Join-Path $outDir "report.md"
$metaPath = Join-Path $outDir "meta.json"

$model = (& adb @adbArgs shell getprop ro.product.model 2>$null | Out-String).Trim()
$brand = (& adb @adbArgs shell getprop ro.product.brand 2>$null | Out-String).Trim()
$device = (& adb @adbArgs shell getprop ro.product.device 2>$null | Out-String).Trim()
$fingerprint = (& adb @adbArgs shell getprop ro.build.fingerprint 2>$null | Out-String).Trim()

$dumpsys = (& adb @adbArgs shell dumpsys package $PackageName 2>$null | Out-String)
$versionName = ""
$versionCode = ""
if ($dumpsys -match "versionName=([^\r\n]+)") {
    $versionName = $matches[1].Trim()
}
if ($dumpsys -match "versionCode=(\d+)") {
    $versionCode = $matches[1].Trim()
}

$meta = [ordered]@{
    captured_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    label = $Label
    serial = $Serial
    package_name = $PackageName
    app_version_name = $versionName
    app_version_code = $versionCode
    device_model = $model
    device_brand = $brand
    device_name = $device
    build_fingerprint = $fingerprint
}

$meta | ConvertTo-Json -Depth 4 | Out-File $metaPath -Encoding utf8

Write-Host "[timing] meta saved -> $metaPath"
if (-not [string]::IsNullOrWhiteSpace($versionCode) -or -not [string]::IsNullOrWhiteSpace($versionName)) {
    Write-Host "[timing] app version -> code=$versionCode name=$versionName"
}

Write-Host "[timing] dump logcat -> $logPath"
& adb @adbArgs logcat -d -v time ReactNativeJS:I *:S | Out-File $logPath -Encoding utf8

Write-Host "[timing] analyze logs"
Set-Location $repoRoot
python scripts/analyze_face_sorisae_turn_timing.py `
  --log "$logPath" `
  --out "$jsonPath" `
  --out-md "$mdPath" `
  --face-ok-min 1 `
  --sorisae-ok-min 1 `
  --face-p95-max-ms $FaceP95MaxMs `
  --sorisae-p95-max-ms $SorisaeP95MaxMs `
  --max-cut-signals $MaxCutSignals

if ($LASTEXITCODE -ne 0) {
    Write-Host "[timing] FAIL - report: $jsonPath"
    exit $LASTEXITCODE
}

Write-Host "[timing] PASS - report: $jsonPath"
Write-Host "[timing] markdown: $mdPath"
