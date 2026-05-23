# Admin Dashboard ad-orders richer 복원 체크리스트

## 검증 기준

- 실제 코드와 브라우저 동작으로 확인된 항목만 `[x]` 처리
- 현재 root에서 이미 연결된 데이터만 사용해 경량판보다 체감 가능한 정보량 증가가 있어야 통과 처리
- 수정 후 최소 2회 브라우저 검증 근거가 있어야 닫는다

## 1. summary-only 경량판 해소

- [x] `frontend/frontend/components/admin/admin-ad-orders-section.tsx` 가 단순 총계/기본 테이블만 표시하는 경량 상태를 벗어나 summary + ratio/settlement 정보까지 표시한다.
  - 근거: `frontend/frontend/components/admin/admin-ad-orders-section.tsx` 에 `상태 비율`, `엔진 비율`, `품질 비율`, `일별 정산 차트`, `월별 정산 차트` 블록 추가
- [x] dedicated_engine 주문의 작업 준비 상태를 컷 생산 단계 기준으로 읽을 수 있게 복구한다.
  - 근거: `frontend/frontend/components/admin/admin-ad-orders-section.tsx` 에 `buildProductionStageSummary()` 추가 및 `4D 상태` 컬럼에서 현재 단계/완료 수/승인 요약 표시

## 2. richer table composition 복구

- [x] 주문 테이블이 주문명/엔진/상태/진행률만이 아니라 4D 상태와 정산/스토리보드 힌트를 함께 보여준다.
  - 근거: 2차 브라우저 검증 snippet 에 `ID 사용자 주문명 엔진 4D 상태 품질 상태 진행률 스토리보드 생성시각` 헤더 확인
- [x] 주문 데이터가 비어 있지 않을 때 관리자 입장에서 체감 가능한 추가 맥락이 실제로 보인다.
  - 근거: 2차 브라우저 검증 snippet 에 dedicated 주문의 `4D dedicated`, `입력 보강 필요`, `01 시나리오`, `0/6 완료`, `승인 0/0 · 상품 0장 · 속도 보통` 표시 확인

## 3. 실검증

- [x] `/admin` 에서 `광고 영상 주문 모니터링` 창을 열었을 때 richer composition이 1차 브라우저 검증에서 확인된다.
  - 근거: 1차 브라우저 검증 snippet 에 `상태 비율`, `엔진 비율`, `품질 비율`, `일별 정산 차트`, `월별 정산 차트` 확인
- [x] `/admin` 에서 `광고 영상 주문 모니터링` 창을 다시 열었을 때 richer composition이 2차 브라우저 검증에서도 유지된다.
  - 근거: 2차 브라우저 검증 snippet 에 상기 summary/chart 항목과 테이블 헤더 `4D 상태`, `스토리보드` 확인

## 현재 판정

- [x] 문서 최종 판정을 완료 기준으로 승격한다.
  - 상태: 완료됨
  - 근거: summary-only 경량판 해소, richer table composition 복구, `/admin` 실브라우저 검증 2회 확인 항목이 모두 `[x]`로 닫혀 있다.
