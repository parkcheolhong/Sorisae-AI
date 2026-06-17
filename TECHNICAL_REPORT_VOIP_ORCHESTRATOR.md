# 기술서 — WorldLinco VoIP · Voice Relay Orchestrator · 오케스트레이터

> **최종 갱신:** 2026-06-17  
> **대상 브랜치/커밋:** `gpu-llm-server-awq-20260427` · tag **`v1.0.45`** @ build **74**  
> **현재 운영 APK:** `1.0.45` / **versionCode 74** (`com.parkcheolhong.worldlinco`)  
> **관련 문서:**  
> - `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md` — Voice Relay 파이프라인·파라미터·구조도  
> - `evidence/voip-voice-relay-orchestrator/VERIFICATION_REPORT.md` — 실기기 검증·증적 인덱스  
> - `NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md` — 초기 VoIP 설계안  
> - `docs/checklists/orchestrator-ssot-visual-flow-gap-checklist.md` — PART G Gap 클로저 · DoD-1~6  
> - `docs/ORCHESTRATOR_API_NAMING.md` — ① autonomous vs ② orchestrate/chat 명명  
> - `evidence/worldlinco-v1-launch/E3-8_KO_JA_VOIP_REPORT.md` — E-3-8 strict PASS  
> - `evidence/worldlinco-v1-launch/BUILD73_LAUNCH_STATUS.md` — build 73 SSOT  
> - `AGENTS.md` — 로컬/클라우드 운영 가이드  

---

## 0. 변경 요약 (전체 타임라인)

### 0.1 초기 세션 (P0~P2, `main` / PR #75 계열)

| commit | 내용 |
|--------|------|
| `f127192` | docs: 프론트엔드 기존 테스트 실패/라우트 정보 AGENTS.md 추가 |
| `b1c85aa` | docs: 오케스트레이터 & 월드링코 통번역 분석/방향 체크리스트 |
| `fddfaa2` | fix: CoderAgent 매니페스트 호출, 세션 복원/저장, VoiceResponse.detected_language |
| `4672e67` | feat: VoIP 시그널링 백엔드 P1(REST + WebSocket) — `backend/voip/` |
| `994074f` | feat(voip): P2 Redis 스토어 + pub/sub 릴레이 |
| `7b09d5c` | fix(mobile): WebRTC import/voiceTranslate/tone/props 수정 |

### 0.2 Voice Relay · Silero · build 57~65 (2026-06-14)

| 항목 | 내용 |
|------|------|
| `a989bc9f0` | **WorldLinco VoIP voice relay build 65** — repetition guard, `nadotongryoksa_voip_router`, marketplace APK, 증적·스크립트 |
| build 57~58 | Turn controller 단축, 쌍언어 채팅 UI, `voice_translation` WS 메타(`seq_id`, `utterance_id`, `chunk_index`, `is_final`) |
| build 62~64 | **Silero VAD** 네이티브 모듈, phrase boundary defer, **14s safety cap** |
| build 65 | **반복 환각 가드** (`repetition_hallucination`), TTS 억제·240자 cap, 공백 구분 phrase collapse |

**변경 규모 (build 65 커밋):** 520 files, +47,938 / -2,428 (코드·증적·APK 포함).

### 0.3 v1.0 출시 직전 — build 66 · E-3 자동화 (2026-06-15)

| 항목 | 내용 |
|------|------|
| **APK** | `1.0.41` / **versionCode 66** · Tab+S10 설치 확인 |
| **E-3-1** | WiFi 2대 **5/5 PASS** (`e3_verify_20260615-212949`) — connected + signaling + initiate |
| **누적 DoD** | run A~C **8/10** + build 66 run **5/5** (자동화 게이트 기준) |

**build 66 앱 수정 (`App.tsx`):**
- validation deeplink **자기 보이스 ID 발신 차단** (`VOIP_VALIDATION_AUTO_CALL_REJECTED_SELF`)
- `autoCallVoiceId` **3중 전달** (Modal + ChatRail + Embedded) → Modal만 유지, **중복 initiate** 억제
- `handleStartFriendVoiceCall` **8초 디스패치 디듀프**

**build 66 스크립트 수정 (`voip_manual_call_setup.ps1`, `worldlinco_e3_launch_verify.ps1`):**
- S10 **incoming deeplink auto-accept** (`worldlingo://voip/incoming?...&participant_role=callee`) — UI `받기` 탭 대체
- Tab `call_id` ↔ S10 incoming **매칭** 후 수락 (stale call 혼선 방지)
- `CalleeVoiceId=nado-000001` / `CallerVoiceId=nado-000226` 고정 (Tab→S10)
- pre-call **lightweight hangup** + API stale end (로그인 가능 시)

**잔여 (E-3-2):** ~~Tab 스피커 echo~~ **2026-06-15 완료** — `e3-2_echo_20260615-232900` (repetition 0).

### 0.4 build 67 · 50개국어 정합 · ko↔ja (2026-06-15)

| 항목 | 내용 |
|------|------|
| **APK** | `1.0.42` / **versionCode 67** — 친구 목록 deeplink 재오픈 수정 |
| **백엔드** | `SUPPORTED_LANGUAGES` **50개** (모바일 LANGS 동기화) · `devanalysis114-backend` restart |
| **E-3-6** | `50lang_audit_20260615-235805` — local/remote **50/50** aligned |
| **E-3-7** | ko→ja / ja→ko `voice-translate` API **PASS** |
| **E-3-8** | ko↔ja VoIP E2E — build **69** ja STT + playback · build **73** strict ja→ko (§0.6) |

증적: `evidence/worldlinco-v1-launch/50LANG_ALIGNMENT_REPORT.md` · `BUILD67_LAUNCH_STATUS.md`

### 0.5 build 69 · E-3-8 ko↔ja VoIP (1차 PASS, 2026-06-16)

| 항목 | 내용 |
|------|------|
| **APK** | `1.0.44` / **versionCode 69** — deeplink `preferred_language` · validation `force=1` · Tab+S10 설치 |
| **E-3-8** | **PASS** `call-71a7256e4490` — S10 `detected_lang=ja` · `こんにちは、よろしくお願いします。` · Tab `VOIP_VOICE_RELAY_PLAYBACK` · repetition **0** |
| **프로필** | smoke 전 deeplink: S10 `ja` · Tab `ko` |
| **call_id** | `-SetupOnly` + 8s stable + logcat filter by call_id |
| **한계 (해소됨)** | Tab TTS `Hello, nice to meet you.` (`target_lang=en`) → **build 73 strict PASS** (§0.6) |

**build 69 앱:** `parseAppEntryDeepLink` → `preferred_language` · `VOIP_DEEPLINK_PREFERRED_LANGUAGE_APPLIED`  
**build 69 스크립트:** `worldlinco_ko_ja_voip_smoke.ps1` · `voip_manual_call_setup.ps1` (`-SetupOnly`, `-SetPreferredLanguage`)

증적: `ko_ja_smoke_20260616-005906` · `E3-8_KO_JA_VOIP_REPORT.md` · `BUILD69_LAUNCH_STATUS.md`

### 0.6 build 71~73 · ja→ko relay pairing fix · E-3-8 strict PASS (2026-06-16)

| 항목 | 내용 |
|------|------|
| **APK** | `1.0.45` / **versionCode 73** · Tab+S10 marketplace 설치 확인 |
| **E-3-8 strict** | **PASS** `call-0f44540d27f6` — S10 `ja→ko` · Tab 한국어 TTS `안녕하세요, 잘 부탁드립니다.` · repetition **0** |
| **Backend accept** | `display_language=ko` (invite hint 우선, caller DB `en` 무시) |
| **Tab caller pair** | initiate `display_language=ja` · segment `target_lang=ja` |
| **S10 callee pair** | segment `source_lang=ja` · **`target_lang=ko`** · `VOIP_VOICE_RELAY_SENT` |

