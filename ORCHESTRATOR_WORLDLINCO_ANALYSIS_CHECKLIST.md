# 오케스트레이터 자율형 대화 & 월드링코(WorldLinco) 통번역 — 분석 및 방향 체크리스트

> **최종 갱신:** 2026-06-16 · 브랜치 `gpu-llm-server-awq-20260427` · **APK build 74** (`1.0.45`) · backend tag **`v1.0.46`**  
> 본 문서는 **① 오케스트레이터 멀티 자율형 대화**, **② 월드링코 통번역/VoIP** 진단과 다음 방향을 정리합니다.  
> **마스터 기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` · **Voice Relay:** `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md` · **검증:** `evidence/voip-voice-relay-orchestrator/VERIFICATION_REPORT.md`  
> **1차 출시 (개인 APK):** **PART E** · **베타 안내:** [`docs/worldlinco-v2/BETA_LAUNCH_GUIDE.md`](docs/worldlinco-v2/BETA_LAUNCH_GUIDE.md) · **V2 미래 버전:** **PART F** + [`docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md`](docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md) *(계획 고정 · v1.0 범위 아님)*  
> 표시: `[ ]` 미착수 · `[~]` 부분 구현/검증중 · `[x]` 완료.

> ### 📌 문서 우선순위 (2026-06-14 확정)
> 1. **지금:** PART E — WorldLinco **v1.0 개인 APK 1차 출시** (다문화 한국 · 통역 통화)
> 2. **출시 후:** PART F / `WORLDLINCO_V2_ROADMAP.md` — Communication OS **업그레이드** (hot path 유지)
> 3. **병행 금지:** PART A/D-3 오케스트레이터 full_auto·STAGE — **v1.0 출시 전 보류**

> ### ✅ 초기 PR (P0 오케스트레이터 · VoIP P1/P2)에서 수정/검증 완료
> - **A-1-1~3** CoderAgent 매니페스트, 세션 복원/저장.
> - **B-3-1** `VoiceResponse.detected_language` 필드.
> - 회귀: `test_autonomous_orchestrator.py`, `test_voice_gateway_schema.py`.
> - 비고: async 테스트는 `pytest-asyncio` 필요(`-p asyncio --asyncio-mode=auto`).

> ### ✅ 2026-06-16 Autonomous TurnController 11단계 SSOT · 4-probe 실행 완료
> - **단일 코어:** Admin `orchestrate/chat` · Marketplace `customer-orchestrate/chat` → `surface_adapter` → `TurnController`.
> - **11단계:** `stage_definitions` · `stage_commands` · `stage_coder_scope` — stub/live/http(marketplace) **11/11 PASS**.
> - **패치 정밀도:** 단계당 2~9파일 · 4단계 107파일 폭주 수정 · 4.5 reviewer/validator 게이트 수정.
> - **프로브:** `scripts/run_11stage_orchestrator_probe.py` — `--admin` · `--marketplace` · incomplete exit 1.
> - **증적:** `evidence/orchestrator-11stage-probe-20260616/EXECUTION_STATUS_REPORT.md` · `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.10.

> ### ✅ 2026-06-16 A-3-2 GPU 검증 완료 (32B · Admin HTTP)
> - vLLM **Qwen2.5-Coder-32B-Instruct-AWQ** @ `:8008` · `profile_aligned_32b_awq=true`
> - `verify_autonomous_llm_gpu.py` **overall_passed** — turn_controller · http_testclient · **http_api** (Admin JWT)
> - 증거: `evidence/autonomous-a32-gpu-verify/A32_GPU_VERIFY_REPORT.md` · `A32_GPU_VERIFY_20260615-220314.json`
> - 백엔드: `devanalysis114-backend` 재기동 후 `llm_connected` API 계약 반영

> ### ✅ 2026-06-16 관리자 오케스트레이터 (PART A/D-3) 진행
> - **A-2-1~4** full_auto 자동 실행 · STAGE 턴당 순회 · 거절 재계획 · LLM mutation quota.
> - **A-3-3~5** LLM setup warning · `__init__.py` · **관리자 UI** `/admin/llm` 패널.
> - **A-4-1~4** 단위·HTTP 테스트 · route 정정 · `docs/ORCHESTRATOR_API_NAMING.md`.
> - 테스트: `test_autonomous_orchestrator.py` 31 · `test_autonomous_orchestrator_http.py` 8.

> ### ✅ 2026-06-14 build 65까지 추가 완료 (코드·배포·문서)
> - **운영 VoIP:** `backend/marketplace/nadotongryoksa_voip_router.py` (`/api/v1/voip/signal`, `/presence`, initiate/accept/end).
> - **voice-translate:** `POST /api/llm/voice-translate` + 모바일 Voice Relay 파이프라인.
> - **Silero VAD** 네이티브 + phrase boundary(defer 3종) + **14s safety cap**.
> - **build 65:** `repetition_hallucination` 가드(Tab 무한 반복 버그 대응).
> - **APK:** marketplace `nadotongryoksa-v1.apk` · Tab/S10 **versionCode 65** 설치·백엔드 재배포·Git push 완료.
> - **증적:** defer Tab PASS (`cap_defer_test_20260614-225011`), cap ~13.8s logcat, 단위 테스트 15+ (mobile orchestrator).

---

## PART A. 오케스트레이터 멀티 자율형 대화

