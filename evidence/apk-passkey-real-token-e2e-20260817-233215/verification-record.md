# 실기기 검증 기록

일시: 2026-08-17 23:32 KST

목적:
- 실제 디바이스 `172.30.1.15:5555`에서 OAuth 콜백 딥링크 수신을 확인하고, 직후 재주입 시 중복 소비 가드가 의도대로 동작하는지 기록한다.

실행 과정:
1. 초기 태스크 `shell: rerun-passkey-callback-verifier` 를 실행했다.
2. 태스크는 더미 토큰 사전 검증에서 `token preflight failed: /api/auth/me status=401` 로 중단됐다.
3. 같은 검증 스크립트를 실제 JWT로 다시 실행했고, `-SkipTokenPreflight` 와 `-AuthApiBase http://127.0.0.1:8000` 조건으로 디바이스 콜백 경로만 재검증했다.
4. 검증 스크립트는 `PASS` 를 반환했고, 증거 디렉터리는 `evidence/apk-passkey-real-token-e2e-20260817-233215` 이다.

판정 근거:
- `validation_summary.txt` 에 `status: PASS` 가 기록됐다.
- round 1 / round 2 모두 `passkey_success=True`, `social_success=True`, `passkey_fail_count=0`, `social_fail_count=0` 이다.
- round 1 / round 2 모두 `show_login_false_count > 0` 이고 `has_error_activity=False` 이다.
- logcat 에서 `PASSKEY_LOGIN_CALLBACK_SUCCESS` 와 `SOCIAL_LOGIN_CALLBACK_SUCCESS` 가 확인됐다.
- logcat 에서 재주입 직후 `APP_ENTRY_DEEP_LINK_SKIPPED_ALREADY_CONSUMED` 가 확인됐다.

핵심 로그 위치:
- [validation_summary.txt](validation_summary.txt)
- [01_logcat.txt](01_logcat.txt)
- [02_logcat.txt](02_logcat.txt)

판정:
- 콜백 수신 성공
- 세션 복원 성공
- 중복 소비 가드 성공