**근본 원인 (build 71 FAIL `target_lang=en`):**

1. **Backend** `_build_active_call_response` (callee `/accept`): caller DB `preferred_language`가 initiate invite `display_language=ko`보다 우선 → accept API가 `en` 반환.
2. **Mobile** deeplink auto-accept 시 accept API merge가 invite/deeplink `ko`를 덮어씀 → `voipActiveProfile.preferredLanguage=en` → `effectiveVoipTargetLang=en`.
3. **Tab caller** validation auto-call이 `callee_preferred_language` 미전달 → initiate `display_language`가 친구 DB `en` fallback.

**수정 파일:**

| 파일 | 변경 |
|------|------|
| `backend/marketplace/nadotongryoksa_voip_router.py` | callee accept: `_resolve_call_language_hint(invite, db)` 순서 · accept 로그 `display_language` |
| `apps/mobile-nadotongryoksa/App.tsx` | `resolveVoipRemoteLanguageHint` · accept merge · `callee_preferred_language` deeplink |
| `scripts/voip_manual_call_setup.ps1` | incoming `display_language=$CallerPreferredLanguage` · validation `callee_preferred_language` |
| `scripts/worldlinco_ko_ja_voip_smoke.ps1` | stable wait timeout 45s→**90s** |
| `backend/tests/test_nadotongryoksa_friends_and_voip_contract.py` | `test_voip_accept_prefers_invite_caller_language_over_stale_db` |

**실기기 로그 (strict PASS):**

```
S10 VOIP_VOICE_TRANSLATE_RESULT  source_lang=ja target_lang=ko detected_lang=ja
S10 VOIP_VOICE_RELAY_SENT        translated_text=안녕하세요, 잘 부탁드립니다.
Tab VOIP_VOICE_RELAY_PLAYBACK    target_lang=ko translated_text=안녕하세요, 잘 부탁드립니다.
Backend [VoIP] Call accepted     call_id=call-0f44540d27f6 display_language=ko
```

증적: `ko_ja_smoke_20260616-023813/` · `E3-8_KO_JA_VOIP_REPORT.md` · `BUILD73_LAUNCH_STATUS.md`

### 0.7 build 74 · relay latency trim · marketplace version SSOT (2026-06-16)

| 항목 | 내용 |
|------|------|
| **APK** | `1.0.45` / **versionCode 74** — turn/VAD/Silero 타이밍 단축 |
| **Marketplace** | `nadotongryoksa-v1.manifest.json` + `GET /api/marketplace/apk/worldlinco/manifest` · UI 동적 버전 표기 |
| **Latency** | `playbackMinMs` 2800→**2200** · `silenceFlushMs` 1900→**1500** · Silero `minSegmentMs` 3200→**2800** · `remoteListenHoldMs` 2500→**2100** |
| **E-3-4** | **재개** — backend **`v1.0.46`** 프로필 API + build 74 APK |

**LTE 베타 보안 (v1.0 현재):**

| 항목 | 상태 |
|------|------|
| 앱 VoIP/WSS | `wss://metanova1004.com` TLS only (앱 WiFi-only 차단 **없음**) |
| APK 배포 | 로그인 + HMAC **7일 test_token** (`/apk/test-token`) |
| API | JWT Bearer · voice-translate rate limit (nginx/backend) |
| v1.1 추가 | LTE 전용 QA 매트릭스 · FCM · TURN short-lived token · 데이터 사용량 UI |

### 0.8 v1.0.46 · signup profile API (2026-06-16)

| 항목 | 내용 |
|------|------|
| **Tag** | **`v1.0.46`** @ `88adda287` (GitHub `gpu-llm-server-awq-20260427`) |
| **APK** | build **74** 유지 (`v1.0.45`) — 모바일 재빌드 불필요 |
| **API** | `POST /api/auth/signup` · `GET/PATCH /api/auth/me` — `preferred_language` + `country_code` |
| **Chat** | 1:1 방 생성 시 `default_source_lang` / `default_target_lang` = 양쪽 프로필 |
| **VoIP** | DB 프로필 + 기존 invite/deeplink 언어 힌트 (build 73+ strict 유지) |

### 0.9 관리자 멀티 에이전트 오케스트레이터 (①) — PART A/D-3 (2026-06-16)

| 항목 | 내용 |
|------|------|
| **모듈** | `backend/orchestrator/autonomous/` — `turn_controller` · `session` · `agents/*` |
| **API** | `POST /api/llm/autonomous/chat` · `GET /api/llm/autonomous/session/{id}` |
| **A-2** | `full_auto` coder→validator 자동 · `rejection` 재계획 · `require_llm_mutation_quota` |
| **STAGE** | full_auto 턴당 `AUTONOMOUS_MAX_STAGES_PER_TURN` (기본 **11**) 순회 |
| **GPU A-3-2** | vLLM **32B AWQ** · `verify_autonomous_llm_gpu.py` 3-probe **`overall_passed`** · `evidence/autonomous-a32-gpu-verify/` |
| **vLLM ops** | `gpu-llm-server/docker-compose.vllm-32b.yml` · `scripts/start_vllm_rtx5090_32b.ps1` |
| **Admin ops** | `scripts/reset_fixed_admin_password.py` · 설정 패널 관리자 비밀번호 변경 UI |
| **Admin UI** | `/admin/llm` → `AutonomousOrchestratorPanel` · proxy `app/api/llm/autonomous/*` |
| **명명 SSOT** | `docs/ORCHESTRATOR_API_NAMING.md` (① vs ② vs VoIP relay ③) |
| **테스트** | `test_autonomous_orchestrator.py` **31** · `test_autonomous_orchestrator_http.py` **8** |

**②와 구분:** 관리자 기존 대화형 패널 = `POST /api/llm/orchestrate/chat` (`use-orchestrator-chat.ts`). ①은 승인·STAGE·멀티 에이전트 파이프라인 전용.

### 0.10 Autonomous TurnController 11단계 SSOT · 4-probe 실행 완료 (2026-06-16)

| 항목 | 내용 |
|------|------|
| **SSOT 엔진** | `TurnController` — `stage_definitions.py` · `stage_commands.py` · `stage_coder_scope.py` |
| **표면 어댑터** | `surface_adapter.run_autonomous_surface_chat` — Admin `orchestrate/chat` · Marketplace `customer-orchestrate/chat` **동일 코어** |
| **단계 패치** | 단계당 2~9파일 (`get_stage_patch_scope`) — 기존 파일 필터 제거로 107파일 폭주 방지 |
| **4.5단계** | reviewer → coder fix loop · validator 구조검증(기존 main.py 인정) · reviewer error 시 중단하지 않음 |
| **프로브** | `scripts/run_11stage_orchestrator_probe.py` — `--mode stub|live|http` · `--admin` · `--marketplace` |

**실행 결과 (2026-06-16, 태스크: FastAPI 헬스체크 API):**

| Probe | 결과 | session_id | 증적 |
|-------|------|------------|------|
| stub | **11/11** completed | `064cf9f886464b72` | `evidence/orchestrator-11stage-probe-20260616-125507/` |
| live (vLLM :8008) | **11/11** completed | `b5e16dfa41f94638` | `evidence/orchestrator-11stage-probe-20260616-125528/` |
| http marketplace | **11/11** · stage_run sync OK | `73995f7646e94feb` | `evidence/orchestrator-11stage-probe-20260616-130503/` |
| http admin | **11/11** · `orchestrator_core=autonomous_turn_controller` | `91c715c20e3c4bed` | `evidence/orchestrator-11stage-probe-20260616-131740/` |

