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

*최종 갱신: 2026-06-14*
