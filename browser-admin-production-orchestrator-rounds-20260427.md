# Admin Production Verification (2026-04-27)

## 상태

- 최종 판정: 완료됨
- 범위: 운영 도메인 관리자 페이지 `/admin` 무한 인증 대기 원인 추적 및 재검증 2회

## 체크리스트

- [x] `_next` 청크 경로가 `/admin`으로 307 리다이렉트되지 않는지 재확인
- [x] 운영 도메인 관리자 로그인 후 `/admin` 진입 2회 성공
- [x] 우측 레일 `manual-orchestrator` 런처 노출 확인
- [x] 기존 `llm-control` 런처 비노출 확인
- [x] 수동 오케스트레이터 섹션 클릭 전환 2회 성공
- [x] 브라우저 콘솔 에러(특히 `Unexpected token '<'`) 재발 없음

## 원인 추적 결과

- 과거 실패 시점의 핵심 원인: `/_next/static/chunks/0bgayy1-7mp~x.js` 요청이 `/admin`으로 307 리다이렉트되어 JS 대신 HTML이 반환됨.
- 현재 상태: 동일 청크 URL 직접 확인 시 `200 OK`, `Content-Type: application/javascript`로 정상 응답.

## 복구/반영 작업

- `frontend-marketplace`, `frontend-admin` 컨테이너를 재빌드 및 재기동해 최신 프런트 번들/프록시 동작을 반영.
- nginx 경유 운영 도메인에서 `/admin` 응답 정상화 확인.

## 운영 도메인 2회 실검 증적

- 검증 대상 URL: `https://metanova1004.com/admin/login` -> `https://xn--114-2p7l635dz3bh5j.com/admin`
- 실행 계정: `ui.admin.round@devanalysis.local`

### Run 1

- url: `https://xn--114-2p7l635dz3bh5j.com/admin`
- hasManualLauncher: true
- hasLegacyLlmLauncher: false
- manualSectionVisible: true
- tokenExists: true

### Run 2

- url: `https://xn--114-2p7l635dz3bh5j.com/admin`
- hasManualLauncher: true
- hasLegacyLlmLauncher: false
- manualSectionVisible: true
- tokenExists: true

## 추가 확인

- 운영 도메인 청크 직접 점검:
  - `https://xn--114-2p7l635dz3bh5j.com/_next/static/chunks/0bgayy1-7mp~x.js`
  - 응답: `200 OK`, `Content-Type: application/javascript; charset=UTF-8`
- Playwright 콘솔 에러 레벨 메시지: 0건
