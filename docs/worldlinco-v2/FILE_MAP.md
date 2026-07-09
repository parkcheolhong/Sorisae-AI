# WorldLinco V2 — 레이어 ↔ 파일 매핑 (미래 버전 · SSOT)

> **용도:** V2 업그레이드 시 “어디에 무엇을 붙일지” 참조. **v1.0 출시 전 대규모 rename 금지.**  
> **로드맵:** [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md)

---

## CLIENT LAYER

| V2 | 현재 경로 | v1.0 | V2 |
|----|-----------|------|-----|
| Android | `apps/mobile-nadotongryoksa/` | ✅ | 유지 |
| iOS | `app.json` ios bundle | — | v2.0+ |
| Web | `frontend/.../marketplace/worldlinco/` | 데모 | v2.0+ |
| Desktop | — | — | V2 Ultimate |
| API Client | — | — | V2 Ultimate |

> **모바일 5기능 분리:** Android 앱 `apps/mobile-nadotongryoksa/`의 5개 기능(대면통역/소리새AI+OCR/VOIP+채팅/일반전화+예약/노래번역) 단일-활성 분리 설계는 [`FEATURE_SEPARATION_MASTER_SPEC.md`](FEATURE_SEPARATION_MASTER_SPEC.md).
>
> **`src/features/` 모듈 구조 (2026-06-24 현재):**
>
> ```text
> apps/mobile-nadotongryoksa/src/features/
> ├─ face-interpretation/   # 대면통역 (faceConversationTiming 등)
> ├─ face-conversation/     # 대면 VAD 컨트롤러
> ├─ sorisae/               # 소리새AI: sorisaeEcho(자기에코) + ★5.8 진화형 동반자(companionDomains 멀티도메인·companionMemory 기억·companionPersonaStore 온디바이스) + ★5.9 companionLanguageTutor(50개국 언어쌍 교습)·companionCommands(메모리 명령/능동 제안) + ★5.10 companionIdentity(가입 AI 이름 SSOT→"OOOO AI" 표시명)·companionChatReadAloud(수신 채팅 읽어주기 판정/정리)
> ├─ voip-voice-relay/      # VoIP 음성릴레이 오케스트레이터/오디오메트릭 · ★6.2 voiceRuntimeAutoTuning(사용자 말속도/음량 EMA 학습→통역 TTS rate/volume 자동 조절, 통화 간 영속)
> ├─ voip-auto/             # VoIP 자동/수신 컨트롤러
> ├─ voip/                  # ★5.6g VoIP 식별자/URL/TURN 유틸(voipSignaling)
> ├─ call-mode/             # 콜모드 컨트롤러 + ★5.6d 순수 헬퍼(callModeHelpers)
> ├─ chat/                  # 채팅 화면/API/타입 (★5.10 수신 읽어주기 토글+expo-speech · ★5.11 chatVoiceInput/useChatVoiceInput 마이크 입력 + ChatRoomScreen 🎙️/📨 SNS 초대 배선)
> ├─ sorisae/               # ★5.8~5.10 동반자(Identity/Memory/Persona/Commands/Tutor/ReadAloud) · ★6.1 companionVoiceCall(음성 호출형 웨이크워드 상태기계: dormant/awake·3분 자동 종료)
> ├─ contacts/              # ★5.11 contactFriendMatch(연락처↔친구 매칭) · ★5.12 ContactsDirectoryModal(단말 전화번호부 전체 디렉터리: 통역통화/VoIP/채팅 3액션)
> ├─ sns-share/             # ★5.11 snsShare(초대 메시지/설치URL/딥링크 + OS Share) · ★5.12 shareAppPromotion(앱 홍보 공유)
> ├─ translation/           # 번역 공용 헬퍼
> ├─ pstn-assist/           # 일반전화(PSTN) 어시스트 컨트롤러
> ├─ travel-booking/        # 여행예약 순수 헬퍼/타입
> ├─ travel-itinerary/      # 여행 일정 패널
> ├─ song/                  # 노래번역 텍스트/언어 헬퍼
> ├─ friends/               # 친구 폴더/지도탐색/타입
> ├─ language/              # ★공용 언어 SSOT(languageCatalog: LANGS/LangCode)
> ├─ tts/                   # 공용 발화 텍스트(ttsText)
> ├─ country/               # ★5.6e 국가 클러스터(countryLanguage→countryCatalog/regionHints)
> ├─ profile/               # ★5.6c 프로필 표시 포매터(국기/로케일/언어/성별)
> ├─ monetization/          # ★5.6b 결제/구독 도메인(플랜/구매판정)
> ├─ app-update/            # 인앱 자동 업데이트(appUpdate)
> ├─ shared/                # ★5.6f 공용 텍스트/API 유틸(textFormat)
> ├─ navigation/            # ★5.7 섹션 레일 SSOT 레지스트리(sectionRegistry: 고유ID 자동 넘버링/자동 연결)
> └─ correlation/           # 기능별 로그 correlation id(FEATURE_IDS) ← navigation 레일이 featureId 자동 연결
> ```
>
> ★ = Phase 5.6 순수 모듈/유틸 분리(2026-06-24, [`FEATURE_SEPARATION_MASTER_SPEC.md`](FEATURE_SEPARATION_MASTER_SPEC.md) §7). 의존 토대: `language/languageCatalog`(LangCode) ← `country/countryLanguage` ← `country/{countryCatalog,regionHints}`. **Phase 5.7**(§7-2): 섹션 레일 정의를 `navigation/sectionRegistry`(SSOT 배열 1곳)로 통합 → `SectionRailKey`/`SECTION_RAIL_ITEMS`/셀렉터/딥링크 파서/`numericId` 자동 넘버링/correlation `featureId`까지 전부 파생(레일 1개 추가 = 전 시스템 자동 연결). 잔여(5.1~5.4 상태/JSX/핸들러)는 디바이스 검증 동반 단계.

