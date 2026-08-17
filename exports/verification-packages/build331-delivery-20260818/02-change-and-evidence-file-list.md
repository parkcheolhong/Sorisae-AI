# 변경/근거 파일 목록 (2026-08-18)

## A. 이번 작업에서 변경된 파일

1. `mobile-realdevice-readiness-validation-20260818.md`
- 변경 내용: 일반 리포트 형식을 체크리스트 형식으로 병합 (상태/목적/범위/체크 항목/근거/최종 판정).

1. `exports/bundle-331-featured/EXTRACT_MANIFEST.txt`
- 변경 내용: `extract_331_feature_bundle.ps1 -CleanOutput` 재실행으로 재생성.

1. `exports/verification-reports/bundle-331-featured-copy-verify-20260818-045931.md`
- 변경 내용: 추출본 복제 후 무결성 검증 1차 리포트 생성.

1. `exports/verification-reports/bundle-331-featured-copy-verify-20260818-045940.md`
- 변경 내용: 무결성 검증 2차 리포트 생성.

## B. 이번 검증의 핵심 근거 파일

1. 추출/무결성
- `exports/bundle-331-featured/EXTRACT_MANIFEST.txt`
- `exports/verification-reports/bundle-331-featured-copy-verify-20260818-045931.md`
- `exports/verification-reports/bundle-331-featured-copy-verify-20260818-045940.md`

1. 관리자 패스키 운영 검증
- `frontend/frontend/tests/admin-passkey-operational.playwright.spec.ts`
- `frontend/frontend/test-results/admin-passkey-operational.-068ea--operational-flow-attempt-1-chromium/admin-passkey-operational-evidence-attempt-1.json`
- `frontend/frontend/test-results/admin-passkey-operational.-d09d6--operational-flow-attempt-2-chromium/admin-passkey-operational-evidence-attempt-2.json`

1. 마켓플레이스 패스키 로그인 검증
- `frontend/frontend/tests/marketplace-passkey-login.playwright.spec.ts`
- 실행 근거: 플레이wright 재실행 결과 `2 passed (1.9s)`

1. 체크리스트 병합 결과
- `mobile-realdevice-readiness-validation-20260818.md`

## C. 참고 스크립트
- `scripts/extract_331_feature_bundle.ps1`
