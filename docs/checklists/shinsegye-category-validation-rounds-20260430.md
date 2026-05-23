# 신세계 분류군별 2회 실검증 배치 결과 (2026-04-30)

## 실행 범위

- 라운드 1: `docs/checklists/generated/run_category_validation.ps1 -Round round1`
- 라운드 2: `docs/checklists/generated/run_category_validation.ps1 -Round round2`
- 개선 라운드 1: `docs/checklists/generated/run_category_validation.ps1 -Round round1_fix`
- 개선 라운드 2: `docs/checklists/generated/run_category_validation.ps1 -Round round2_fix`
- 개선 라운드 3-1: `docs/checklists/generated/run_category_validation.ps1 -Round round3_fix1`
- 개선 라운드 3-2: `docs/checklists/generated/run_category_validation.ps1 -Round round3_fix2`
- 개선 라운드 4-1: `docs/checklists/generated/run_category_validation.ps1 -Round round4_fix1`
- 개선 라운드 4-2: `docs/checklists/generated/run_category_validation.ps1 -Round round4_fix2`
- 검증/테스트 분류군 추가 근거:
  - `npm --prefix frontend/frontend run e2e:marketplace:shinsegye-safe` (2회)

## 라운드 결과 요약

| 분류군 | round1 | round2 | round1_fix | round2_fix | round3_fix1 | round3_fix2 | 최종 상태 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 보안/권한 | PASS | PASS | PASS | PASS | PASS | PASS | 완료됨 |
| 운영관측/헬스 | PASS | PASS | PASS | PASS | PASS | PASS | 완료됨 |
| API/서버 | PASS | PASS | PASS | PASS | PASS | PASS | 완료됨 |
| 통역/언어 | FAIL | FAIL | PASS | PASS | PASS | PASS | 완료됨 |
| 음악/오디오 | FAIL | FAIL | PASS | PASS | PASS | PASS | 완료됨 |
| 코드/개발 | FAIL | FAIL | PASS | PASS | PASS | PASS | 완료됨 |
| 브레인/학습 | BLOCKED | BLOCKED | PASS | PASS | PASS | PASS | 완료됨 |
| 오케스트레이션/에이전트 | BLOCKED | BLOCKED | PASS | PASS | PASS | PASS | 완료됨 |
| 데이터/저장소 | BLOCKED | BLOCKED | PASS | PASS | PASS | PASS | 완료됨 |
| 대시보드/UI | PASS | PASS | PASS | PASS | PASS | PASS | 완료됨 |
| 검증/테스트 | PASS | PASS | PASS | PASS | PASS | PASS | 완료됨 |
| 기타 | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | PASS | 완료됨 |

## 실패/차단 근거

- 통역/언어 401 원인: 검증 스크립트에서 인증 헤더 누락
- 음악/오디오 401 원인: 검증 스크립트에서 인증 헤더 누락
- 코드/개발 400 원인: `code-generator/generate` 요청 계약 불일치(`title/prompt/stack` 사용)
- 브레인/학습 BLOCKED 개선: `GET /api/marketplace/feature-catalog` 실검증 경로 추가 후 PASS
- 오케스트레이션/에이전트 BLOCKED 개선: `POST /api/marketplace/customer-orchestrate/stage-runs` 실검증 경로 추가 후 PASS
- 데이터/저장소 BLOCKED 개선: `codegen history/download` 저장소 경로 검증 추가 후 PASS
- 기타 BLOCKED 개선: `GET /api/marketplace/campaign-orchestrate/strategies` 실검증 경로 추가 후 PASS

## 즉시 개선 조치

- 통역/음악 체크에 `Authorization: Bearer <token>` 적용
- 음악 compose 요청 본문을 실제 계약(`emotion`, `intensity`, `theme`)으로 조정
- 코드생성 요청 본문을 실제 계약(`project_name`, `task`, `profile`)으로 조정
- BLOCKED 분류군 3개에 대체 실검증 라우트 연결
- 기타 분류군에 campaign orchestration read-only probe를 추가해 BLOCKED 해소

## 근거 파일

- `docs/checklists/generated/category_validation_round1.json`
- `docs/checklists/generated/category_validation_round2.json`
- `docs/checklists/generated/category_validation_round1.summary.json`
- `docs/checklists/generated/category_validation_round2.summary.json`
- `docs/checklists/generated/category_validation_round1_fix.json`
- `docs/checklists/generated/category_validation_round2_fix.json`
- `docs/checklists/generated/category_validation_round1_fix.summary.json`
- `docs/checklists/generated/category_validation_round2_fix.summary.json`
- `docs/checklists/generated/category_validation_round3_fix1.json`
- `docs/checklists/generated/category_validation_round3_fix2.json`
- `docs/checklists/generated/category_validation_round3_fix1.summary.json`
- `docs/checklists/generated/category_validation_round3_fix2.summary.json`
- `docs/checklists/generated/category_validation_round4_fix1.json`
- `docs/checklists/generated/category_validation_round4_fix2.json`
- `docs/checklists/generated/category_validation_round4_fix1.summary.json`
- `docs/checklists/generated/category_validation_round4_fix2.summary.json`
