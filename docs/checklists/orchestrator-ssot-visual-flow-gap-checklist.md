# 오케스트레이터 SSOT · 실시간 시각 흐름 — 구현 Gap 체크리스트

> **작성:** 2026-06-17  
> **목표:** 10단계 시각 패널 + 4단계 이후 협업 Q&A + 기술스택 제안 + 설계·체크리스트 + 음성/텍스트 자율 멀티 대화를 **단일 SSOT 코어**로 통합하고, **실시간 흐름이 화면에서 분명히 보이도록** 한다.  
> **SSOT 문서:** `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART A · `docs/ORCHESTRATOR_API_NAMING.md` · `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.10  
> **표시:** `[ ]` 미착수 · `[~]` 부분 구현/검증중 · `[x]` 완료  
> **상태 정책:** Evidence(테스트·스크린·프로브 JSON) 없이 `[x]` 금지

---

## 0. 제품 UX 원칙 (이번 Gap 클로저의 고정 목표)

사용자가 **지금 어디에 있는지**, **다음에 무엇이 일어나는지**, **개선·수정할지 말지**를 **한 화면에서** 이해할 수 있어야 한다.

| 원칙 | 사용자에게 보여야 하는 것 |
|------|---------------------------|
| **실시간 흐름 가시화** | 현재 단계(ARCH/STAGE) · 실행 중 에이전트 · intent(design/execute/discuss) · 승인 대기 |
| **개선 내용 안내** | 기술 제안 · 체크리스트 항목 · diff/영향 파일 · “다음 액션” 카드 |
| **수정 여부 질문** | “이 제안을 반영할까요?” / “N단계로 진행할까요?” / “설계를 수정할까요?” — **예/아니오/수정 후 진행** |
| **답변 채널** | 텍스트 입력 · 음성 STT · 카드 버튼(승인/보류/수정) — **동일 TurnController message** 로 수렴 |
| **단일 코어** | 채팅·실행·stage_run 동기화가 **① TurnController** 기준 |

---

## PART G-0. 실시간 시각 흐름 패널 (신규 · P0)

> **Gap:** `OrchestratorStageCardPanel`은 단계 카드는 있으나, **턴 단위 live pipeline**(에이전트·intent·승인 게이트)이 마켓/관리자에서 **통일되게** 보이지 않음. Admin `LiveProgressSnapshot`은 legacy pipeline(`DESIGN→…→DONE`)과 11 STAGE SSOT가 **불일치**.

### G-0-1. 공통 Live Flow 컴포넌트

- [x] **(G-0-1-1)** `shared/orchestrator-live-flow-rail.tsx` 신규 — 11 STAGE(`STAGE-01`~`STAGE-10` + `045`) 가로/세로 레일
  - 상태: `pending` · `running` · `completed` · `awaiting_approval` · `discuss` · `failed`
  - 현재 턴 `autonomous_intent` · `stage_command` · `stage_number` 배지
- [x] **(G-0-1-2)** 에이전트 버스 타임라인 슬롯 — reasoner → planner → coder → reviewer → validator 순서 표시
  - 데이터: `diagnostics.agent_results[]` · `diagnostics.orchestrator_core`
- [x] **(G-0-1-3)** “지금 무슨 일이?” 한 줄 요약 (`stage_command_hint` + `next_action_suggestions` 병합)
- [x] **(G-0-1-4)** `data-testid="orchestrator-live-flow-rail"` — Playwright 계약
- [x] **(G-0-1-5)** Admin `/admin/llm` · Marketplace `/marketplace/orchestrator` 에 rail 마운트
- [x] **(G-0-1-6)** `lib/orchestrator-live-flow.ts` — diagnostics ↔ snapshot 빌더 · stage_run merge

**관련 파일:** `frontend/frontend/shared/orchestrator-stage-card-panel.tsx` · `backend/orchestrator/autonomous/surface_adapter.py` (`stage_command_hint`, diagnostics)

