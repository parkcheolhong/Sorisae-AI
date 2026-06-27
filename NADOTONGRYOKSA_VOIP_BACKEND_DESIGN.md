# 월드링코(WorldLinco) VoIP 통역 통화 — 백엔드 API·시그널링 스캐폴딩 설계안

> 상태: **설계 제안(구현 전)**. 본 문서는 `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md`의 **B-2(VoIP 실시간 통역 통화)** 블로커를 해소하기 위한 백엔드 스캐폴딩 설계입니다.
> 원칙: **모바일이 이미 기대하는 계약에 백엔드를 맞춘다**(모바일 코드 변경 최소화). 아래 계약은 실제 모바일 소스에서 추출했습니다.

## 0. 설계가 근거로 삼은 모바일 계약 (실측)

| 항목 | 모바일 소스 | 핵심 |
|------|------------|------|
| REST initiate | `src/hooks/useVoIPCall.ts:55`, `src/features/voip-auto/useVoipAutoController.ts:110` | `POST /api/v1/voip/calls/initiate` (Bearer 인증) |
| REST audit | `src/screens/VoIPCallScreen.tsx:217` | `GET /api/v1/voip/calls/{call_id}/audit` |
| REST end | `src/screens/VoIPCallScreen.tsx:1119` | `POST /api/v1/voip/calls/{call_id}/end` |
| 시그널링 연결 | `src/services/voipCallClient.ts:608` | `new WebSocket(callInitResponse.signaling_server)` — **응답의 `signaling_server`를 그대로 ws URL로 사용** |
| initiate 응답 타입 | `voipCallClient.ts:48-72` `CallInitResponse` | `call_id`, `signaling_server`, `turn_servers`, `participant_role`, … |
| 시그널링 메시지 | `voipCallClient.ts` | `offer / answer / candidate / chat_message / voice_translation / ping / pong / hangup` |

### 핵심 설계 제약 (놓치면 안 됨)
1. **`signaling_server`는 완전한 WebSocket URL이어야 한다.** 모바일은 경로/토큰을 조립하지 않고 그대로 `new WebSocket()`에 넣음. → 백엔드가 `wss://<host>/api/v1/voip/ws/{call_id}?token=<jwt>&role=caller` 형태를 통째로 반환.
2. **메시지는 같은 `call_id` 룸 안에서 상대에게 그대로 릴레이**된다(SFU 아님, 시그널링 릴레이만). offer→callee, answer→caller, candidate→상대, chat/voice_translation→상대.
3. **`ping`에는 `pong`으로 응답**(모바일이 20초 keepalive 전송, `voipCallClient.ts:178`).
4. WebRTC 미디어는 P2P(+TURN). 백엔드는 **미디어를 중계하지 않음**(시그널링·번역 릴레이만).

---

## 1. 범위 (Phase 분리)

| Phase | 범위 | 비고 |
|-------|------|------|
| **P1 (이번 스캐폴딩)** | 앱↔앱 통화: initiate/audit/end REST + WebSocket 시그널링 룸 릴레이 + ping/pong + chat/voice_translation 릴레이. 인메모리 레지스트리. STUN만(공용) + TURN 환경변수 주입 | GPU 불필요, 단일 워커에서 E2E 검증 가능 |
| **P2** | Redis 백엔드 레지스트리(멀티 워커/스케일), 서버측 chat 번역(`translation_status`), presence 정확도 | 운영 확장 |
| **P3** | PSTN(`callee_phone`) 다이얼아웃, FCM 푸시 presence/착신, TURN 인증 토큰 발급 | 외부 통신사/Firebase 연동 — 별도 계약 필요 |

> 모바일은 `callee_phone`(PSTN)과 `callee_user_id/callee_voice_id/friend_id`(앱 타깃)를 모두 보냄. **P1은 앱 타깃만 실제 연결**하고, PSTN은 `phone_dialer_required=true` + `fallback_dial_url`로 우아하게 폴백(모바일이 이미 이 필드들을 처리: `voipCallClient.ts:54-55`).

---

## 2. 컴포넌트 아키텍처

