# WorldLinco — 서비스 분리 설계 (여행 대면 통역 ↔ VoIP/채팅)

> **목적:** 성격이 다른 두 서비스(① 여행 대면 통역, ② VoIP/채팅)를 어떻게 분리할지 설계하고, 분리 시 vs 현 상태의 장단점을 명시한 뒤 A/B/C 안을 논의·결정하기 위한 SSOT.
> **상위 문서:** [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md) · [`FILE_MAP.md`](FILE_MAP.md)
> **원칙(고정):** V2 Strangler Fig — `POST /api/llm/voice-translate` + `voip-voice-relay/*` **public contract(hot path) 동결**. 분리는 상위 경계만 추가.

---

## 1. 배경 — 두 서비스의 성격은 본질적으로 다르다

| 항목 | ① 여행 대면 통역 | ② VoIP / 채팅 |
|------|------------------|----------------|
| 언어 결정 | **자동 감지**(bilingual, 양방향) + GPS 지역 힌트 | **지정 언어 고정**(화자=자국어, 상대=자국어) |
| 입력 환경 | 한 기기·한 마이크, 두 사람이 번갈아 말함 | WebRTC 통화(원격 오디오 존재) / 텍스트 |
| STT 모드 | auto-detect → 언어쌍 라우팅 | **언어 락(language-locked)이 맞음** |
| VAD | 개방형 발화, 말 끝 감지 필요(증가율 VAD) | 턴 기반 + silero + 에코 억제 |
| 에코 원인 | 같은 기기 스피커의 자기 TTS | 원격 TTS + 스피커폰 + WebRTC 마이크 |
| 지역 힌트 | 필요(GPS) | 불필요 |
| 난이도 | 높음(감지+세그먼트) | 낮음(언어를 이미 앎) |

**결론:** ②는 언어를 **이미 알고 있으므로** 자동감지·불일치거부가 불필요하다. 현재 이 둘이 한 코드(특히 백엔드 단일 엔드포인트)에서 분기 처리되며 **서로의 버그를 유발**한다(예: VoIP에서 Whisper 오감지로 "지정 언어 불일치" 거부 → 딜리버리 멈춤).

---

## 2. 현재 구조 (지금은 "한 몸")

```text
                ┌──────────────────────────────────────────┐
                │   POST /api/llm/voice-translate (공유)     │
                │   - bilingual_mode 분기 (face)            │
                │   - designated 분기 (voip/chat)           │  ← 분기 혼재
                └──────────────────────────────────────────┘
   App.tsx (face autoVoice)        VoIPCallScreen.tsx          chat_router (text)
   + faceConversationVadController  + silero monitor
        │                               │
        └──── 공유: voiceRelayOrchestrator.ts / voiceRelayAudioMetrics.ts ────┘
   튜닝: worldlincoTuningConfig { face_conversation, voip }  ← 섹션은 이미 분리됨
```

- **이미 분리된 것:** 프론트 VAD 컨트롤러, 튜닝 섹션(`face_conversation` vs `voip`), 백엔드 모드 분기.
- **아직 섞여 문제인 것:** 단일 STT 엔드포인트가 두 정책을 함께 처리. VoIP가 언어를 알면서도 auto-detect + 불일치거부를 수행.

---

## 3. 장점 / 단점 — 분리 시 vs 현 상태 (명시)

### 3-A. 분리했을 때 — 장점
1. **정확성·버그 제거:** VoIP/채팅을 지정 언어 락으로 바꾸면 오감지·불일치거부(오늘의 멈춤/미전달)가 **원천 소멸**. STT 정확도↑.
2. **독립 튜닝:** 각 채널의 VAD/에코/지연 파라미터를 서로 영향 없이 조정.
3. **독립 진화:** V2 Delivery Engine(채널 분리)과 방향 일치 → V2 선투자.
4. **테스트 격리:** 한 경로 수정이 다른 경로를 깨뜨릴 위험↓ (지금까지 face↔voip 상호 회귀 발생).
5. **명확한 책임/SSOT:** 채널별 소유 경계가 분명.

### 3-B. 분리했을 때 — 단점/위험
1. **코드 중복:** VAD/에코 로직이 갈라지면 유지보수 부담(공통 코어로 묶지 않으면).
2. **핫패스 위험:** `voice-translate`/`voip-voice-relay/*` 계약을 잘못 건드리면 V2 동결 원칙 위반·회귀.
3. **공수:** 물리적 분리(엔드포인트/화면/모듈 분할)는 규모 큼.
4. **동기화 비용:** 공통 개선(예: TTS 개선)을 양쪽에 반영해야 함.

### 3-C. 현 상태 유지 — 장점
- 단일 엔드포인트·적은 코드, 공통 개선이 한 번에 전파.

### 3-D. 현 상태 유지 — 단점
- 분기 혼재로 버그 유발(지정 불일치 거부), 튜닝 충돌, 추론 난해, 취약. (실측으로 확인됨)