### G-0-2. 개선·수정 확인 UX (질문 → 답변)

- [x] **(G-0-2-1)** `OrchestratorDecisionPanel` / `OrchestratorDecisionCard` — 반영·저장·수정 버튼 (`orchestrator-decision-*`)
- [x] **(G-0-2-2)** 승인 게이트 CTA — **진행해** · **수정해** · **거절** (`orchestrator-approval-*`)
- [x] **(G-0-2-3)** Admin · Marketplace 마운트 + `sendChatMessage` / `sendStageChat` 연동
- [x] **(G-0-2-4)** 빈 상태 `orchestrator-decision-empty`
- [x] **(G-0-2-5)** discuss 모드 배너 — “4단계+ 협업 Q&A 중 · 코드 생성은 ‘N단계 진행해줘’로 시작” (`OrchestratorDiscussBanner` · live rail + StageCardPanel)
- [x] **(G-0-2-6)** `clarification_questions[]` 카드 (G-2 mapper 연동 후 · ① discuss → surface_adapter)

**관련 파일:** `shared/orchestrator-decision-card.tsx` · `lib/orchestrator-live-flow.ts`

### G-0-3. 실시간 갱신 (폴링 · SSE · WS)

- [x] **(G-0-3-1)** 채팅 응답 직후 live rail + stage_run 카드 **동시 갱신** (단일 `refreshStageRun` + diagnostics merge)
- [x] **(G-0-3-2)** 코드 실행 중 progress — `GET /api/llm/orchestrate/progress/{run_id}` 또는 autonomous session poll
  - Admin `ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY` 패턴을 **마켓에도** 동일 키/스키마로 확장 (`orchestrator_live_progress_v1`)
- [x] **(G-0-3-2b)** progress 스키마 확장 — `stage_number` · `substeps` · `active_substep` · `progress_logs` → Live Flow Rail 실시간 반영
- [x] **(G-0-3-3)** long-running substep 실시간 — **SSE + WebSocket** (`GET .../stream/{run_id}` · `WS .../progress/ws/{run_id}`) · poll 폴백 · `useOrchestratorLiveProgress`

**관련 파일:** `backend/orchestrator/autonomous/progress_stream.py` · `lib/use-orchestrator-live-progress.ts` · `lib/use-orchestrator-live-progress-stream.ts` · Admin/Market `OrchestratorFlowSection.tsx`

### G-0-4. 시각 흐름 검증

- [x] **(G-0-4-1)** Playwright — Admin rail · `Live Flow · 11 STAGE` · `1단계`/`10단계` · `core:`/`intent:`
- [x] **(G-0-4-2)** Playwright — Marketplace rail · `4.5단계` · Decision Panel shell
- [x] **(G-0-4-3)** Playwright 인프라 — `npm run e2e:orchestrator-live-flow-rail` · **5/5 passed** (2026-06-17)
- [x] **(G-0-4-4)** Playwright — discuss-4 ARCH-004 고정 (G-4 연동 후) · `npm run e2e:orchestrator-discuss4`
- [x] **(G-0-4-5)** 수동 스크린 — `evidence/orchestrator-visual-flow-YYYYMMDD/` (`npm run e2e:orchestrator-visual-evidence`)

---

## PART G-1. HTTP 채팅 → `run_autonomous_surface_chat` 연결 (P0)

> **Gap:** 문서 A-6-1은 완료로 표기되나, 현재 HTTP는 ② `chat_service.answer_orchestrator_chat` 직행. `run_autonomous_surface_chat`은 테스트에서만 호출됨.

### G-1-1. Admin `/api/llm/orchestrate/chat`

