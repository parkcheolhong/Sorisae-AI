# Capability 상태/성공률 스냅샷 (2026-05-03)

기준 API:
- GET /api/admin/orchestrator/capabilities/summary (live)

수집 시각:
- collected_at: 2026-05-03T03:35:56
- summary_generated_at: 2026-05-02T18:35:55Z

## 1) 코딩봇 + 오케스트레이터 상태 요약

| 항목 | 값 |
|---|---:|
| capability_total | 7 |
| active | 7 |
| warning | 0 |
| error | 0 |
| attention_required | 0 |
| completion_gate_pass_count | 7 |
| project_creation_success_rate_percent | 100.00% |
| self_run_status(not_applicable) | 7 |

## 2) 그룹별 상태

| 그룹 | state | active | warning | error | summary |
|---|---|---:|---:|---:|---|
| diagnosis-control | active | 3 | 0 | 0 | 정상 3 · 대기 0 · 주의 0 · 오류 0 |
| improvement-control | active | 2 | 0 | 0 | 정상 2 · 대기 0 · 주의 0 · 오류 0 |
| expansion-control | active | 2 | 0 | 0 | 정상 2 · 대기 0 · 주의 0 · 오류 0 |

## 3) capability 상세표 (프로젝트 생성 성공률 기준 관측값)

성공률 계산식:
- success_rate = completion_gate_ok == true 인 capability 수 / capability_total

| capability | state | completion_gate_ok | self_run_status | metric | detail |
|---|---|---|---|---|---|
| project-scanner | active | true | not_applicable | 핵심파일 6개 · 실행범위 프로젝트 하위 경로 | 최신 self-run 상태=pending_approval, 범위=프로젝트 하위 경로, 오류 4건 |
| dependency-graph | active | true | not_applicable | 연결점 4개 | 서비스 13개 |
| security-guard | active | true | not_applicable | Python 보안 오류 0건 · 경고 0건 | 관리자 인증/SECRET_KEY/런타임 설정 + python_security_validation |
| self-healing-engine | active | true | not_applicable | 복구안 3건 | 회복 점수 64 · 최신상태 pending_approval |
| code-generator | active | true | not_applicable | 생성로그 64개 / 최소 27개 | 폴더 16개 / 최소 3개 · Python 오류 0건 |
| admin-command-interface | active | true | not_applicable | 명령 5개 | 실행/설정/진단 경로 정리 |
| ollama-model-controller | active | true | not_applicable | 모델 1개 | 프로필 2개 |

## 4) 해석

- 수치상 생성 성공률은 100%로 관측됨(7/7).
- `localhost`/legacy 서비스 계약 표기가 남아 있던 6개 문서를 동기화한 뒤 `documentation_sync.stale_count=0` 으로 수렴했고, 그룹 warning은 2 -> 0으로 감소했다.
- detail 문자열의 `pending_approval` 표기는 기록 컨텍스트를 설명하는 메타 정보이며, 현재 capability state 자체는 모두 `active`다.
