# Marketplace Popup Telemetry Checklist

## Scope
- 대상:
  - `frontend/frontend/hooks/use-feature-orchestrator.ts`
  - `frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx`
  - 필요 시 telemetry 유틸 파일

## Checklist
- [x] popup telemetry 이벤트 구조를 정의한다.
- [x] popup open / close 이벤트를 기록한다.
- [x] popup submit 이벤트를 기록한다.
- [x] popup dwell time 이벤트를 기록한다.
- [x] featureId / popupMode / runId / elapsed 등 핵심 컨텍스트를 포함한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)
- 2차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- telemetry는 중복 발행을 최소화하고, 브라우저 환경에서 안전하게 동작해야 한다.
- 구현 근거: `frontend/frontend/lib/marketplace-popup-telemetry.ts` 추가. `use-feature-orchestrator.ts`에서 popup_open / popup_close / popup_submit / popup_dwell_time 이벤트를 featureId, popupMode, runId, elapsedSeconds, trigger, metadata와 함께 기록하도록 연결함.
