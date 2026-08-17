# adb_sorisae_runtime 원인 축소 리포트

- 대상 번들: evidence/device-validation-rerun2-20260816-153238
- 대상 프로브: evidence/sorisae-friend-chat-probe-20260816-063105/report.json

## 결론
`adb_sorisae_runtime` 실패의 1차 원인은 모델/백엔드/STT 경로가 아니라 **실기기 UI가 로그인 모달 상태로 시작되어 소리새 진입이 차단되는 것**으로 축소되었습니다.

즉, 현재 프로브의 고정 좌표 탭이 소리새 FAB/윈도우를 열지 못해 `segment_response` 로그가 발생하지 않습니다.

## 근거
- UI 덤프 판정
  - `worldlinco-login-modal`: `True`
  - `worldlinco-auth-login-submit-button` 또는 텍스트 `로그인`: `True`
  - `worldlinco-sorisae-fab` / `worldlinco-sorisae-window` / `소리새` 노드: `False`
- 로그 판정 (`adb_sorisae_runtime` 규칙과 동일)
  - `segment_response` 존재: `False`
  - `sorisae_segment_skip_preupload` 과도 루프(>=8): `False`
  - `rejected noise/hallucination` 과다(>=3): `False`

## 해석
- 실패는 "잘못된 음성 입력"이나 "서버 불응" 패턴이 아니라,
  **소리새 세그먼트 요청 자체가 시작되지 않은 UI 진입 실패 패턴**입니다.
- 따라서 다음 수정 포인트는 런타임/모델이 아니라 프로브 진입 단계입니다.
  - 로그인 모달 닫기/로그인 선행
  - 고정 좌표 탭 대신 접근성 ID(`worldlinco-sorisae-fab`) 기반 탭 사용
