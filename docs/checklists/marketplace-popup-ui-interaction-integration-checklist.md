# Marketplace Popup UI Interaction Integration Checklist

## Scope
- 대상:
  - `frontend/frontend/package.json`
  - `frontend/frontend/playwright.marketplace.config.ts`
  - `frontend/frontend/tests/marketplace-popup-interactions.playwright.spec.ts`
  - `docs/checklists/marketplace-popup-ui-interaction-tests-checklist.md`

## Checklist
- [x] popup interaction Playwright를 공식 검증 흐름에 편입할 구조를 확정한다.
- [x] package 스크립트에 정식 검증 경로를 추가한다.
- [x] production 외부 서버 재사용 전략을 문서/스크립트 기준으로 고정한다.
- [x] 편입된 검증 경로를 실제 실행해 통과를 확인한다.
- [x] 자동 검증 관련 문서와 체크리스트를 동기화한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:popup-ui` - build/verify/test:popup-ui-interactions/Playwright 3개 테스트 성공)
- 2차 verify: 통과 (`npm run verify:popup-ui` 실행 구조와 기존 UI interaction checklist를 동기화하고, production 외부 서버 재사용 경로를 공식 검증 흐름으로 고정함)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- popup interaction Playwright는 production 서버 재사용 흐름을 기준으로 정식화한다.
- 구현 근거: `frontend/frontend/scripts/run-marketplace-popup-interactions.ps1` 추가, `package.json`에 `test:popup-ui-interactions`와 `verify:popup-ui` 추가. `verify:popup-ui`는 `npm run verify` 뒤에 production build/start 기반 Playwright popup interaction 검증을 이어서 실행한다.
