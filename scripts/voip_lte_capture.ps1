#!/usr/bin/env pwsh
# 장거리(통신사 교차) 통화 릴레이 실측 캡처 — 두 단말 logcat + coturn + backend 동시 수집/판정.
#
# 사용:
#   pwsh scripts/voip_lte_capture.ps1 -SkDevice R3CT209943N -KtDevice R83W70QY11H -DurationSec 150
#   (스크립트 시작 후 안내가 뜨면 한 폰에서 상대 폰으로 보이스톡을 걸고 받으세요.)
param(
    [string]$SkDevice = "R3CT209943N",
    [string]$KtDevice = "R83W70QY11H",
    [int]$DurationSec = 150,
    [string]$CoturnContainer = "worldlinco-coturn",
    [string]$BackendContainer = "devanalysis114-backend"
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RepoRoot "evidence/lte-matrix/relay-call-$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$startUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss")

Write-Host "[capture] run dir: $RunDir"
Write-Host "[capture] clearing logcat on both devices..."
adb -s $SkDevice logcat -c 2>&1 | Out-Null
adb -s $KtDevice logcat -c 2>&1 | Out-Null

# 단말 logcat 을 백그라운드 Job 으로 수집(ReactNativeJS = JS 콘솔 로그 태그).
$skLog = Join-Path $RunDir "sk_logcat.log"
$ktLog = Join-Path $RunDir "kt_logcat.log"
$jobSk = Start-Job { param($d,$f) & adb -s $d logcat -v time ReactNativeJS:* *:S | Out-File -FilePath $f -Encoding utf8 } -ArgumentList $SkDevice,$skLog
$jobKt = Start-Job { param($d,$f) & adb -s $d logcat -v time ReactNativeJS:* *:S | Out-File -FilePath $f -Encoding utf8 } -ArgumentList $KtDevice,$ktLog

Write-Host ""
Write-Host "================== 지금 통화를 거세요 =================="
Write-Host "  SK폰($SkDevice) → KT폰($KtDevice) 로 보이스톡 걸기 → KT폰에서 받기"
Write-Host "  ${DurationSec}초 동안 캡처합니다. 통화 연결 후 몇 초 말해 보세요."
Write-Host "========================================================"
Write-Host ""
for ($i = $DurationSec; $i -gt 0; $i -= 10) {
    Start-Sleep -Seconds 10
    Write-Host "[capture] $i 초 남음..."
}

Write-Host "[capture] stopping logcat jobs..."
Stop-Job $jobSk, $jobKt 2>&1 | Out-Null
Receive-Job $jobSk 2>&1 | Out-Null
Receive-Job $jobKt 2>&1 | Out-Null
Remove-Job $jobSk, $jobKt -Force 2>&1 | Out-Null

# coturn / backend 로그(캡처 시작 이후).
docker logs $CoturnContainer --since "${startUtc}Z" 2>&1 | Out-File (Join-Path $RunDir "coturn.log") -Encoding utf8
docker logs $BackendContainer --since "${startUtc}Z" 2>&1 | Out-File (Join-Path $RunDir "backend.log") -Encoding utf8

function Show-Gate([string]$Name, [bool]$Ok, [string]$Detail) {
    $flag = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host ("  [{0}] {1}: {2}" -f $flag, $Name, $Detail)
}

Write-Host ""
Write-Host "================== 판정(게이트) =================="

# 1) 통화 시그널링 발생(백엔드 Offer/Answer)
$offer = (Select-String -Path (Join-Path $RunDir "backend.log") -Pattern "Offer received|Answer sent|Call initiated" -ErrorAction SilentlyContinue)
Show-Gate "signaling" ([bool]$offer) ("backend Offer/Answer/Init " + (($offer | Measure-Object).Count) + "건")

# 2) TURN 릴레이 활성(force_relay)
$turnAct = (Select-String -Path (Join-Path $RunDir "backend.log") -Pattern "\[voip\]\[TURN\] 릴레이 활성" -ErrorAction SilentlyContinue | Select-Object -First 1)
Show-Gate "turn_active" ([bool]$turnAct) ($(if ($turnAct) { $turnAct.Line.Trim() } else { "백엔드 릴레이 활성 로그 없음" }))

# 3) coturn 세션/할당(실제 미디어 릴레이 — 두 통신사 IP)
$cotAlloc = (Select-String -Path (Join-Path $RunDir "coturn.log") -Pattern "allocation|new session|peer|channel|created permission" -ErrorAction SilentlyContinue)
Show-Gate "coturn_relay" ([bool]$cotAlloc) ("coturn 세션/할당 " + (($cotAlloc | Measure-Object).Count) + "건(통신사 IP 릴레이 증거)")

# 4) 단말에서 원격 오디오 트랙 수신(=음성 도달)
$skTrack = (Select-String -Path $skLog -Pattern "Track received|Remote stream received" -ErrorAction SilentlyContinue)
$ktTrack = (Select-String -Path $ktLog -Pattern "Track received|Remote stream received" -ErrorAction SilentlyContinue)
Show-Gate "media_sk" ([bool]$skTrack) ("SK폰 ontrack/remote-stream " + (($skTrack | Measure-Object).Count) + "건")
Show-Gate "media_kt" ([bool]$ktTrack) ("KT폰 ontrack/remote-stream " + (($ktTrack | Measure-Object).Count) + "건")

Write-Host "=================================================="
Write-Host "[capture] 증거: $RunDir (sk_logcat.log / kt_logcat.log / coturn.log / backend.log)"
