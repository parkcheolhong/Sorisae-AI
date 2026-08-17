# Sorisae Passkey/FAB 통합 닫기 체크리스트 (2026-08-16)

상태: 완료됨

목적:
- 패스키 콜백 성공, Sorisae FAB 실제 이벤트, 동일 조건 2회 연속 PASS를 단일 체크리스트로 닫는다.

범위:
- 모바일 실디바이스 콜백 검증 스크립트 결과물
- APK 재설치 이후 런타임 기준

## 1) 실검증 전제 고정

- [x] 동일 조건 고정 확인 (디바이스/토큰/API/DevClientUrl)
  - 근거: `scripts/verify_passkey_callback_real_token.ps1` 동일 파라미터로 rerun11, rerun12 실행
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun11-after-reinstall/validation_summary.txt`
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun12-after-reinstall/validation_summary.txt`

- [x] APK 재설치 후 런타임 교체 확인
  - 근거: `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` 강제 재설치(`adb install -r`) 수행
  - 근거: 단말 패키지 정보에서 `lastUpdateTime=2026-08-16 19:30:50` 확인

## 2) 콜백/인증 실검증

- [x] rerun11에서 콜백 성공 및 실패 0건 확인
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun11-after-reinstall/validation_summary.txt`에 `status: PASS`
  - 근거: 동일 파일 전 라운드에서 `passkey_fail_count=0`, `social_fail_count=0`

- [x] rerun12에서 콜백 성공 및 실패 0건 재확인
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun12-after-reinstall/validation_summary.txt`에 `status: PASS`
  - 근거: 동일 파일 전 라운드에서 `passkey_fail_count=0`, `social_fail_count=0`

## 3) Sorisae FAB 실제 이벤트 실검증

- [x] rerun11에서 `SORISAE_FAB_VISIBLE_EVAL` 실이벤트 관측
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun11-after-reinstall/validation_summary.txt` 전 라운드 `sorisae_fab_eval_count>=1`
  - 근거: 동일 파일 `fab_gate_status: PASS`

- [x] rerun12에서 `SORISAE_FAB_VISIBLE_EVAL` 실이벤트 재관측
  - 근거: `evidence/apk-passkey-real-token-e2e-20260816-rerun12-after-reinstall/validation_summary.txt` 전 라운드 `sorisae_fab_eval_count>=1`
  - 근거: 동일 파일 `fab_gate_status: PASS`

## 4) 동일 조건 2회 연속 PASS 닫기

- [x] 2연속 PASS 통합 판정 닫기
  - 근거: rerun11 `status: PASS` + rerun12 `status: PASS`
  - 근거: 두 번들 모두 콜백 성공 이벤트(`PASSKEY_LOGIN_CALLBACK_SUCCESS`, `SOCIAL_LOGIN_CALLBACK_SUCCESS`) 확인
  - 근거: 두 번들 모두 FAB 실제 이벤트 카운트 1 이상 확인

최종 판정:
- 완료됨
