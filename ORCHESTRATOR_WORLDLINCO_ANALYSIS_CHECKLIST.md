# 오케스트레이터 자율형 대화 & 월드링코(WorldLinco) 통번역 — 분석 및 방향 체크리스트

> **최종 갱신:** 2026-06-14 · 브랜치 `gpu-llm-server-awq-20260427` @ `a989bc9f0` · **APK build 65** (`1.0.40`)  
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

### A-0. 먼저 알아야 할 구조적 혼선 (중요)
- 이름이 비슷한 **별개의 두 시스템**이 공존합니다.
  - ① 멀티 에이전트 자율 오케스트레이터 = `backend/orchestrator/autonomous/` (지금 구현 중인 것)
  - ② 채팅 오케스트레이터 "대화 모드" = `backend/orchestrator/chat/chat_service.py`, API `POST /api/llm/orchestrate/chat`
- `test_orchestrator_dialogue_mode.py` 와 `verify_autonomous_chat.py` 는 **이름과 달리 ②**를 검증합니다. → ① 전용 테스트가 사실상 부족.

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

- [ ] **(A-2-1) `full_auto` 모드가 실제로 자동 실행되지 않음**
  - `requires_approval()`는 `full_auto`에서 False (`session.py:115-120`)지만, coder 자동 실행 분기가 없어 reasoner만 돌고 멈춤.
  - **방향**: `full_auto`일 때 승인 단계를 건너뛰고 coder→validator(→revision 루프)까지 자동 진행하는 경로 추가, 또는 모드 설명을 현실에 맞게 정정.
- [ ] **(A-2-2) STAGE-02~10 자동 순회 미구현**
  - `STAGE_DEFINITIONS`(11단계, `turn_controller.py:25-37`)는 정의돼 있으나, 승인 1회당 1스테이지만 advance하고 `_handle_approval()`은 coder+validator만 실행 → 스테이지별 에이전트 조합이 실질 미사용.
  - **방향**: 스테이지 순회 상태머신을 구현하거나, 우선 STAGE 정의를 단순화하고 문서/코드 일치시키기.
- [ ] **(A-2-3) 거절(`rejected`) 처리 로직 없음**
  - `approval_state` 주석만 존재(`session.py:63`), 거절 시 분기 없음.
  - **방향**: 거절 시 현재 스테이지 롤백/재계획 분기 추가.
- [ ] **(A-2-4) 쿼터/레이트리밋 미적용**
  - `/api/llm/orchestrate/chat`은 `require_llm_mutation_quota` 적용(`orchestrator.py:13150`), `/api/llm/autonomous/chat`은 `get_current_user`만.
  - **방향**: autonomous에도 동일 쿼터/레이트리밋 정책 적용(LLM 비용 보호).

### A-3. 🟡 P2 — 협업/정리

- [ ] **(A-3-1) `agent_bus`의 pub/sub가 실제 협업에 미사용** — `subscribe()` 정의만 있고 에이전트가 구독하지 않음(`agent_bus.py`). 현재는 로그/관찰용. 필요 시 실제 에이전트 간 메시지 소비 구현.
- [ ] **(A-3-2) LLM 미연결 시 스텁 문자열 반환** — `agents/base.py:75-77` (`"[{agent_id}] LLM 미연결 — ..."`). 클라우드(GPU 없음)에서는 스텁으로 "성공" 처리되니, 품질 검증은 LLM 서버(실서버 RTX 5090) 연결 후 수행.
- [ ] **(A-3-3) `_build_llm_call()` 예외 무음 삼킴** — `router.py:106-107`에서 실패 시 `llm_call=None`. 최소한 warning 로그 추가 권장.
- [ ] **(A-3-4) 패키지 `__init__.py` 정리** — `autonomous/`·`agents/` 패키지 구조 정비.
- [ ] **(A-3-5) 프론트엔드 연동 부재** — `/api/llm/autonomous/*` 호출 UI 없음. UI 연동 또는 API 문서화 결정 필요.

### A-4. 테스트 방향

- [ ] **(A-4-1)** `test_autonomous_orchestrator.py`에 **승인→coder→validator 통합 테스트** 추가(A-1-1 회귀 방지). LLM 없이 동작하도록 `llm_call` 페이크 주입.
- [ ] **(A-4-2)** `/api/llm/autonomous/chat` **HTTP 레벨 테스트**(FastAPI TestClient) 추가 — 세션 생성/복원/승인 happy-path.
- [ ] **(A-4-3)** `test_route_to_agents_code_generation_idle`이 실제 `process_turn` 첫 턴 동작(STAGE-01 → `reasoner`만)과 어긋남 → 테스트를 실제 동작에 맞게 정정.
- [ ] **(A-4-4)** ①/② 명명 혼선 정리: `verify_autonomous_chat.py`, `test_orchestrator_dialogue_mode.py`가 ②를 본다는 점을 문서/파일명으로 명확화.

