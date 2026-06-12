# 기술서 — 개발환경 구성 · 오케스트레이터/음성 버그 수정 · VoIP 통역 통화(P1/P2) · 모바일 수정

> 대상 브랜치: `cursor/setup-dev-environment-1c5e` (PR #75)
> 작성: Cursor Cloud Agent. 본 문서는 이번 작업에서 **작성·수정한 모든 내용**과 **남은 방향(P3, voice-translate)** 을 기록한 기술서입니다.
> 관련 문서: `NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md`(설계 제안), `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md`(진단/방향 체크리스트), `AGENTS.md`(클라우드 운영 가이드).

---

## 0. 변경 요약 (commit 단위, `main` 기준)

| commit | 내용 |
|--------|------|
| `f127192` | docs: 프론트엔드 기존 테스트 실패/라우트 정보 AGENTS.md 추가 |
| `b1c85aa` | docs: 오케스트레이터 & 월드링코 통번역 분석/방향 체크리스트 |
| `fddfaa2` | fix: CoderAgent 매니페스트 호출, 세션 복원/저장, VoiceResponse.detected_language |
| `40fc25c` | test: 위 수정 회귀 테스트(coder/session/voice) |
| `459a378` | docs: 체크리스트 수정완료 표시 + pytest-asyncio/autonomous caveat |
| `62edba4` | docs: VoIP 백엔드 스캐폴딩 설계안 |
| `4672e67` | feat: VoIP 시그널링 백엔드 P1(REST + WebSocket) |
| `47dbc69` | docs: VoIP P1(B-2-1/2-2) 완료 표시 |
| `7b09d5c` | fix(mobile): WebRTC import/voiceTranslate/tone/props 수정 |
| `994074f` | feat(voip): P2 Redis 스토어 + pub/sub 릴레이 |
| `90ca825` | test+docs: 라이브-Redis P2 통합 테스트 + 체크리스트 갱신 |

변경 규모: 23개 파일, +1713/-18.

---

## 1. 개발 환경 구성 (Cursor Cloud)

상세 운영 절차는 `AGENTS.md`의 `## Cursor Cloud specific instructions` 참조. 이번에 환경에서 수행/검증한 것:

- **시스템 의존성**: Docker Engine 29(fuse-overlayfs 스토리지 드라이버 + iptables-legacy, Firecracker VM 대응), Python 3.13(deadsnakes), portaudio/libpq/build-essential/ffmpeg, `pytest-asyncio`.
- **인프라 컨테이너**: Postgres 15(5432), Redis 7(host 6380→6379), Qdrant v1.16.2(6333), MinIO(9000/9001). `/etc/hosts`에 postgres/redis/qdrant/minio→127.0.0.1.
- **백엔드**: `.venv`(Python 3.13) + `requirements.txt`, `uvicorn backend.main:app --reload :8000`.
- **프론트엔드**: `frontend/frontend`에서 `npm ci` + `npm run dev`(Next.js 16). 라우트는 `/marketplace`, `/admin`(루트 `/`는 404).
- **업데이트 스크립트**(세션 시작 시 의존성 갱신): `python3.13 -m venv .venv` → `pip install -r requirements.txt` → `pip install pytest-asyncio` → `npm ci --prefix frontend/frontend`.

### 환경 검증(Hello-world)
- 백엔드 `/health` 200(`gpu`만 warning — 클라우드 VM에 GPU 없음. 실서버 RTX 5090에선 정상).
- 회원가입 → 로그인(JWT) → `/api/auth/me` 흐름 성공, 마켓플레이스 UI 로그인 시연 성공.

> **클라우드 제약**: GPU/Ollama LLM 서버 부재 → A뇌 에이전트(reasoner 등) 및 LLM 의존 경로는 클라우드에서 `error`/stub. LLM 불필요 경로(코드 생성 generator, validator, VoIP 시그널링, 번역 사전/googletrans)는 정상.

---

## 2. P0 버그 수정 (자율 오케스트레이터 · 음성)

분석은 `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` 참조. 코드로 검증 후 수정.

### A-1-1 CoderAgent 매니페스트 호출 시그니처 (`backend/orchestrator/autonomous/agents/coder.py`)
- 문제: `_compat_manifest_for_request(task, project_name, validation_profile, required_files)`(정의: `backend/llm/orchestrator.py:9191`)를 존재하지 않는 인자 `output_dir=`/`b_brain_result=`로 호출하고 `required_files` 누락 → 승인 후 코드생성 시 `TypeError`.
- 수정: 위치 인자로 정정(`required_files`는 compat 기본/템플릿과 병합되므로 빈 리스트 안전) + `b_result["written_files"]`를 매니페스트 결과와 병합(메인 경로 `orchestrator.py:12665-12669`와 동일).

### A-1-2 세션 복원 불완전 (`backend/orchestrator/autonomous/session.py`)
- 문제: `to_dict()`는 stages/agent_results 저장하나 `load()`는 `conversation`만 복원 → 멀티턴 재개 시 상태 소실.
- 수정: `load()`에 `stages`(StageState)·`agent_results`(AgentResult)·`pending_approval_data`·`model_routes`·`extra` 복원, `to_dict()`에 누락 필드 보완.

### A-1-3 세션 저장 누락 (`backend/orchestrator/autonomous/turn_controller.py`)
- 문제: greeting/status 등 일부 턴에서 `save()` 미호출 → 후속 `load()` 404.
- 수정: 모든 응답이 거치는 `_build_response`에서 `session.save()` 보장(중복 save 제거).

### B-3-1 VoiceResponse.detected_language (`backend/llm/voice_gateway.py`)
- 문제: `VoiceResponse`에 `detected_language` 필드 부재 → `# pyright: ignore`로 전달해도 Pydantic이 드롭 → 모바일 자동 언어전환 항상 미수신.
- 수정: `detected_language: Optional[str] = None` 필드 추가 + ignore 주석 제거.

### 회귀 테스트
- `backend/tests/test_autonomous_orchestrator.py`(coder TypeError 회귀, 세션 복원/저장, greeting 저장) — 신규 케이스 포함 **29 passed**.
- `backend/tests/test_voice_gateway_schema.py` — VoiceResponse 스키마 2 passed.
- 실제 API E2E: code_generation→승인→`coder success`/`validator success`, 세션 재조회 복원 확인.

---

## 3. VoIP 통역 통화 백엔드 — P1(시그널링)

설계: `NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md`. 모바일이 이미 기대하는 계약(`apps/mobile-nadotongryoksa/src/services/voipCallClient.ts`, `useVoIPCall.ts`)에 백엔드를 1:1로 맞춤.

### 패키지 구성 (`backend/voip/`)
| 파일 | 역할 |
|------|------|
| `config.py` | STUN(공용)+TURN(env) ICE 서버, 완전한 `signaling_server` ws URL 조립, ws 토큰 TTL |
| `models.py` | `CallInitiateRequest`/`CallInitResponse`/`AuditResponse` — 모바일 타입과 1:1 |
| `registry.py` | 인메모리 `CallRegistry`(앱↔앱 자동매칭, 감사 이벤트), `CallRoom`/`Participant`(+`to_dict`/`from_dict`) |
| `signaling.py` | `SignalingHub` — 같은 call_id 룸의 두 소켓 간 릴레이(로컬) |
| `router.py` | REST 3종 + WebSocket 엔드포인트 |
| `__init__.py` | 패키지 |

`backend/main.py`에 try/except 패턴으로 라우터 등록.

### REST 계약
- `POST /api/v1/voip/calls/initiate` (Bearer) — 앱 타깃(callee_user_id/voice_id/friend_id) 시 룸 생성/매칭 후 `call_id`+`signaling_server`(완전 ws URL)+`turn_servers`+`participant_role` 반환. PSTN-only는 `phone_dialer_required=true`+`fallback_dial_url`로 폴백.
- `GET /api/v1/voip/calls/{call_id}/audit` (Bearer) — 통화 상태/참가자/감사 이벤트.
- `POST /api/v1/voip/calls/{call_id}/end` (Bearer) — 종료 + 상대에게 hangup 통지.

### WebSocket 시그널링
- `WS /api/v1/voip/ws/{call_id}?token=<JWT>&role=<caller|callee>`
- 인증: initiate가 발급한 단기 JWT(claims: sub/uid/voip_call_id/voip_role) query 검증.
- 릴레이 타입: `offer/answer/candidate/chat_message/voice_translation`(상대 역할로 그대로 전달, `from_role` 부가), `ping`→`pong`, `hangup`→상대 전달+종료.
- **앱↔앱 자동매칭**: A가 callee=B로 initiate(룸 생성), B가 initiate하면 "자신이 callee인 ringing 룸"을 찾아 같은 call_id에 callee로 합류(별도 엔드포인트 불필요, `participant_role`로 구분).

### 범위/전제 (P1)
앱↔앱 한정 · STUN + 환경변수 TURN · 인메모리 단일 워커. 서버는 미디어 미중계(P2P+TURN), 시그널링·번역 릴레이만.

### 검증
- `backend/tests/test_voip_signaling.py` — TestClient 2-클라이언트 릴레이 E2E(initiate 자동매칭, PSTN 폴백, turn_servers, offer/answer/candidate/chat/voice_translation 릴레이, ping/pong, hangup, audit) **5 passed**.
- 라이브 uvicorn에 실제 WebSocket 2개 연결 E2E 성공(자동매칭·릴레이·audit 타임라인 확인).

---

## 4. VoIP 백엔드 — P2(Redis 스토어 + pub/sub 릴레이)

멀티 워커 지원. 기능 플래그 `VOIP_REDIS_URL`(미설정 시 인메모리 P1 기본).

### `backend/voip/redis_backend.py`
- **`RedisCallStore`** — `CallRegistry`와 동일 비동기 API를 Redis로 구현. 룸=`voip:room:{call_id}`(JSON, TTL), 감사 이벤트는 룸 JSON에 축적, 앱↔앱 매칭은 `voip:incoming:{user_id}` 세트 인덱스로 O(1) 조회. → 워커가 달라도 initiate/audit/end 일관.
- **`RedisRelay`** — 시그널링을 `voip:relay:{call_id}` 채널로 publish. 각 소켓은 구독 후 자신의 role 대상 메시지만 전달(중복 없음) → 두 소켓이 다른 워커에 있어도 릴레이 성립.
- **팩토리** `get_store()`/`get_relay()` — `VOIP_REDIS_URL` 유무로 Redis/인메모리 선택. 소켓 객체는 프로세스 로컬이므로 릴레이만 pub/sub로 브리지.

### 공유 코드경로
`registry.py`에 `add_event()` 및 `CallRoom.to_dict/from_dict` 추가. `router.py`는 store/relay 추상화를 사용해 **단일워커(인메모리)·멀티워커(Redis)가 동일 코드경로**로 동작.

### 서버측 chat 번역(설계상 P2 옵션) — 제외
모바일 `VoIPCallScreen`이 수신 chat을 이미 클라이언트에서 번역(`translateText`)하므로, 서버측 중복 번역은 충돌 위험 → 이번 P2에서 제외(문서화). 필요 시 후속에서 langs를 룸/메시지에 실어 `NadoTranslator`로 처리 가능.

### 검증
- `backend/tests/test_voip_signaling_redis.py` — 라이브 Redis(127.0.0.1:6380/db5)로 스토어(initiate/audit/자동매칭) + pub/sub 릴레이(offer/answer/ping/pong/hangup, 감사 영속) **2 passed**(Redis 미가용 시 skip).
- 전체 VoIP+오케스트레이터+음성 스위트 **38 passed**. 라이브 백엔드(인메모리 기본) `/health=200`, initiate=200.

### 환경변수 (P2/P3 공통)
| 변수 | 기본 | 용도 |
|------|------|------|
| `VOIP_REDIS_URL` | (없음=인메모리) | Redis 스토어/릴레이 활성화 |
| `VOIP_PUBLIC_WS_BASE` | 요청에서 유도/`ws://localhost:8000` | signaling_server URL 베이스 |
| `VOIP_STUN_URLS` | `stun:stun.l.google.com:19302` | STUN |
| `VOIP_TURN_URLS`/`_USERNAME`/`_CREDENTIAL` | (없음) | TURN |
| `VOIP_SIGNALING_TOKEN_TTL_SEC` | `600` | ws 토큰 수명 |

---

## 5. VoIP 모바일 클라이언트 버그 수정

`apps/mobile-nadotongryoksa`(`tsc --noEmit`로 검증, 수정 파일 클린):

- `src/services/voipCallClient.ts` — WebRTC 로드 오타: `require('react-native-wert')`→`react-native-webrtc`, `WBTC.*`→`webrtc.*`, `ONameStream`→`onaddstream`. (미수정 시 WebRTC 미로딩으로 통화 불가)
- `src/api/translate.ts` — `voiceTranslate`에 4번째 인자 `regionHint?` 추가 + `audio_base64`/`audio_format` 응답 노출, `TranslateOptions.regionHint` 추가.
- `src/screens/VoIPCallScreen.tsx` — `playwingbackTone`→`playRingbackTone`(런타임 크래시 방지).
- `App.tsx` — `VoIPCallScreen`에 필수 prop `localSourceLang`/`localTargetLang` 전달.

> 잔여 typecheck 오류는 `node_modules/expo/tsconfig.base.json`의 기존 설정 문제(코드 무관). 모바일 `node_modules`는 gitignore.

---

## 6. 테스트/검증 요약

| 영역 | 명령 | 결과 |
|------|------|------|
| 자율 오케스트레이터 | `pytest backend/tests/test_autonomous_orchestrator.py -p asyncio --asyncio-mode=auto` | 29 passed |
| 음성 스키마 | `pytest backend/tests/test_voice_gateway_schema.py` | 2 passed |
| VoIP P1(인메모리) | `pytest backend/tests/test_voip_signaling.py` | 5 passed |
| VoIP P2(라이브 Redis) | `pytest backend/tests/test_voip_signaling_redis.py` | 2 passed |
| 코어 백엔드 | `pytest tests/test_health.py test_routes.py test_runtime.py test_security_runtime.py` | 6 passed |
| 모바일 타입 | `npm run typecheck` (apps/mobile-nadotongryoksa) | 수정 파일 클린 |
| 라이브 E2E | uvicorn + 2 WebSocket / 실제 API initiate→승인 | 성공 |

> 비동기 테스트는 `pytest-asyncio` 필요: `python -m pytest <file> -p asyncio --asyncio-mode=auto`.

---

## 7. 남은 방향 (미구현) — P3 및 voice-translate 설계

### 7.1 P3-A: FCM presence / 콜리 착신
- **목적**: 현재 P1/P2의 앱↔앱은 "양측이 initiate"하는 자동매칭으로 성립. 실제 착신(상대가 안 걸어도 전화가 울림)에는 푸시가 필요.
- **설계**:
  1. 디바이스 토큰 등록 엔드포인트(`POST /api/v1/voip/devices/register {fcm_token, platform}`)와 사용자별 토큰 저장(DB/Redis).
  2. `initiate`(앱 타깃) 시: 룸 생성 후 callee에게 **FCM data 푸시**(`call_id`, caller 표시정보) 전송. callee 앱은 푸시 수신 → `signaling_server`(callee 토큰) 발급용 `accept` 호출 또는 initiate 자동매칭으로 합류.
  3. `callee_app_online`은 등록 토큰/최근 presence(ws 접속 또는 Redis presence 키 TTL)로 산정.
  4. Firebase Admin SDK 서버 키 필요(환경변수 `FCM_*`). 앱 측 Firebase 초기화(이전 로그의 `No Firebase App '[DEFAULT]'` 오류 해소) 동반.
- **신규**: `backend/voip/presence.py`(토큰 저장/presence), `push.py`(FCM 발송), router에 `/devices/register` 및 initiate 푸시 훅.
- **테스트**: FCM은 외부 의존 → 발송 부분은 어댑터 모킹으로 단위 테스트, presence 산정/토큰 저장은 라이브 Redis로 검증.

### 7.2 P3-B: PSTN 다이얼아웃
- **목적**: `callee_phone`(앱 미설치 대상) 실제 발신. 현재 P1은 `phone_dialer_required` 폴백만.
- **설계**: SIP/통신사 게이트웨이(예: Twilio Programmable Voice, 또는 자체 SIP trunk) 어댑터. `initiate`에서 PSTN 경로 선택 시 통신사 콜 생성 + 미디어 브리지(통신사↔WebRTC). 통역은 통신사 오디오 스트림에 STT/TTS 삽입 필요(서버측 미디어 처리 → 비용/지연 큼).
- **결정 필요**: 통신사 선정, 미디어 브리지 호스팅(SFU/미디어서버), 요금/규제(국가별 발신). **외부 계약 선행** 항목.
- **단계**: 1) 통신사 어댑터 인터페이스 정의 + 콜 생성/종료, 2) 미디어 브리지 PoC, 3) 통역 삽입.

