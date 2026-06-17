# 오케스트레이터 API 명명 · SSOT (A-4-4 · A-6)

> **갱신:** 2026-06-17  
> SSOT: `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART A-0 · Gap: `docs/checklists/orchestrator-ssot-visual-flow-gap-checklist.md`

## 제품 SSOT (확정)

**코어 엔진 하나** · **표면 두 곳** · **음성 우선**

| 표면 | 사용자 | UI | scope 차이 |
|------|--------|-----|------------|
| **직원 마켓 오케스트레이터** | marketplace 직원 | `/marketplace/orchestrator` | customer-orchestrate · tenant · stage-run |
| **관리자 오케스트레이터** | admin | `/admin/llm` | 전역 · output_dir · generator 제어 |

**동일해야 하는 것:** `TurnController` · STAGE · reasoner/planner/reviewer/coder/validator · LLM model routes · `llm_connected` · 세션/승인 계약.

**다를 수 있는 것:** auth · quota · project/output 경로 · Admin-only generator 패널.

**음성:** 두 표면 모두 **음성 지시 → STT → 동일 코어 `message`**. 수동 버튼 UX 지양.  
**예외 버튼 (직원 마켓만):** 자가진단 · 자가개선 · 자가확장 (VoIP/운영 트랙).

**VoIP ③:** 모바일 통역 통화 · Voice Relay — 코드 오케스트레이터 SSOT **외부**.

---

## 목표 코어 vs 레거시 (G-1 완료 후)

| | **SSOT 코어 (①)** | **레거시 ② (fallback)** |
|---|-------------------|---------------------------|
| **모듈** | `backend/orchestrator/autonomous/` | `backend/orchestrator/chat/` |
| **Admin HTTP** | `POST /api/llm/orchestrate/chat` → `run_autonomous_surface_chat(surface=admin)` when `manual_*` | lightweight · reverse_question → ② |
| **Marketplace HTTP** | `POST /api/marketplace/customer-orchestrate/chat` → `run_autonomous_surface_chat(surface=marketplace)` | legacy discuss fields via ② mapper (G-2) |
| **UI 표면** | Live Flow Rail + Decision Panel (`orchestrator-live-flow-rail.tsx`) | structured-response 중복 (G-5 축소 예정) |
| **내부 디버그** | `POST /api/llm/autonomous/chat` (raw TurnController · `X-Orchestrator-Api-Tier: debug-internal`) | Admin 숨김 패널 · HTTP regression |
| **프론트 SSOT** | `postAdminOrchestratorChat` → `/api/llm/orchestrate/chat` · `postCustomerOrchestratorChat` → customer path | `lib/orchestrator-chat-endpoints.ts` |

---

## 테스트 · 스크립트 (이름 주의)

| 파일 | 검증 대상 |
|------|-----------|
| `test_autonomous_orchestrator.py` | **코어 ①** |
| `test_autonomous_orchestrator_http.py` | **코어 ①** HTTP |
| `scripts/verify_autonomous_llm_gpu.py` | **코어 ①** GPU + Admin http_api |
| `test_orchestrator_dialogue_mode.py` | **②** (misleading name) |
| `verify_autonomous_chat.py` | **②** (misleading name) |
| `test_marketplace_customer_orchestrate_contract.py` | **마켓 ②** (SSOT 정렬 후 ① 기대로 갱신 필요) |

---

## VoIP Voice Relay (③)

- 문서: `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md`
- 체크리스트: PART B-7

---

## 코어 API 예 (SSOT)

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"FastAPI 블로그 API 만들어줘","mode":"manual_9step","manual_mode":true}' \
  https://metanova1004.com/api/llm/orchestrate/chat
```

Raw TurnController (debug/regression only):

```bash
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"FastAPI 블로그 API 만들어줘","mode":"semi_auto"}' \
  https://metanova1004.com/api/llm/autonomous/chat
```

환경: `AUTONOMOUS_MAX_STAGES_PER_TURN` (기본 11) · `AUTONOMOUS_SESSION_DIR` · `OLLAMA_BASE` · `LLM_RESOLVE_LIVE_MODELS`
