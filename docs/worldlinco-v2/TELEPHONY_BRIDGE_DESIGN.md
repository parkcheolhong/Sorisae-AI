# WorldLinco V.2 — 일반 전화(셀룰러/PSTN) 착신 통역 설계서 (Telephony Bridge)

> **목표:** 현재의 **인앱 VOIP 통역**(양 끝단을 우리가 제어)을 넘어, **일반 전화(셀룰러/PSTN) 착·발신 통화에도
> 실시간 통역**을 제공하기 위한 경로를 정의한다. 핵심 제약(안드로이드 통화 오디오 권한)을 직시하고
> **A(음향 브리지) vs B(서버측 SIP/통신사 브리지)** 를 타당성·비용·품질로 비교한다.
>
> **본 문서는 비교·의사결정 설계서다.** 경로 확정(특히 B의 통신사/CPaaS 계약)은 사업 결정 후 진행한다.

> ⚠️ **운영 원칙 — 현재 hot path 무접촉**
> 본 문서의 어떤 경로도 현재 운영 중인 인앱 VOIP 통역(`POST /api/llm/voice-translate`, voice relay)·대면 통역(🔒 동결)을
> **변경하지 않는다.** 전화 착신 통역은 **신규 진입 채널**로 추가되며, 검증된 STT→MT→(표현형)TTS 코어를 재사용한다.