---

## 4. V1 → V2 연계성 분석 (무시 불가)

V2 ROADMAP/FILE_MAP의 목표 계층:

```text
DELIVERY ENGINE   : VoIP | Chat | Meeting | Video | API | SMS | Email   ← 채널별 분리
        ▲
LANGUAGE ENGINE   : Detection | Translation Router                      ← 공유
        ▲
VOICE PIPELINE ★  : VAD | STT | Translation | TTS  (hot path 동결)        ← 공유 코어
```

**핵심 정합성:**
- V2는 "모든 채널을 한 몸으로" 가 아니라 **공유 Voice Pipeline 위에 채널별 어댑터(Delivery channel)** 를 두는 구조다.
- 즉 올바른 분리는 *전부 복제*가 아니라 **「공유 Voice Pipeline 코어 + 채널별 프로파일/어댑터」**.
  - 여행 대면 통역 = `face` 채널 프로파일 (auto-detect, GPS, 증가율 VAD)
  - VoIP = `voip` 채널 프로파일 (지정 언어 락, silero, 에코 억제)
  - 채팅 = `chat` 채널 프로파일 (텍스트, 지정 언어)
- 이렇게 하면 **hot path 동결**을 지키면서(계약 불변, 모드 파라미터만 명시화) V2 Delivery 어댑터로 자연 승격된다.

> **시사점:** "채널 프로파일 경계"를 지금 도입하면 그것이 곧 V2 Delivery 채널 어댑터의 씨앗이 된다. 분리 작업이 V2 재작업이 아니라 **V2로 가는 1단계**가 된다.

---

## 5. 선택지 A / B / C

### Option A — 논리적 분리 (Channel Profiles) · **권장**
- 백엔드: `voice-translate`에 **명시적 mode**(`designated` | `bilingual`) 경계 도입. `designated`는 **언어 락 STT + 불일치거부 제거**(스크립트 불일치는 조용히 스킵만).
- 프론트: 이미 갈린 컨트롤러를 채널 프로파일로 공식화(face/voip/chat).
- 공유 Voice Pipeline 코어 보존 → **hot path 계약 불변**.
- 장점: 저위험·신속·버그 해결·**V2 Delivery 어댑터로 직승격**. 단점: 물리적 파일 분할은 아님(추후 B에서 수행).

### Option B — 물리적 분리 (엔드포인트/화면/모듈 완전 분할)
- `/api/voice/designated`, `/api/voice/bilingual` 별도 엔드포인트, 프론트 화면/서비스/VAD 모듈 분리.
- 장점: 장기 소유 경계 가장 깔끔. 단점: **대규모 리팩터링, 핫패스 동결 위반 위험, 회귀 위험, 기간 김.**

### Option C — 즉시 핫픽스(designated-lock) 우선, 분리 설계는 단계적 · **현실적**
- 1단계: VoIP/채팅을 **지금 즉시** 지정 언어 락 + 불일치거부 제거로 전환 → 딜리버리 정상화(오늘 문제 해결).
- 2단계: 그 수정을 A의 채널 프로파일 추상화로 흡수·공식화.
- 3단계(선택): V2 시점에 B로 물리 분할.

---

## 6. 권장안 — **C → A (단계적), B는 V2에서**

| 단계 | 내용 | 위험 | 효과 |
|------|------|------|------|
| **1 (즉시)** | VoIP/채팅 `designated-lock` STT + 불일치거부 제거(스크립트 불일치만 조용히 스킵) | 낮음 | 딜리버리 정상화(오늘 버그 해결) |
| **2** | 백엔드 `mode` 경계 명시화 + 프론트 채널 프로파일(face/voip/chat) 공식화 | 낮음 | 분기 혼재 제거·독립 튜닝 |
| **3** | 대면 통역 증가율 VAD를 VoIP 무음/에코 스킵에도 반영(공유 코어) | 중 | no-speech 거부 폭주 제거 |
| **4 (V2)** | Delivery 채널 어댑터로 승격(`backend/communication/`), 필요 시 물리 분할(B) | — | V2 Delivery Engine |

- **hot path 동결 준수:** 1~3단계는 `voice-translate`/`voip-voice-relay/*` *계약*을 바꾸지 않고 모드 파라미터·내부 정책만 명시화.
- **V1↔V2 연속성:** 2단계의 채널 프로파일 = V2 Delivery 채널 어댑터의 씨앗.

---

## 7. 영향 파일 맵 (단계별)

