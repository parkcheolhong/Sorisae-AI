# Autonomous TurnController 11단계 — 실행·구현 상태 보고서

> **작성:** 2026-06-16  
> **SSOT 엔진:** `backend/orchestrator/autonomous/turn_controller.py`  
> **프로브 스크립트:** `scripts/run_11stage_orchestrator_probe.py`

---

## 1. 실행 검증 요약 (4-probe)

| Probe | 명령 | 결과 | session_id | 리포트 |
|-------|------|------|------------|--------|
| **stub** | `--mode stub` | **11/11** · `execution_state=completed` · errors=0 | `064cf9f886464b72` | `evidence/orchestrator-11stage-probe-20260616-125507/report.json` |
| **live** | `--mode live` + `OLLAMA_BASE=http://127.0.0.1:8008/v1` | **11/11** · vLLM 32B AWQ · errors=0 | `b5e16dfa41f94638` | `evidence/orchestrator-11stage-probe-20260616-125528/report.json` |
| **http (marketplace)** | `--mode http --marketplace` | **11/11** · stage_run sync OK · errors=0 | `73995f7646e94feb` | `evidence/orchestrator-11stage-probe-20260616-130503/report.json` |
| **http (admin)** | `--mode http --admin` | **11/11** · `/admin/llm` · errors=0 | `91c715c20e3c4bed` | `evidence/orchestrator-11stage-probe-20260616-131740/report.json` |

**태스크:** `FastAPI 헬스체크 API 만들어줘`  
**시퀀스:** register-task → 설계해줘 → 진행해 → 2~10단계 진행해줘 (+ 4단계 후 discuss-4 협업 Q&A)

---

## 2. 핵심 수정 (4/11 → 11/11)

| 이슈 | 수정 파일 | 내용 |
|------|-----------|------|
| 단계 패치 스코프 소실 → 107파일 폭주 | `stage_coder_scope.py`, `coder.py` | `get_stage_patch_scope()` — 기존 파일 여부와 무관하게 단계별 파일 목록 유지 |
| patch-only 구조 검증 실패 | `validator.py` | 프로젝트에 `main.py`/`app.py` 존재 시 구조 검증 통과 |
| LLM 미연결 시 agent error | `base.py` | `_call_llm_tracked()` stub 폴백 |
| 4.5단계 reviewer error 시 중단 | `turn_controller.py` | reviewer error → 코더/검증 계속 진행 |
| HTTP 프로브 미완료 오탐 | `run_11stage_orchestrator_probe.py` | `stages_completed < 11` 시 exit 1 |

---

## 3. 단계별 패치 파일 수 (stub/live 검증)

| 단계 | STAGE ID | 파일 수 (대표) |
|------|----------|----------------|
| 1 | STAGE-01 | 9 |
| 2 | STAGE-02 | 5 |
| 3 | STAGE-03 | 5 |
| 4 | STAGE-04 | 3 |
| 4.5 | STAGE-045 | 6 (reviewer → coder → validator) |
| 5~10 | STAGE-05~10 | 2~3 each |

---

## 4. HTTP Marketplace stage_run 동기화

- API: `POST /api/marketplace/customer-orchestrate/chat`
- stage_run: `stage_run_vBt3RUb8sBg1Mz5WL1LnrEGd`
- 모든 execute 턴 `stage_run_synced: true`
- ARCH-001 → ARCH-010 passed_stages 순차 증가 확인

---

## 5. Admin HTTP 프로브

```powershell
$env:PROBE_LOGIN_EMAIL="admin@example.com"   # is_admin 계정
$env:PROBE_LOGIN_PASSWORD="..."
python scripts/run_11stage_orchestrator_probe.py --mode http --admin
```

- UI surface: `/admin/llm`
- API: `POST /api/llm/orchestrate/chat` (`surface_adapter.run_autonomous_surface_chat`, surface=`admin`)
- stage_run 동기화 없음 (admin 전용 diagnostics: `orchestrator_core`, `autonomous_intent`, `stages_completed`)

---

## 6. 재현 명령

```powershell
# stub (~5s)
python scripts/run_11stage_orchestrator_probe.py --mode stub

# live (vLLM @ :8008)
$env:OLLAMA_BASE="http://127.0.0.1:8008/v1"
python scripts/run_11stage_orchestrator_probe.py --mode live

# marketplace HTTP
$env:PROBE_LOGIN_EMAIL="..."
$env:PROBE_LOGIN_PASSWORD="..."
python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace

# admin HTTP
python scripts/run_11stage_orchestrator_probe.py --mode http --admin
```

---

## 7. 잔여 / 후속

- [x] Admin HTTP probe **11/11** (`131740/report.json`, session `91c715c20e3c4bed`)
- [ ] `pytest-asyncio` 설치 후 async 단위 테스트 CI green
- [ ] discuss-4 중 stage_run 카드 ARCH-005 선행 표시 — UX 정합 (marketplace only, 기능 차단 아님)
