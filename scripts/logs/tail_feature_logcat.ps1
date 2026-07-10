#!/usr/bin/env pwsh
# 기능별 클라이언트(logcat) 로그 분리 스트림.
# 사용자는 한 번에 한 기능만 사용하므로, 디버깅/검증 시 기능별로 로그를 격리해서 본다.
#
# 사용:
#   pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature face
#   pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature sorisae -DeviceId R3CT...
#   pwsh -File scripts/logs/tail_feature_logcat.ps1 -Feature voip
#
# Feature: face | sorisae | voip | chat | phone | song | all
#
# 분리 기준(마스터 기술서 §3 / correlationId FEATURE_IDS):
#   - 콘솔 태그([FACE_CONVERSATION] 등) + 기능 correlation 접두(face.interpret 등)로 grep.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('face', 'sorisae', 'voip', 'chat', 'phone', 'song', 'all')]
    [string]$Feature,
    [string]$DeviceId = ""
)

$ErrorActionPreference = "Stop"

# 기능별 매칭 패턴(콘솔 태그 + correlation 접두 + 핵심 키워드). ReactNativeJS 로그를 통과시킨다.
$patterns = @{
    face    = '\[FACE_CONVERSATION\]|face\.interpret|voice-translate|bilingual'
    # 소리새는 대면통역과 같은 캡처 루프를 쓰지만 라우트가 친구챗 → 별도 키워드로 분리 가시화.
    sorisae = '소리새|friend-chat|sorisae|SORISAE'
    voip    = '\[VOIP|\[VoIP|voip\.voice_relay|VOIP_VOICE_RELAY|VoIPPendingIncoming|signaling'
    chat    = '\[CHAT|chat\.translate|ChatRoom|chat_message'
    phone   = 'inter_call|InterCall|PSTN|pstn|dialer|일반 통화'
    song    = 'song\.translate|SongFile|가사|songMode|노래'
}

$tagPattern = if ($Feature -eq 'all') {
    'ReactNativeJS'
} else {
    $patterns[$Feature]
}

$deviceArg = if ($DeviceId) { @('-s', $DeviceId) } else { @() }

Write-Host "[feature-logcat] feature=$Feature pattern=/$tagPattern/" -ForegroundColor Cyan
Write-Host "[feature-logcat] (Ctrl+C 로 종료)" -ForegroundColor DarkGray

# 버퍼 비우고 실시간 tail. ReactNativeJS 우선 + 패턴 필터.
& adb @deviceArg logcat -c 2>$null
& adb @deviceArg logcat ReactNativeJS:V '*:S' --format=time |
    Select-String -Pattern $tagPattern