### 7.3 P3-C: TURN 시간제한 토큰
- **목적**: 정적 TURN 자격(현재 `VOIP_TURN_USERNAME/CREDENTIAL`) 대신 단기 HMAC 자격으로 보안 강화.
- **설계**: coturn `use-auth-secret` 방식 — `username = <expiry_unix>:<user_id>`, `credential = base64(HMAC-SHA1(secret, username))`. `config.get_ice_servers()`를 사용자/통화별 동적 생성으로 확장(`VOIP_TURN_STATIC_AUTH_SECRET`, TTL). initiate 응답의 `turn_servers`에 통화별 토큰 주입.
- **테스트**: HMAC 자격 생성 단위 테스트(만료/서명 검증). coturn 실연동은 별도.

### 7.4 백엔드 `POST /api/llm/voice-translate` (STT→번역)
- **목적**: 모바일 `voiceTranslate`(`translate.ts`)와 VoIP 음성 릴레이가 호출하는 엔드포인트(현재 백엔드 부재).
- **설계**:
  1. 요청 `{audio_base64, from_lang, to_lang, region_hint?}`.
  2. STT: `backend/llm/voice_gateway.py`의 whisper.cpp/faster-whisper 헬퍼 재사용(언어 힌트 `from_lang` 전달로 CJK 오인식 방지). `detected_language` 반환.
  3. 번역: `backend/services/nadotongryoksa/translator.py`의 `NadoTranslator`로 transcript를 from→to 번역.
  4. (옵션) TTS: 합성 오디오 `audio_base64`/`audio_format` 반환.
  5. 응답 `{original_text, translated, engine, detected_language, audio_url?, audio_base64?, audio_format?}` — 모바일 `VoiceTranslateResult`와 일치.