**재현:**

```powershell
.\scripts\restart_backend_8000.ps1
python scripts/run_11stage_orchestrator_probe.py --mode stub
$env:OLLAMA_BASE="http://127.0.0.1:8008/v1"; python scripts/run_11stage_orchestrator_probe.py --mode live
python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace --base-url http://127.0.0.1:8000
python scripts/run_11stage_orchestrator_probe.py --mode http --admin --base-url http://127.0.0.1:8000
```

**배포:** `docker compose build backend && docker compose up -d backend` (`devanalysis114-backend` · `./backend` 볼륨 마운트)

### 0.11 Live Flow Rail · Decision Panel · Playwright 계약 (2026-06-17)

| 항목 | 내용 |
|------|------|
| **Live Flow Rail** | `frontend/frontend/shared/orchestrator-live-flow-rail.tsx` — 11 STAGE 레일 · intent/cmd 배지 · 에이전트 타임라인 · `data-testid=orchestrator-live-flow-rail` |
| **Snapshot 빌더** | `frontend/frontend/lib/orchestrator-live-flow.ts` — `diagnostics` + `stage_run` → `OrchestratorLiveFlowSnapshot` |
| **Decision Panel** | `frontend/frontend/shared/orchestrator-decision-card.tsx` — 제안 카드 · 승인 게이트 · `orchestrator-decision-*` / `orchestrator-approval-*` testids |
| **마운트** | Admin `/admin/llm` · Marketplace `/marketplace/orchestrator` — `use-orchestrator-chat.ts` `liveFlowSnapshot` |
| **HTTP SSOT** | Admin `POST /api/llm/orchestrate/chat` · Marketplace `customer-orchestrate/chat` → `run_autonomous_surface_chat` (G-1) |
| **Playwright** | `tests/orchestrator-live-flow-rail.playwright.spec.ts` — **5/5 passed** · 전용 dev **3025** · mock auth |
| **Discuss UI (G-4-2)** | `OrchestratorDiscussBanner` · StageCardPanel discuss 오버레이 · `resolveDiscussArchId` rail↔ARCH sync · `orchestrator-discuss-*` testids |
| **Discuss 검증 (G-4-3)** | probe `discuss4_assertions` (stub/http + sync-inline) · Playwright `e2e:orchestrator-discuss4` (ARCH-004 running · ARCH-005 pending) |
| **실행** | 루트 `npm run e2e:orchestrator-live-flow-rail` · `npm run e2e:orchestrator-discuss4` · 포트 충돌 시 `:fresh` |

**Gap 체크리스트:** `docs/checklists/orchestrator-ssot-visual-flow-gap-checklist.md` (PART G-0~G-5 · DoD-1~6)

### 0.12 PART G Gap 클로저 · DoD-1~6 · Edge TTS · :8000 SSOT (2026-06-17)

> **마스터 Gap 체크리스트:** `docs/checklists/orchestrator-ssot-visual-flow-gap-checklist.md`  
> **증적:** `evidence/orchestrator-visual-flow-20260617/` · `evidence/orchestrator-11stage-probe-20260617-*/`

#### 0.12.1 아키텍처 요약

| 계층 | SSOT | 비고 |
|------|------|------|
| **① 코어** | `TurnController` (`backend/orchestrator/autonomous/`) | design · execute · discuss · approval |
| **표면 어댑터** | `surface_adapter.run_autonomous_surface_chat` | Admin `surface=admin` · Market `surface=marketplace` |
| **HTTP 진입** | `POST /api/llm/orchestrate/chat` · `POST /api/marketplace/customer-orchestrate/chat` | `manual_*` → ① · lightweight/reverse_question → ② fallback |
| **stage_run 동기화** | `stage_run_sync.py` | discuss 턴 `current_stage_id` 전진 금지 (ARCH-004 고정) |
| **프론트 SSOT** | `use-orchestrator-chat.ts` · `orchestrator-live-flow.ts` | diagnostics → Live Flow Rail · Decision Panel |
| **음성** | `orchestrator-voice-entry.ts` · `useOrchestratorVoiceStt` | STT → 동일 `message` · `voice-stt`/`voice-entry` tags |
| **TTS** | `orchestrator-speech.ts` → `/api/llm/voice/synthesize` | Edge neural 우선 · browser `speechSynthesis` fallback |
| **백엔드 포트** | **`:8000` SSOT** | `devanalysis114-backend` · `scripts/restart_backend_8000.ps1` |

#### 0.12.2 PART G 구현 완료 항목

| Part | 내용 | 핵심 파일 |
|------|------|-----------|
| **G-0** | Live Flow Rail · Decision Panel · discuss 배너 · progress substeps | `shared/orchestrator-live-flow-rail.tsx` · `orchestrator-decision-card.tsx` |
| **G-1** | HTTP 채팅 → ① TurnController | `backend/llm/orchestrator.py` · `customer_orchestrate_router.py` |
| **G-2** | discuss intent · `/ask`/`/search` · technology_recommendations mapper | `turn_controller.py` · `autonomous/advisory.py` |
| **G-3** | 음성 STT SSOT · voice badge · Edge TTS | `orchestrator-voice-entry.ts` · `voice_gateway.py` · `orchestrator-speech.ts` |
| **G-4** | discuss-4 ↔ stage_run ARCH-004 고정 | `stage_run_sync.py` · probe · Playwright discuss4 |
| **G-5** | Admin workbench · miniConsoleLayout · API URL 단일화 | `admin/llm/page.tsx` · `orchestrator-chat-endpoints.ts` |

**G-5-3 API 표면 축소:**

| 클라이언트 | 엔드포인트 | 파일 |
|------------|-----------|------|
| Admin | `POST /api/llm/orchestrate/chat` | `postAdminOrchestratorChat` |
| Marketplace | `POST /api/marketplace/customer-orchestrate/chat` | `postCustomerOrchestratorChat` |
| 디버그 | `/api/llm/autonomous/chat` | 내부·디버그 전용 (응답 헤더 `X-Orchestrator-Core`) |

#### 0.12.3 Definition of Done (PART G-6)