> **연계:** [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md) · [`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md) · [`EMOTION_EXPRESSIVE_DESIGN.md`](EMOTION_EXPRESSIVE_DESIGN.md) · [`SCALING_STT_MT_SEPARATION.md`](SCALING_STT_MT_SEPARATION.md) · [`SECURITY_STRIDE_DESIGN.md`](SECURITY_STRIDE_DESIGN.md)
> **최종 갱신:** 2026-06-21

---

## 0. 핵심 제약 — 왜 "그냥 앱으로 통화를 가로채기"가 안 되는가

안드로이드는 통화 오디오 소스 `VOICE_CALL`·`VOICE_UPLINK`·`VOICE_DOWNLINK` 를 **Android 9(API 28)부터 시스템/특권 앱 전용**으로 제한했다.
이를 쓰려면 `CAPTURE_AUDIO_OUTPUT`(보호등급 `signature|privileged`)이 필요한데, 이는 **플랫폼 키 서명 또는 시스템 파티션 선탑재 앱만** 보유할 수 있다.
([Android Developers — Sharing audio input](https://developer.android.com/media/platform/sharing-audio-input))

| Android | 통화 녹음/캡처 |
|---------|----------------|
| ~8 | 일반 앱도 `VOICE_CALL` 일부 가능(기기차) |
| **9 (API 28)** | `VOICE_CALL/UPLINK/DOWNLINK` **시스템 앱 전용** |
| 10 (API 29) | 통화 중 `AudioRecord` 추가 제한 |
| 11+ | 접근성 기반 통화 녹음도 **비시스템 앱 차단** |

> **결론:** **삼성이 되는 이유는 기술이 아니라 권한**이다. 삼성은 OEM이라 자사 다이얼러가 플랫폼 서명 권한으로 통화 오디오(모뎀/텔레포니 HAL)에 접근한다. **플레이스토어 일반 앱은 원천 불가.**
> 따라서 우리의 선택지는 ① 마이크 음향으로 우회(A) 또는 ② 통화 자체를 서버를 거치게 해 미디어 접근권 확보(B)뿐이다.

---

## 1. 경로 A — 스피커폰 음향 브리지 (On-device acoustic)

```mermaid
flowchart LR
    Far[상대(원거리)] -- 셀룰러 통화 --> Phone[내 폰<br/>스피커폰 ON]
    Phone -- 스피커 출력(상대 음성) --> Air((공기))
    Air -- 기기 마이크 캡처 --> App[WorldLinco 앱<br/>STT→MT→TTS]
    App -- TTS 소리내어 재생 --> Air2((공기))
    Air2 -- 통화 마이크 픽업 --> Phone -- 셀룰러 --> Far
```

- **원리:** 통화를 스피커폰으로 두고, **상대 음성을 기기 마이크로 캡처**해 통역, **번역 TTS를 소리내어 재생** → 통화 마이크가 픽업해 상대에게 전달.
- **장점:** 특별 권한·인프라 불필요. 어떤 폰에서도 즉시 PoC 가능.
- **한계(우리가 VOIP에서 이미 겪은 물리):** 반이중, 음향 에코(자기 TTS 재캡처 — G10과 동형), 주변 소음, 저품질. 사용자가 스피커폰을 켜야 함. **상용 품질 도달 어려움.**
- **위치:** **PoC·데모·접근성 보조** 용도. 정식 서비스 품질로는 부적합.

---

## 2. 경로 B — 서버측 SIP/통신사 콜 브리지 (Network-side) ⭐ 권장

```mermaid
flowchart LR
    Far[상대 전화] -- PSTN/셀룰러 --> Carrier[통신사 / CPaaS<br/>SIP 트렁크·번호]
    Carrier -- SIP/RTP --> MS[WorldLinco 미디어 서버<br/>SFU/B2BUA]
    subgraph CORE[통역 코어 (재사용)]
        STT[STT] --> MT[MT/LLM] --> XTTS[표현형 TTS]
    end
    MS <--> CORE
    MS -- SIP/RTP(통역 합성) --> Carrier
    Carrier -- PSTN/셀룰러 --> User[사용자 전화]
    MS -. 텔레메트리 .-> EVAL[(자가 진화 평가)]
```

- **원리:** 착신 번호를 **통신사 SIP 트렁크/CPaaS**(예: KT, Twilio류)로 받아 **우리 미디어 서버가 통화를 브리지(B2BUA)**. 서버에서 **양방향 RTP 오디오에 직접 접근**해 STT→MT→(표현형)TTS 통역 후 양쪽 레그에 합성 주입.
- **장점:**
  - **권한 벽 완전 우회**(서버측 미디어 — 안드로이드 제한 무관, **어떤 폰이든 앱 없이도** 가능).
  - **품질 통제**(서버 GPU·AEC·지터버퍼·코덱), 인앱 통역 코어 재사용.
  - **양방향·표현형 통역**([`EMOTION_EXPRESSIVE_DESIGN.md`](EMOTION_EXPRESSIVE_DESIGN.md)) 적용 용이.
- **한계/필요사항:**
  - **통신 인프라**: SIP 트렁크·전화번호 발급·통신사/CPaaS 계약·요금(분당 과금).
  - **법규**: 통화 녹음·통역 **고지·동의**, 통신사업 규제([`SECURITY_STRIDE_DESIGN.md`](SECURITY_STRIDE_DESIGN.md) 연계).
  - **지연 예산**: PSTN 왕복 + 통역 지연(ITU-T G.114 — mouth-to-ear ≤400ms는 통역 특성상 초과 불가피, 동시통역 정책으로 완화).
- **번호 모델(택1):**
  - **포워딩**: 사용자 번호 → 우리 번호로 착신전환 → 브리지.
  - **전용 통역 번호**: 사용자에게 통역 전용 번호 발급(상대가 이 번호로 발신 시 통역).
  - **콜백/디스패치**: 앱이 발신 요청 → 서버가 양쪽에 콜 → 브리지.

---

## 3. A vs B 비교표 (의사결정용)

| 기준 | A. 음향 브리지 | B. SIP/통신사 브리지 |
|------|---------------|----------------------|
| 통화 오디오 접근 | 마이크 우회(간접) | **서버측 직접(RTP)** |
| 품질 | 낮음(반이중·에코) | **높음(통제 가능)** |
| 폰 앱 설치 | 필요 | **불필요 가능**(번호 기반) |
| 권한/플랫폼 제약 | 없음 | 없음(서버측) |
| 인프라 비용 | 0 | 통신사/CPaaS·번호·분당요금 |
| 법규/계약 | 경미 | 통신·녹음 동의·사업 규제 |
| 양방향 통역 | 어려움 | **용이** |
| 착수 속도 | 즉시(PoC) | 계약·구축 필요 |
| 상용 적합성 | ❌ | ✅ |

---

## 4. 단계별 로드맵 (확정 후)

| Phase | 내용 | 산출물 | 선행 |
|-------|------|--------|------|
| **T0. 타당성·계약 조사** 🟡진행 | CPaaS/통신사(KT 등) SIP·번호·요금·규제 검토, 번호 모델 결정 | [타당성 리포트](TELEPHONY_T0_FEASIBILITY.md) ✅초안 | 사업 결정 |
| **T1. 미디어 서버 PoC** 🟡시뮬레이션+✅실통화준비+✅Twilio어댑터 | SIP B2BUA/SFU 1콜 브리지(에코·지터·코덱) + 코어 연결 | [`telephony/`](../../backend/communication/telephony/) 시뮬레이션 브리지 + **실통화 준비**: [`codec.py`](../../backend/communication/telephony/codec.py)(G.711 μ-law/A-law ↔ PCM16, 8k↔16k 리샘플) + [`transport.py`](../../backend/communication/telephony/transport.py)(`MediaTransport` 경계 + `MediaBridgeRunner`) + [`twilio_transport.py`](../../backend/communication/telephony/twilio_transport.py)(**Twilio Media Streams 어댑터** — JSON↔μ-law 프레이밍·streamSid↔leg). 실 WS 연결·번호는 T0 계약 후(§4.1) | T0 |
| **T2. 통역 코어 연결** ✅엔진어댑터 | 기존 STT→MT→(표현형)TTS 재사용, 동시통역 정책(LAAL) | [`engine_pipeline.py`](../../backend/communication/telephony/engine_pipeline.py)(실엔진 주입) | T1 |
| **T3. 동의·법규·보안** | 통역/녹음 고지·동의 흐름, STRIDE 위협모델, 보존·삭제 | 컴플라이언스 | T1 |
| **T4. 텔레메트리·평가 연동** | 자가 진화 하니스(`eval/worldlinco/`)에 통화채널 지표 편입 | 통합 대시보드 | T2 |
| **T5. 베타** | 소수 번호·소수 사용자 카나리 | 베타 운영 | T2–T4 |

> A(음향 브리지)는 **T0와 병행해 PoC/데모용**으로만 즉시 구현 가능(인앱 코어 재사용). 정식 서비스는 B로 수렴.

### 4.1 실통화 준비 체크리스트 (T1→실 캐리어 연결)

코어(`SimulatedMediaBridge`)는 전송 무의존이고, 코덱/전송 경계가 분리됐다. 실 캐리어를 붙일 때 필요한 것:

- [x] **코덱 변환** — G.711 μ-law(PCMU, 북미/일본)·A-law(PCMA, 유럽) 8kHz ↔ 엔진 PCM16 16kHz([`codec.py`](../../backend/communication/telephony/codec.py), `audioop` 미사용 순수파이썬 — Python 3.13 호환).
- [x] **전송 어댑터 경계** — `MediaTransport`(`poll_inbound`/`send_outbound`/`closed`) + `MediaBridgeRunner`(코덱/드레인 루프). 실 provider는 이 프로토콜만 구현(strangler-fig).
- [x] **실 provider 어댑터(프레이밍)** — Twilio **Media Streams** 어댑터([`twilio_transport.py`](../../backend/communication/telephony/twilio_transport.py)): WS JSON(connected/start/media/stop/dtmf) ↔ μ-law `InboundChunk`·outbound `media` JSON, streamSid↔leg(customParameters) 라우팅. 오프라인 검증 완료. (SIP/RTP 미디어 서버(FreeSWITCH/Janus)는 동일 프로토콜로 추가 가능.)
- [x] **실 연결 코드 스캐폴드** — TwiML `<Connect><Stream>` 빌더 + WS 브리지 핸들러 + call_id 세션스토어 + FastAPI 라우터([`twilio_app.py`](../../backend/communication/telephony/twilio_app.py), 가짜 ws 단위테스트). **기본 미마운트**(`COMM_V2_TELEPHONY_BRIDGE`+`TELEPHONY_TWILIO_ENABLED` opt-in).
- [ ] **실 WS 트래픽·번호** — Twilio 콘솔 번호·트렁크·Account SID/Auth Token, `mount_twilio_routes(app)` 호출(T0 계약). BYE·재호·mark/clear·바지인(clear) 정밀화.
- [ ] **지터버퍼/RTP 타이밍** — 실 RTP 20ms 페이싱·패킷 손실·지터(현 러너는 동기 펌프 PoC). 폴리페이즈 리샘플로 품질 상향.
- [ ] **AEC/게인** — 캐리어 에코·레벨 정규화(서버측), half-duplex 게이팅.
- [ ] **동의·녹음 고지**(T3) + 텔레메트리(T4).

---

## 5. 가드레일

- **법적 고지·동의** — 통화 통역/녹음은 양 당사자 고지·동의 필요(관할 법규 준수).
- **현 hot path 무접촉** — 전화 채널은 신규 채널, 인앱 VOIP·대면(🔒) 코드 경로 무변경.
- **지연 예산** — 동시통역 정책(wait-k/LA/AlignAtt)로 첫 토큰 지연 최소화([`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md) §4.3).
- **보안/프라이버시** — 통화 미디어·전사본 저장은 STRIDE 설계 준수, 보존기간·삭제권.

---

## 6. 인용

- ITU-T G.114 / G.107 (지연·E-model) — [`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md) §4.1.
- Android Developers, *Sharing audio input* — 통화 오디오 소스 권한 제약. <https://developer.android.com/media/platform/sharing-audio-input>
- 동시통역 정책·지표(AlignAtt/LAAL) — [`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md) §4.3.
