# Marketplace Playwright CI Integration Checklist

## Scope
- 대상:
  - `frontend/frontend/package.json`
  - `frontend/frontend/scripts/run-marketplace-popup-interactions.ps1`
  - `frontend/frontend/scripts/run-marketplace-liveview-sheet.ps1`
  - 관련 Playwright 검증 체크리스트 문서

## Checklist
- [x] popup UI / liveview Playwright를 CI에서도 같은 흐름으로 실행할 구조를 확정한다.
- [x] package 스크립트에 CI용 상위 검증 경로를 추가한다.
- [x] production build/start 기반 실행 흐름을 CI 기준으로 정리한다.
- [x] CI용 검증 경로를 실제 실행해 통과를 확인한다.
- [x] 관련 체크리스트와 문서를 동기화한다.

## Verification Log
- 1차 verify: 통과 (`npm run ci:marketplace` - verify:popup-ui + liveview sheet production-backed Playwright 경로 성공)
- 2차 verify: 통과 (`verify:marketplace-playwright`/`ci:marketplace` 구조를 package 스크립트에 고정하고 관련 체크리스트 문서와 동기화함)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- CI에서는 popup UI와 liveview 검증이 동일한 상위 명령 체계로 호출되도록 정리한다.
- 구현 근거: `package.json`에 `verify:marketplace-playwright`와 `ci:marketplace`를 추가해 popup UI와 liveview sheet Playwright를 하나의 상위 검증 경로로 묶었다. 기존 `run-marketplace-popup-interactions.ps1`, `run-marketplace-liveview-sheet.ps1`를 재사용해 production build/start 기반 실행 흐름을 유지한다.