| DoD | 상태 | 검증 |
|-----|------|------|
| **DoD-1** | ✅ | Admin·Market `diagnostics.orchestrator_core=autonomous_turn_controller` · `test_orchestrator_dialogue_mode_autonomous.py` |
| **DoD-2** | ✅ | stub **11/11** · **live 11/11** (`064143`) · http admin/market **`orchestrator_core` 13/13** (`063700`/`063618`) |
| **DoD-3** | ✅ | discuss-4 ARCH-004 고정 · probe stub/sync-inline · `e2e:orchestrator-discuss4` |
| **DoD-4** | ✅ | Redis discuss → DecisionCard → execute → live rail passed · `e2e:orchestrator-dod4` |
| **DoD-5** | ✅ | Admin+Market 음성 시나리오 · `e2e:orchestrator-dod5` **3/3** |
| **DoD-6** | ✅ | `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART G 링크 · A-6 gap 정리 |

**DoD-2 HTTP probe (2026-06-17, `:8000` after `docker restart devanalysis114-backend`):**

| Probe | orchestrator_core | stages | 증적 |
|-------|-------------------|--------|------|
| stub | 11/11 | 11/11 | `evidence/orchestrator-11stage-probe-20260617-062243/` |
| **live** (vLLM :8008) | **11/11** | 11/11 | `...064143/` · `llm_connected=true` · ~91s |
| http --admin | **13/13 PASS** | 11/11 | `...063700/` (discuss-4 stage_run skip) |
| http --marketplace | **13/13 PASS** | 11/11 | `...063618/` (discuss-4 **ARCH-004** ✅) |

#### 0.12.4 Edge Neural TTS (로봇 읽기 → 자연스러운 안내)

**문제:** 브라우저 `speechSynthesis`만 사용 시 Windows SAPI 기계음.

**해결:**

| 구성요소 | 내용 |
|----------|------|
| **백엔드** | `POST /api/llm/voice/synthesize` · `_synthesize_edge_tts()` · voice `ko-KR-SunHiNeural` · rate `-6%` |
| **의존성** | `edge-tts>=7.0.0` (`requirements.txt`) · Docker: `pip install edge-tts` |
| **프록시** | `frontend/app/api/llm/voice/synthesize/route.ts` → `BACKEND_PROXY_TARGET` (:8000) |
| **프론트** | `speakOrchestratorReply` — server MP3 우선 → `speechSynthesis` fallback |
| **humanize** | `humanizeOrchestratorSpeech()` — 이모지·마크다운 제거 · `4단계`→`사 단계` · `Redis`→`레디스` |
| **확인** | `tts_delivery=server_audio` · `audio_format=audio/mpeg` |

**보조 스크립트:** `scripts/edge_tts_speak.py` (`VOICE_TTS_COMMAND`용)

**환경 변수:**

| 변수 | 기본 | 설명 |
|------|------|------|
| `VOICE_EDGE_TTS_ENABLED` | `1` | `0`/`false` 시 Edge TTS 비활성 |
| `VOICE_EDGE_TTS_VOICE` | `ko-KR-SunHiNeural` | Edge neural voice |
| `VOICE_EDGE_TTS_RATE` | `-6%` | 발화 속도 |

#### 0.12.5 시각 흐름 증적 (G-0-4-5 · G-3-3)

`npm run e2e:orchestrator-visual-evidence` → `evidence/orchestrator-visual-flow-20260617/`:

| 파일 | Surface | 설명 |
|------|---------|------|
| `01-admin-workbench-live-flow.png` | Admin `/admin/llm` | Workbench + Live Flow Rail |
| `02-marketplace-three-track-discuss.png` | Marketplace | 3-track + discuss DecisionCard |
| `03-admin-voice-live-rail.png` | Admin | 음성 STT → voice badge (G-3-3-2) |
| `04-marketplace-voice-live-rail.png` | Marketplace | 음성 STT → DecisionCard (G-3-3-3) |

#### 0.12.7 discuss-4 stage_run 버그 수정 (2026-06-17)

**증상:** execute-4 완료 후 `current_stage_id=ARCH-0045` 상태에서 discuss-4 → `ARCH-0045` 유지 (기대: **ARCH-004**).

**원인:** `_sync_discuss_substeps`가 ARCH-004가 이미 `passed`이면 `current_stage_id` 갱신을 건너뜀.

**수정:** `backend/orchestrator/autonomous/stage_run_sync.py` — discuss 턴은 passed ARCH에도 Q&A 오버레이 + `current_stage_id` **항상** 고정.

**검증:** `test_sync_discuss_turn_pins_arch004_after_stage_passed` · http marketplace probe `063618` discuss4 **PASS** · `e2e:orchestrator-discuss4` 2/2.

#### 0.12.6 백엔드 포트 SSOT (:8000)

로컬·프론트 프록시·HTTP probe는 **항상 `:8000`**. Windows `8001` uvicorn은 `WinError 10013` 바인드 거부 가능 → **사용하지 않음**.

| 설정 | 값 |
|------|-----|
| Docker | `devanalysis114-backend` · `127.0.0.1:8000:8000` |
| `.env` | `LOCAL_API_BASE_URL=http://127.0.0.1:8000` |
| `frontend/frontend/.env.local` | `BACKEND_PROXY_TARGET` · `LOCAL_API_BASE_URL` → `:8000` |
| Playwright | `playwright.config.ts` webServer env 동일 |
| 재기동 | `.\scripts\restart_backend_8000.ps1` |

**재현 (AGENTS.md § Backend port SSOT):**

```powershell
.\scripts\restart_backend_8000.ps1
python scripts/run_11stage_orchestrator_probe.py --mode stub
$env:PROBE_LOGIN_EMAIL="119cash@naver.com"
$env:PROBE_LOGIN_PASSWORD='your-password'   # PowerShell: # 등 특수문자 → 작은따옴표
python scripts/run_11stage_orchestrator_probe.py --mode live
```

#### 0.12.8 Golden probe JWT · pytest-asyncio (2026-06-17)

| 항목 | 내용 |
|------|------|
| **Golden G2/G3 JWT** | `run_11stage_orchestrator_probe.py` — live/stub에서도 `PROBE_LOGIN_*` / `.runtime/secrets` 로그인 · 실패 시 `golden_login` JSON 기록 |
| **pytest-asyncio** | `requirements.txt` + `pyproject.toml` `asyncio_mode=auto` — async orchestrator 테스트 42 passed |

**검증:** stub probe `065043` — `voip_initiate=PASS` · `G3_admin_settings=PASS` · `golden_login.source=login`

#### 0.12.9 G-0-3-3 네이티브 SSE / WebSocket (2026-06-17)

| 항목 | Admin | Marketplace |
|------|-------|-------------|
| **SSE** | `GET /api/llm/orchestrate/stream/{run_id}?token=` | `GET /api/marketplace/customer-orchestrate/progress/stream/{run_id}?token=` |
| **WebSocket** | `WS /api/llm/orchestrate/progress/ws/{run_id}?token=` | `WS /api/marketplace/customer-orchestrate/progress/ws/{run_id}?token=` |
| **Poll 폴백** | `GET /api/llm/orchestrate/progress/{run_id}` | `GET .../customer-orchestrate/progress/{run_id}` |

- **백엔드:** `backend/orchestrator/autonomous/progress_stream.py` — `progress` · `heartbeat` · `done` SSE frames
- **프론트:** `use-orchestrator-live-progress.ts` — SSE 우선 · 실패 시 poll · `OrchestratorFlowSection` SSE/WS/Poll 배지
- **인증:** `get_current_user_flexible` — Bearer 또는 `?token=` (EventSource 호환)

**테스트:** `backend/tests/test_autonomous_progress_stream.py` · `node tests/orchestrator-live-progress-stream.test.mjs`

```powershell
python scripts/run_11stage_orchestrator_probe.py --mode http --admin --base-url http://127.0.0.1:8000
python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace --base-url http://127.0.0.1:8000
cd frontend/frontend
npm run e2e:orchestrator-dod4
npm run e2e:orchestrator-dod5
npm run e2e:orchestrator-visual-evidence
node tests/orchestrator-speech.test.mjs
```

### 0.13 회원가입·친구 OTP + LTE/5G 통신 진단 (2026-06-17)

| 항목 | 내용 |
|------|------|
| **회원가입 이메일 OTP** | `POST /api/auth/signup/request-code` → `/confirm` · legacy `/signup` → **428** (`ALLOW_UNVERIFIED_SIGNUP=1` dev 우회) |
| **회원가입 전화 OTP** | `verificationChannel=phone` + `phone_number` (E.164) · `backend/services/sms_dispatch.py` (Twilio `TWILIO_*` 또는 dev-log) · `User.phone_number` |
| **프로필 필수** | `preferred_language` + `country_code` (국기) — OTP verify 단계에서도 UI 유지 · confirm 시 최종값 merge |
| **친구 수기 OTP** | `POST /api/friends/invites/request-code` → `/confirm` · 이메일/전화 채널 |
| **LTE/5G 진단** | `@react-native-community/netinfo` · `NetworkTestBanner` · `VOIP_NETWORK_SNAPSHOT` / `NETWORK_TRANSPORT_CHANGED` probe |
| **Audit** | `call_initiated.metadata.client_network` — transport · cellular_generation · carrier |
| **Health** | `GET /api/v1/voip/health` → `network_test_matrix` (wifi_lte · lte_lte · min 2 runs) |
| **스크립트** | `scripts/worldlinco_lte_matrix_verify.ps1` — health + audit `client_network` 조회 |
| **테스트** | `test_signup_email_otp.py` (email+phone) · `test_sms_dispatch.py` · `test_voip_backend_consistency` matrix |

