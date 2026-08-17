# WorldLinco 회귀 방지 규칙 (테스트/CI 게이트 SSOT)

## 목적
- 인증, 음성 캡처, VoIP 상태전이, 여행 검색, 채팅 핵심 경로의 무단 회귀를 차단한다.
- PR 단계에서 테스트 근거 없는 핫패스 변경을 방지한다.

## 1) 변경 금지 계약 (Hot Path)
- 인증 핫패스:
  - 로그인 엔드포인트/폼 계약 유지: POST /api/auth/login, x-www-form-urlencoded username/password
  - 세션 조회 인증 헤더 유지: Authorization Bearer 토큰
- 음성 캡처 핫패스:
  - 단일 소유권 계약 유지: acquire 시 기존 owner revoke 우선, owner 교체 후 start
  - 강제 정리 경로 유지: revokeCurrentVoiceCapture는 owner/revoke 상태를 null로 정리
- VoIP 상태전이 핫패스:
  - remote listen hold 동안 capture/send 차단 규칙 유지
  - local send 이후 장기 lock 금지(짧은 re-arm만 허용)
- 여행 검색 핫패스:
  - 거리 표기 계약(1km 미만 m, 이상 km 소수 1자리)
  - 지도 라벨 HTML escape 계약 유지

## 2) 공개 API 계약 (Public API)
- appApiClient
  - callLoginApi(email, password) => access_token string
  - fetchVoipCallResumeSnapshot(apiBase, token, callId) => CallInitResponse|null
  - requestEndVoipCall(apiBase, token, callId, callQuality) => void
- translate API
  - translateText(text, from, to, timeoutMs?, options?) => TranslateResult
- chat API
  - sendChatRoomMessage(apiBase, token, roomId, payload) => ChatMessageItem

## 3) 상태 계약 (State Contract)
- voiceCaptureLease
  - current owner는 동시 1개만 허용
  - 동일 owner 재획득은 revoke 콜백만 갱신
  - release/revoke 후 owner는 null이어야 함
- VoIP turn state
  - remote relay 수신 후 listen hold 적용
  - hold 구간에서 capture/send 금지
  - hold 종료 후 capture 허용

## 4) 필수 검증 세트
- Unit Gate
  - src/__tests__/biometricGate.test.ts
  - src/__tests__/voiceCaptureLease.test.ts
  - src/__tests__/voiceRelayTurnController.test.ts
  - src/__tests__/travelBooking.test.ts
- Integration Gate
  - src/__tests__/worldlincoCoreFlow.integration.test.ts

## 5) PR 체크리스트 연동
- PR은 아래 조건을 모두 충족해야 한다.
  - 본 문서의 Hot Path/Public API/State Contract 위반 없음
  - Unit Gate + Integration Gate CI 2회 연속 PASS
  - 체크리스트 근거 파일 업데이트 완료