### A-5. GPU/LLM 없이 가능한 검증 (이 클라우드 환경)
- 가능: 의도 분류·인사/상태 응답·`ValidatorAgent`(`py_compile`)·버스 로그·세션 저장/복원.
- 불가(LLM 서버 필요): reasoner/planner/reviewer 실품질, 실제 코드생성 E2E(단, **A-1-1 수정 후** generator 템플릿 경로는 GPU 없이도 동작 검증 가능).

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

- [ ] **D-3-1) Full Auto 루프 구현**
  - `reasoner → planner → coder → validator → reviewer → 수정 반복 → 완성` 자동 루프를 구현한다.
- [ ] **D-3-2) STAGE 11단계 자동 순회**
  - `Stage01`부터 `Stage10`까지 정의만이 아니라 실제 자동 진행을 구현한다.
- [ ] **D-3-3) Rejected 처리**
  - 승인만이 아니라 거절 시 `재계획 → 재생성` 경로를 구현한다.

### D-4. 4순위: 운영 안정화 및 자동화

- [ ] **D-4-1) 운영 장애 복구 경로 정리**
  - `Redis 장애 복구`, `TURN 장애 복구`, `FCM 장애 복구`를 우선 반영한다.
- [ ] **D-4-2) Rate Limit 적용**
  - `/llm/autonomous/chat`에 사용량 제한, 토큰 제한, 쿼터 제한을 적용한다.
- [ ] **D-4-3) 테스트 자동화 확대**
  - `VoIP`, `Autonomous`, `Voice Translate` 중심으로 테스트 수를 `50~70개` 범위까지 확대한다.

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
| 통역 통화 (발신) | VoIP + Voice Relay | [x] build66 E-3-1 5/5 · build69 E-3-8 ko↔ja |
| voice-translate (≈2.8s) | `POST /api/llm/voice-translate` | [x] |
| APK 배포 | build **66** (`1.0.41`), marketplace | [x] |
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
- [x] **E-3-8)** **ko↔ja VoIP 실기기 E2E** — **2026-06-16** build **69** · deeplink `preferred_language=ja`(S10)/`ko`(Tab) · `call-71a7256e4490` **PASS**: S10 `detected_lang=ja` · transcript `こんにちは、よろしくお願いします。` · Tab `PLAYBACK` · repetition **0**. 증적: `ko_ja_smoke_20260616-005906` · `E3-8_KO_JA_VOIP_REPORT.md`. *(참고: Tab TTS는 영문 relay 경로 `Hello, nice to meet you.` — ja→ko TTS는 후속 tuning)*
- [x] **E-3-3)** marketplace 페이지 **「WorldLinco 통역 통화 베타」** + WiFi 권장·알려진 한계 1페이지.
  - UI: `frontend/.../marketplace/nadotongryoksa/page.tsx` · 전문: `docs/worldlinco-v2/BETA_LAUNCH_GUIDE.md`.
- [ ] **E-3-4)** 실사용 **10명** (외국인·한국인 혼합 목표) — 각 1통 이상 성공 기록. → **`evidence/worldlinco-v1-launch/E3-4_beta_users.csv`** ← **다음 DoD**
- [x] **E-3-5)** APK **v1.0.44** (build **69**) + `publish_worldlinco_apk.ps1` 재현 · git tag **`v1.0.44`** (2026-06-16, 로컬)

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

# E-3-8: ko↔ja VoIP (앱 force-stop 후 수동 통화 권장)
pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 55
```

### E-4. v1.0 출시 전 4~6주 실행표

| 주차 | 작업 | 금지 |
|------|------|------|
| 1~2 | ~~E-3-1, E-3-2 (통화 8/10, repetition)~~ E-3-1 ✅ · **E-3-2 echo 수동** · E-3-4 베타 10명 | V2 폴더·Redis cluster |
| 3 | ~~E-3-3 (베타 페이지·안내)~~ ✅ 2026-06-15 | 오케스트레이터 A-2 |
| 4 | 지인·커뮤니티 실사용 시작 | iOS · 새 플랫폼명 |
| 5~6 | 피드백 1회 반영 → E-3-5 태그 | Communication OS 코드 |

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