**실기기 LTE 매트릭스 (D-0-5 미완 — 증적 필요):**

1. A단말: WiFi OFF · LTE/5G ON → 배너 **셀룰러** 확인  
2. B단말: WiFi ON (또는 반대 조합)  
3. 보이스톡 initiate → `GET /api/v1/voip/calls/{id}/audit` → `metadata.client_network.transport=cellular`  
4. `WiFi↔WiFi` · `WiFi↔LTE` · `LTE↔LTE` 각 **2회+**

```powershell
.\scripts\worldlinco_lte_matrix_verify.ps1 -HealthOnly
$env:WORLDLINGO_TEST_TOKEN='<jwt>'
.\scripts\worldlinco_lte_matrix_verify.ps1 -CallId call-xxxxxxxxxxxx
```

**APK:** NetInfo 네이티브 모듈 추가 → **dev client / EAS rebuild 필수**

**베타 UX 원칙:** 테스터에게 “미완성 베타” 인상을 주지 않음 — 연결 배너 **안심 톤** · OTP **발송 완료** 문구 · QA/LTE 힌트는 디버그 모드(`__DEV__` / `EXPO_PUBLIC_AUTH_DEBUG_MARKER=1`)에서만 표시 · SMTP/Twilio 설정 시 실제 발송.

---

## 1. 개발 환경 구성

상세 운영 절차는 `AGENTS.md` 참조.

| 서비스 | 포트 | 비고 |
|--------|------|------|
| Backend (FastAPI) | 8000 | `uvicorn backend.main:app` 또는 Docker `devanalysis114-backend` |
| Marketplace FE | 3000 | Next.js |
| Admin FE | 3005 | Next.js |
| Postgres | 5432 | |
| Redis | **6380** (host) → 6379 (container) | |
| nginx (운영) | 80/443 | `metanova1004.com` |

**실서버:** RTX 5090, Docker Compose 전체 스택 가동. APK는 `uploads/marketplace_local/apk/` → 컨테이너 `/app/uploads` 볼륨 마운트.

---

## 2. 자율 오케스트레이터 (①) · 음성 P0