---

## API GATEWAY

| V2 | 현재 경로 |
|----|-----------|
| TLS · Routing | `nginx/nginx.conf/nginx.conf` |
| Auth | `backend/auth.py`, `backend/auth_router.py` |
| Billing | `backend/marketplace/subscription_router.py` |
| RateLimit/WAF | 부분 — `backend/marketplace/prometheus_metrics.py` |

---

## COMMUNICATION ORCHESTRATOR

| V2 | 현재 | V2 목표 |
|----|------|---------|
| Session · Presence · Routing | `nadotongryoksa_voip_router.py` (인메모리) | `backend/communication/orchestrator/` |
| Audit · Policy | `call_mode_audit_service.py` | orchestrator + Postgres |
| Failover · Monitoring | — | v2.0 |

---

## HUBS

| Hub | 현재 | V2 목표 |
|-----|------|---------|
| **Signal** | `nadotongryoksa_voip_router` WS, `backend/voip/signaling.py` | `communication/hubs/signal_hub.py` |
| **Agent** | `backend/orchestrator/autonomous/` | `communication/hubs/agent_hub.py` |
| **Event** | Redis pub/sub (`voip/redis_backend.py`) | Kafka/NATS `infra/event/` |

---

## SESSION CORE

| Manager | 현재 | V2 목표 |
|---------|------|---------|
| Session | call `session_id`, audit | `communication/session/session_manager.py` |
| Context | Voice Relay lang pair (client) | `context_manager.py` |
| Relationship | `nadotongryoksa_friends_router.py` | `relationship_manager.py` |
| Memory | chat rooms, Qdrant (platform) | `memory/` + Memory Fabric |
| Language | `translator.py`, signup langs | `language_manager.py` |

---

## INTELLIGENCE ENGINE

