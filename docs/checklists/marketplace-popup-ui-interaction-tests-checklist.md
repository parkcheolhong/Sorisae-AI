# Marketplace Popup UI Interaction Tests Checklist

## Scope
- 대상:
  - `frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-*.tsx`
  - `frontend/frontend/package.json`

## Checklist
- [x] UI 상호작용 테스트 방식과 실행 스택을 확정한다.
- [x] 팝업 열림/닫힘 상호작용 테스트를 추가한다.
- [x] Escape / focus / submit 관련 상호작용 테스트를 추가한다.
- [x] 기능별 결과 패널 노출 상호작용 테스트를 추가한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run build` 성공, `npm run start -- --hostname 127.0.0.1 --port 3000` 서버 기동 성공, `npm run e2e:marketplace-popup-interactions` 3개 테스트 통과)
- 2차 verify: 통과 (`npm run verify:frontend` 2회 선행 통과 상태 유지, Playwright popup interaction E2E는 production 외부 서버 재사용 흐름에서 통과)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- 기존 스택으로 어려우면 실행 가능한 최소 UI 상호작용 테스트 환경을 추가한다.
- 구현 근거: `frontend/frontend/tests/marketplace-popup-interactions.playwright.spec.ts` 추가. 열기/닫기, Escape, focus 이동, 입력/submit, 기능별 결과 패널 노출을 Playwright로 검증했다. `playwright.marketplace.config.ts`는 외부 서버 재사용 우선 구조로 조정했고, `npm run build` 후 `npm run start -- --hostname 127.0.0.1 --port 3000`로 띄운 production 서버에 붙여 테스트를 통과시켰다.
- 정식 편입 경로: `npm run verify:popup-ui` → `npm run verify` + `npm run test:popup-ui-interactions` 순서로 실행한다.
