# Marketplace Popup Output Specialization Checklist

## Scope
- 대상: `frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx`
- 연계: `frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx`

## Checklist
- [x] AI 이미지 결과 카드를 composition/quality/warnings 중심으로 강화한다.
- [x] AI 음악 결과 카드를 트랙 구조/무드/패키지 중심으로 강화한다.
- [x] AI 문서 결과 카드를 outline/핵심 포인트/패키지 중심으로 강화한다.
- [x] AI 영상 결과 카드를 storyboard/scene/CTA 중심으로 강화한다.
- [x] AI 엑셀 시트 결과 카드는 workbook/download 가독성을 유지·보강한다.
- [x] 기능별 데이터가 비어 있을 때 fallback 결과 패널이 깨지지 않도록 유지한다.
- [x] 자동 검증 `npm run verify:frontend`를 2회 수행해 모두 통과한다.

## Verification Log
- 1차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer 모두 성공)
- 2차 verify: 통과 (`npm run verify:frontend` - build/test/test:normalizer 모두 성공)

## Notes
- 체크는 실제 구현 및 검증 근거가 확인된 뒤에만 반영한다.
- 검증 2회가 모두 통과하기 전에는 완료로 판정하지 않는다.
- 구현 근거: `feature-popup-output-section.tsx`에서 outputKind 기반 결과 카드 분기 추가. 이미지는 composition/keywords, 음악은 track structure, 문서는 outline/sections, 영상은 scene cards/CTA, 엑셀은 workbook/download 패널 유지로 특화함.