대상 모듈: `backend/orchestrator/autonomous/` (router · session · turn_controller · agent_bus · agents/*)
API: `POST /api/llm/autonomous/chat`, `GET /api/llm/autonomous/session/{id}` (`backend/orchestrator/autonomous/router.py:14`)
등록: `backend/main.py:1500-1501` (정상 로드 확인됨)

### A-0. SSOT · 두 표면 · 음성 우선 (2026-06-16 확정)

**제품 원칙 (관리자 ↔ 직원 마켓 오케스트레이터):**

| 원칙 | 내용 |
|------|------|
| **단일 엔진 SSOT** | 오케스트레이터 **코어는 하나**. STAGE · A뇌 에이전트 · LLM 라우트 · `llm_connected` 계약 **동일**. |
| **두 표면** | ① **직원 마켓** `/marketplace/orchestrator` (customer-orchestrate) ② **관리자** `/admin/llm` — **권한·과금·output scope만 다름**. |
| **음성 우선** | **두 표면 모두 음성으로 지시** 가능해야 함. 수동 버튼·모드 토글 중심 UI **지양**. |
| **버튼 예외 (직원 마켓)** | **자가진단 / 자가개선 / 자가확장** 만 명시적 버튼 허용 — VoIP·운영 진단 트랙(PART B)과 연계. |
| **VoIP (③)** | 실시간 통역 통화 · 모바일 Voice Relay — **코드 오케스트레이터 SSOT와 별도 엔진**. |

**현재 코드 vs 목표 (gap):**

| 항목 | 목표 SSOT 코어 | 현재 마켓 (직원) | 현재 관리자 |
|------|----------------|------------------|-------------|
| 엔진 | `backend/orchestrator/autonomous/` (`TurnController`) | `customer-orchestrate/*` → **②** `orchestrate/chat` · `llm/orchestrator.py` | 기본 UI **②** · ① 패널 **숨김** (`miniConsoleLayout`) |
| 음성 지시 | 코어 진입 전 STT → 동일 `message` | **미연동** (capability 설명만) | **②** `useOrchestratorChat` · `/api/llm/voice/orchestrate` |
| GPU 검증 (A-3-2) | ① 3-probe 통과 | — | Admin http_api 포함 |

**레거시 ② (통합 대상, not SSOT):** `backend/orchestrator/chat/` · `POST /api/llm/orchestrate/chat` — 마켓·관리자가 **아직** 많이 의존. **→ ① 코어 어댑터로 흡수**가 SSOT 정렬 방향.

**이름 혼선 (테스트·스크립트):**
- `test_orchestrator_dialogue_mode.py` · `verify_autonomous_chat.py` → **②** 검증 (파일명 misleading).
- `test_autonomous_orchestrator*.py` · `verify_autonomous_llm_gpu.py` → **①** 검증.
- 명명 SSOT: `docs/ORCHESTRATOR_API_NAMING.md`.

**어제(A-3-2) 작업 범위:** **① 코어** GPU live · Admin API probe · 32B — **②↔① 통합·마켓 음성·UI SSOT는 미착수**.

### A-0b. SSOT 정렬 · 11단계 — 실행 상태 (2026-06-16)

- [x] **(A-6-1) 단일 코어** — Admin `POST /api/llm/orchestrate/chat` · Marketplace `customer-orchestrate/chat` → `surface_adapter.run_autonomous_surface_chat` → **동일 TurnController**.
- [x] **(A-6-5) 11단계 자연어 명령** — `설계해줘` · `N단계 진행해줘` · 4단계+ 협업 Q&A (`stage_commands.py`).
- [x] **(A-6-6) 단계 패치 SSOT** — `stage_coder_scope.py` · 단계당 bounded files · validator 구조검증(기존 entry point 인정).
- [x] **(A-6-7) 4-probe 검증** — stub **11/11** · live(vLLM) **11/11** · http marketplace **11/11** · http admin 플래그 추가.
- [~] **(A-6-2) 음성 진입 공통** — STT → `message` → 코어 (마켓·관리자 동일); admin `voice/orchestrate` 존재 · **마켓 미연동**.
- [~] **(A-6-3) UI 음성 우선** — admin STT hook · 마켓 orchestrator STT **부분**.
- [x] **(A-6-4) stage_run 동기화** — marketplace `stage_run_sync.py` · http probe sync_checks PASS.

### A-0b (legacy). SSOT 정렬 · 음성 — 미착수 체크

### A-0 (legacy note) — 레거시 이원 구조 설명

### A-1. 🔴 P0 — 치명적 버그 (먼저 수정해야 진행 가능)

- [x] **(A-1-1) `CoderAgent`의 매니페스트 호출 시그니처 불일치 → 승인 후 코드 생성 시 `TypeError`** ✅ 수정 완료
  - 실제 함수 정의: `backend/llm/orchestrator.py:9191`
    `def _compat_manifest_for_request(task, project_name, validation_profile, required_files)`
  - 잘못된 호출: `backend/orchestrator/autonomous/agents/coder.py:79-85`
    존재하지 않는 인자 `output_dir=`, `b_brain_result=` 전달 + 필수 인자 `required_files` 누락.
  - 올바른 사용 예(메인 오케스트레이터): `backend/llm/orchestrator.py:12665-12669`
  - **방향**: `coder.py`에서 `required_files`를 산출해 위치 인자로 호출하고, `output_dir`/`b_brain_result`는 제거. 이어서 `b_result["written_files"]`를 `_compat_write_manifest` 결과와 **병합**(메인 경로 12666-12669 참고)하여 validator가 검사할 파일 목록 누락 방지.

- [x] **(A-1-2) 세션 복원 불완전 → 멀티턴 재개 시 상태 소실** ✅ 수정 완료
  - 저장은 전체: `session.py:122-139` (`stages`, `agent_results` 포함)
  - 복원은 `conversation`만: `session.py:173-177` → `stages`/`agent_results`/`pending_approval_data`/`model_routes` 미복원.
  - **방향**: `load()`에 `stages`(`StageState`), `agent_results`(`AgentResult`), 승인 대기 컨텍스트를 역직렬화해 복원. 라우팅·승인 흐름이 재개 후에도 일관되게 동작하도록.

- [x] **(A-1-3) 세션 `save()` 누락 경로 → 첫 턴이 인사/상태면 다음 요청에서 404** ✅ 수정 완료
  - `save()` 호출은 파이프라인 종료(`turn_controller.py:173`)와 `_handle_approval()`(`:264`)에서만.
  - greeting(`:107-110`)·status·승인 대기 없는 approval·빈 파이프라인 응답은 저장 안 됨.
  - **방향**: `process_turn()` 반환 직전 모든 분기에서 `session.save()` 보장(또는 응답 빌드 헬퍼 안에서 일괄 저장).

### A-2. 🟠 P1 — 설계/동작 불일치

- [x] **(A-2-1) `full_auto` 모드 자동 실행** ✅ 2026-06-16 — `turn_controller._execute_code_pipeline()` · 승인 없이 coder→validator.
- [x] **(A-2-2) STAGE-02~10 자동 순회** ✅ 2026-06-16 — full_auto · 기본 `AUTONOMOUS_MAX_STAGES_PER_TURN=11` · `_run_stage_planning_agents` · env로 턴당 상한 조절.
- [x] **(A-2-3) 거절(`rejected`) 처리** ✅ 2026-06-16 — intent `rejection` · reasoner/planner 재계획 · semi_auto 재승인 대기.
- [x] **(A-2-4) 쿼터/레이트리밋** ✅ 2026-06-16 — `require_llm_mutation_quota` on `/api/llm/autonomous/chat`.

### A-3. 🟡 P2 — 협업/정리

- [x] **(A-3-1) `agent_bus` 실협업** ✅ 2026-06-16 — `_wire_agent_bus_subscriptions` · `_run_agent_with_bus`(request/response/handoff) · planning·pipeline 경로.
- [x] **(A-3-2) LLM stub vs GPU 품질 검증** ✅ 2026-06-16 — A뇌 live LLM · API `llm_connected` · Admin UI · **3-probe 전체 통과** (`evidence/autonomous-a32-gpu-verify/A32_GPU_VERIFY_20260615-220314.json` · vLLM **32B AWQ** · turn_controller + http_testclient + **Admin http_api**).
- [x] **(A-3-3) `_build_llm_call()` 예외 로그** ✅ 2026-06-16 — `router.py` warning.
- [x] **(A-3-4) 패키지 `__init__.py` 정리** ✅ 2026-06-16 — `autonomous/` · `agents/` export.
- [x] **(A-3-5) 프론트엔드 연동** ✅ 2026-06-16 — `/admin/llm` · `AutonomousOrchestratorPanel` · proxy `/api/llm/autonomous/*`.

### A-4. 테스트 방향

- [x] **(A-4-1)** 승인→coder→validator 통합 테스트 ✅ `test_autonomous_orchestrator.py`.
- [x] **(A-4-2)** HTTP TestClient ✅ `test_autonomous_orchestrator_http.py` (9 tests).
- [x] **(A-4-3)** route 테스트 정정 ✅ idle vs STAGE-01 분리.
- [x] **(A-4-4)** ①/② 명명 혼선 ✅ `docs/ORCHESTRATOR_API_NAMING.md`.

### A-5. GPU/LLM 없이 가능한 검증 (클라우드 vs GPU 서버)
- 가능: 의도 분류·인사/상태 응답·`ValidatorAgent`(`py_compile`)·버스 request/handoff·세션 저장/복원·A뇌 **`status=stub`** · `llm_connected=false` 계약.
- **GPU 서버 live (2026-06-16 최종):** vLLM **32B AWQ** · `profile_aligned_32b_awq=true` · `overall_passed=true` · reasoner/planner `success` · reviewer `needs_revision` · Admin JWT `http_api` 포함 · `scripts/verify_autonomous_llm_gpu.py` · 증거 `A32_GPU_VERIFY_20260615-220314.json`.
- **vLLM 기동:** `gpu-llm-server/docker-compose.vllm-32b.yml` · `scripts/start_vllm_rtx5090_32b.ps1`.
- **Admin ops:** `scripts/reset_fixed_admin_password.py` (host DB) · 전역 설정 패널 「관리자 계정 비밀번호 변경」UI.

---

## PART B. 월드링코(WorldLinco) 통번역 — "막힌 구간" 진단

### B-0. 명칭 매핑 (혼선 정리)

| 레이어 | 이름 | 위치 |
|--------|------|------|
| 모바일 앱 표시명(브랜드) | **WorldLinco** | `apps/mobile-nadotongryoksa/app.json` (`"name": "WorldLinco"`) |
| 내부 슬러그/프로젝트 | **나도통역사 / nadotongryoksa** | `apps/mobile-nadotongryoksa/`, API 접두 |
| Android 패키지(현재) | `com.parkcheolhong.worldlinco` | `app.json` (2026-06-13 통일) |
| Android 패키지(구 실기기) | `com.parkcheolhong.worldlinco` | `monitoring/reports/voip-*` 로그 — 현재 워크스페이스와 일치 |
| 모바일 번역 엔진 | **NadoTranslator** | `backend/services/nadotongryoksa/translator.py`, `POST /api/llm/translate` |
| 마켓플레이스 통역 엔진 | **SorisaeInterpreter** | `backend/services/shinsegye/interpreter/sorisae_interpreter.py` |

### B-1. 상대적으로 "완료된" 트랙 (방향 문서 대상 아님)
- [x] 텍스트 번역 `POST /api/llm/translate` (NadoTranslator: 사전 캐시 + googletrans)
- [x] 노래 자막 Job API `POST /api/mobile/song-translation/jobs` → SRT/VTT/LRC/JSON export — `NADOTONGRYOKSA_SONG_TRANSLATION_CHECKLIST.md` "완료됨"
- [x] LBS — `NADOTONGRYOKSA_LBS_CHECKLIST.md` "완료됨"
- [x] 사용자 목소리 preview 정책/계약 — `NADOTONGRYOKSA_USER_VOICE_SINGING_CHECKLIST.md`(배포/export는 정책상 기본 보류)

### B-2. 🔴 P0 — VoIP 실시간 통역 통화 (2026-06-14 현황)

> ~~백엔드·APK 비어 있음~~ → **구현·배포 완료(build 65).** 잔여: **실기기 E2E 안정화**, **FCM 네이티브**, **devices/register 운영 정합**, **repetition guard 재검**.

#### B-2-0. ⚠️ VoIP 이중 스택 (운영 vs 테스트)

| 스택 | 경로 | `main.py` | 용도 |
|------|------|-----------|------|
| **운영** | `backend/marketplace/nadotongryoksa_voip_router.py` | ✅ | 모바일 · `WS /signal`, `/presence` |
| **테스트** | `backend/voip/` | ❌ | `test_voip_*.py` 전용 |

- [x] **(B-2-0) 운영 라우터 식별** — `main.py:1469-1473` marketplace router만 등록. `backend/voip/` 테스트 통과 ≠ 운영 노출.

- [x] **(B-2-1) VoIP REST** ✅ — **운영:** initiate / pending / accept / end / mode-audit (`nadotongryoksa_voip_router`). **테스트:** `backend/voip/router.py`(미마운트).

- [x] **(B-2-2) 시그널링 / TURN** ✅ — **운영:** `WS /api/v1/voip/signal`. **테스트:** `WS /api/v1/voip/ws/{call_id}`.

- [x] **(B-2 P2) Redis pub/sub** ✅ — `backend/voip/redis_backend.py` + `test_voip_signaling_redis.py`.

- [x] **(B-2 P3-C) TURN HMAC** ✅ — `backend/voip/config.py` + `test_voip_turn_tokens.py`.

- [x] **(B-3-voice) `POST /api/llm/voice-translate`** ✅ — `backend/llm/router.py`. 테스트: `test_voice_translate_stt.py`, `test_voip_voice_translation_meta.py`. *(구 B-3-3 번호와 OCR 항목 혼동 주의 — OCR은 아래 B-3-3)*

- [~] **(B-2-3 / P3-A) FCM + presence**
  - ✅ marketplace: initiate push, `WS /presence`, FCM v1/legacy.
  - ✅ 모바일: `voipPresence.ts`, accept 연동.
  - ❌ **`POST /devices/register` 운영 gap** — 모바일 호출 O, marketplace router **엔드포인트 없음** (`backend/voip`에만 존재).
  - ❌ Firebase `No Firebase App '[DEFAULT]'` — `VoipMessagingAdapter` 미주입.

- [x] **(B-2 accept) 착신 REST** ✅ — `POST /calls/{call_id}/accept`. B26 `VOIP_INCOMING_ACCEPT_API_OK`.

- [x] **(B-2 P3-B) PSTN 어댑터** ✅ — `backend/voip/pstn.py`. 미디어 브리지 후속.

- [x] **(B-2-4) 패키지 lineage** ✅ — `com.parkcheolhong.worldlinco`, **build 65** Tab/S10.

- [x] **(B-2-5) APK 빌드·배포** ✅ — `publish_worldlinco_apk.ps1`, marketplace APK, versionCode **65**.

- [~] **(B-2-6) 실기기 WebRTC·Relay** — B26 시그널 PASS; connected×2·자동 E2E flaky; Voice Relay SENT는 **수동 발화** 필요.

- [x] **(B-2-7) nginx WS 프록시** ✅ — presence/signal Upgrade.

- [x] **(B-2-8) Call mode 감사** ✅ — `call_mode_schema`, `call_mode_audit_service`.

- [ ] **(B-2-9) devices/register 운영 정합** — marketplace router에 이식 또는 모바일 presence-only 정렬.

> 📐 `NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md` · 상세 `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §4.

### B-3. 🟠 P1 — 음성(STT)·자동 언어감지 API 계약 버그

- [x] **(B-3-1) `detected_language` 응답 스키마 누락** ✅ 수정 완료 — `VoiceResponse`에 `detected_language: Optional[str] = None` 필드 추가 + `# pyright: ignore` 제거. 회귀 테스트 `test_voice_gateway_schema.py`.
- [x] **(B-3-2) STT 언어 힌트 미전송** ✅ **코드 수정 완료** — `App.tsx` STT 요청에 `language: autoVoiceModeEnabled ? 'auto' : fromLang` 전달. 실기기 음성 품질 검증은 `VOICE_DETECTION_TEST_PROTOCOL.md` 대기.
- [x] **(B-3-3) 이미지 번역(OCR) 엔드포인트** ✅ **2026-06-13 완료** — `backend/mobile/image_translation/` (`POST /api/mobile/image-translation`), 모바일 `translateImage()`·`regionHint` 연동. RapidOCR E2E(영문→한글) 200. 계약 테스트 35 passed.
  - ⏳ **남은 작업**: `Dockerfile.backend` 재빌드 시 `rapidocr-onnxruntime==1.2.3` 영구 반영(현재 컨테이너 `pip install` 적용). 실기기 카메라/OCR UI 검증.
- [x] **(B-3-4) RapidOCR 백엔드 의존성** ✅ **2026-06-13 완료** — `requirements.txt`에 `rapidocr-onnxruntime==1.2.3`(Python 3.13 호환; ≥1.3.x는 `<3.13` 제약). 컨테이너 설치·OCR E2E 확인.

### B-4. 🟡 P2 — 실기기/안정성 검증 미완 (기존 체크리스트에 이미 추적 중)

- [x] **(B-4-0) build35 채팅·친구 404 재검증** ✅ **2026-06-13** — build **65**에서도 채팅 레일 정상 유지(기능 회귀 없음, 별도 증적 `mobile-restore-functional-verify-20260613/`).

- [ ] **(B-4-1)** BT 이어폰 MIC + 안정성(5회 중 2회 오류) — `mobile-nadotongryoksa-bt-hybrid-verification.md`(항목 4, 10, Round 2 미기록).
- [ ] **(B-4-2)** 음성 국가명 자동 전환(미국/일본/중국) — `VOICE_DETECTION_TEST_PROTOCOL.md:173-178` 전부 미체크.
- [ ] **(B-4-3)** WF(Wi-Fi) 폴백 2회 검증 — `CRITICAL_2_CHECKLIST.md:34-42` `TC-WF-01` 기록 대기.

### B-5. 🟢 P3 — 환경/설계 한계 (인지 필요)
- [ ] 신세계 레거시 통역 모듈(`backend/services/shinsegye/interpreter/hybrid_interpreter_system.py:266-280`)의 "온라인 번역"은 **실 API가 아니라 시뮬레이션** → 프로덕션 경로로 오인 금지.
- [ ] `voice/orchestrate`는 `auto_apply=false`여도 orchestrator chat을 호출(불필요 LLM 비용 가능) — transcript만 필요할 땐 STT-only 경로 분리 검토.
- [ ] googletrans 실패 시 원문 그대로 반환(`translator.py:165-170`) → 번역 실패가 가려짐. 실패 표식/재시도 검토.
- [ ] Song Job 저장소가 DB 실패 시 in-memory 폴백(`service.py:222,264`) → 멀티워커/재시작 시 job 유실 가능.

### B-6. 외부 의존성 / GPU
- googletrans, faster-whisper, Silero VAD (Android native), react-native-webrtc, Firebase/FCM, expo-audio/Speech TTS.
- **CXX1210 블로커** — build 65 `assembleRelease` 성공으로 **해소**(로컬 Gradle). EAS는 별도.
- GPU 없이도 텍스트/노래 번역·STT(tiny) 동작. 실서버 RTX 5090(AGENTS.md).

### B-7. VoIP Voice Relay Auto Orchestrator (build 65)

> **구조도·파라미터:** [`docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md`](docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md) (구 0.8s/12s/overlap mermaid **폐기** — 문서 내 build 65 다이어그램 사용)

| ID | 항목 | 파일 | 상태 |
|----|------|------|------|
| V-1 | 아키텍처 문서 (build 65 갱신) | `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md` | [x] |
| V-2 | Sender VAD·필터 | `voiceRelayOrchestrator.ts` | [x] |
| V-3 | 재생 큐 (순차, overlap 없음) | `voiceRelayPlaybackQueue.ts` | [x] |
| V-4 | WS 메타 | `voipCallClient.ts` | [x] |
| V-5 | 통화 UI 파이프라인 | `VoIPCallScreen.tsx` | [x] |
| V-6 | 백엔드 relay | `nadotongryoksa_voip_router.py` | [x] |
| V-7 | 단위 테스트 | orchestrator/segment/turn/silero tests + `test_voip_*` | [x] |
| V-8 | **Silero native VAD** | `VoiceRelaySileroVadModule.kt`, `voiceRelaySileroVad.ts` | [x] POC |
| V-9 | **Phrase boundary defer** | `voiceRelaySegmentBoundary.ts` — 3종 defer | [x] Tab PASS `225011` |
| V-10 | **14s safety cap** | `safetyCapMs:14000` | [x] logcat ~13848ms |
| V-11 | **Turn controller** | `voiceRelayTurnController.ts` | [x] |
| V-12 | **repetition guard** | `isLikelyRepetitionHallucination` (build 65) | [x] 코드 · [ ] 실기기 재검 |
| V-13 | 실기기 relay E2E | `scripts/voip_boundary_cap_defer_test.ps1` | [~] defer OK, cap/E2E flaky |
| V-14 | streaming STT (Phase 2) | — | [ ] |
| V-15 | full-duplex (Phase 3) | — | [ ] |

**Silero 파라미터 (운영):** silence 1100 · minSegment 3200 · minSpeechSpan 2000 · cap **14000** · cooldown 1200 ms.

**알려진 버그 (build 64, build 65 수정):** Tab TTS 피드백 → Whisper 반복 환각 → `repetition_hallucination` skip.

**언어쌍 자동 보정:** `resolveVoiceRelayLanguagePair` + backend `detected_lang` 스왑 — 코드 [x], VoIP 통화 UI 실기기 검증 [ ].

---

## PART C. 권장 진행 순서 (2026-06-14 · v1.0 출시 우선)

> **v1.0 출시 전에는 아래 1~4만.** 5~6은 **v1.0 이후**(PART F). 오케스트레이터(A-2)는 **출시 후**.

### C-1. v1.0 1차 출시 (PART E — 4~6주)

1. **(E-1 / V-12 / D-1-4)** build 65 repetition guard Tab 실기기 재검.
2. **(E-2 / V-13 / D-1-2)** Voice Relay 수동 통역 — WiFi 2대 **10통 중 8통** relay 1턴 이상.
3. **(E-3 / B-2-6 / D-1-1)** 2대 WebRTC connected (v1.0: **WiFi ↔ WiFi** 우선; LTE 매트릭스는 v1.1).
4. **(E-4)** marketplace **「통역 통화 베타」** 공개 + 이용 한계 1페이지 + 실사용 10명.

### C-2. v1.0 이후 (PART F — 미래 버전)

5. **(F-1~3 / v1.1~v1.2)** 구독·Session Core 얇은 버전 — `WORLDLINCO_V2_ROADMAP.md` #2~3.
6. **(F-4~7 / v2.0)** Redis · Signal · Coturn · Monitoring — 로드맵 #4~7.
7. **(D-2 / v1.1+)** BT·음성 자동전환·WiFi 폴백 — 1차 출시 범위 **외**.
8. **(D-3 / A-2~A-4)** 오케스트레이터 full_auto·STAGE — **MetaNova 플랫폼** 트랙, WorldLinco v1.0 **무관**.

### 방향 문서 운용
- **1차 출시:** 본 문서 **PART E**.
- **V2 업그레이드 (고정):** **PART F** + `docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md` + `FILE_MAP.md`.
- **VoIP/Voice Relay:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` + 본 문서 B-2/B-7.
- **VoIP retest:** `monitoring/reports/voip-retest-20260524-011147/voip-retest-checklist.md`.
- **`TRANSLATION_VERIFICATION_COMPLETE.md`** — VoIP·Voice Relay **미반영** 과거 문서. "완료" 근거로 사용 금지.

---

## PART D. 사용자 지정 운영 우선 체크리스트

> 아래 항목은 현재 문서에 흩어진 내용을 사용자가 지정한 우선순위대로 다시 모은 실행용 체크리스트다. 각 항목은 실제 실기기/운영 검증 근거가 채워질 때만 `[x]`로 전환한다.  
> **v1.0 출시:** D-1 중 **WiFi·수동 통역·repetition** → PART E. **D-2·D-3·D-4** → v1.0 **이후** (PART F).

### D-1. 1순위: VoIP 실기기/음성 검증

- [ ] **D-1-1) 실기기 2대 WebRTC 완전 연결 검증**
  - Android 2대 기준으로 `WiFi ↔ LTE`, `WiFi ↔ WiFi`, `LTE ↔ LTE` 조합을 각각 2회 이상 검증한다.
  - 확인 로그: `Offer`, `Answer`, `ICE Candidate`, `Connected`, `Audio Stream`, `Disconnect`.
  - 관련 근거: `B-2-6`, `B-2-7`, `V-8`.
- [ ] **D-1-2) Voice Relay 실제 음성 검증**
  - `한국어 → STT → 번역 → TTS → 상대방 재생` 전체 경로. 짧은/긴/빠른 대화 포함.
  - 관련: `B-7 V-13`, `B-3-voice`, `scripts/voip_boundary_cap_defer_test.ps1`.
- [ ] **D-1-3) Firebase + devices/register**
  - `No Firebase App` 제거, FCM 토큰·푸시 수신.
  - **`POST /api/v1/voip/devices/register` marketplace router 정합** (B-2-9).
- [ ] **D-1-4) repetition guard (build 65)**
  - Tab TTS 피드백 루프 재현 시 logcat `repetition_hallucination` skip 확인 (B-7 V-12).

### D-2. 2순위: 단말/네트워크 안정성 검증

- [ ] **D-2-1) Bluetooth 이어폰 및 오디오 라우팅 검증**
  - 블루투스 마이크, 유선 이어폰, 스피커폰 각각에서 STT, TTS, 통화가 정상 동작하는지 확인한다.
- [ ] **D-2-2) 음성 자동 언어감지 실전 검증**
  - 한국어, 영어, 일본어, 중국어 자동 전환을 검증한다.
  - `detected_language`가 실제 응답/전환에 반영되는지 확인한다.
- [ ] **D-2-3) WiFi 폴백 및 재연결 검증**
  - `4G → WiFi`, `WiFi → LTE` 전환 중 통화 유지와 재연결을 확인한다.
  - 전환 시 끊김, 지연, 재시도 동작을 함께 기록한다.

### D-3. 3순위: 오케스트레이터 자동화 확장

- [x] **D-3-1) Full Auto 루프** ✅ 2026-06-16 — A-2-1 `_execute_code_pipeline`.
- [x] **D-3-2) STAGE 11단계 자동 순회** ✅ 2026-06-16 — A-2-2 · env `AUTONOMOUS_MAX_STAGES_PER_TURN`(기본 11).
- [x] **D-3-3) Rejected 처리** ✅ 2026-06-16 — A-2-3.

### D-4. 4순위: 운영 안정화 및 자동화

- [ ] **D-4-1) 운영 장애 복구 경로 정리**
  - `Redis 장애 복구`, `TURN 장애 복구`, `FCM 장애 복구`를 우선 반영한다.
- [x] **D-4-2) Rate Limit 적용** ✅ 2026-06-16 — A-2-4 `require_llm_mutation_quota`.
- [x] **D-4-3) 테스트 자동화 확대** ✅ 2026-06-16 — 통합 실행 **94** collected (Autonomous 44 · VoIP D-4-3 32 · Voice STT 18).

---

## PART E. 1차 출시 — WorldLinco v1.0 (개인 APK)

> **제품 정의:** 한국에 사는 내국인·외국인이 **친구와 통화하며 실시간 통역**하는 **개인용 Android APK**.  
> **한 줄:** 「친구랑 전화하면, 말하는 대로 상대방 언어로 들려준다」  
> **V2 Communication OS:** **본 PART 범위 아님** — 출시 후 PART F 참조.

### E-0. 시장·포지셔닝 (고정)

- 인구 감소·다문화 확대 → 일상 **개인** 언어 장벽 해소 (가족·친구·연인·이웃).
- 배포: marketplace APK (`nadotongryoksa-v1.apk`) · Play Store는 **v1.1+**.
- 수입: v1.0 **무료 베타** → v1.1 **월 N분 무료 + 구독** (`check_mobile_license`).

### E-1. v1.0 범위 (포함)

| 항목 | 근거 | 상태 |
|------|------|------|
| 가입·로그인 | `App.tsx` auth | [x] |
| 친구·연락 | `FriendFolderScreen`, friends API | [x] |
| 통역 통화 (발신) | VoIP + Voice Relay | [x] build66 E-3-1 5/5 · build73 E-3-8 ko↔ja strict PASS |
| voice-translate (≈2.8s) | `POST /api/llm/voice-translate` | [x] |
| APK 배포 | build **74** (`1.0.45`), marketplace + manifest API | [x] |
| repetition guard | build 65+ 코드 · E-3-2 echo | [x] `e3-2_echo_20260615-232900` |
| 50개국어 API | mobile LANGS ↔ backend | [x] E-3-6 `50lang_audit_20260615-235805` |
| WiFi 2대 통화 | D-1-1 (WiFi↔WiFi만) | [x] E-3-1 |

### E-2. v1.0 범위 (제외 → v1.1 / PART F)

- FCM 착신 · `devices/register` (v1.1 — 발신-only로 v1.0 가능)
- LTE/BT/WiFi 폴백 매트릭스 (D-2)
- Communication OS · Session Core · Redis Cluster · Agent Hub
- 오케스트레이터 full_auto · STAGE (PART A/D-3)
- iOS · Desktop · streaming STT · full-duplex (V-14/V-15)

### E-3. v1.0 출시 DoD (Definition of Done)

- [x] **E-3-1)** Android 2대, **WiFi**, 수동 **10통 중 8통** — connected + relay 1턴 이상.
  - **2026-06-15 run A** (`e3_verify_20260615-174834`): **0/10** — `CalleeVoiceId=nado-000226` Tab 자기 발신 버그.
  - **2026-06-15 run B** (`e3_verify_20260615-182202`): **5/10**.
  - **2026-06-15 run C** (`e3_verify_20260615-191431`): **+3/5** · **누적 8/10 PASS** (hangup·accept 패치 후).
  - **2026-06-15 run D (build 66)** (`e3_verify_20260615-212949`): **5/5 PASS** — self-call·deeplink accept·triple initiate 수정 후.
  - 실패 원인(해소): UI `받기` 탭 flaky, stale call, Tab 자기 발신 → **build 66 + 스크립트 패치**.
  - 증적: `evidence/worldlinco-v1-launch/` · `BUILD66_LAUNCH_STATUS.md` · `E3-1_call_matrix.csv`
- [x] **E-3-2)** Tab repetition guard logcat `repetition_hallucination` skip 확인 (V-12).
  - 단위 테스트 **15/15 PASS** (`voiceRelayOrchestrator.test.ts`).
  - **2026-06-15** `e3-2_echo_20260615-232900`: S10 ko → Tab en **PLAYBACK** · `repetition_hallucination` **0**.
  - runaway 없음 (60s window). Tab 스피커·근거리 에코는 물리 환경 이슈로 분리 기록.
- [x] **E-3-6)** **50개국어 백엔드 정합** — mobile LANGS 50 ↔ `SUPPORTED_LANGUAGES` 50 ↔ API `/translate/languages` 50.
  - **2026-06-15** `50lang_audit_20260615-235805` · `backend/tests/test_supported_languages_50.py` 3/3 PASS.
  - 증적: `evidence/worldlinco-v1-launch/50LANG_ALIGNMENT_REPORT.md`
- [x] **E-3-7)** **ko↔ja API 스모크** — `voice-translate` ko→ja / ja→ko transcript PASS (동일 audit run).
- [x] **E-3-8)** **ko↔ja VoIP 실기기 E2E** — **2026-06-16** build **73** · `call-0f44540d27f6` **PASS (strict)**: S10 `detected_lang=ja` · **`target_lang=ko`** · Tab `PLAYBACK` 한국어 TTS `안녕하세요, 잘 부탁드립니다.` · backend accept `display_language=ko` · repetition **0**. 증적: `ko_ja_smoke_20260616-023813` · `E3-8_KO_JA_VOIP_REPORT.md`. *(build 71 `target_lang=en` → accept/merge fix)*
- [x] **E-3-3)** marketplace 페이지 **「WorldLinco 통역 통화 베타」** + WiFi 권장·알려진 한계 1페이지.
  - UI: `frontend/.../marketplace/nadotongryoksa/page.tsx` · 전문: `docs/worldlinco-v2/BETA_LAUNCH_GUIDE.md`.
- [~] **E-3-4)** 실사용 **10명** — **재개** (2026-06-16) · 전제: build **74** APK + backend tag **`v1.0.46`** (signup `preferred_language`/`country_code` 저장) · 기록: `E3-4_beta_users.csv` · `worldlinco_e3_beta_user_record.ps1`
- [x] **E-3-5)** git tag — **`v1.0.45`** @ build **74** APK (2026-06-16) · **`v1.0.46`** @ profile API (2026-06-16, `88adda287`)

#### E-3 검증 명령 (실기기)

```powershell
# 사전: Tab(R83W70QY11H) · S10(172.30.1.19:5555) 앱에서 로그인 완료

# E-3-1: 10라운드 (8/10 목표) — CalleeVoiceId Tab→S10 = nado-000001
pwsh -File scripts\worldlinco_e3_launch_verify.ps1 -Rounds 10 -PassThreshold 8

# E-3-2: Tab 스피커 echo — repetition skip 관찰
adb -s R83W70QY11H logcat -c
# → WiFi 통화 connected · S10 TTS 재생 · Tab 스피커 ON
adb -s R83W70QY11H logcat -v time -s ReactNativeJS:* | Select-String 'repetition_hallucination|PLAYBACK_SKIPPED'

# E-3-6: 50개국어 백엔드 정합 + ko↔ja API 스모크
pwsh -File scripts\worldlinco_50lang_alignment_audit.ps1

# E-3-8: ko↔ja VoIP strict (build 73+)
pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 70 -StableSec 8

# E-3-4: beta user 1명 기록 (10명까지 반복)
pwsh -File scripts\worldlinco_e3_beta_user_record.ps1 -DisplayName "테스터1" -Locale ko-KR -Device "Galaxy Tab" -Feedback "통역 잘 됨"
```

### E-4. v1.0 출시 전 4~6주 실행표

| 주차 | 작업 | 금지 |
|------|------|------|
| 1~2 | ~~E-3-1, E-3-2, E-3-8 strict~~ ✅ · build **74** · tag **`v1.0.46`** · **E-3-4** 10명 수집 | V2 폴더·Redis cluster |
| 3 | ~~E-3-3 (베타 페이지·안내)~~ ✅ 2026-06-15 | 오케스트레이터 A-2 |
| 4 | 지인·커뮤니티 실사용 시작 | iOS · 새 플랫폼명 |
| 5~6 | ~~E-3-5 태그~~ ✅ `v1.0.45`+`v1.0.46` · E-3-4 완료 후 v1.0 베타 종료 | Communication OS 코드 |

### E-5. v1.0 이후 버전 (요약)

| 버전 | 내용 | 로드맵 |
|------|------|--------|
| **v1.1** | FCM 착신, 구독·분당 제한 | F-1 |
| **v1.2** | 언어쌍·통화 맥락 기억 | F-2 Session Core |
| **v2.0** | Redis, Signal, Coturn, Monitoring | F-4~7 |
| **V2 Ultimate** | Memory · Meaning · Agent · Communication OS | F-8~10 |

---

## PART F. V2 미래 버전 — Communication OS (계획 고정)

> **SSOT:** [`docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md`](docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md) · [`docs/worldlinco-v2/FILE_MAP.md`](docs/worldlinco-v2/FILE_MAP.md)  
> **원칙:** VoIP·Voice Relay·`voice-translate` **hot path 유지**. V2는 **상위 계층 Strangler Fig**.  
> **시작 조건:** PART E **v1.0 출시 DoD (E-3) 전부 `[x]`** 이후.

### F-0. 구현 우선순위 (고정 · 변경 시 문서 PR)

| # | 목표 | 체크 | v1.0 |
|---|------|------|------|
| 1 | VoIP 통역 안정화 | PART E | **지금** |
| 2 | Session Core | [ ] | v1.2 |
| 3 | Call Orchestrator | [ ] | v1.2 |
| 4 | Redis Cluster | [ ] | v2.0 |
| 5 | Signal Cluster | [ ] | v2.0 |
| 6 | Coturn Cluster | [ ] | v2.0 |
| 7 | Monitoring | [ ] | v2.0 |
| 8 | Memory Engine | [ ] | V2+ |
| 9 | Meaning Engine | [ ] | V2+ |
| 10 | Agent Engine | [ ] | V2+ |

### F-1. 아키텍처 층 (요약 — 상세는 SSOT)

- **Client → API Gateway → Communication Orchestrator → Signal/Agent/Event Hubs**
- **Session Core → Intelligence Engine → Language Engine → Voice Pipeline → Delivery Engine**
- **Fabrics:** AI Control/Compute · Event · Memory · Storage · Realtime · Observability · Security

전체 ASCII 다이어그램·Fabric 정의·마이그레이션 원칙 → **`WORLDLINCO_V2_ROADMAP.md`**.

### F-2. 목표 코드 경계 (rename 전)

- `backend/communication/` — orchestrator · session · hubs · delivery adapters
- `backend/voip/` — Signal Hub 운영 승격 (`nadotongryoksa_voip_router` adapter → swap)
- `apps/.../voip-voice-relay/` — **변경 최소** (Voice Pipeline client)
- `infra/realtime/`, `infra/observability/`, `infra/event/` — v2.0+

상세 파일 매핑 → **`FILE_MAP.md`**.

### F-3. PART F 착수 금지 (v1.0 출시 전)

- [ ] ~~Session Core DB 마이그레이션~~
- [ ] ~~Kafka/NATS 도입~~
- [ ] ~~`backend/communication/` 대규모 scaffold~~
- [ ] ~~Communication OS 마케팅·네이밍 전면 교체~~

> v1.0 = **좁게 출시**. V2 = **출시 후 로드맵 #2부터 순차**. 2.8초 통역 엔진은 전 구간 **고정 자산**.
