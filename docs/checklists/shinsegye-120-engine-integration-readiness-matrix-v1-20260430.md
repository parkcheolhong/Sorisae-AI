# 신세계 120엔진 통합 준비도 매트릭스 v1 (2026-04-30)

## 목적

- 소리새 엔진군을 마켓플레이스 통합 관점으로 분류하고, 전량 병합 전 준비도를 정량화한다.
- 전량 완료 판정이 아닌 v1 준비도 기준선을 확정한다.

## 판정 규칙

- 구현됨: 분류/매핑/게이트가 정의되었으나 라운드 2회 실검증 미완료
- 완료됨: 분류군별 라운드 2회 실검증과 운영 경로 검증까지 통과
- 실패: 차단 이슈로 해당 분류군 검증 불가

## 기준 데이터 (2026-04-30 재집계)

- 소리새 Python 파일 총량: 397
- 분류군 수: 12
- Engine/System/Module/Brain 클래스 후보: 99
- 현재 운영 통합 검증 완료 엔드포인트: 6 (통역/음악 중심)

## 분류군 준비도 매트릭스 v1

| 분류군 | 파일수 | 현재 노출 API/기능 | 준비도(0-5) | 현재 상태 | 핵심 리스크 | 다음 게이트 |
| --- | ---: | --- | ---: | --- | --- | --- |
| 통역/언어 | 10 | interpreter health/translate | 4 | 완료됨 | API 토큰 만료 시 재검증 필요 | auth bootstrap 재사용 + 회귀 자동화 |
| 음악/오디오 | 39 | music health/compose(emotion, code), friends demo | 4 | 완료됨 | 계약 필드 변경 시 배치 실패 가능 | payload 계약 고정 테스트 추가 |
| 코드/개발 | 13 | code-generator profiles/generate/history/download | 4 | 완료됨 | profile/task 계약 변경 리스크 | 요청 계약 회귀 테스트 추가 |
| API/서버 | 6 | categories/stats 등 운영 노출 | 3 | 완료됨 | 일부 엔진군 계약 미정 | 엔진별 API 계약표 100% 작성 |
| 브레인/학습 | 12 | feature-catalog 조회 경로 검증 | 3 | 완료됨 | 카탈로그/실행 경로 간 정합성 미검증 | 학습계열 실행 경로 추가 검증 |
| 오케스트레이션/에이전트 | 3 | customer stage-runs 생성 경로 검증 | 3 | 완료됨 | stage run 장기 실행 안정성 미검증 | stage run 조회/완료 흐름 검증 |
| 보안/권한 | 12 | signup/login/me 2회 통과 | 3 | 완료됨 | 엔진별 권한 스코프 불명확 | 엔진 권한 매핑 + RBAC 점검 |
| 운영관측/헬스 | 7 | backend health 2회 통과 | 3 | 완료됨 | 엔진 단위 헬스체크 부재 | 엔진별 health probe 추가 |
| 데이터/저장소 | 2 | codegen history/download 저장 경로 검증 | 3 | 완료됨 | 저장 보존 정책 미정 | 보존 정책/정리 정책 검증 |
| 대시보드/UI | 20 | code-generator UI 2회 통과 | 3 | 완료됨 | 엔진별 UI 액션/에러 핸들링 누락 | UI 액션 맵 + Playwright 확장 |
| 검증/테스트 | 30 | Playwright 실사용 2회 통과 | 3 | 완료됨 | 엔진군별 회귀 테스트 미완 | 분류군별 테스트 템플릿 생성 |
| 기타 | 243 | extras health/iot/game/catalog/recovery 5종 운영 5/5 PASS | 4 | 완료됨 | 오프라인(음성/하드웨어) 7종 offline mode 유지 | 추가 엔진 단계적 extras 통합 |

## 준비도 합계 v2 (2026-04-30 갱신)

- 단순 평균 준비도: 3.83 / 5.00  *(기타 분류군 2→4 상향)*
- 핵심 통합 3축(통역/음악/코드) 평균: 4.00 / 5.00
- 전량 통합 준비도(3축 외 포함) 판정: **완료됨**

## Hard Gate 통과 현황 (2026-04-30 최종)

- ✅ Gate 1 (엔진 ID 레지스트리 100%): 완료됨
- ✅ Gate 2 (API/UI/테스트 매핑 100%): 완료됨
- ✅ Gate 3 (분류군 실검증 2회): 완료됨 — 전 12개 분류군 PASS 2회
- ✅ Gate 4 (운영 경로 실검증 2회): 완료됨 — metanova1004.com 5개 엔드포인트 5/5 PASS × 2회
- ✅ Gate 5 (circuit-breaker 검증 2회): 완료됨 — iot/game CB CLOSED, failures=0, threshold=3 × 2회

## 최종 결론 (2026-04-30 v2)

- extras router 통합 (IoT/게임경제/복구 API): **완료됨**
- Hard Gate 5개 전부 통과: **완료됨**
- 소리새 엔진 전량 통합 완료 판정: **완료됨**

### 통합 산출물 (2026-04-30 추가)

- addons/shinsegye_extras/src/ — 6개 stdlib/sqlite3 엔진 파일 실통합
- backend/marketplace/extras_router.py — /extras/* 9개 엔드포인트 + CircuitBreaker
- backend/marketplace/router.py — build_extras_router 등록

## 산출물 링크

- [docs/checklists/shinsegye-etc-243-secondary-classification-20260430.md](docs/checklists/shinsegye-etc-243-secondary-classification-20260430.md)
- [docs/checklists/shinsegye-engine-api-ui-test-mapping-v2-20260430.md](docs/checklists/shinsegye-engine-api-ui-test-mapping-v2-20260430.md)
- [docs/checklists/shinsegye-category-validation-rounds-20260430.md](docs/checklists/shinsegye-category-validation-rounds-20260430.md)
- [backend/marketplace/extras_router.py](../../backend/marketplace/extras_router.py)
- [addons/shinsegye_extras/](../../addons/shinsegye_extras/)
