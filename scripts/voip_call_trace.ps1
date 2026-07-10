#!/usr/bin/env pwsh
<#
.SYNOPSIS
    장거리 통화 테스트용 통화 이력 추적기.
    백엔드 컨테이너 로그에서 VoIP/음성/번역 이벤트만 추려 [신호]/[음성]/[텍스트]/[통화] 로 분류해 보여준다.

.DESCRIPTION
    "신호는 가는지 / 음성(통역)은 되는지 / 텍스트 전달은 되는지" 를 한 화면에서 확인하기 위한 도구.
    - 신호(SIGNAL): WebRTC offer/answer/candidate 중계, 시그널링 연결/해제 — 통화 연결 여부
    - 음성(VOICE) : voice_translation 중계, STT 전사/감지 언어 — 음성 통역 전달 여부
    - 텍스트(TEXT): chat_message 중계 — 채팅/번역 텍스트 전달 여부
    - 통화(CALL)  : 통화 시작/종료/상태/오류

.PARAMETER CallId
    특정 call_id 만 필터. 비우면 모든 통화 이벤트.

.PARAMETER Follow
    실시간 추적(통화하면서 바로 보기). 미지정 시 최근 로그 1회 출력 + 요약.

.PARAMETER Since
    조회 시작 시점(docker 형식). 예: 10m, 1h, 2026-06-22T10:00:00. 기본 30m.

.PARAMETER TailLines
    1회 출력 시 마지막 N줄에서 추림. 기본 2000.

.EXAMPLE
    # 실시간으로 모든 통화 추적(테스트 중 켜두기)
    pwsh scripts/voip_call_trace.ps1 -Follow

.EXAMPLE
    # 특정 통화만, 최근 1시간
    pwsh scripts/voip_call_trace.ps1 -CallId 1a2b3c -Since 1h
#>
param(
    [string]$CallId = "",
    [switch]$Follow,
    [string]$Since = "30m",
    [int]$TailLines = 2000,
    [string]$Container = "devanalysis114-backend"
)

$ErrorActionPreference = "Stop"

# 관심 로그만 통과시키는 1차 필터(노이즈 제거).
$interest = '(\[VoIP\]|\[voice-stt\]|\[voice/synthesize\]|voice_translation|chat_message)'

function Get-Category {
    param([string]$line)
    switch -Regex ($line) {
        'voice_translation|\[voice-stt\]|\[voice/synthesize\]|transcript|detected' { return 'VOICE' }
        'chat_message'                                                             { return 'TEXT' }
        'Signal relayed|Signal queued|Signal direct|App signaling|type=offer|type=answer|type=candidate' { return 'SIGNAL' }
        'Call initiated|hangup|Call state|pruned|disconnected|error|threshold'      { return 'CALL' }
        default                                                                    { return 'CALL' }
    }
}

function Write-TraceLine {
    param([string]$line)
    if ($line -notmatch $interest) { return }
    if ($CallId -and ($line -notmatch [regex]::Escape($CallId))) { return }

    $cat = Get-Category $line
    $tag, $color = switch ($cat) {
        'SIGNAL' { '[신호]', 'Cyan' }
        'VOICE'  { '[음성]', 'Green' }
        'TEXT'   { '[텍스트]', 'Yellow' }
        default  { '[통화]', 'Magenta' }
    }
    # docker 로그 앞 타임스탬프(있으면) 그대로 살림.
    Write-Host $tag -ForegroundColor $color -NoNewline
    Write-Host (" " + $line)
    return $cat
}

Write-Host "==== VoIP 통화 추적기 ($Container) ====" -ForegroundColor White
if ($CallId) { Write-Host "필터 call_id = $CallId" -ForegroundColor DarkGray }
Write-Host "범례: [신호]=연결 신호  [음성]=음성통역 전달  [텍스트]=채팅 전달  [통화]=시작/종료/오류" -ForegroundColor DarkGray
Write-Host ("-" * 60) -ForegroundColor DarkGray

if ($Follow) {
    Write-Host "실시간 추적 중... (중지: Ctrl+C)" -ForegroundColor DarkGray
    # docker logs 는 stderr 로 출력 → 2>&1 병합 후 라인별 처리.
    docker logs -f --since $Since --timestamps $Container 2>&1 | ForEach-Object {
        Write-TraceLine ([string]$_) | Out-Null
    }
}
else {
    $lines = docker logs --since $Since --timestamps --tail $TailLines $Container 2>&1
    $counts = @{ SIGNAL = 0; VOICE = 0; TEXT = 0; CALL = 0 }
    foreach ($l in $lines) {
        $cat = Write-TraceLine ([string]$l)
        if ($cat) { $counts[$cat]++ }
    }
    Write-Host ("-" * 60) -ForegroundColor DarkGray
    Write-Host "요약(최근 $Since):" -ForegroundColor White
    Write-Host ("  신호(SIGNAL)  : {0}  →  통화 연결 신호 교환 여부" -f $counts.SIGNAL) -ForegroundColor Cyan
    Write-Host ("  음성(VOICE)   : {0}  →  음성 통역 전달 여부" -f $counts.VOICE) -ForegroundColor Green
    Write-Host ("  텍스트(TEXT)  : {0}  →  채팅/번역 텍스트 전달 여부" -f $counts.TEXT) -ForegroundColor Yellow
    Write-Host ("  통화(CALL)    : {0}  →  시작/종료/상태/오류" -f $counts.CALL) -ForegroundColor Magenta
    if ($counts.SIGNAL -eq 0 -and $counts.VOICE -eq 0 -and $counts.TEXT -eq 0) {
        Write-Host "  (해당 구간에 통화 이벤트 없음 — -Since 를 늘리거나 통화를 시작하세요)" -ForegroundColor DarkYellow
    }
}
