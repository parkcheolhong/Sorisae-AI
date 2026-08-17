# Marketplace Popup Accessibility Checklist

## Scope
- 대상: `frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx`
- 관련 섹션 모듈:
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-live-view-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-input-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-state-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx`

## Checklist
- [x] 팝업 루트에 `role="dialog"`, `aria-modal="true"`, 제목/설명 연결을 적용한다.
- [x] 팝업이 열릴 때 초기 포커스를 안전한 대상에 이동시킨다.
- [x] 팝업 내부에서 Tab / Shift+Tab 포커스 순환을 보장한다.
- [x] Escape 키로 닫기 동작을 지원한다.
- [x] 팝업이 열린 동안 배경 스크롤을 잠그고, 닫힐 때 복구한다.
- [x] 닫기 버튼과 주요 입력 요소에 명확한 접근성 레이블을 유지한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer 모두 성공)
- 2차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer 모두 성공)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- 검증 2회가 모두 통과하기 전에는 완료로 판정하지 않는다.
- 구현 근거: `feature-orchestrator-popup.tsx`에 dialog role, aria-labelledby/aria-describedby, 초기 포커스, 포커스 트랩, Escape 닫기, body scroll lock, 닫기 버튼 aria-label 반영.