> 체크리스트: `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART A · D-3 · D-4-2

### 2.1 P0 — A-1 (완료)

| ID | 파일 | 내용 |
|----|------|------|
| A-1-1 | `agents/coder.py` | `_compat_manifest_for_request` 시그니처 · `written_files` 병합 |
| A-1-2 | `session.py` | `load()` — stages · agent_results · pending_approval_data · model_routes |
| A-1-3 | `turn_controller.py` | 모든 턴 분기 `session.save()` |

### 2.2 P1 — A-2 / D-3 (2026-06-16)

| ID | 상태 | 구현 |
|----|------|------|
| A-2-1 | ✅ | `full_auto` → `_execute_code_pipeline()` (승인 생략) |
| A-2-2 | ✅ | full_auto STAGE loop · 기본 `AUTONOMOUS_MAX_STAGES_PER_TURN=11` · env 조절 |
| A-2-3 | ✅ | intent `rejection` · `_handle_rejection()` |
| A-2-4 | ✅ | `router.py` · `Depends(require_llm_mutation_quota)` |

### 2.3 P2 — A-3 (2026-06-16)

| ID | 상태 | 구현 |
|----|------|------|
| A-3-3 | ✅ | LLM setup failure → `logger.warning` |
| A-3-4 | ✅ | `autonomous/__init__.py` · `agents/__init__.py` |
| A-3-5 | ✅ | `components/ui/AutonomousOrchestratorPanel.tsx` · `/admin/llm` |
| A-3-1 | ✅ | `_run_agent_with_bus` · request/response/handoff · inbox |
| A-3-2 | ✅ | A뇌 live LLM · `llm_connected` · **32B AWQ 3-probe** (`A32_GPU_VERIFY_20260615-220314.json`) |

**A-3-2 GPU 검증 (2026-06-16):**

| Probe | 결과 |
|-------|------|
| turn_controller | reasoner/planner `success` · reviewer `needs_revision` |
| http_testclient | subprocess 격리 · reasoner `success` |
| http_api | Admin login + `/api/llm/autonomous/chat` · `llm_connected: true` |
| vLLM | `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` · `profile_aligned_32b_awq: true` |

재현: `scripts/verify_autonomous_llm_gpu.py` · 보고서 `evidence/autonomous-a32-gpu-verify/A32_GPU_VERIFY_REPORT.md`

### 2.4 테스트 — A-4 (2026-06-16)

| 파일 | tests | 범위 |
|------|-------|------|
| `test_autonomous_orchestrator.py` | 35 | TurnController · session · validator · bus · stub · STAGE cap |
| `test_autonomous_orchestrator_http.py` | 9 | HTTP greeting · semi_auto · approval · full_auto · rejection · llm_connected |
| `test_model_config_live_routes.py` | 3 | live vLLM model route fallback |
| `test_voice_voip_d4_extended.py` | 32 | VoIP relay · call mode · signaling helpers |
| `test_voice_translate_stt.py` | 18 | STT energy · duration · language hint |
| `test_voice_gateway_schema.py` | 2 | B-3-1 `detected_language` |

실행:

```powershell
python -m pytest backend/tests/test_autonomous_orchestrator.py backend/tests/test_autonomous_orchestrator_http.py backend/tests/test_voice_voip_d4_extended.py backend/tests/test_voice_translate_stt.py -p asyncio --asyncio-mode=auto -q
```

### 2.5 B-3-1 VoiceResponse.detected_language

- `backend/llm/voice_gateway.py` — Pydantic 필드 → 모바일 자동 언어전환

---

## 3. VoIP 백엔드 — P1/P2 (`backend/voip/`)

초기 시그널링 스캐폴딩. 인메모리 또는 Redis(`VOIP_REDIS_URL`) 멀티 워커.

| REST/WS | 경로 |
|---------|------|
| initiate | `POST /api/v1/voip/calls/initiate` |
| audit | `GET /api/v1/voip/calls/{call_id}/audit` |
| end | `POST /api/v1/voip/calls/{call_id}/end` |
| signaling | `WS /api/v1/voip/ws/{call_id}?token=&role=` |

**검증:** `test_voip_signaling.py` (5 passed), `test_voip_signaling_redis.py` (2 passed, Redis 필요).

> **운영 주 경로:** 모바일 WorldLinco는 아래 §4 **`nadotongryoksa_voip_router`** (`/api/v1/voip/signal`, `/presence`)를 사용. P1 `backend/voip/`와 병존.

---

## 4. VoIP 백엔드 — Marketplace Router (운영)

**파일:** `backend/marketplace/nadotongryoksa_voip_router.py`  
**등록:** `backend/main.py` → `prefix="/api"` + router `prefix="/v1/voip"`

### 4.1 REST 엔드포인트

| 메서드 | 경로 | 역할 |
|--------|------|------|
| GET | `/api/v1/voip/identity` | 발신자 voice_id 등 VoIP 신원 |
| POST | `/api/v1/voip/calls/initiate` | 통화 개시, signaling URL·TURN·participant_role 반환 |
| GET | `/api/v1/voip/calls/pending/incoming` | 착신 대기 통화 조회 |
| POST | `/api/v1/voip/calls/{call_id}/accept` | 수락 |
| POST | `/api/v1/voip/calls/{call_id}/end` | 종료 |
| GET | `/api/v1/voip/calls/{call_id}` | 통화 상태 |
| GET | `/api/v1/voip/calls/{call_id}/mode-audit` | call-mode 감사 이벤트 |
| GET | `/api/v1/voip/calls/missed/recent` | 부재중 최근 목록 |
| GET | `/api/v1/voip/health` | VoIP 서브시스템 헬스 |

### 4.2 WebSocket

| 경로 | 역할 |
|------|------|
| `WS /api/v1/voip/presence` | 온라인·FCM 연동 presence |
| `WS /api/v1/voip/signal` | WebRTC offer/answer/candidate + **`voice_translation`** 릴레이 |

**nginx:** `location ^~ /api/v1/voip/presence`, `location ^~ /api/v1/voip/signal` — WebSocket 업그레이드 프록시.

### 4.3 Call Mode · 감사

- **모드:** `pstn_assist` | `voip_full_auto` (`VALID_CALL_MODES`)
- **스키마:** `backend/marketplace/call_mode_schema.py`
- **서비스:** `backend/marketplace/services/call_mode_audit_service.py`
- initiate 응답에 `requested_mode`, `resolved_mode`, `auto_relay_applied` 포함.

### 4.4 FCM / PSTN (부분 구현)

- FCM: `_send_incoming_call_push_invite`, service account / legacy key 경로
- PSTN: `_is_pstn_gateway_configured()`, `phone_dialer_required` 폴백
- **테스트:** `test_voip_presence_push.py`, `test_voip_pstn.py`, `test_voip_turn_tokens.py`

### 4.5 voice_translation WS 릴레이 (서버)

- 클라이언트 → signal WS → `_build_voice_translation_relay_payload` → 상대에게 전달
- 서버측 필터: `_collapse_voice_relay_text`, `_should_reject_voice_translation_relay` (동일언어 identity 번역 거부)
- **오디오 base64는 WS에 실리지 않음** — 텍스트 메타만 relay (모바일 `device_speech` TTS)

---

## 5. 음성 통역 API — `POST /api/llm/voice-translate`

**상태: ✅ 구현 완료** (구 §7.4 “미구현” → **폐기**)

**파일:** `backend/llm/router.py` (`tags=["mobile-public"]`)

### 요청
```json
{
  "audio_base64": "...",
  "from_lang": "ko",
  "to_lang": "en",
  "language": "auto",
  "region_hint": null,
  "transcript": null
}
```

### 처리
1. **STT:** `_transcribe_mobile_voice_audio` (faster-whisper, `language_hint` / auto)
2. **언어쌍 보정:** detected_lang ≠ client from → relay 방향 자동 스왑
3. **필터:** gibberish transcript/translation → 422
4. **번역:** `NadoTranslator`
5. **응답:** `original_text`, `translated`, `from`, `to`, `detected_language`, `engine`, (옵션) `audio_*`

### 최소 세그먼트
- 백엔드 ffmpeg 정규화 후 최소 길이 검사 (`VOICE_RELAY_MIN_SEGMENT_MS` 등, translator 연동)
- 짧은/무음 → 422 `"음성이 감지되지 않았습니다..."`

### 테스트
- `backend/tests/test_voip_voice_translation_meta.py`
- `backend/tests/test_voice_translate_stt.py`
- `backend/tests/test_voip_backend_consistency.py`

---

## 6. 모바일 — Voice Relay Auto Orchestrator

WebRTC **원음 통화**와 **통역 릴레이**를 분리. Phase 1 = **half-duplex turn 교대**.

### 6.1 모듈 구조

| 레이어 | 파일 |
|--------|------|
| 화면·파이프라인 | `apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx` |
| VAD·STT 게이트 | `src/features/voip-voice-relay/voiceRelayOrchestrator.ts` |
| Silero 경계 | `src/features/voip-voice-relay/voiceRelaySegmentBoundary.ts` |
| Turn / 언어쌍 | `src/features/voip-voice-relay/voiceRelayTurnController.ts` |
| 파일 RMS | `src/features/voip-voice-relay/voiceRelayAudioMetrics.ts` |
| 재생 큐 | `src/features/voip-voice-relay/voiceRelayPlaybackQueue.ts` |
| Silero JS 브리지 | `src/native/voiceRelaySileroVad.ts` |
| **Silero Native** | `android/.../voip/VoiceRelaySileroVadModule.kt` |
| WS 클라이언트 | `src/services/voipCallClient.ts` |
| HTTP STT/번역 | `src/api/translate.ts` → `voiceTranslate()` |
| Signaling URL | `src/utils/voipSignalingUrl.ts` |
| 에러 경계 | `src/components/VoipCallErrorBoundary.tsx` |
| expo 호환 | `src/compat/expoAvAudio.ts`, `expoLegacyFileSystem.ts` |

### 6.2 이중 VAD 계층

#### A) Silero (phrase boundary — 1순위, build 62+)

`VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS` (`voiceRelaySegmentBoundary.ts`):

| 상수 | 값 | 의미 |
|------|-----|------|
| `silenceMs` | **1100** | trailing silence → `speech_end` |
| `speechMs` | 120 | 최소 voiced frames → `speech_start` |
| `minSegmentMs` | **3200** | flush 전 최소 캡처 길이 |
| `minSpeechSpanMs` | **2000** | speech_start→speech_end 최소 span |
| `safetyCapMs` | **14000** | 장발화 safety cap (`max_duration`) |
| `postFlushCooldownMs` | **1200** | flush 직후 endpoint 무시 |

**Defer 사유 (`flush:false`):**
- `segment_too_short`
- `speech_span_too_short`
- `post_flush_cooldown`

**Safety cap:** `shouldFlushSileroSafetyCap` → `reason: max_duration` (14s 근처, 실측 ~13.8s)

#### B) Expo meter / file-RMS (fallback)

`VOICE_RELAY_VAD_DEFAULTS` (`voiceRelayOrchestrator.ts`):

| 상수 | 값 | 의미 |
|------|-----|------|
| `minSegmentMs` | **2400** | STT send 최소 (processVoiceRelaySegment) |
| `maxSegmentMs` | 12000 | meter 살아 있을 때 chunk 상한 |
| `silenceFlushMs` | 1900 | 침묵 flush |
| `meterUnavailableFixedFlushMs` | **5400** | Android 미터 dead 시 타이머 |
| `speechMeterMinDb` | -52 | 발화 미터 임계 |

> Silero 활성 시 phrase boundary는 Silero가 담당. `fixed_interval`은 meter-dead fallback.

### 6.3 Turn Controller (에코·반쪽 duplex)

`VOICE_RELAY_TURN_DEFAULTS` (`voiceRelayTurnController.ts`):

| 상수 | 값 |
|------|-----|
| `remoteListenHoldMs` | 2500 |
| `postPlaybackGuardMs` | 700 |
| `playbackMinMs` ~ `playbackMaxMs` | 2200 ~ 5500 | 예상 재생 시간 (build 74) |
| `playbackCharMs` | 45 |

**게이트 함수:**
- `shouldStartVoiceRelayCapture` — `remote_listen_active` 시 캡처 금지
- `shouldDeferVoiceRelayFlush` — caller/callee별 timer flush defer
- `shouldSendVoiceRelaySegment` — listen hold·remote WebRTC 구간 send 차단
- `shouldPlayRemoteVoiceRelay` — 발화자 폰 TTS skip

### 6.4 송신 파이프라인 (`processVoiceRelaySegment`)

1. 세그먼트 flush → base64 read
2. `shouldSendVoiceRelaySegment` / silent skip / min duration
3. `voiceTranslate(base64, from, to, regionHint, 'auto')`
4. **필터 체인 (순서):**
   - `isLikelyRepetitionHallucination` → skip `repetition_hallucination` **(build 65)**
   - `collapseRepeatedRelayPhrases` (`.`, `,`, **공백 구분** 반복 collapse)
   - `isLikelySilenceHallucination` / `isLikelyGibberishRelayTranscript`
   - `isLikelyVoiceRelayEcho` (`playback_pickup_echo`, `remote_transcript_echo`, …)
   - `remote_echo_dedupe`, `identity_translation`, duplicate key (12s)
5. WS `sendVoiceTranslation` + 채팅 UI `appendChatEntry`

### 6.5 수신·재생 (`playVoiceRelayOutput`)

- `Speech.speak(translated)` — `tts_delivery: device_speech`
- **발화자 폰은 TTS 재생 안 함** (`shouldPlayRemoteVoiceRelay`)
- build 65: repetition 시 `PLAYBACK_SKIPPED` / `repetition_hallucination`
- TTS 텍스트 **최대 240자** (`VOICE_RELAY_MAX_SPEAK_CHARS`)
- 억제: `estimateVoiceRelayPlaybackMs` + 700ms (구 4.5s 고정 cap 제거)

### 6.6 에코·중복 가드 상수 (`VoIPCallScreen.tsx`)

| 상수 | ms | 용도 |
|------|-----|------|
| `VOICE_RELAY_DUPLICATE_GUARD_MS` | 12000 | 동일 transcript+translation 재송신 |
| `VOICE_RELAY_REMOTE_PLAYBACK_DEDUPE_MS` | 4000 | 원격 재생 dedupe |
| `VOICE_RELAY_REMOTE_ECHO_DEDUPE_MS` | 12000 | remote transcript echo |
| `VOICE_RELAY_REMOTE_ECHO_GUARD_MS` | 4000 | suppress after remote |
| `VOICE_RELAY_SPEAKER_ECHO_GUARD_MS` | 5500 | 스피커 ON |
| `VOICE_RELAY_ECHO_GUARD_MS` (orchestrator) | 20000 | playback pickup echo |

### 6.7 build 65 — Tab 무한 반복 버그 수정

**증상:** 통화 중 Tab에서 동일 문구 TTS/텍스트가 순식간에 무한 반복, **다시 말하면 멈춤**.

**원인 (logcat `call-7acec80be31c`):**
1. TTS/원격음 → Tab 마이크 수음 → Silero 14s 세gment
2. Whisper가 `안녕하세요 여러분` × 수백 회 STT 환각
3. 기존 `collapseRepeatedRelayPhrases`는 **마침표/쉼표** 구분만 처리 → 공백 반복 통과
4. TTS suppress 4.5s cap → 긴 TTS 재생 중 마이크 재개 → 피드백 루프

**수정 (build 65):**
- `isLikelyRepetitionHallucination()` — 공백 구분 4회+ 반복, 고유 단어 비율, collapse 후 길이 급감
- 송신·수신·`shouldRejectRemoteVoiceRelayPlayback` 전 구간 차단
- TTS 240자 cap + playbackMs 기반 suppress

**재현 테스트 (다음 세션):**
```powershell
adb -s R83W70QY11H logcat -v time -s ReactNativeJS:* |
  Select-String 'repetition_hallucination|VOIP_VOICE_RELAY_PLAYBACK_SKIPPED'