- [x] **(G-1-1-1)** `backend/llm/orchestrator.py` `answer_orchestrator_chat` — `manual_mode`/`mode` manual_* 일 때 `surface_adapter.run_autonomous_surface_chat(surface="admin")` 분기
- [x] **(G-1-1-2)** lightweight · reverse_question → ② fallback (`should_route_orchestrator_chat_to_autonomous`)
- [x] **(G-1-1-3)** 응답 `diagnostics.orchestrator_core === "autonomous_turn_controller"` — mapper + `test_live_flow_diagnostics_mapper.py`
- [x] **(G-1-1-4)** `frontend/lib/use-orchestrator-chat.ts` — diagnostics → `liveFlowSnapshot` → Admin rail
- [x] **(G-1-1-5)** `backend/tests/test_orchestrate_chat_autonomous_route.py` — routing 단위 테스트

**검증:** `python scripts/run_11stage_orchestrator_probe.py --mode http --admin` → 11/11 + `orchestrator_core` 확인

### G-1-2. Marketplace `/api/marketplace/customer-orchestrate/chat`

- [x] **(G-1-2-1)** `customer_orchestrate_router.py` — `should_route` → `run_autonomous_surface_chat(surface="marketplace", stage_run_id=run_id)`
- [x] **(G-1-2-2)** `synced_stage_run` diagnostics — `stage_run_sync.py` · `run_autonomous_surface_chat` stage_run_id 경로
- [x] **(G-1-2-3)** legacy 필드(`technology_recommendations` 등) — DecisionPanel + `buildDecisionItems` (① discuss mapper → admin/market `technologyRecommendations` 연동)
- [x] **(G-1-2-4)** marketplace surface 회귀 — `test_autonomous_surface_adapter.py` · `test_should_route_manual_10step_marketplace_mode`

### G-1-3. 문서·명명 정합

- [x] **(G-1-3-1)** `docs/ORCHESTRATOR_API_NAMING.md` — G-1 완료 반영 (마켓·Admin HTTP → ①)
- [x] **(G-1-3-2)** `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` — 2026-06-17 Live Flow · A-6-8 추가
- [x] **(G-1-3-3)** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.11 — Live Flow Rail · Playwright

---

## PART G-2. ② 협업·기술 제안 → ① `discuss` intent 흡수 (P1)

> **Gap:** `technology_recommendations` · `/ask` · `/search` · `/news` · `/revise`는 ② `chat_service`에만 풍부. ① `discuss`는 reasoner/planner 텍스트 위주.

### G-2-1. discuss intent 기능 이식

- [x] **(G-2-1-1)** `turn_controller.py` discuss 분기 — `build_discuss_advisory_payload()` · `autonomous/advisory.py`
- [x] **(G-2-1-2)** `/ask` · `/search` · `/news` · `/revise` · `/resume` — `parse_stage_command` 슬래시 discuss SSOT
- [x] **(G-2-1-3)** `OrchestratorChatResponse` mapper — discuss 턴에 `proposal_items` · `technology_recommendations` · `clarification_questions` 채움
- [x] **(G-2-1-4)** 4단계 미만 discuss 시도 → “4단계부터 협업 Q&A 가능” 안내 + live rail locked 표시

**관련 파일:** `backend/orchestrator/chat/chat_service.py` (L358, L936, L959) · `stage_commands.py`

### G-2-2. 웹 검색·뉴스 그라unding (선택)

- [x] **(G-2-2-1)** discuss + `/search` — 기존 web grounding을 ① context.extra로 전달
- [x] **(G-2-2-2)** evidence_highlights → G-0 DecisionCard “근거” 섹션

### G-2-3. 테스트

- [x] **(G-2-3-1)** `test_stage_commands.py` — discuss + slash `/ask` · command_rules mirror 회귀
- [x] **(G-2-3-2)** `test_autonomous_surface_adapter.py` — discuss 응답에 `technology_recommendations` non-empty (stub)
- [x] **(G-2-3-3)** `test_orchestrator_dialogue_mode.py` — ① 경로로 이전 또는 dual-path 명시 deprecated

---

## PART G-3. 마켓·관리자 음성 STT SSOT 완료 (P1)

