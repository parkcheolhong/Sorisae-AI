# Admin Dashboard auto-connect / runtime evidence 복원 체크리스트

## 검증 기준

- 실제 코드와 브라우저 동작으로 확인된 항목만 `[x]` 처리
- `auto-connect` 는 lookup 전용 경량 상태를 넘어서 live history / action / retry composition 이 보여야 통과 처리
- `runtime evidence` 는 3장 요약 카드가 아니라 segmented board + gate summary + probe table 수준으로 체감 가능한 정보량 증가가 있어야 통과 처리
- 수정 후 최소 2회 브라우저 검증 근거가 있어야 닫는다

## 1. auto-connect deeper action/history 복원

- [x] `frontend/frontend/components/admin/admin-auto-connect-graph-panel.tsx` 가 active graph + DB lookup 만이 아니라 live completion / trace / retry history 와 filter 조합을 함께 보여준다.
  - 근거: `frontend/frontend/components/admin/admin-auto-connect-graph-panel.tsx` 에 `live action / history composition`, `history 새로고침`, `completion history`, `trace history`, `retry queue history` 섹션 추가
  - 근거: 1차 브라우저 검증에서 `live action / history composition`, `completion history`, `trace history`, `retry queue history`, `history 새로고침` 문자열 확인
- [x] `frontend/frontend/lib/use-admin-auto-connect-controller.ts` 가 live history 조회와 trace filter 를 다시 제공한다.
  - 근거: `frontend/frontend/lib/admin-auto-connect-service.ts` 에 completions/logs/retry-queue loader 추가
  - 근거: `frontend/frontend/lib/use-admin-auto-connect-controller.ts` 에 `loadAdminCompletionHistory`, `loadAdminTraceHistory`, `loadAdminRetryQueue`, `adminTraceFilter`, filtered history 배열 추가

## 2. runtime evidence / connectivity 세분화 복원

- [x] `frontend/frontend/app/admin/page.tsx` 의 health-analysis 영역이 3장 summary card 에서 segmented board 로 확장된다.
  - 근거: `frontend/frontend/app/admin/page.tsx` 에 runtime banner, segmented observability cards, `Gate Status`, `Probe Table`, `Connectivity drill-down` 블록 추가
- [x] gate summary 와 probe table 이 관리자 홈에서 직접 보이도록 복구한다.
  - 근거: 1차 브라우저 검증에서 `runtime-verification 최종 집계`, `현재 probe 상태` 확인
  - 근거: 2차 브라우저 검증에서 `Evidence Verified`, `Warnings / Failed` 확인

## 3. 실검증

- [x] `/admin` 에서 `self auto-connect graph` 창을 열었을 때 live history / filter / retry composition 이 1차 브라우저 검증에서 확인된다.
  - 근거: Playwright 1차 검증에서 launcher `창 열기` 4번째 버튼을 눌러 `live action / history composition`, `completion history`, `trace history`, `retry queue history`, `history 새로고침` 확인
- [x] `/admin` 에서 `self auto-connect graph` 창을 다시 열었을 때 같은 richer composition 이 2차 브라우저 검증에서도 유지된다.
  - 근거: Playwright 2차 검증에서 `live action / history composition`, `completion history`, `trace history`, `retry queue history`, `connection_id 기준 DB 조회` 재확인
- [x] `/admin` 메인에서 runtime evidence / connectivity segmented board 가 1차 브라우저 검증에서 확인된다.
  - 근거: Playwright 1차 검증에서 `runtime-verification 최종 집계`, `현재 probe 상태` 확인
- [x] `/admin` 메인에서 runtime evidence / connectivity segmented board 가 2차 브라우저 검증에서도 유지된다.
  - 근거: Playwright 2차 검증에서 `runtime-verification 최종 집계`, `현재 probe 상태`, `Evidence Verified`, `Warnings / Failed` 재확인

## 현재 판정

- [x] 문서 최종 판정을 완료 기준으로 승격한다.
  - 상태: 완료됨
  - 근거: auto-connect richer composition 복구와 runtime evidence 세분화 복구 항목, `/admin` 브라우저 검증 2회 항목이 모두 `[x]`로 닫혀 있다.
