# Call Orchestrator (#3) — 라이프사이클·정책 레이어

로드맵([`WORLDLINCO_V2_ROADMAP.md`](../../../docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md)) #3.
기존 VoIP hot path(`nadotongryoksa_voip_router`)를 **변경하지 않고**, 통화의
**라이프사이클 상태 전이 + admission 정책 + 감사**를 상위에서 관찰/기록하는 얇은 래퍼.

> Session Core(#2)와 동일한 Strangler Fig 원칙. `COMM_V2_CALL_ORCHESTRATOR` env opt-in,
> 기본 **off → 완전 no-op**. integration 훅은 **절대 throw 하지 않는다**.

## 구성
| 파일 | 역할 |
|------|------|
| `config.py` | 피처 플래그 + 설정(`CallOrchestratorConfig`) |
| `models.py` | `CallStateV2`(정규 상태) · `LifecycleEvent` · `CallLifecycle` · `PolicyDecision` |
| `store.py` | `LifecycleStore` 추상 + 인메모리(TTL/LRU). Redis 승격 대비(#4) |
| `policy.py` | admission 순수 함수(동시 active 상한, 관찰/강제 모드) |
| `manager.py` | `CallOrchestrator` 진입점(flag off면 no-op) |
| `integration.py` | hot path 한 줄 훅(best-effort, 완전 가드) |

## 상태 모델
라우터의 자유 문자열 status를 정규 집합으로 매핑:
`INITIATING → RINGING/CONNECTING → ACTIVE → ENDING → ENDED/MISSED/FAILED`.
허용 전이는 느슨하게 검증하되 **위반은 거부가 아니라 `out_of_order` 플래그로만 기록**(관찰 우선).

## 오케스트레이터 얇은 연결(hot path 훅)
`nadotongryoksa_voip_router.py`:
- **call_init** 직후: `orchestrator_integration.on_call_init(call_id, session_id=session_id or call_id, route=..., initial_status=..., admission=evaluate_admission())`
- **call_end** 시: `orchestrator_integration.on_call_end(call_id, status="ended", reason=...)`

세션 키는 Session Core와 동일(`request.session_id or call_id`)하게 정렬된다.

## 환경변수
| 변수 | 기본 | 설명 |
|------|------|------|
| `COMM_V2_CALL_ORCHESTRATOR` | `false` | 마스터 스위치 |
| `COMM_V2_CALL_ORCH_TTL_SEC` | `3600` | 종료 라이프사이클 보존(초) |
| `COMM_V2_CALL_ORCH_MAX_CALLS` | `10000` | 추적 통화 수 상한 |
| `COMM_V2_CALL_ORCH_MAX_EVENTS` | `64` | 통화당 이벤트 보존 개수 |
| `COMM_V2_CALL_ORCH_MAX_CONCURRENT` | `0` | 동시 active 상한(0=무제한) |
| `COMM_V2_CALL_ORCH_ENFORCE` | `false` | true면 상한 초과 시 admission 거부, false면 관찰만 |

## 안전성
- flag off면 라우터 훅은 즉시 반환(상태 추적조차 안 함).
- 모든 integration 함수는 예외를 흡수 → hot path 무영향.
- admission은 기본 **관찰 모드**(`enforce=false`): 상한 초과해도 allow하고 사유만 기록.
  운영 검증 후 `COMM_V2_CALL_ORCH_ENFORCE=true`로 강제 전환.

## 테스트
[`backend/tests/test_communication_call_orchestrator.py`](../../tests/test_communication_call_orchestrator.py) — 12 케이스
(no-op·전이 기록·out-of-order 플래그·상태 매핑·admission 관찰/강제·active 카운트·이벤트 캡·TTL purge·integration throw 금지).