| 단계 | 파일 | 변경 |
|------|------|------|
| 1 | `backend/llm/router.py` | designated 경로: 언어 락 STT, 불일치거부 제거 |
| 1 | `apps/.../VoIPCallScreen.tsx`, `chat_router` | 스크립트 불일치는 조용히 스킵(이미 transient 처리됨) |
| 2 | `backend/llm/router.py` payload | `mode: 'designated'|'bilingual'` 명시 필드 |
| 2 | `apps/.../src/features/*` | 채널 프로파일 모듈(face/voip/chat) 경계 정리 |
| 2 | `worldlincoTuningConfig.ts` | 섹션별 프로파일 확정(이미 분리됨) |
| 3 | `faceConversationVadController.ts`, `voiceRelayOrchestrator.ts` | 증가율 VAD 공통화 |
| 4 | `backend/communication/` | V2 Delivery 어댑터 승격 |

---

---

## 8. 결정 및 진행 현황

- **결정(2026-06-18):** **C → A** 채택. (B는 V.2 시점)
- **근거(사용자 기준 = 정확성·속도·UX):** VoIP/채팅은 언어를 이미 알므로 자동감지·불일치거부가 정확성·속도·UX를 모두 깎는다. 지정 언어 락이 세 축을 동시에 개선.

### 1단계(C 핫픽스) — 구현 완료
| 항목 | 파일 | 상태 |
|------|------|------|
| designated STT 지정 언어 락(`lock_language`, auto-detect 폴백 제거) | `backend/llm/router.py` `_transcribe_mobile_voice_audio` | ✅ |
| designated 경로 언어 불일치 422 거부 **완전 제거** | `backend/llm/router.py` voice-translate else 분기 | ✅ |
| 프론트 지정 언어 명시 전달(`localSourceLang`) + transient 안내 유지 | `VoIPCallScreen.tsx`, `api/translate.ts` | ✅ |
| 백엔드 재배포(즉시 적용 — build 110에도 효과) | docker | ✅ (health 200) |
| build 111 빌드/설치 + 라이브 검증 | `app.json` versionCode 111 | 진행 |

### 1단계 라이브 검증(build 111) — 통과
일↔한 양방향 VoIP 실통화 로그: `ja→ko おはようございます→안녕하세요`, `ko→ja 고맙습니다→ありがとうございます`, `네, 반갑습니다→はい、嬉しいです` — **전부 200 OK, 422 거부 0건, 멈춤 0건.**

### 2단계(A 공식화) — 구현 완료
| 항목 | 파일 | 상태 |
|------|------|------|
| 백엔드 payload `mode: 'designated'|'bilingual'` 명시 필드(+레거시 `bilingual_mode` 폴백) | `backend/llm/router.py` `_resolve_voice_channel_mode` | ✅ |
| voice-translate 로그에 `mode=` 추가(관측성) | `backend/llm/router.py` | ✅ |
| 프론트 채널 프로파일 SSOT(face/voip/chat) | `src/features/channelProfiles.ts` | ✅ |
| `voiceTranslate` API `mode` 옵션 전송(기본 designated) | `src/api/translate.ts` | ✅ |
| VoIP가 `CHANNEL_PROFILES.voip.mode` 명시 전달 | `VoIPCallScreen.tsx` | ✅ |
| 대면 통역 payload `mode: 'bilingual'`/수동 `mode: 'designated'` | `App.tsx` | ✅ |
| build 112 빌드/설치 + mode 명시 라이브 확인 | `app.json` versionCode 112 | 진행 |

> 채널 프로파일(`channelProfiles.ts`) + 백엔드 `mode` 필드 = **V.2 Delivery 채널 어댑터의 씨앗.** 하위호환(레거시 `bilingual_mode`) 유지로 hot path 동결 준수.

### 3단계(VoIP 증가율 VAD) + 재생 크래시 수정 — 구현·검증 완료 (build 113)
| 항목 | 파일 | 상태 |
|------|------|------|
| ★재생 크래시 수정: `VoiceRelayPlaybackQueue` import 누락(런타임 ReferenceError로 원격 TTS 미재생) | `VoIPCallScreen.tsx` | ✅ |
| VoIP meter-dead VAD: file-RMS → 증가율(byte-growth) | `VoIPCallScreen.tsx` | ✅ |
| 라이브 검증(build 113, 일↔한) | — | ✅ |

**build 113 라이브 결과:** 양방향 `VOIP_VOICE_RELAY_PLAYBACK`(`device_speech`) 재생 복원, `VoiceRelayPlaybackQueue` 에러 0건, flush가 `max_duration`→`silence`로 개선. (잔여: meter-dead에서 가끔 `max_duration`·반복환각 — gibberish 필터 422로 차단)

> **교훈:** Metro/Babel은 타입 체크를 안 해 `VoiceRelayPlaybackQueue` 미import가 빌드는 통과하고 런타임 크래시로만 드러났다. TS 린트(L368/L834)가 신호였음.

### B(물리 분할)는 V.2에서
- 별도 엔드포인트/화면/모듈 분할은 V.2 `backend/communication/` Delivery 어댑터 승격 시점에 수행.

*작성: 2026-06-18 · C→A 결정 · 1단계 라이브 검증 통과 · 2단계 구현 완료(build 112 검증 진행)*
