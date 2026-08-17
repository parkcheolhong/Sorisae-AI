# Admin Dashboard authenticated runtime evidence bootstrap 체크리스트

## 검증 기준

- 실제 코드와 브라우저 동작으로 확인된 항목만 `[x]` 처리
- `/admin` 진입 시 토큰이 비어 있어도 검증용 고정 관리자 bootstrap 경로가 살아 있으면 runtime probe 와 auto-connect history 가 인증 상태로 다시 조회되어야 통과 처리
- 수정 후 최소 2회 브라우저 검증 근거가 있어야 닫는다

## 1. 인증 bootstrap 경로 복원

- [x] `frontend/frontend/app/api/proxy/route.ts` 에서 검증 환경용 고정 관리자 세션 bootstrap action 을 제공한다.
  - 근거: `POST http://127.0.0.1:3101/api/proxy?action=admin-bootstrap-session` 실호출이 `source: "fixed-admin-bootstrap"` 와 `access_token` 을 반환했다.
- [x] `frontend/frontend/lib/admin-session.ts` 에서 토큰 부재 시 bootstrap 세션을 확보하는 helper 를 제공한다.
  - 근거: 브라우저 검증 1차/2차 모두 빈 storage 상태로 `/admin` 진입 후 `localStorage.admin_token` 이 자동 생성됐다.

## 2. 관리자 홈 runtime probe / history 연결

- [x] `frontend/frontend/app/admin/page.tsx` 가 토큰 부재 시에도 bootstrap 세션 확보 후 runtime verification 을 재시도한다.
  - 근거: 브라우저 검증 1차/2차 모두 `/admin` 및 `/admin/observability` 에서 `login required` 문구가 사라지고 authenticated 상태로 렌더링됐다.
- [x] `frontend/frontend/app/admin/page.tsx` 가 동일 bootstrap 세션으로 auto-connect history / retry queue / ad-orders preload 를 다시 채운다.
  - 근거: same-origin proxy + validation seed bootstrap 적용 후 브라우저 검증에서 auto-connect panel 요약 수치가 `completion history 2건`, `trace history 2건`, `retry queue 1건` 으로 렌더링됐고, frontend 로그에서도 `admin-ad-video-orders`, `admin-auto-connect-*` preload 200 응답이 함께 확인됐다.

## 3. 실검증

- [x] `/admin` 메인에서 runtime evidence 상태가 `login required` 대신 실제 인증된 probe 결과로 보이는지 1차 브라우저 검증으로 확인한다.
  - 근거: Playwright 1차 검증 결과 `homeHasLoginRequired=false`, `homeTokenPresent=true`, `observabilityHasLoginRequired=false`.
- [x] `/admin` 메인에서 같은 authenticated runtime evidence 상태가 2차 브라우저 검증에서도 유지되는지 확인한다.
  - 근거: Playwright 2차 검증에서 auto-connect panel 을 연 상태에서도 `tokenPresent=true`, `hasLoginRequired=false`, `live action / history composition` 렌더링이 유지됐다.
- [x] `/admin` auto-connect panel 이 실제 DB seed 결과를 history summary 와 `connection_id 기준 DB 조회` 양쪽에 반영하는지 추가 브라우저 검증으로 확인한다.
  - 근거: Playwright 검증에서 panel 요약이 `2건 / 2건 / 1건` 으로 보였고, 이어서 `active 불러오기` → `DB 조회` 실행 시 `trace_key=FLOW-ADM-AUTO-HOME-2:STEP-REFRESH-HISTORY:REFRESH_GRAPH`, `completion=1건`, `logs=1건`, `retry queue=1건` 이 렌더링됐다.

## 현재 판정

- [x] 문서 최종 판정을 완료 기준으로 승격한다.
  - 상태: 완료됨
  - 근거: bootstrap 경로 복원, runtime probe/history 연결, `/admin` 브라우저 검증 2회와 DB 조회 반영 검증까지 모두 `[x]`로 닫혀 있다.