```
backend/voip/                         (신규 패키지)
├── __init__.py
├── router.py            # FastAPI APIRouter: REST 3종 + WebSocket 엔드포인트
├── registry.py          # CallRegistry: call_id→CallRoom(참가자, 상태, 감사 이벤트). P1 인메모리
├── models.py            # Pydantic: CallInitiateRequest / CallInitResponse / AuditResponse
├── signaling.py         # SignalingHub: 룸별 소켓 관리, 메시지 릴레이, ping/pong
├── translation_relay.py # voice_translation/chat 릴레이 시 NadoTranslator 연동(P2 서버측 번역)
└── config.py            # TURN/STUN, 외부 호스트(공개 wss base) 환경변수
```

등록(`backend/main.py`, 기존 try/except 패턴):
```python
# ── VoIP Interpretation Calls ──
try:
    from backend.voip.router import router as voip_router
    app.include_router(voip_router)
    logger.info("[OK] voip router loaded")
except Exception as e:
    logger.warning(f"[WARN] voip router skipped: {e}")
```
> FastAPI WebSocket 지원 확인됨(`uvicorn[standard]`+`websockets` 설치, 기존 `backend/llm/ws_channel.py` 패턴 존재).

---

## 3. REST 계약 (모바일 타입과 1:1)

### 3.1 `POST /api/v1/voip/calls/initiate`  (인증: `Depends(get_current_user)`)
요청(모바일 `useVoipAutoController.ts:116-125`):
```json
{
  "callee_phone": "+8210...",        // PSTN 타깃(선택)
  "callee_user_id": 123,             // 앱 타깃(선택)
  "callee_voice_id": "voice_...",    // 앱 타깃(선택)
  "friend_id": "...",                // 친구 타깃(선택)
  "caller_id": "user@nadotongryoksa",
  "session_id": "...",               // 통역 세션 연계(선택)
  "mode": "voip_full_auto",          // 또는 voip_manual 등
  "auto_relay": false
}
```
응답(모바일 `CallInitResponse` — 필드명 정확히 일치):
```json
{
  "call_id": "c_ab12...",
  "signaling_server": "wss://<host>/api/v1/voip/ws/c_ab12?token=<jwt>&role=caller",
  "turn_servers": [{"urls": ["stun:stun.l.google.com:19302"]},
                   {"urls": ["turn:<host>:3478"], "username": "...", "credential": "..."}],
  "session_id": "...",
  "participant_role": "caller",
  "status": "ringing",
  "requested_mode": "voip_full_auto",
  "resolved_mode": "voip_full_auto",
  "auto_relay_requested": false,
  "auto_relay_applied": false,
  "callee_app_online": true,
  "caller_user_id": 1, "callee_user_id": 123,
  "caller_voice_id": "...", "callee_voice_id": "...",
  "display_label": "홍길동", "display_language": "ja", "display_country_code": "JP",
  "call_route": "app",              // app | pstn_fallback
  "phone_dialer_required": false,   // PSTN 폴백 시 true
  "fallback_dial_url": null,        // tel:+82...
  "user_message": null,
  "error_code": null
}
```
규칙:
- 앱 타깃 식별자(`callee_user_id|callee_voice_id|friend_id`)가 있으면 `call_route="app"`, 룸 생성 후 `signaling_server` 발급.
- 앱 타깃이 없고 PSTN만 있으면 P1에선 `call_route="pstn_fallback"`, `phone_dialer_required=true`, `fallback_dial_url="tel:..."`, `status="dialer_required"`.
- 콜리 식별 실패 → `error_code` + HTTP 4xx, body `{"detail": {"code": "...", "message": "...", "fallback_dial_url": ...}}` (모바일 `useVoipAutoController.ts:135-150` 파싱 형식).

### 3.2 `GET /api/v1/voip/calls/{call_id}/audit`  (인증)
- 통화 수명주기 감사 이벤트를 반환(모바일 `VoIPCallScreen.tsx:217`에서 call_id로 조회·표시).
- 반환 예: `{"call_id","status","created_at","participants":[...],"events":[{"ts","type","role","detail"}]}`.
- `events`에 `initiate / ws_connected(role) / offer / answer / candidate(count) / chat / voice_translation / hangup / end` 기록 → **실기기 2회 검증의 게이트 로그**를 서버측에서도 남김.

