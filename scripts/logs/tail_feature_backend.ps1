#!/usr/bin/env pwsh
# 기능별 백엔드(docker) 로그 분리 스트림.
# 통역/통화/채팅/예약 경로가 백엔드 로그에서 섞이지 않도록 기능 단위로 필터해서 본다.
#
# 사용:
#   pwsh -File scripts/logs/tail_feature_backend.ps1 -Feature voip
#   pwsh -File scripts/logs/tail_feature_backend.ps1 -Feature face -Since 10m
#
# Feature: face | sorisae | voip | chat | phone | song | bridge | all
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('face', 'sorisae', 'voip', 'chat', 'phone', 'song', 'bridge', 'all')]
    [string]$Feature,
    [string]$Container = "devanalysis114-backend",
    [string]$Since = "5m"
)

$ErrorActionPreference = "Stop"

# 기능별 백엔드 로거/엔드포인트 매칭(라우터 모듈명 + 엔드포인트 경로 + correlation 접두).
$patterns = @{
    face    = 'face/voice-translate|face\.interpret|bilingual'
    sorisae = 'voice/friend-chat|friend_chat|sorisae'
    voip    = 'nadotongryoksa_voip_router|voip-voice-relay|\[VoIP\]|signaling'
    chat    = 'nadotongryoksa_chat_router|chat\.translate|chat_message'
    phone   = 'pstn|inter_call|telephony|orchestrate'
    song    = 'song\.translate|voice/orchestrate|lyric'
    bridge  = 'media_bridge|\[bridge\]|interpret emit|tts injected'
    all     = '.'
}

$pattern = $patterns[$Feature]

Write-Host "[feature-backend] feature=$Feature container=$Container since=$Since pattern=/$pattern/" -ForegroundColor Cyan
Write-Host "[feature-backend] (Ctrl+C 로 종료)" -ForegroundColor DarkGray

if ($Feature -eq 'all') {
    & docker logs -f --since $Since $Container 2>&1
} else {
    & docker logs -f --since $Since $Container 2>&1 | Select-String -Pattern $pattern
}