| AI | 현재 | V2 |
|----|------|-----|
| Meaning | translator LLM | `communication/intelligence/meaning/` |
| Emotion | — | V2 Ultimate |
| Culture | — | V2 Ultimate |
| Memory AI | — | 로드맵 #8 |
| Knowledge | Qdrant, `knowledge/` | V2 Ultimate |
| Agent AI | `orchestrator/autonomous/` | 로드맵 #10 |

---

## LANGUAGE ENGINE CORE

| 기능 | 현재 |
|------|------|
| Detection | `voice-translate` detected_language |
| Translation Router | `backend/services/nadotongryoksa/translator.py` |
| Accent/Dialect | — (V2) |

---

## VOICE PIPELINE ★ hot path

| 기능 | 현재 | 변경 |
|------|------|------|
| VAD | `VoiceRelaySileroVadModule.kt`, segment boundary | v1.x 유지 |
| STT/TTS/Translation | `POST /api/llm/voice-translate` | v1.x 유지 |
| Orchestration | `voip-voice-relay/*` | v1.x 유지 |
| Noise Remove · Speaker ID · Clone | — | V2+ |

---

## DELIVERY ENGINE

| 채널 | 현재 | V2 |
|------|------|-----|
| VoIP | `voipCallClient.ts`, voip router | v1.0 |
| Chat | `nadotongryoksa_chat_router.py` | v1.0 |
| Meeting/Video/SMS/Email | — | V2 Ultimate |

---

## FABRICS

| Fabric | 현재 | V2 |
|--------|------|-----|
| Storage | postgres, redis, qdrant, minio — `docker-compose.yml` | cluster |
| Realtime | single WS | Signal + Coturn cluster |
| Observability | prometheus partial, `monitoring/reports/` | Grafana stack |
| Security | JWT, admin RBAC | ABAC, consent, threat |

---

## AI CONTROL / COMPUTE

| Plane | 현재 |
|-------|------|
| Control | `backend/orchestrator/`, `llm/orchestrator.py` manifests |
| Compute | `gpu-llm-server/`, RTX server Whisper/LLM/TTS |

---

*최종 갱신: 2026-06-24 (CLIENT LAYER `src/features/` 구조도 — Phase 5.6 순수 모듈 분리 + Phase 5.7 navigation/sectionRegistry SSOT + Phase 5.8 sorisae 진화형 멀티도메인 동반자(companionDomains/Memory/PersonaStore, 온디바이스 기억) + Phase 5.9 언어쌍 교습(companionLanguageTutor)·메모리 명령/능동 제안(companionCommands)·정직 계약 + Phase 5.10 가입 필수 AI 이름(companionIdentity→"OOOO AI" 자동 치환)·수신 채팅 읽어주기(companionChatReadAloud + ChatRoomScreen expo-speech) + Phase 5.11 채팅 마이크/텍스트 겸용(chat/chatVoiceInput·useChatVoiceInput)·연락처 연동(contacts/contactFriendMatch + services/phoneKey 순수 분리)·SNS 연동 채팅(sns-share/snsShare) + Phase 5.12 마이크 STT 작동불능 수정(화자 지정언어 designated)·단말 전화번호부 전체 디렉터리(contacts/ContactsDirectoryModal)·expo-contacts/legacy 버그수정(services/deviceContacts)·SNS 앱 홍보(sns-share/shareAppPromotion) + Phase 6.1 tsc/잔재테스트 전수 정리(TS5.8 업그레이드)·소리새 음성 호출형 웨이크워드 상태기계(sorisae/companionVoiceCall, 3분 자동 종료)·소리새 심볼 앱 아이콘(assets/icon·adaptive-icon + android mipmap 재생성) + Phase 6.2 대면 언어감지 정상 확인(조사)·VoIP 음성 속도/볼륨 사용자패턴 자동 튜닝(voip-voice-relay/voiceRuntimeAutoTuning + VoIPCallScreen 배선·AsyncStorage 영속) 반영)*