### 3.3 `POST /api/v1/voip/calls/{call_id}/end`  (인증)
- 통화 종료. 룸의 다른 참가자에게 `{"type":"hangup"}` 릴레이 후 소켓 정리. `status="ended"`.

---

## 4. WebSocket 시그널링 계약

엔드포인트: `WS /api/v1/voip/ws/{call_id}?token=<jwt>&role=<caller|callee>`
- **인증**: 헤더 대신 query `token`으로 JWT 검증(브라우저 WebSocket은 커스텀 헤더 불가). `get_current_user`와 동일 검증 로직을 query 토큰용으로 분리.
- **룸 입장**: `call_id` 레지스트리 확인 → 역할 등록 → `audit`에 `ws_connected` 기록.

### 메시지 릴레이 규칙 (서버는 내용 변형 없이 상대에게 전달, P1)
| 수신 type | 동작 |
|-----------|------|
| `offer` | 룸의 상대(callee)에게 그대로 relay |
| `answer` | 상대(caller)에게 relay |
| `candidate` | 상대에게 relay (`sdpMid`, `sdpMLineIndex` 보존) |
| `chat_message` | 상대에게 relay. P2에서 `source_lang/target_lang` 기준 `NadoTranslator` 번역 후 `translated_text`,`translation_status` 채워 relay |
| `voice_translation` | 상대에게 relay(이미 모바일이 transcript+translated_text 생성) |
| `ping` | **송신자에게 `{"type":"pong"}` 응답** |
| `hangup` | 상대에게 relay + 룸 종료 |

> 모든 relay 메시지에 `call_id` 포함. P1은 "그대로 전달"만으로 통화 성립(모바일이 번역을 자체 수행). 서버측 번역은 P2 옵션.

---

## 5. 데이터 모델 (P1 인메모리 → P2 Redis)

```python
@dataclass
class Participant: role: str; user_id: int|None; voice_id: str|None; ws: WebSocket|None; connected_at: float|None
@dataclass
class CallRoom:
    call_id: str; status: str; created_at: float
    caller: Participant; callee: Participant
    session_id: str|None; mode: str; auto_relay: bool
    events: list[dict]   # 감사 로그
```
- P1: 프로세스 전역 `dict[str, CallRoom]` + `asyncio.Lock`. **단일 워커 전제**(개발/검증 OK).
- P2: Redis Pub/Sub로 워커 간 릴레이 + TTL로 좀비 룸 청소. (기존 `agent_bus.py`의 Redis 폴백 패턴 참고)

---

## 6. 설정 (config.py, 환경변수)

| 변수 | 기본 | 용도 |
|------|------|------|
| `VOIP_PUBLIC_WS_BASE` | `wss://<DOMAIN>` | `signaling_server` URL 조립의 호스트 베이스 |
| `VOIP_STUN_URLS` | `stun:stun.l.google.com:19302` | 공용 STUN |
| `VOIP_TURN_URLS` | (없음) | TURN 서버 (없으면 STUN만 → 대칭 NAT 환경 연결 제한) |
| `VOIP_TURN_USERNAME` / `VOIP_TURN_CREDENTIAL` | (없음) | TURN 정적 자격(향후 시간제한 토큰으로 대체) |
| `VOIP_ENABLE_PSTN` | `false` | P3 PSTN 다이얼아웃 |
| `VOIP_SIGNALING_TOKEN_TTL_SEC` | `600` | ws 토큰 수명 |

> 로컬 개발: `VOIP_PUBLIC_WS_BASE=ws://localhost:8000`로 두면 시뮬레이터/웹에서 검증 가능.

---

## 7. 인증·보안
- REST 3종: 기존 `get_current_user`(Bearer).
- WS: query `token` JWT 검증 + `call_id` 룸 소속(참가자 user_id 일치) 확인 → 무단 룸 난입 차단.
- 룸 입장은 정확히 2인(caller/callee)로 제한. 동일 역할 재접속은 이전 소켓 교체.
- 메시지 크기 상한(모바일이 chat/voice 280자 슬라이스), 서버도 방어적 제한.

