# Marketplace Popup Section Tests Checklist

## Scope
- 대상 섹션:
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-live-view-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-input-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-state-section.tsx`
  - `frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx`

## Checklist
- [x] 테스트 대상 섹션과 실행 방식을 확정한다.
- [x] 라이브뷰 섹션 핵심 렌더링 계약 테스트를 추가한다.
- [x] 입력 섹션 핵심 렌더링 계약 테스트를 추가한다.
- [x] 상태 섹션 핵심 렌더링 계약 테스트를 추가한다.
- [x] 출력 섹션 핵심 렌더링 계약 테스트를 추가한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)
- 2차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer/test:popup-sections 모두 성공)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- 테스트 러너 제약이 있으면 실행 가능한 경량 계약 테스트 방식으로 우회한다.
- 구현 근거: `frontend/frontend/lib/marketplace-popup-sections.contract.test.js` 추가. 라이브뷰/입력/상태/출력 섹션의 핵심 data-testid, 접근성 라벨, 기능별 결과 분기 문자열을 검증하도록 구성함.
