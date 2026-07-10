# 전화 브리지 (T1) — 미디어 서버 1콜 PoC (시뮬레이션)

설계: [`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) 경로 B +
[`TELEPHONY_T0_FEASIBILITY.md`](../../../docs/worldlinco-v2/TELEPHONY_T0_FEASIBILITY.md) T1.

> ⚠️ **SIMULATION ONLY — 통신사/CPaaS 트렁크 무의존.** 실 SIP B2BUA/SFU 연결(번호·트렁크·요금)은
> **T0 사업 결정 이후**다. 이 패키지는 캐리어를 부르지 않으며, 서버측 브리지가 수행할 **콜 플로우
> 로직**(레그 관리·세그먼트 종단·교차 통역 주입·페이싱)을 전송 계층과 분리해 검증한다.

## 왜 시뮬레이션인가
T1의 "실통화 1콜"은 SIP 트렁크·전화번호 계약이 선행(= T0 Go). 계약 전에도 **브리지 오케스트레이션
로직은 미리 검증**할 수 있어, 실 미디어 서버(FreeSWITCH/Asterisk/Janus/mediasoup) 통합 시 위험을
줄인다. 실 STT/MT/TTS 엔진은 `BridgePipeline` 콜백으로 그대로 끼운다.

## 구성
| 파일 | 역할 |
|------|------|
| `config.py` | 플래그(`COMM_V2_TELEPHONY_BRIDGE`, 기본 off) + 프레임/세그먼트 파라미터 |
| `models.py` | `CallLeg`·`LegRole`·`AudioFrame`·`BridgeStats` |
| `pipeline.py` | `BridgePipeline` 프로토콜 + 결정적 `StubPipeline`(엔진 주입 경계) |
| `media_bridge.py` | `SimulatedMediaBridge` — B2BUA 콜 플로우 코어(전송 무의존) |
| `engine_pipeline.py` | **T2**: 실 STT→MT→TTS 어댑터(`EnginePipeline`) — hot path와 동일 엔진, 지연 import·주입 가능 |
| `codec.py` | **T1 실통화준비**: G.711 μ-law(PCMU)·A-law(PCMA) ↔ PCM16, 8k↔16k 리샘플(순수파이썬, `audioop` 미사용/3.13 호환) |
| `transport.py` | **T1 실통화준비**: `MediaTransport` 어댑터 경계 + `MediaBridgeRunner`(코덱/드레인 루프) + `InMemoryCarrierTransport`(시뮬레이션) |
| `twilio_transport.py` | **T1 실 provider 어댑터**: `TwilioMediaStreamTransport`(Twilio Media Streams JSON ↔ μ-law 프레이밍·streamSid↔leg 라우팅·DTMF), 오프라인 — 실 WS 연결은 T0 후 |
| `twilio_app.py` | **T1 실 연결 스캐폴드**: TwiML `<Connect><Stream>` 빌더 + WS 브리지 핸들러(`run_twilio_media_stream`) + 세션스토어 + FastAPI 라우터(`mount_twilio_routes`, **기본 미마운트**) |
| `poc.py` | 실행 가능한 1콜 양방향 PoC (`python -m backend.communication.telephony.poc`) |

## 콜 플로우 (B2BUA 대응)
```
레그 A(ko) 프레임 ──push_frame──▶ [세그먼트 누적 + 무음/상한 종단]
                                        │ 세그먼트 PCM
                                        ▼
                         transcribe(ko) → translate(ko→en) → synthesize(en)
                                        │ 합성 PCM
                                        ▼
                              레그 B 출력 큐로 주입 ──drain_output("B")──▶ (RTP 송출)
```
- **종단**: 무음 누적 ≥ `segment_silence_ms` 또는 버퍼 ≥ `segment_max_ms`. 순수 무음 세그먼트는 미실행.
- **방향**: 화자 레그 언어 → 상대 레그 언어로 번역해 상대 레그에 주입.
- **격리**: 파이프라인 예외는 흡수(`rejects` 카운트), 브리지는 죽지 않음.

## 실행
```bash
python -m backend.communication.telephony.poc --turns 3
# {"turns":3,"injection_counts":{...},"stats":{"segments_bridged":{...}},"note":"SIMULATION ONLY ..."}
```

## T2 — 실 엔진 어댑터 연결
`EnginePipeline` 이 시뮬레이션 브리지를 **hot path와 동일한** 엔진으로 구동한다:
```python
from backend.communication.telephony import SimulatedMediaBridge, EnginePipeline, TelephonyBridgeConfig
bridge = SimulatedMediaBridge(EnginePipeline(), config=TelephonyBridgeConfig(enabled=True))
# STT=_transcribe_mobile_voice_audio · MT=NadoTranslator · TTS=_synthesize_tts (지연 import)
```
- **샘플↔바이트**: 브리지 PCM16 int 샘플 ↔ 엔진 WAV/base64 자동 변환(`pcm16_to_wav_bytes`, base64 decode).
- **주입 가능**: `EnginePipeline(stt_fn=..., mt_fn=..., tts_fn=...)` 로 테스트/대체 엔진 주입.
- **라이브 실행**: 실 STT/MT/TTS는 GPU/Whisper/LLM 스택 필요 → 운영 서버(RTX 5090)에서.

## T1 실통화 준비 — 코덱 + 전송 어댑터 경계
실 캐리어 미디어(G.711 8kHz)와 엔진(PCM16 16kHz)의 경계를 **코덱+전송 어댑터**로 분리했다.
실 provider(Twilio Media Streams·SIP/RTP)는 `MediaTransport` 프로토콜만 구현하면 코어 변경 없이 끼운다.
```python
from backend.communication.telephony import (
    SimulatedMediaBridge, EnginePipeline, TelephonyBridgeConfig,
    MediaBridgeRunner, InMemoryCarrierTransport, CallLeg, LegRole,
)
legs = [CallLeg("A", LegRole.CALLER, "ko", "en"), CallLeg("B", LegRole.CALLEE, "en", "ko")]
transport = InMemoryCarrierTransport(legs)              # ← 실 provider 어댑터로 교체
bridge = SimulatedMediaBridge(EnginePipeline(), config=TelephonyBridgeConfig(enabled=True))
runner = MediaBridgeRunner(bridge, transport, encoding="ulaw")  # 캐리어 8k μ-law ↔ 엔진 16k PCM16
# transport.feed("A", ulaw_8k_bytes, is_speech=True); ...; transport.close(); runner.run()
# 통역 오디오 → transport.outbound_payload("B") (캐리어 코덱으로 송출)
```
- **코덱 경계**: 인바운드 캐리어(μ-law/A-law 8k) → PCM16 16k(엔진), 아웃바운드 역변환. `codec.py` 단독 사용 가능.
- **실통화 체크리스트**: [`TELEPHONY_BRIDGE_DESIGN.md` §4.1](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md)(시그널링·지터버퍼·AEC 남은 항목).

### Twilio Media Streams provider 어댑터
실 provider 예시로 **Twilio Media Streams**(WebSocket, base64 μ-law 8k) 어댑터를 구현했다.
실 WS 핸들러가 수신 프레임마다 `ingest_message(raw)` 를 호출하고, 송신은 `drain_outbound_messages(leg_id)`
가 돌려주는 Twilio JSON 을 write 한다(코덱은 러너가 `encoding="ulaw"` 로 처리).
```python
from backend.communication.telephony import (
    TwilioMediaStreamTransport, MediaBridgeRunner, SimulatedMediaBridge,
    EnginePipeline, TelephonyBridgeConfig, TWILIO_ENCODING, CallLeg, LegRole,
)
legs = [CallLeg("caller", LegRole.CALLER, "ko", "en"), CallLeg("callee", LegRole.CALLEE, "en", "ko")]
transport = TwilioMediaStreamTransport(legs)
runner = MediaBridgeRunner(SimulatedMediaBridge(EnginePipeline(),
                           config=TelephonyBridgeConfig(enabled=True)),
                           transport, encoding=TWILIO_ENCODING)
# WS 수신:  transport.ingest_message(ws_text)   ← start/media/stop/dtmf
# 펌프:     runner.pump_once()                   ← 코덱+브리지+드레인
# WS 송신:  for m in transport.drain_outbound_messages("callee"): await ws.send(m)
```
- **leg 식별**: TwiML `<Connect><Stream><Parameter name="leg" value="caller"/></Stream>` → `start` 이벤트 `customParameters.leg`.
- **남은 것(T0 후)**: 번호/트렁크·인증(Account SID/Auth Token). 어댑터·서버 코드는 카드 없이 검증.

### 실 연결 스캐폴드(`twilio_app.py`, T0 후 마운트)
실 라이브에 필요한 **TwiML 웹훅 + WebSocket 브리지 핸들러 + 세션 수명관리**를 미리 작성했다(가짜 ws 단위테스트 검증, **기본 미마운트**).
```python
from backend.communication.telephony import (
    build_stream_connect_twiml, run_twilio_media_stream,
    TwilioBridgeSessionStore, mount_twilio_routes,
)
# 1) 인바운드 콜 웹훅 응답(TwiML): 양방향 Media Stream 연결.
twiml = build_stream_connect_twiml("wss://host/api/telephony/twilio/stream/CALLID/caller", leg="caller")
# 2) WS 엔드포인트: 세션스토어가 call_id 별 transport/runner 를 두 leg 가 공유.
store = TwilioBridgeSessionStore()            # 기본 EnginePipeline(실 STT→MT→TTS)
transport, runner = store.get_or_create("CALLID")
# await run_twilio_media_stream(websocket, transport=transport, runner=runner, leg_id="caller")
# 3) FastAPI 마운트(T0 후, opt-in): COMM_V2_TELEPHONY_BRIDGE=1 + TELEPHONY_TWILIO_ENABLED=1
mount_twilio_routes(app)                       # /api/telephony/twilio/voice (TwiML) · .../stream/{call_id}/{leg} (WS)
```
- **게이트**: `is_twilio_live_enabled()` = `COMM_V2_TELEPHONY_BRIDGE` AND `TELEPHONY_TWILIO_ENABLED`(둘 다 기본 off). `TELEPHONY_TWILIO_WS_URL` 로 Stream URL 지정.
- **멀티노드**: call_id sticky 라우팅([`nginx.conf`](../../../nginx/nginx.conf/nginx.conf) `$voip_call_id` 해시)으로 같은 인스턴스 고정, 또는 외부 미디어 서버 일원화.

## 실 미디어 서버 통합(T1 이후) 매핑
| 시뮬레이션 | 실 통합 |
|-----------|---------|
| `InMemoryCarrierTransport` | `TwilioMediaStreamTransport`(✅프레이밍 구현, 실 WS만 T0 후) / SIP·RTP 미디어 서버 |
| `MediaBridgeRunner` 동기 펌프 | 실 RTP 20ms 페이싱·지터버퍼·비동기 루프 |
| `codec.py` 선형 리샘플 | 폴리페이즈/FIR 리샘플(품질 상향) |
| `SimulatedMediaBridge` | B2BUA/SFU 세션 핸들러 |
| `EnginePipeline`(T2) | 운영 STT→MT→TTS(이미 hot path 함수 재사용) |
| half-duplex 세그먼트 | 동시통역(LAAL/wait-k) 스트리밍 페이싱(정밀화) |

## 테스트
- [`backend/tests/test_communication_telephony_bridge.py`](../../tests/test_communication_telephony_bridge.py) — 콜 플로우 9 케이스
  (무음 종단·순수무음 미실행·번역 방향·상한 강제 종단·빈 전사 거부·예외 격리·미등록 레그 무시·flush_all·양방향 PoC).
- [`backend/tests/test_communication_telephony_transport.py`](../../tests/test_communication_telephony_transport.py) — **T1 실통화준비** 10 케이스
  (μ-law/A-law 왕복 양자화 한계·8k↔16k 리샘플·캐리어 헬퍼·러너 E2E 통역 송출·미지원 코덱 거부).
- [`backend/tests/test_communication_telephony_twilio.py`](../../tests/test_communication_telephony_twilio.py) — **T1 Twilio 어댑터** 9 케이스
  (이벤트 파싱·media JSON 왕복·start→sid매핑·media→InboundChunk·start전 송신 드롭·stop→closed·DTMF·러너 E2E).
- [`backend/tests/test_communication_telephony_twilio_app.py`](../../tests/test_communication_telephony_twilio_app.py) — **T1 실 연결 스캐폴드** 4 케이스
  (TwiML 구조/이스케이프·세션스토어 call_id 공유·live flag 게이팅·WS 핸들러 가짜ws E2E 통역 송출).
