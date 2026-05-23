# Marketplace Popup Mobile Responsive Checklist

## Scope
- 대상:
  - `frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-live-view-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-input-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-state-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx`

## Checklist
- [x] 팝업 루트 여백/최대높이/스크롤을 모바일 우선으로 조정한다.
- [x] 헤더와 액션 버튼 배치를 모바일에서 더 읽기 쉽게 조정한다.
- [x] 라이브뷰/입력/상태/출력 카드 레이아웃을 모바일에서 세로 흐름 중심으로 조정한다.
- [x] 버튼, 표, 이미지 높이, 카드 간격을 모바일에서 더 안정적으로 보정한다.
- [x] 기능별 결과 패널이 모바일에서 깨지지 않도록 유지한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)
- 2차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- 데스크톱 배치를 해치지 않는 범위에서 모바일 전용 클래스 보정을 우선한다.
- 구현 근거: `feature-orchestrator-popup.tsx`에서 모바일 여백/스크롤/헤더/닫기 버튼을 스택 구조로 보정했고, `feature-popup-live-view-section.tsx`, `feature-popup-input-section.tsx`, `feature-popup-output-section.tsx`에서 카드, 이미지 높이, 다운로드/품질 헤더, 액션 버튼을 모바일 우선 레이아웃으로 조정했다.