```

### 6.9 build 66 — v1.0 출시 블로커 3건 해소

| 이슈 | 원인 | 수정 |
|------|------|------|
| Accept tap failed | UI Automator `받기` testID flaky | S10 **incoming deeplink** + Tab `call_id` 매칭 |
| S10 incoming timeout | stale ringing + 다중 initiate | lightweight hangup, API `/end`, triple auto-call 차단 |
| Tab→자기 voice id | `CalleeVoiceId=nado-000226` / validation deeplink | 앱 self-call guard + 스크립트 `nado-000001` |

**E-3-1 실검 (build 66, 2026-06-15):**

| 라운드 | connected | signaling | initiate | relay | accept(log) | pass |
|--------|-----------|-----------|----------|-------|-------------|------|
| 1~5 | yes | yes | yes | no* | no* | yes |

\* setup 스크립트는 monitor/accept log 패턴으로 `exit=1`이나 logcat 게이트는 PASS. relay는 무음 구간이라 SENT 미관측 가능.

증적: `evidence/worldlinco-v1-launch/e3_verify_20260615-212949/`

---

### 6.8 초기 모바일 VoIP 버그 (유지)

- `voipCallClient.ts` — `react-native-webrtc` import/타입 수정
- `translate.ts` — `voiceTranslate` regionHint, audio 응답 필드
- `VoIPCallScreen.tsx` — `playRingbackTone` 오타
- `App.tsx` — `localSourceLang`/`localTargetLang` props

---

## 7. APK · 마켓플레이스 배포

| 항목 | 값 |
|------|-----|
| versionName | **1.0.45** |
| versionCode | **74** |
| package | `com.parkcheolhong.worldlinco` |
| canonical | `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` |
| versioned | `uploads/marketplace_local/apk/nadotongryoksa-v1.0.45-build74-current.apk` |
| manifest | `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json` |
| 빌드 스크립트 | `scripts/publish_worldlinco_apk.ps1` |
| 다운로드 (공개 latest) | `GET /api/marketplace/latest.apk` |
| manifest API | `GET /api/marketplace/apk/worldlinco/manifest` |
| 다운로드 (구매/토큰) | `GET /api/marketplace/apk/nadotongryoksa-v1.apk?test_token=...` |

**2026-06-16 배포 확인 (build 74):**
- APK size: **~67.0 MB**
- Tab `R83W70QY11H`, S10 `172.30.1.19:5555` — versionCode **74** 설치 확인
- E-3-8 strict + latency smoke: `ko_ja_smoke_20260616-030406`

**2026-06-15 배포 확인 (build 66, superseded by 74):**
- APK size: **~63.9 MB**
- Tab `R83W70QY11H`, S10 `172.30.1.19:5555` — versionCode **66** 설치 확인
- E-3-1 자동 5/5: `e3_verify_20260615-212949`

**2026-06-14 배포 확인 (build 65):**
- 로컬·컨테이너 APK size: **67,020,732 bytes**
- `https://metanova1004.com/api/marketplace/latest.apk` → **200**
- Tab `R83W70QY11H`, S10 `172.30.1.19:5555` — versionCode **65** 설치 확인

---

## 8. 검증 · 증적 · 스크립트

### 8.1 단위 테스트 (모바일)

| 파일 | 대상 |
|------|------|
| `voiceRelayOrchestrator.test.ts` | VAD, collapse, repetition, echo, gibberish |
| `voiceRelaySegmentBoundary.test.ts` | Silero defer/cap |
| `voiceRelayTurnController.test.ts` | turn/send/defer |
| `voiceRelaySileroVad.test.ts` | native bridge contract |
| `voiceRelayAudioMetrics.test.ts` | file RMS |
| `voipIncomingCallStatus.test.ts` | 착신 상태 |

### 8.2 단위·통합 테스트 (백엔드)