---

## 8. 통역(번역) 연동
- **P1**: `voice_translation`은 모바일이 STT+번역(이미 `App.tsx`/`translate.ts`)해서 보냄 → 서버는 릴레이만.
- **P2**: `chat_message` 서버측 번역 — `backend/services/nadotongryoksa/translator.py`의 `NadoTranslator` 재사용해 `translated_text`,`translation_status`(`ok|failed`) 채움. (B-3 `voice-translate` 신규 엔드포인트와 동일 번역 코어 공유)
- `session_id`로 기존 통역 세션과 연계 가능(향후 대화 로그 통합).

---

## 9. 단계별 작업 목록 (P1 구현 시)

- [ ] `backend/voip/{__init__,models,config,registry,signaling,router}.py` 스캐폴딩
- [ ] `models.py`: `CallInitiateRequest`, `CallInitResponse`(모바일 필드 1:1), `AuditResponse`
- [ ] `registry.py`: 인메모리 `CallRegistry`(create/get/end + 감사 이벤트 append)
- [ ] `router.py`: REST initiate/audit/end + `signaling_server` URL 발급(JWT ws 토큰)
- [ ] `signaling.py`: WS 엔드포인트, 룸 입장/역할/relay/ping-pong/정리
- [ ] `main.py` 라우터 등록(try/except)
- [ ] 환경변수 문서화(`.env.example`, AGENTS.md)
- [ ] 테스트(아래)

## 10. 테스트 전략 (GPU/외부망 불필요)
- **단위**: `CallRegistry` 생성/종료/감사 이벤트; initiate 분기(app vs pstn_fallback); ws 토큰 검증.
- **통합(WebSocket relay)**: FastAPI `TestClient`로 **2개의 ws 클라이언트(caller/callee)** 접속 → caller가 `offer` 전송 → callee가 동일 sdp 수신 → `answer`/`candidate` 역방향 relay 검증 → `ping`→`pong` → `hangup` 룸 종료. (pytest-asyncio 사용)
- **계약**: initiate 응답 JSON에 모바일 `CallInitResponse` 필수 키 존재 검증(`call_id`,`signaling_server`,`turn_servers`,`participant_role`).
- **수동(실기기/시뮬)**: `VOIP_PUBLIC_WS_BASE=ws://<dev-host>:8000`로 2 디바이스 통화 → `VOIP_START_CALL_PRESS`,`[VoIP] Offer sent`,`Answer applied`,`Connection state: connected` 로그 확인(voip-retest-checklist 게이트).

## 11. 결정 필요(오픈 이슈)
1. **TURN 서버 제공 주체**: 자체 coturn 호스팅 vs 관리형(Twilio/메타지원). STUN만으로는 대칭 NAT에서 연결 실패율 높음 → P1 검증은 동일망/STUN로 가능하나, 실사용엔 TURN 필수.
2. **PSTN 연동 여부/사업자**(P3) — `callee_phone` 실제 발신을 할지, 앱↔앱만 공식 지원할지.
3. **presence(callee_app_online) 소스**: P1은 레지스트리/최근 ws 접속 기반 추정 → 정확한 착신엔 FCM 푸시(P3) 필요.
4. **멀티 워커 운영 시점**: 단일 워커로 출시 후 Redis 백엔드(P2) 전환 시점.
5. `com.shinsegye.nadotongryoksa` vs `com.parkcheolhong.worldlinco` **패키지 ID 확정**(실기기 검증 신뢰성).

---

## 부록 A. 모바일 무변경 확인
이 설계대로면 모바일 변경 없이 동작합니다. 단, 분석에서 발견된 **클라이언트 버그 2건**은 VoIP 실연결 전 별도 수정 필요(이 PR 범위 밖, 체크리스트 B-3-3):
- `voipCallClient.ts:18-23`: `react-native-wert`/`WBTC`/`webrtc` 오타로 WebRTC 로드 실패 가능 → `react-native-webrtc` 정정 필요.
- `VoIPCallScreen.tsx:528`: `voiceTranslate(...)`에 인자 4개 전달하나 정의는 3개.