- **위치**: `backend/llm/router.py`(또는 voice_gateway에 라우트 추가).
- **의존/제약**: STT 모델(faster-whisper tiny, CPU 가능) — 클라우드에서 동작하나 실음성 E2E는 음원 필요. **테스트**: STT 함수 모킹 + 번역 경로 계약 테스트, 실 음원은 수동.
- **연계**: 이 엔드포인트 구현 시 모바일 `voiceTranslate`(이미 시그니처 수정 완료)와 VoIP `voice_translation` 릴레이가 실제로 동작.

### 7.5 기타 후속(체크리스트 참조)
- 실기기 2회 게이트 검증(`voip-retest-checklist`), APK 빌드 정합(`CXX1210`), 패키지 ID 통일(`com.shinsegye.nadotongryoksa` vs `com.parkcheolhong.worldlinco`), BT/WF/음성 자동언어 검증.

---

## 8. 파일 인덱스 (이번 작업 신규/수정)

- 신규: `backend/voip/{__init__,config,models,registry,signaling,router,redis_backend}.py`, `backend/tests/{test_voip_signaling,test_voip_signaling_redis,test_voice_gateway_schema}.py`, `NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md`, `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md`, `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md`(본 문서).
- 수정: `backend/main.py`, `backend/llm/voice_gateway.py`, `backend/orchestrator/autonomous/{agents/coder.py,session.py,turn_controller.py}`, `backend/tests/test_autonomous_orchestrator.py`, `AGENTS.md`, `apps/mobile-nadotongryoksa/{App.tsx,src/api/translate.ts,src/screens/VoIPCallScreen.tsx,src/services/voipCallClient.ts}`.
