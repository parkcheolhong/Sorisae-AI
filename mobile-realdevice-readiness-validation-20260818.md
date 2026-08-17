# 모바일 실기기 검증 전 실행준비 체크리스트 (2026-08-18)

상태: 완료됨

목적:
- 실기기 검증 전, 현재 앱이 실제 실행 가능한 상태인지 확인한다.
- 마켓플레이스/관리자 운영 화면 경로와 응답이 추출 정제본 검증 의도와 일치하는지 닫는다.

범위:
- 브라우저 기반 운영 경로 실검증
- 관리자/마켓플레이스 패스키 흐름
- 핵심 라우트 응답 상태 확인

## 1) 관리자 패스키 운영 흐름

- [x] 관리자 패스키 운영 시나리오가 2회 시도 모두 통과했다.
- 근거: 실행 명령 `npm run e2e:admin:passkey-operational` 결과 `2 passed (10.3s)`.
- 근거: `frontend/frontend/test-results/admin-passkey-operational.-068ea--operational-flow-attempt-1-chromium/admin-passkey-operational-evidence-attempt-1.json`.
- 근거: `frontend/frontend/test-results/admin-passkey-operational.-d09d6--operational-flow-attempt-2-chromium/admin-passkey-operational-evidence-attempt-2.json`.

## 2) 마켓플레이스 패스키 로그인 흐름

- [x] 외부 서버 재사용 모드에서 패스키 로그인 시나리오가 통과했다.
- 근거: 실행 명령 `$env:PLAYWRIGHT_USE_WEBSERVER='0'; $env:PLAYWRIGHT_MARKETPLACE_BASE_URL='http://localhost:3000'; npx playwright test -c playwright.config.ts tests/marketplace-passkey-login.playwright.spec.ts --project chromium --no-deps` 결과 `2 passed (1.9s)`.
- 근거: 검증 행동 `auth_mode=passkey_login` 딥링크 세션 적용, 사용자 프로필 표시, `mobile_return_uri` 콜백 리다이렉트 확인.

- [x] 기본 npm 스크립트 충돌 조건을 식별하고 우회 경로를 고정했다.
- 근거: `npm run e2e:marketplace:passkey-login` 1회 실패 원인 `PLAYWRIGHT_USE_WEBSERVER=1` + `PLAYWRIGHT_MARKETPLACE_BASE_URL=http://localhost:3005` URL/포트 충돌.
- 근거: 외부 서버 재사용 모드(`PLAYWRIGHT_USE_WEBSERVER=0`)에서 재실행 PASS.

## 3) 운영 라우트 응답 상태

- [x] 핵심 화면 라우트가 실제 HTTP 200 으로 응답했다.
- 근거: `http://localhost:3000/marketplace` -> 200, `text/html; charset=utf-8`.
- 근거: `http://localhost:3005/admin/login` -> 200, `text/html; charset=utf-8`.

## 4) 결론

- [x] 실기기 검증 전 브라우저 기반 실행준비 게이트를 통과했다.
- 근거: 관리자 패스키 PASS + 마켓플레이스 패스키 PASS + 핵심 라우트 200 확인.

최종 판정:
- 완료됨

비고:
- 현재 환경은 물리 단말 직접 제어가 불가하므로, 실기기 단계 직전 게이트는 브라우저 기반 운영 경로/딥링크/콜백 검증으로 대체해 닫았다.
