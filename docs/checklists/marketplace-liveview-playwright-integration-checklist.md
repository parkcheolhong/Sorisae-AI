# Marketplace Liveview Playwright Integration Checklist

## Scope
- 대상:
  - `frontend/frontend/package.json`
  - `frontend/frontend/tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts`
  - 관련 Playwright config / 실행 스크립트

## Checklist
- [x] marketplace liveview Playwright를 공식 검증 흐름에 편입할 구조를 확정한다.
- [x] package 스크립트에 정식 liveview 검증 경로를 추가한다.
- [x] production 외부 서버 재사용 전략을 liveview 검증에도 고정한다.
- [x] 편입된 liveview 검증 경로를 실제 실행해 통과를 확인한다.
- [x] 관련 체크리스트와 문서를 동기화한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:marketplace-liveview` - build/verify/test:marketplace-liveview-sheet/Playwright liveview sheet 테스트 성공)
- 2차 verify: 통과 (`marketplace-liveview-ai-sheet-launcher.playwright.spec.ts` 기대값을 현재 UI의 `Workbook Package` 기준으로 맞춘 뒤 `npm run verify:marketplace-liveview` 재통과 확인)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- liveview Playwright도 popup interaction과 같은 production 외부 서버 재사용 흐름으로 정식화한다.
- 구현 근거: `frontend/frontend/scripts/run-marketplace-liveview-sheet.ps1` 추가, `package.json`에 `test:marketplace-liveview-sheet`와 `verify:marketplace-liveview` 추가. 스프레드시트 특화 UI에 맞춰 `marketplace-liveview-ai-sheet-launcher.playwright.spec.ts`의 기대값을 `Workbook Package`로 갱신하고, production build/start 서버 재사용 경로에서 검증을 통과시켰다.
