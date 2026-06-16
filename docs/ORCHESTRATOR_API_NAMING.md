# 오케스트레이터 API 명명 · SSOT (A-4-4 · A-6)

> **갱신:** 2026-06-16  
> SSOT: `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART A-0

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

## 목표 코어 vs 레거시 (통합 중)

| | **SSOT 코어 (목표)** | **레거시 ② (흡수 대상)** |
|---|----------------------|---------------------------|
| **모듈** | `backend/orchestrator/autonomous/` | `backend/orchestrator/chat/` · `backend/llm/orchestrator.py` |
| **API** | `POST /api/llm/autonomous/chat` | `POST /api/llm/orchestrate/chat` |
| **마켓 today** | *(미연결)* | `POST /api/marketplace/customer-orchestrate/chat` → ② |
| **관리자 today** | 패널 숨김 · A-3-2 검증 | `/admin/llm` 기본 UI → ② + `voice/orchestrate` |

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
  -d '{"message":"FastAPI 블로그 API 만들어줘","mode":"semi_auto"}' \
  https://metanova1004.com/api/llm/autonomous/chat
```

환경: `AUTONOMOUS_MAX_STAGES_PER_TURN` (기본 11) · `AUTONOMOUS_SESSION_DIR` · `OLLAMA_BASE` · `LLM_RESOLVE_LIVE_MODELS`