> **Gap (해소):** Admin · Marketplace 모두 `useOrchestratorVoiceStt` + Edge TTS SSOT.

### G-3-1. 공통 STT 진입

- [x] **(G-3-1-1)** `lib/orchestrator-voice-entry.ts` — STT → `message` · `context_tags: ['voice-stt','voice-entry']` · speaker `*(음성)` SSOT
- [x] **(G-3-1-2)** Admin · Marketplace 동일 hook (`useOrchestratorVoiceStt`) — `use-orchestrator-chat.ts` / `marketplace-orchestrator-client.tsx` 중복 제거
- [x] **(G-3-1-3)** STT 후 **live rail**에 “음성 입력” 턴 표시 + TTS (`speakOrchestratorReply` · **Edge neural `/api/llm/voice/synthesize` 우선**, 브라우저 speechSynthesis fallback)

### G-3-2. 음성 → discuss / execute 라우팅

- [x] **(G-3-2-1)** 음성 transcript에 discuss marker 포함 시 → 자동 `discuss` (4단계+)
- [x] **(G-3-2-2)** “진행해” · “N단계 진행해줘” 음성 → `execute` intent
- [x] **(G-3-2-3)** DecisionCard 버튼 클릭 시 TTS로 확인 질문 재생 (접근성)

### G-3-3. 검증

- [x] **(G-3-3-1)** `test_voice_gateway_schema.py` — orchestrate voice path 회귀
- [x] **(G-3-3-2)** 수동: Admin `/admin/llm` — 마이크 → STT → live rail 갱신 (스크린 1장) · `03-admin-voice-live-rail.png`
- [x] **(G-3-3-3)** 수동: Marketplace `/marketplace/orchestrator` — 동일 시나리오 · `04-marketplace-voice-live-rail.png`

**완료 조건:** `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` A-6-3 → `[x]`

---

## PART G-4. discuss-4 ↔ stage_run 카드 UX 정합 (P1)

> **Gap:** `EXECUTION_STATUS_REPORT.md` §7 — discuss-4 중 stage_run이 ARCH-005를 선행 표시 (기능 차단 아님, UX 혼란).

### G-4-1. 동기화 규칙

- [x] **(G-4-1-1)** `stage_run_sync.py` — `discuss` 턴 `current_stage_id` 전진 금지 · `test_sync_discuss_turn_keeps_arch004`
- [x] **(G-4-1-2)** discuss substep — “협업 Q&A 진행 중” `running`
- [x] **(G-4-1-3)** `format_stage_progress_hint` → stage_run `command_modes` / 패널 commandRules에 mirror (`build_stage_command_rules` · diagnostics `command_rules`)

### G-4-2. UI 표시

- [x] **(G-4-2-1)** `OrchestratorStageCardPanel` — active stage = `current_stage_id` + `diagnostics.autonomous_intent=stage_discuss` 시 **노란 discuss 오버레이**
- [x] **(G-4-2-2)** ARCH-004 카드에 “아이디어·기술 제안 대화 중” 서브 상태
- [x] **(G-4-2-3)** live rail과 stage 카드 **동일 stage index** 하이라이트 (STAGE-04 ↔ ARCH-004 · `resolveDiscussArchId`)

### G-4-3. 검증

- [x] **(G-4-3-1)** probe discuss-4 턴 — `stage_run_current === ARCH-004` assert 추가 (`run_11stage_orchestrator_probe.py`)
- [x] **(G-4-3-2)** Playwright — discuss 후 ARCH-005가 `pending` 유지 (`orchestrator-discuss4-stage-run.playwright.spec.ts` · 2/2 passed)

---

## PART G-5. AutonomousOrchestratorPanel ↔ StageCardPanel UI 통합 (P2)

