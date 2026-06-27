# WorldLinco — Communication OS (현재 실행맵 · ACTIVE · SSOT)

> **상태:** 🟢 **현재 실행맵(ACTIVE) — 지금 진행 중** (미래 계획·v1 게이팅 아님)  
> **연계 체크리스트:** `docs/worldlinco-v2/V2_FEATURE_AUDIT.md`(hot path 정합성) · `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md`  
> **자가 진화 설계:** [`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md) — LLM(엔진)+평가/학습 루프(진화)+게이트(안전) 2층 구조로 통역 품질·정책을 데이터로 점진 개선  
> **신규 채널/품질 설계:** [`TELEPHONY_BRIDGE_DESIGN.md`](TELEPHONY_BRIDGE_DESIGN.md)(일반 전화 착신 통역 — 권한 제약·SIP 브리지) · [`EMOTION_EXPRESSIVE_DESIGN.md`](EMOTION_EXPRESSIVE_DESIGN.md)(감성·표현형 통역 — SeamlessExpressive·SER)  
> **현재 제품:** APK WorldLinco **build 157** — 통역 통화(G10 AEC 정합+재무장 직렬화 해소 검증) + 대면 통역(동결) 운영 중  
> **원칙:** 기존 VoIP·Voice Relay·`POST /api/llm/voice-translate`(≈2.8s) **hot path 무중단 유지**하며 상위 계층·인프라를 **현재 진행으로 점진 적용**(Strangler Fig).

---

## 제품 비전 (V2 궁극 목표)

**Communication OS** — 사람↔사람, 사람↔AI, AI↔AI. 언어·감정·의도·문화·기억·지식·행동을 잇는 **자동 연결 플랫폼**.

| v1.0 (1차 출시) | V2 (업그레이드) |
|-----------------|-----------------|
| 개인 APK · 친구 통역 통화 | Communication OS · 다 채널 Delivery |
| Android · marketplace APK | Android · iOS · Web · Desktop · API Client |
| voice-translate hot path | Language Engine + Intelligence Engine 전층 |
| 베타 → v1.1 구독 | AI Control/Compute Plane · Event/Memory Fabric |

---

## 아키텍처 — WORLDLINCO V2 COMMUNICATION OS

```text
┌─────────────────────────────────────────────┐
│                 CLIENT LAYER                │
├─────────────────────────────────────────────┤
│ Android │ iOS │ Web │ Desktop │ API Client │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                API GATEWAY                  │
├─────────────────────────────────────────────┤
│ Auth │ RateLimit │ Routing │ WAF │ Billing │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│          COMMUNICATION ORCHESTRATOR         │
├─────────────────────────────────────────────┤
│ Session │ Presence │ Routing │ Workflow     │
│ Failover│ Audit    │ Policy  │ Monitoring   │
└─────────────────────────────────────────────┘

       ┌───────────────┼───────────────┐
       ▼               ▼               ▼

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ SIGNAL HUB  │ │ AGENT HUB   │ │ EVENT BUS   │
└─────────────┘ └─────────────┘ └─────────────┘

       │               │               │
       └───────┬───────┴───────┬───────┘
               ▼               ▼

┌─────────────────────────────────────────────┐
│          COMMUNICATION SESSION CORE         │
├─────────────────────────────────────────────┤
│ Session Manager                             │
│ Context Manager                             │
│ Relationship Manager                        │
│ Memory Manager                              │
│ Language Manager                            │
└─────────────────────────────────────────────┘

                       │
                       ▼

┌─────────────────────────────────────────────┐
│         INTELLIGENCE ENGINE LAYER           │
└─────────────────────────────────────────────┘

 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ Meaning AI  │ │ Emotion AI  │ │ Culture AI  │
 └─────────────┘ └─────────────┘ └─────────────┘
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ Memory AI   │ │ KnowledgeAI │ │ Agent AI    │
 └─────────────┘ └─────────────┘ └─────────────┘

                       │
                       ▼

┌─────────────────────────────────────────────┐
│            LANGUAGE ENGINE CORE             │
├─────────────────────────────────────────────┤
│ Language Detection │ Accent │ Dialect       │
│ Translation Router                            │
└─────────────────────────────────────────────┘

                       │
                       ▼

┌─────────────────────────────────────────────┐
│               VOICE PIPELINE                │
├─────────────────────────────────────────────┤
│ VAD │ Noise Remove │ Speaker ID │ STT       │
│ Translation │ TTS │ Voice Clone              │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│             DELIVERY ENGINE                 │
├─────────────────────────────────────────────┤
│ VoIP │ Chat │ Meeting │ Video │ API         │
│ SMS  │ Email                                   │
└─────────────────────────────────────────────┘
```

---

## AI CONTROL PLANE

```text
Model Registry │ Prompt Registry │ Workflow Registry │ Agent Registry
Policy Registry │ Feature Registry │ Memory Registry │ Experiment Registry
Cost Registry │ Version Registry
```

**현재 코드 매핑 (시드):** `backend/orchestrator/`, `backend/llm/model_config.py`, marketplace feature orchestrator.

---

## AI COMPUTE PLANE

```text
GPU SCHEDULER → STT GPU POOL │ LLM GPU POOL │ TTS GPU POOL
```

**현재 코드 매핑:** `gpu-llm-server/`, docker `interpreter-service`, `backend/llm/router.py` voice-translate.

---

## FABRICS

### Event Fabric (Kafka/NATS)

Voice · Translation · Session · Presence · Billing · Monitoring · Audit · AI Events

### Memory Fabric

Short · Session · Relationship · User · Team · Global Knowledge Memory

### Storage Fabric

PostgreSQL Cluster · Redis Cluster · Vector DB · MinIO/S3 · Audit · Knowledge · Conversation Storage

### Realtime Fabric

Signal Cluster (Signal-01…04) → Coturn Cluster (Turn-01…04)

### Observability Fabric

Prometheus · Grafana · OpenTelemetry · Jaeger · Loki · Tempo · AlertManager

### Security Fabric

RBAC · ABAC · JWT · OAuth · Encryption · Consent Manager · Audit Manager · Threat Detection

---

## 구현 우선순위 (현재 실행 순서 · ACTIVE)

> **지금 실행 중:** 1번(VoIP 통역 안정화) **안정화 달성**(G10 build 157 검증, 정합성 갭 G1~G10 종결). #2 Session Core·#3 Call Orchestrator 얇은 버전 배선 완료. 자가 진화 **P2 스캐폴드**([`optimize.py`](../../eval/worldlinco/optimize.py))·전화 **T0 타당성**([리포트](TELEPHONY_T0_FEASIBILITY.md))·**T1 시뮬레이션 브리지**+**T2 실엔진 어댑터**([`telephony/`](../../backend/communication/telephony/))·감정 **E0 SER**+**E1 register 제어**([`emotion/`](../../backend/communication/emotion/))+**E2 보존도 목적함수 항**([`objective.py`](../../eval/worldlinco/objective.py)) + **EMOTION_PROBE emission E2E 배선**(서버 `build_emotion_probe`→응답 `emotion`→클라 `VOIP_EMOTION_PROBE` 로그캣, `COMM_V2_EMOTION_PROBE`) 부트스트랩 완료. **인프라 #4~#7 운영화 완료**(Redis HA·nginx WS 라우팅+sticky·멀티노드 coturn·Prometheus/Grafana 대시보드 [`infra/observability/`](../../infra/observability/)). **전화 T1 실통화 준비**(G.711 μ-law/A-law↔PCM16·8k↔16k 코덱 [`codec.py`](../../backend/communication/telephony/codec.py) + `MediaTransport` 경계·`MediaBridgeRunner` [`transport.py`](../../backend/communication/telephony/transport.py) + **Twilio Media Streams 어댑터** [`twilio_transport.py`](../../backend/communication/telephony/twilio_transport.py) — JSON↔μ-law 프레이밍·streamSid↔leg, 오프라인 검증)·**감정 E3 표현형 TTS**(감정→rate/pitch/volume [`expressive_tts.py`](../../backend/communication/emotion/expressive_tts.py) + **카나리 배선** router→`voice_gateway._synthesize_tts(expressive=)`→edge-tts + **지연 예산 P95<2s 모니터링/폴백** [`budget.py`](../../backend/communication/emotion/budget.py)·Grafana TTS 패널, `COMM_V2_EMOTION_EXPRESSIVE_TTS` 기본 off)·**전화 T1 실 연결 스캐폴드**(Twilio TwiML `<Connect><Stream>`+WS 브리지 핸들러+세션스토어+FastAPI 라우터 [`twilio_app.py`](../../backend/communication/telephony/twilio_app.py), 기본 미마운트) 완료. 잔여: 데이터 누적(≥10통화/기기) 후 P2 의사결정, 전화 T1 실 WS 트래픽·번호(Twilio 콘솔·`mount_twilio_routes`, T0 계약 후), 감정 E1/E2/E3 플래그 on 실통화 검증.

| # | 목표 | 현재 기반 | 현재 진행/다음 |
|---|------|-----------|---------|
| **1** | VoIP 통역 안정화 ✅안정화 | build 157 Voice Relay | **G10 종결**(AEC 정합+재무장 직렬화 해소, flush_rearm −1.2s 검증). 잔여: reject% 10통화 케이던스 감시(§자가진화 §3.6) |
| **2** | Session Core ✅E2E 배선 | `session_id`, `CallModeAuditLog` | ✅ 얇은 버전 + 오케스트레이터 얇은 연결 + **세션 맥락 MT 주입(#9 Meaning 첫 다리)** + **클라이언트 `session_id` 전송**(VoIPCallScreen→`voiceTranslate` `sessionId=call_id`, 서버 call_init도 call_id 키 정렬). designated 전용·대면🔒·`COMM_V2_SESSION_CORE` off면 no-op. test: 서버 20/20·voice-translate contract 23/23·모바일 10/10 무회귀. **build 158** 빌드 후 실통화 검증 대기(플래그 on 환경에서) |
| **3** | Call Orchestrator ✅얇은 버전 | `nadotongryoksa_voip_router` | [`backend/communication/orchestrator/`](../../backend/communication/orchestrator/) — 라이프사이클 상태 전이 + admission 정책(관찰/강제) + 감사. `COMM_V2_CALL_ORCHESTRATOR` off면 no-op, hot path 한 줄 훅(call_init·call_end) best-effort. test 12/12·회귀 43/43 |
| **4** | Redis HA ✅클라이언트 | `backend/voip/redis_backend.py` | ✅ `VOIP_REDIS_URL` compose 배선(DB1) + **HA 클라이언트**(`_client_plan`: Sentinel `VOIP_REDIS_SENTINELS`/Cluster `VOIP_REDIS_CLUSTER`/standalone, 풀·health_check·retry·timeout 튜닝, 실패 시 standalone 폴백). test 7/7. 잔여: 실 Sentinel/Cluster 환경 통합 검증 |
| **5** | Signal Cluster ✅nginx | WS `/api/v1/voip/ws/{call_id}` | ✅ Redis relay 승격(#4) + **nginx `^~ /api/v1/voip/ws/` WS 라우팅 추가(업그레이드 헤더 누락 갭 수정)** + **sticky upstream**(`hash $voip_call_id consistent` → 통화별 레그 동일 인스턴스). `nginx -t` 통과. 잔여: 시그널링 전용 CPU 백엔드 레플리카 배치 |
| **6** | Coturn Cluster ✅멀티노드 | `backend/voip/config.py` TURN HMAC + `coturn/` | ✅ env 이름 정합화 + **멀티노드 운영화**(노드 파라미터화·헬스체크·하드닝 `coturn/docker-compose.coturn.yml`, `.env.example`, 멀티노드 가이드 `README.md`). `TURN_URLS` CSV로 다노드 ICE 후보. compose config 통과 |
| **7** | Monitoring ✅메트릭+대시보드 | `marketplace/prometheus_metrics.py` + **`voip/metrics.py`** + **`infra/observability/`** | ✅ VoIP 전용 메트릭(active WS·call join 지연·시그널링 메시지/오류·TURN 발급·통화 개시) off-path 계측 + `/metrics` 노출 + **Prometheus+Grafana 스택**(분리 compose) + **VoIP 대시보드**(7패널). 잔여: 알림 규칙·메인 스택 통합(선택) |
| **8** | Memory Engine | Qdrant, chat history | session-scoped memory |
| **9** | Meaning Engine | translator LLM | post-STT meaning (feature flag) |
| **10** | Agent Engine | `orchestrator/autonomous/` | Agent Hub (통화와 분리) |

---

## 코드 건강·보안·위생 — 2026-06-21 (강강 검진의 날)

> hot path/기능 무변경 원칙 하에 **건강검진(테스트 전수) → 버그 개선 → v.2 보안 체크리스트 Phase 0 → deprecation 위생**을 수행. 라이브 활성화(Twilio 번호·E3 플래그 on)는 T0 계약/카나리 환경으로 보류.

### A. 건강검진 + 버그 개선 (실패 6건 수정 · 회귀 0)

| 영역 | 증상 | 조치 | 검증 |
|------|------|------|------|
| VoIP presence/push 테스트(2) | Py 3.13에서 제거된 `asyncio.get_event_loop().run_until_complete()` → `RuntimeError` | `asyncio.run()`로 교체 | `test_voip_presence_push.py` 그린 |
| nginx R7 보안 게이트 회귀 | 직전 추가한 VoIP `/ws/`·`/signal` 프록시 타임아웃 `3600s`가 R7(장기 타임아웃 DoS 위험) 위반 | `300s`로 하향(앱 20s ping/pong 유지, `/api/llm/ws` 패턴과 정합) | `test_r6_r7_operational_risk_scan.py::test_r7_*` |
| auth 비밀번호 복구 보안 테스트(2) | 리팩터된 OTP 위임 구조와 불일치한 **stale 테스트**(`randbelow`/`_PASSWORD_RECOVERY_MAX_VERIFY_ATTEMPTS` 내부 가정) | 현재 계약(OTP 위임 + 429/401 매핑)으로 재작성. 난수성/시도제한은 `contact_verification` SSOT가 보장 | `test_auth_router_security.py` 그린 |
| health 진단 정화 테스트 | Windows에 없는 `os.getloadavg` → `monkeypatch.setattr` 실패(POSIX 전용) | `raising=False`로 크로스플랫폼화(서버는 Linux라 런타임 무영향) | `test_health_diagnostics_sanitization.py` 그린 |

- **환경성(코드 결함 아님):** 루트 `tests/test_health|routes|security_runtime.py`는 Postgres 필요(미기동 시 collection 에러), `test_voip_pstn.py`/contract 테스트는 무거운 LLM/Whisper 임포트로 로컬 행 — 둘 다 서버/CI 환경 한정.

### B. v.2 보안 체크리스트 Phase 0 (앱 레벨, GPU 비의존)

- **신규 (STRIDE-D DoS):** `POST /api/v1/voip/calls/initiate` 에 사용자·클라이언트 단위 쿼터(기본 **20/분**, 초과 시 **429 + `Retry-After`**) — 방 생성·콜리 푸시 남용 방어. 기존 `_InMemoryQuotaGate` SSOT(`backend/security_gates.py`) 재사용, `VOIP_CALL_QUOTA_MAX_REQUESTS`/`VOIP_CALL_QUOTA_WINDOW_SEC`(0=비활성)로 운영 조정. test: `test_voip_presence_push.py::test_calls_initiate_enforces_rate_limit`.
- **테스트 격리:** `backend/tests/conftest.py` autouse 픽스처가 전역 인메모리 쿼터(LLM/이미지/관리자/VoIP)를 테스트마다 리셋 → 누적 429 플레이키 차단(`security_gates.reset_for_test()`).
- **문서화:** [`SECURITY_STRIDE_DESIGN.md`](SECURITY_STRIDE_DESIGN.md) **§11 "Phase 0 코드 레벨 충족 현황"** 신설 — 인증 게이트·SECRET_KEY 부팅 강제·OTP 난수/시도제한·진단 정화·내부포트 127.0.0.1·WS 타임아웃 하향·변경/통화 쿼터를 STRIDE별로 매핑, GPU 증설 후 잔여(mTLS/PodSecurity/NetworkPolicy/ELK/at-rest/GDPR) 명시.

### C. `datetime.utcnow()` deprecation 위생 (Py 3.12+)

- **SSOT 헬퍼 신설:** `backend/time_utils.py::utcnow()` = `datetime.now(timezone.utc).replace(tzinfo=None)` — **naive UTC drop-in**으로 동작/포맷 완전 보존(DB naive 비교 `TypeError` 없음, `isoformat()+"Z"` 동일).
- **치환:** 실행 코드 **19개 파일 ~30 호출지점** `datetime.utcnow()` → `utcnow()`(core/auth JWT exp, payment_service DB 비교, voip/marketplace/orchestrator 라우터, progress_tracker 등).
- **의도적 보존(락스텝):** `backend/llm/orchestrator.py`의 **코드 생성 템플릿 문자열**(16건)과 그 산출물인 생성 참조앱 `app/` — 변경 시 golden-task 정합이 깨지므로 템플릿↔산출물 동시 보존. `tmp_*`/스캐폴드(`repair_refiner_result.py`)는 비앱 스크래치라 제외.
- **검증:** py_compile 20파일 무오류 · 포맷 동일성 확인 · `-W error::DeprecationWarning` 28건 통과(경로 경고 0) · 회귀 146건 통과.

---

## 목표 파일 구조 (V2 · 코드 rename 전 문서 SSOT)

```text
codeAI/
├── apps/mobile-nadotongryoksa/
│   └── src/features/voip-voice-relay/     # ★ hot path 보존
├── backend/
│   ├── communication/                     # [V2] Orchestrator · Session · Hubs
│   ├── voip/                              # Signal Hub · Redis (운영 승격)
│   ├── llm/                               # Language + voice-translate
│   ├── orchestrator/                      # AI Control · Agent Hub 원천
│   └── marketplace/                       # Gateway adjunct · billing
├── infra/
│   ├── realtime/                          # coturn · signal cluster
│   ├── observability/
│   └── event/                             # Kafka/NATS (later)
└── docs/worldlinco-v2/                    # 본 문서 · FILE_MAP.md
```

상세 매핑: [`FILE_MAP.md`](FILE_MAP.md)

---

## 마이그레이션 원칙 (Strangler Fig)

1. **Hot path 동결:** `voice-translate` + `voip-voice-relay/*` public contract 변경 금지 (v1.x).
2. **Adapter:** `nadotongryoksa_voip_router` → `backend/voip/` 내부 위임 후 swap.
3. **클라이언트 relay 타이밍 유지:** 서버 orchestrator는 정책·감사·라우팅만.
4. **Feature flag:** Meaning · Memory · Agent는 `COMM_V2_*` env opt-in.

---

## 버전 매핑

| 버전 | 내용 |
|------|------|
| **v1.0** | PART E — 개인 APK 통역 통화 베타 공개 |
| **v1.1** | 무료 N분 → 구독 (`check_mobile_license`) |
| **v1.2** | Session Core 얇은 버전 (언어쌍·통화 맥락 기억) |
| **v2.0** | 본 로드맵 4~7 (Redis · Signal · Coturn · Monitoring) |
| **V2 Ultimate** | 본 로드맵 8~10 + Communication OS 전층 |

---

*최종 갱신: 2026-06-21 · 현재 실행맵(ACTIVE) — build 158 운영 중, 1번 VoIP 안정화 ✅(G10 종결·flush_rearm −1.2s 검증). #2 Session Core·#3 Call Orchestrator 얇은 버전 + 자가진화 P2 + 전화 T0·T1(+실통화준비 코덱/전송 어댑터 + Twilio Media Streams 어댑터 + 실연결 스캐폴드 TwiML/WS/세션스토어)·T2 + 감정 E0·E1·E2(+EMOTION_PROBE emission E2E)·E3(표현형 TTS 운율 매핑 + voice_gateway 카나리 배선 + P95 지연예산 모니터링/폴백) 부트스트랩 완료. **인프라 #4~#7 전 항목 운영화 완료**: #4 Redis HA(Sentinel/Cluster/standalone)·#5 nginx WS 라우팅+sticky upstream·#6 멀티노드 coturn·#7 VoIP 메트릭+Prometheus/Grafana 대시보드. 잔여: 시그널링 전용 백엔드 레플리카 배치(선택)·실 클러스터 통합 검증·전화 T1 실 WS 트래픽·번호(`mount_twilio_routes`, T0 후)·감정 E3 카나리 플래그 on + P95 예산 모니터 검증. 데이터 누적·실통화 검증 단계. **2026-06-21 강강 검진:** 건강검진 후 버그 6건 수정(presence asyncio.run·nginx R7 타임아웃 300s·stale auth 테스트 재작성·Windows health 테스트 이식성) + v.2 보안 Phase 0(VoIP 통화 개시 쿼터 429·테스트 격리 픽스처·SECURITY §11) + `datetime.utcnow()` 위생(`backend/time_utils.py` SSOT, 19파일 치환, 템플릿/`app/` 락스텝 보존). 회귀 146건 통과 — "코드 건강·보안·위생" 절 참조*