| 파일 | 대상 |
|------|------|
| `test_voip_voice_translation_meta.py` | WS 메타 passthrough |
| `test_voice_translate_stt.py` | voice-translate STT |
| `test_voip_backend_consistency.py` | 라우터 일관성 |
| `test_voip_signaling*.py` | P1/P2 signaling |
| `test_nadotongryoksa_friends_and_voip_contract.py` | friends+voip 계약 |

### 8.3 실기기 E2E · 경계 테스트 스크립트

| 스크립트 | 용도 |
|----------|------|
| `scripts/voip_voice_relay_v8_e2e.ps1` | accept·signaling·connected·relay 게이트 |
| `scripts/voip_boundary_cap_defer_test.ps1` | **14s cap** + **defer 3종** dual-device logcat |
| `scripts/voip_boundary_monitor.ps1` | Silero flush 실시간 모니터 |
| `scripts/voip_manual_call_setup.ps1` | 수동 통화 연결 |
| `scripts/voip_audit_relay_diag.ps1` | relay 감사 진단 |
| `scripts/worldlinco_ko_ja_voip_smoke.ps1` | E-3-8 ko↔ja VoIP smoke strict (build 73+) |
| `scripts/worldlinco_e3_beta_user_record.ps1` | E-3-4 beta user CSV append |
| `scripts/worldlinco_50lang_alignment_audit.ps1` | E-3-6/7 50-lang + API smoke |
| `scripts/worldlinco_e3_launch_verify.ps1` | E-3-1 multi-round WiFi verify |

**표준 테스트 기기:**
- Tab (caller): `R83W70QY11H`
- S10 (callee): `172.30.1.19:5555`, voice_id `nado-000226`

| `scripts/publish_worldlinco_apk.ps1` | Gradle release + marketplace 복사 |

### 8.4 v1.0 E-3 실측 (2026-06-15~16)

| Gate | build | 결과 | 증적 |
|------|-------|------|------|
| E-3-1 WiFi connected | 66 | **PASS** 5/5 + 누적 8/10 | `e3_verify_20260615-212949` |
| E-3-2 repetition echo | 66 | **PASS** repetition 0 | `e3-2_echo_20260615-232900` |
| E-3-6 50-lang align | 67 | **PASS** 50/50 | `50lang_audit_20260615-235805` |
| E-3-7 ko↔ja API | 67 | **PASS** | 동일 audit |
| **E-3-8 ko↔ja VoIP (1차)** | **69** | **PASS** ja STT + Tab PLAYBACK | `ko_ja_smoke_20260616-005906` |
| **E-3-8 ko↔ja strict** | **73** | **PASS** `target_lang=ko` + Tab KO TTS | `ko_ja_smoke_20260616-023813` |
| E-3-4 beta ×10 | — | **ON HOLD** | `E3-4_beta_users.csv` |
| E-3-5 git tag | 74+46 | **PASS** | **`v1.0.45`** @ build 74 · **`v1.0.46`** profile API |

### 8.5 Silero·경계 실측 (2026-06-14)

| 항목 | build | 결과 | 증적 |
|------|-------|------|------|
| Silero START/END | 62 | PASS | `run_20260614-211448` |
| 14s safety cap | 64 | PASS (logcat ~**13848–13868ms**) | `cap_defer_test_20260614-220616`, `230216/s10_cap_phase.log` |
| defer `segment_too_short` (Tab) | 64 | PASS | `cap_defer_test_20260614-225011` (`defer_repro_pass: true`) |
| defer 3종 (역사) | 64 | Tab `call-89b67e1b5f4e` | segment/speech_span/post_flush_cooldown |
| `fixed_interval` mid-phrase | 63+ | **0** (모니터 run) | `boundary_build63_monitor_*` |
| Tab 무한 반복 | 64 | **재현** | logcat `call-7acec80be31c` 23:06 |
| repetition guard | **65** | 코드 반영, **실기기 재검 pending** | — |
| E2E accept+connected | 62 | FAIL (자동 accept flaky) | `run_20260614-211448` |

상세: `evidence/voip-voice-relay-orchestrator/VERIFICATION_REPORT.md`

---

## 9. 기타 백엔드·모바일 (동일 커밋)

| 영역 | 파일/기능 |
|------|-----------|
| 이미지 번역 | `backend/mobile/image_translation/` |
| 친구 API | `apps/mobile-nadotongryoksa/src/api/friends.ts` |
| Call mode UI | `useCallModeController.ts` |
| Hybrid GPS | `src/utils/hybridGps.ts`, `hybridGpsCache.ts` |
| nginx | VoIP WS 프록시, voice-translate 프록시 |
| docker-compose | backend/interpreter/music 서비스 갱신 |

---

## 10. 남은 방향 (미완 · Phase 2~3)

### 10.1 즉시 후속 (build 73+)
- [x] E-3-1 WiFi 2대 connected 자동화 **5/5** (build 66)
- [x] E2E accept — incoming deeplink + call_id 매칭
- [x] Tab self-call / triple initiate 차단 (build 66)
- [x] Tab **repetition_hallucination** echo (E-3-2)
- [x] **E-3-8** ko↔ja VoIP smoke (build 69) — ja STT + Tab playback
- [x] **E-3-8 strict** ja→ko · `target_lang=ko` · Tab 한국어 TTS (build **73**)
- [~] **E-3-4** 지인·커뮤니티 실사용 **10명** — **보류**
- [x] **E-3-5** git tag **`v1.0.45`** @ build 74 · **`v1.0.46`** profile API (2026-06-16)
- [~] **LTE 베타 QA 매트릭스** — 앱 배너·audit·health·script ✅ · **실기기 6+ runs 증적** 미완 (D-0-5)
- [ ] `voip_boundary_cap_defer_test.ps1` cap phase **summary.json PASS** 안정화

### 10.2 P3 (체크리스트·설계 잔여)
- FCM 착신 push 완전 연동 (Firebase 앱 초기화)
- PSTN 다이얼아웃 (통신사/SIP)
- TURN HMAC 단기 토큰 (`test_voip_turn_tokens.py` 기반)

### 10.3 Voice Relay Phase 2~3
- [ ] streaming partial STT
- [ ] full-duplex / barge-in
- [x] **오케스트레이터 웹 TTS** — Edge neural `/api/llm/voice/synthesize` (§0.12.4) · VoIP relay는 여전히 device Speech 위주

### 10.4 문서·운영
- [ ] APK Git LFS (65MB+ GitHub warning)
- [ ] `certbot/` 로컬 인증서 — **git 미포함** (secret)

---

## 11. 파일 인덱스 (build 65 기준)

### 신규·핵심
- `backend/marketplace/nadotongryoksa_voip_router.py`
- `backend/marketplace/call_mode_schema.py`
- `backend/marketplace/services/call_mode_audit_service.py`
- `backend/mobile/image_translation/`
- `backend/llm/router.py` — `/voice-translate`
- `apps/mobile-nadotongryoksa/src/features/voip-voice-relay/*`
- `apps/mobile-nadotongryoksa/src/native/voiceRelaySileroVad.ts`
- `apps/mobile-nadotongryoksa/android/.../VoiceRelaySileroVadModule.kt`
- `docs/VOIP_VOICE_RELAY_ORCHESTRATOR_ARCHITECTURE.md`
- `scripts/voip_*.ps1`, `scripts/publish_worldlinco_apk.ps1`
- `uploads/marketplace_local/apk/nadotongryoksa-v1.apk`
- `evidence/voip-voice-relay-orchestrator/**`

### 초기 VoIP (P1/P2, 병존)
- `backend/voip/{config,models,registry,signaling,router,redis_backend}.py`

### 본 문서
- `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` — **마스터 기술서 (본 파일)**