> **Gap:** Admin `/admin/llm` — ① `AutonomousOrchestratorPanel`(/autonomous/*) vs ② `useOrchestratorChat` + StageCardPanel 이원. 마켓은 StageCard + customer chat.

### G-5-1. Admin 단일 워크스페이스

- [x] **(G-5-1-1)** `/admin/llm` — **하나의 “오케스트레이터 워크bench”** 탭: Live Flow Rail + StageCard + Chat + (접기) Generator (`data-testid="orchestrator-workbench"`)
- [x] **(G-5-1-2)** `miniConsoleLayout` — workbench SSOT 기본 (`orchestrator-workbench`) · Capability/RuntimeConfig 등 legacy 패널 접음 · Generator 채팅은 workbench 내 유지
- [x] **(G-5-1-3)** `AdminManualStepStrip` ARCH-001~010 ↔ live rail STAGE-01~10 **라벨 통일** (`resolveLiveFlowLabelForArchId`)

### G-5-2. Marketplace 정렬

- [x] **(G-5-2-1)** terminalFocusedView / structured-response — G-0 DecisionCard로 **중복 패널 축소** (`showLegacyStructuredResponse`)
- [x] **(G-5-2-2)** “주문하기” 실행 vs “단계 카드” vs “채팅” — 상단 **3-track diagram** (`orchestrator-three-track-diagram`)

### G-5-3. API 표면 축소

- [x] **(G-5-3-1)** G-1 완료 후 `/api/llm/autonomous/chat` — 내부·디버그 전용 또는 orchestrate/chat alias
- [x] **(G-5-3-2)** 프론트 fetch URL 단일화 — `postAdminOrchestratorChat` → `/api/llm/orchestrate/chat` (+ marketplace `postCustomerOrchestratorChat`)

### G-5-4. 검증

- [x] **(G-5-4-1)** `admin-dashboard-ops.playwright.spec.ts` — unified workbench selector (`orchestrator-workbench`)
- [x] **(G-5-4-2)** `marketplace-orchestrator-chat.playwright.spec.ts` — live rail + decision card

---

## PART G-6. 권장 구현 순서 · DoD

### 순서 (의존성)

```
G-1 (HTTP→①)  →  G-4 (discuss sync)  →  G-2 (기술제안 흡수)
       ↓
G-0 (실시간 시각 흐름)  ← 병행 가능, G-1 diagnostics 필요
       ↓
G-3 (음성 SSOT)  →  G-5 (UI 통합)
```

### Definition of Done (전체 Gap 클로저)

- [x] **DoD-1** Admin·Marketplace 채팅 **모두** `diagnostics.orchestrator_core=autonomous_turn_controller` (`test_orchestrator_dialogue_mode_autonomous.py` · probe http assert)
- [x] **DoD-2** 11-stage probe **4종** — stub **11/11** ✅ · **live** **11/11** ✅ (`064143`, vLLM `:8008`) · http-admin/marketplace **`orchestrator_core` 13/13** ✅ (`063700`/`063618`) · discuss-4 market **ARCH-004** ✅
- [x] **DoD-3** discuss-4 시 stage_run **ARCH-004 고정** (G-4-3 · probe stub + sync-inline + Playwright)
- [x] **DoD-4** 사용자 시나리오 E2E: “4단계 Redis 제안 → DecisionCard → ‘반영하고 4단계 진행’ → live rail execute → 카드 passed”
- [x] **DoD-5** 음성 동일 시나리오 1회 통과 (Admin + Marketplace) — `npm run e2e:orchestrator-dod5`
- [x] **DoD-6** `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md`에 PART G 링크 + A-6 gap 문구 정리

---

## PART G-7. 파일 맵 (수정 예상)

| 영역 | 파일 |
|------|------|
| HTTP SSOT | `backend/llm/orchestrator.py` · `backend/marketplace/customer_orchestrate_router.py` |
| 코어 | `backend/orchestrator/autonomous/turn_controller.py` · `surface_adapter.py` · `stage_run_sync.py` |
| Advisory | `backend/orchestrator/chat/chat_service.py` → extract `autonomous/advisory.py` |
| Live UI | `frontend/frontend/shared/orchestrator-live-flow-rail.tsx` *(신규)* · `orchestrator-stage-card-panel.tsx` |
| Admin | `frontend/frontend/app/admin/llm/page.tsx` · `components/ui/AutonomousOrchestratorPanel.tsx` |
| Market | `frontend/frontend/app/marketplace/orchestrator/marketplace-orchestrator-client.tsx` |
| Voice | `frontend/frontend/lib/use-orchestrator-chat.ts` · `components/orchestrator/OrchestratorVoiceMicButton.tsx` |
| Test | `scripts/run_11stage_orchestrator_probe.py` · `backend/tests/test_autonomous_surface_adapter.py` · `backend/tests/test_stage_run_sync.py` · `tests/orchestrator-live-flow-rail.playwright.spec.ts` · `tests/orchestrator-discuss4-stage-run.playwright.spec.ts` |
| Evidence | `evidence/orchestrator-visual-flow-*/` · `evidence/orchestrator-ssot-gap-*/` |

---

## PART G-8. 재현·검증 명령

```powershell
# 백엔드 SSOT :8000 재기동 후 probe
.\scripts\restart_backend_8000.ps1

# 11-stage SSOT (G-1 완료 후 매 커밋)
python scripts/run_11stage_orchestrator_probe.py --mode stub
$env:OLLAMA_BASE="http://127.0.0.1:8008/v1"
python scripts/run_11stage_orchestrator_probe.py --mode live
$env:PROBE_LOGIN_EMAIL="119cash@naver.com"; $env:PROBE_LOGIN_PASSWORD="changeme-probe-local"
python scripts/run_11stage_orchestrator_probe.py --mode http --admin --base-url http://127.0.0.1:8000
python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace --base-url http://127.0.0.1:8000

# 단위 (async)
python -m pytest backend/tests/test_stage_commands.py backend/tests/test_autonomous_surface_adapter.py -p asyncio --asyncio-mode=auto

# 프론트 — Live Flow Rail 계약 (G-0-4)
npm run e2e:orchestrator-live-flow-rail
# discuss-4 stage_run 고정 (G-4-3)
npm run e2e:orchestrator-discuss4
# DoD-4 Redis · DoD-5 음성 · G-0-4-5/G-3-3 스크린
npm run e2e:orchestrator-dod4
npm run e2e:orchestrator-dod5
npm run e2e:orchestrator-visual-evidence
node tests/orchestrator-speech.test.mjs
# 3025 포트 충돌 시
npm run e2e:orchestrator-live-flow-rail:fresh

cd frontend/frontend
npx playwright test tests/marketplace-orchestrator-chat.playwright.spec.ts tests/admin-dashboard-ops.playwright.spec.ts
```

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-17 | 초안 — 5항목 Gap + 실시간 시각 흐름 PART G-0 추가 |
| 2026-06-17 | G-0-1/2·G-1-1/2·G-0-4-1~3 — Live Flow Rail · Decision Panel · Playwright 5/5 |
| 2026-06-17 | G-4-1-1/2 discuss stage_run 고정 · G-1-3 문서 정합 (§0.11 · API naming) |
| 2026-06-17 | G-4-2 discuss UI — StageCardPanel 오버레이 · ARCH-004 배지 · `OrchestratorDiscussBanner` · rail/card sync |
| 2026-06-17 | G-4-3 — probe discuss-4 assert · Playwright ARCH-004/005 · DoD-3 |
| 2026-06-17 | G-3 TTS Edge neural · G-5-3 API 단일화 · DoD-4/5 · visual evidence 4 PNG · :8000 SSOT · **기술서 §0.12** |
| 2026-06-17 | DoD-2 **4-probe 완료** — live `064143` 11/11 · http `063618`/`063700` · G-0-3-3 poll 1차 완료 |
| 2026-06-17 | G-0-3-2b — progress 스키마 확장 · Live Flow Rail 실시간 logs/substeps · FlowSection 11 STAGE |
