# VoIP 통역 — 근본 작업 A 구현 계획서 (AEC 참조 루프 정합)

> **상태:** 📋 계획(PLAN) — 검토용. 코드 변경 전 단계.
> **기준 설계도(SSOT):** [`MOBILE_CALL_TRANSLATION_ARCHITECTURE.md`](MOBILE_CALL_TRANSLATION_ARCHITECTURE.md) §1.2·§2·§3.1·§4.2
> **실행맵:** [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md) 1번(VoIP 통역 안정화)
> **연계 트래커:** [`V2_FEATURE_AUDIT.md`](V2_FEATURE_AUDIT.md)
> **원칙:** 릴레이 public contract(`voice-translate` / `voip-voice-relay/*`) 동결, **캡처·재생 구현(내부)만** 교체 — Strangler Fig 정합. 한 번에 하나·실통화 검증.

---

## 0. 왜 이 계획인가 (땜질 중단 선언)

이번 세션의 텍스트/억제 가드(G7 meter-dead, G9 원격 트랙 강제 mute)는 설계도 §1.2가 경고한 **"버그 땜질"** 이었고, 증상의 근본을 못 건드렸다. 본 계획은 **설계도가 이미 확정한 근본 원인**만 다룬다. 재수정 없는 단일 방향.

---

## 1. 근본 원인 (라이브 로그 + 코드 + 설계도 3중 확정)

### 1.1 확정된 사실

| # | 사실 | 증거 |
|---|------|------|
| A | 음성 릴레이 **캡처는 이미 네이티브 `AudioRecord(VOICE_COMMUNICATION)`** | `VoiceRelaySileroVadModule.kt` L88–89 (`MediaRecorder.AudioSource.VOICE_COMMUNICATION`), 동일 스트림에서 세그먼트 PCM export(L45–57). 로그 이벤트명 `VOIP_VOICE_RELAY_NATIVE_CAPTURE` |
| B | 그런데 **TTS 재생은 expo-av `Audio.Sound`(미디어 스트림)** | `VoIPCallScreen.tsx` L967 `Audio.Sound.createAsync(... shouldPlay)`; 재생 직전 audio mode는 `setAudioModeAsync`(L869) |
| C | `VoipAudioModule`은 `MODE_IN_COMMUNICATION`+라우팅+볼륨만 설정, **AEC/NS/AGC 이펙트를 어떤 세션에도 attach 안 함** | `VoipAudioModule.kt`: `aec/ns/agc` 필드 선언(L42–44)·`releaseEffects()`만 있고 `AcousticEchoCanceler.create(sessionId)` **호출 0회** |
| D | 통화 중 S10 마이크가 **자기 스피커의 상대 TTS를 peak ≈ 0dB로 되잡음** | `call-978201e696c5` 로그: PLAYBACK 시점과 겹치는 `NATIVE_CAPTURE peak_db=0~-3` |
| E | 그 에코 캡처가 S10 턴을 잡아먹어 **굶김**(10분에 송신 기회 5회·`START_BLOCKED remote_tts_active` 146회·송신 0건) | 동일 통화 로그 |

### 1.2 근본 메커니즘 (설계도 §1.2·§3.1 매핑)

HW AEC(AEC3 계열)는 **스피커로 나가는 far-end(render) 신호를 참조(AnalyzeReverseStream)** 해 그만큼을 마이크 캡처에서 뺀다. `VOICE_COMMUNICATION` 캡처의 AEC 참조 루프는 **통화(voice-call/communication) 렌더 경로**다.

> **그런데 우리 TTS는 expo-av `Audio.Sound` = 미디어(STREAM_MUSIC) 경로로 재생**된다. 이 경로는 HW AEC의 참조 루프에 들어가지 않으므로, **AEC가 TTS를 "내가 낸 소리"로 인식하지 못해 빼지 못한다.** → 마이크가 TTS를 그대로 되잡음(peak≈0) → 자가 재캡처·턴 굶김.

설계도 §1.2 명문: *"스피커 음량↑ 와 에코 제거는 세트여야 한다. 한쪽만 하면 반드시 회귀한다."* / §3.1: *"출력은 상대(far-end)의 렌더 경로에 병렬 트랙으로 합류시킨다."*

**즉 근본 결함 = 캡처(AEC ON)와 재생(미디어 경로, AEC 참조 밖)의 경로 불일치.** AEC가 없는 게 아니라 **AEC가 참조할 곳에 TTS를 안 흘려보낸 것.**

---

## 2. 해결 설계 (A — AEC 참조 루프 정합)

### 2.1 목표 한 줄
**TTS 재생을 HW AEC가 참조하는 통화 렌더 경로(STREAM_VOICE_CALL / `USAGE_VOICE_COMMUNICATION`)로 옮긴다.** 그러면 `VOICE_COMMUNICATION` 캡처의 HW AEC가 그 TTS를 참조·소거 → 마이크가 자기 TTS를 안 잡음 → 굶김·자가에코 동시 해소.

### 2.2 변경 후보 (택1, §3에서 결정)

| 안 | 내용 | 장점 | 위험 |
|----|------|------|------|
| **A-1 (권장)** | 네이티브 재생 모듈 추가: TTS PCM/파일을 **`AudioTrack`(`AudioAttributes.USAGE_VOICE_COMMUNICATION`, `CONTENT_TYPE_SPEECH`, STREAM_VOICE_CALL)** 로 재생. expo-av `Audio.Sound` 재생을 이걸로 대체(통역 모드 한정). | HW AEC 참조 루프에 정확히 합류 → 설계도 정합·근본 해결. 기존 네이티브 캡처와 짝 | 네이티브 모듈 신규/확장. 재생 완료 콜백·볼륨·중단 처리 재구현 |
| A-2 | 명시적 `AcousticEchoCanceler.create(audioRecord.audioSessionId)`를 `VoiceRelaySileroVadModule` 캡처 세션에 attach | 작은 변경 | **단독으론 불충분** — TTS가 여전히 미디어 경로면 AEC 참조에 없어 못 지움. A-1과 병행해야 의미 |
| A-3 | expo-av audio mode를 통화 스트림으로 강제(`InterruptionModeAndroid` + STREAM_VOICE_CALL 매핑) | 네이티브 최소 | expo-av가 STREAM 매핑을 노출하지 않아 **신뢰 불가**(설계도 §4 expo-av 한계) |

### 2.3 보존 불변식 (회귀 방지 — 절대 건드리지 않음)
- §6.4 원음(WebRTC raw) 차단: `applyRemoteAudioSuppression`를 ontrack/onaddstream에서 호출(늦은 트랙 재음소거) — **제거 금지.**
- §8 라운드트립 셀프에코 가드(caller/callee 양방향, 원문 전사 동일언어 비교) — **유지.**
- §9 자기발신 차단(링/세션보다 먼저) — **유지.**
- 대면 통역 경로(App.tsx) — **🔒 동결, 무접촉.**
- 릴레이 public contract(전송 포맷·시그널 메시지) — **불변.**

---

## 3. 사전 확인 단계 (코드 변경 전 — 가설 확정)

> 한 줄도 고치기 전에 아래를 로그/코드로 못박는다. (잘못된 가설로 또 고치지 않기 위함)

- **C1. STT로 가는 오디오의 실제 출처 확정** — `VoIPCallScreen.tsx`의 send 경로(L1682 `getURI()` / L2247)와 네이티브 세그먼트 PCM export(`VoiceRelaySileroVadModule` beginCapture/export) 중 **무엇이 base64로 전송되는가.** (expo-av .m4a면 캡처도 MIC일 수 있으니 1.1-A 재검증)
- **C2. TTS 재생 스트림 확정** — `Audio.Sound`가 Android에서 어떤 스트림으로 나가는지(기대: STREAM_MUSIC). audio mode 설정(L869) 영향 포함.
- **C3. HW AEC 가용성** — 실기기에서 `enableVoipAudio` 반환의 `aec_supported`/`ns_supported`/`agc_supported` 값(Tab·S10 삼성). logcat로 1회 확인.
- **C4. 멀티 AudioRecord/AudioTrack 동시성** — 네이티브 캡처(VOICE_COMMUNICATION)와 네이티브 재생(AudioTrack VOICE_CALL) 동시 운용이 삼성에서 가능한지(§4.1 "MultiRecord 차단" 이력 참조).

**산출물:** C1–C4 결과표 → A-1/A-2 최종 확정. (가설이 틀리면 여기서 설계 수정, 코드 0줄)

### 3.1 C1–C4 결과표 (2026-06-20 실기기 확정, 코드 0줄)

| 항목 | 확정 결과 | 근거(파일·로그) | 결론 |
|------|-----------|------------------|------|
| **C1** STT 오디오 출처 | 네이티브 캡처 활성 시 **VOICE_COMMUNICATION WAV** 업로드(expo-av .m4a는 삭제). 네이티브 캡처 비가용 시에만 m4a 폴백 | `VoIPCallScreen.tsx` L1690-1718: `endVoiceRelaySileroCapture()` 성공 시 `uploadUri = nativeCaptureUri`, m4a `deleteAsync`. 캡처 소스는 `VoiceRelaySileroVadModule.kt` L88-89 `AudioRecord(VOICE_COMMUNICATION)` | 캡처는 **AEC 적용 소스가 맞다**. peak≈0 에코는 캡처 결함이 아니라 재생 경로 불일치 |
| **C2** TTS 재생 스트림 | **USAGE_MEDIA / STREAM_MUSIC** (expo-av `Audio.Sound`). 디바이스 폴백 `Speech.speak`도 media | `VoIPCallScreen.tsx` L967 `Audio.Sound.createAsync`. `setAudioModeAsync`(L894-901)에 Android 스트림/usage 오버라이드 **없음**(expo-av가 미노출, 설계도 §4 한계) | 재생이 AEC 참조 스트림(voice_communication) **밖** → 자기 TTS 소거 불가 |
| **C3** HW AEC 가용성 | S10 `audio_effects_sec.xml`: `aec`/`ns`가 **`<preprocess><stream type="voice_communication">`에만** `apply`. 주석 `<!-- fake AEC and NS -->` → AudioEffect는 스텁, 실상쇄는 **HAL/DSP가 voice-call RX(다운링크) 참조** | `adb cat /vendor/etc/audio_effects_sec.xml` (실기기 확인). 표준 `audio_effects.xml`엔 AEC/NS 미등재 | (1) 캡처에 AEC가 붙는다 ✓ (2) **A-2(소프트 attach) 무의미** — AEC 기준은 통화 RX이지 media가 아님 |
| **C4** 캡처/재생 동시성 | 단일 `AudioRecord(VOICE_COMMUNICATION)` 캡처 + 신규 `AudioTrack`(VOICE_CALL) **재생** 공존 가능(저위험) | `VoiceRelaySileroVadModule.kt` L45-47 주석: 과거 차단은 **두 개의 동시 캡처**(expo+Silero)였고 단일 캡처로 해결. 캡처+렌더는 별개 | A-1이 MultiRecord 차단을 **재유발하지 않음** |

**최종 확정:** **A-1 채택**(TTS를 네이티브 `AudioTrack` `USAGE_VOICE_COMMUNICATION`/STREAM_VOICE_CALL 렌더로 이전). A-2는 단독 무의미(C3), A-3는 expo-av 한계로 신뢰 불가(C2). 가설 수정 없음 → §4 구현 단계로 진행.

---

## 4. 구현 단계 (C 확정 후) — ✅ 코드 완료(2026-06-20, build 152)

1. ✅ **네이티브 재생 모듈** — 신규 `VoipTtsPlayerModule.kt`(name `VoipTtsPlayer`), `VoipIncomingAlertPackage`에 등록.
   - `playFile(path)`: MediaExtractor+MediaCodec 로 디코드 → `AudioTrack(MODE_STREAM)` 재생, 완료/중단까지 Promise 보류.
   - `AudioTrack(AudioAttributes.USAGE_VOICE_COMMUNICATION, CONTENT_TYPE_SPEECH)` — **통화 렌더(STREAM_VOICE_CALL) → HW AEC 참조 루프 합류.**
   - `stop()`: pause/flush/stop + worker join 으로 즉시 중단(다음 발화/종료 전).
   - (A-2 옵션 미적용 — C3에서 단독 무의미 확인, A-1만으로 충분 판단.)
2. ✅ **JS 브리지**(`native/voipAudio.ts`): `isVoipTtsPlayerNativeAvailable()`, `playVoiceCallTts(path)`, `stopVoiceCallTts()`.
3. ✅ **`VoIPCallScreen.playVoiceRelayOutput`**: 서버 TTS 파일을 **네이티브 통화-렌더로 우선 재생**(`voiceCallTtsNativeEnabledRef` 기본 on). 실패/미가용 시 **기존 expo-av `Audio.Sound` 경로로 폴백**(무회귀). 재생 로그 `tts_delivery: 'server_audio_voicecall_native'`. 네이티브 재생 중 `voiceRelayNativeTtsActiveRef`로 원격 억제 유지(조기 해제 방지). `stopVoiceRelayPlayback`에 네이티브 stop 연결.
4. **C(가드 정리)**: 실제 AEC 참조가 동작하면 `voiceRelaySuppressUntilRef` / `remoteListenHoldMs` 등 시간 가드를 **원격 config(B)로 단계 단축** → 굶김 해소. (AEC가 에코를 지우므로 안전) — *실통화 DoD 확인 후 별도 진행.*
5. ✅ **공정성 캡(굶김 방지 barge-in, build 153)** — `shouldStartVoiceRelayCapture`에 `fairnessBargeInMs`(SSOT `voip.fairness_barge_in_ms`, 기본 7000ms) 추가. 로컬이 그 시간 이상 연속으로 턴을 못 잡으면 캡처 강제 허용. **활성 재생(`remotePlaybackUntilMs`) 중에는 미적용**(자기 TTS 재캡처 방지), 에코 억제창·`remote_tts_active`는 상위에서 그대로 차단 → 푸는 것은 재생 종료 후 courtesy hold뿐. 굶김 시계=`lastLocalRelayAtMs`(통화 시작 초기화). 로그 `VOICE_RELAY_FAIRNESS_BARGE_IN`. 단위테스트 25/25.
6. ✅ **재무장 타이밍 정밀화(build 154)** — *개발자 보고 "발화 끝 ↔ 마이크 열림 불일치, 음성 발화중 마이크 녹음은 무의미"* 교정. 기존엔 `voiceRelaySuppressUntilRef`를 재생 **시작 시점에 추정치**(`playbackMs+700`)로 박아두고 재무장 대기(`scheduleVoiceRelayCaptureRetry`)가 그 추정창에 묶여, **추정 > 실제** 길이일 때 마이크가 최대 수초 늦게 열렸다(타이밍 불일치). 수정: `settleOnce`(실제 재생 종료=네이티브 `await playVoiceCallTts` resolve 시점)에서 억제창을 **실측 종료 기준 짧은 에코 꼬리**로 collapse — 네이티브(HW AEC) `VOICE_RELAY_NATIVE_ECHO_TAIL_MS=250`, expo/디바이스 폴백 `VOICE_RELAY_FALLBACK_ECHO_TAIL_MS=700`. 결과 재무장 = 실제 발화 종료 + max(턴가드 550, 꼬리). 재생 중 캡처는 종전대로 `remote_tts_active`로 차단(실제 녹음 0). turn 컨트롤러는 이미 `markRemotePlaybackDrained`로 실측 collapse돼 있어 억제창만 정합.

---

## 5. 병행 트랙 B (무재빌드 — 즉시 가능)

설계도 §5.3 표 기준 **백엔드 `worldlinco_tuning`** 원격 조정(APK 재빌드 불필요·회귀 시 즉시 복구):

| 키 | 현재 | 권장 | 근거 |
|----|------|------|------|
| `silence_ms`(hangover) | 950 | **700** | §5.3 "과다→종료 지연", 대화형 ≤500ms |
| `min_segment_ms` | 2800 | **2400** | 짧은 인사말 지연 완화 |
| `min_speech_span_ms` | 1800 | **1400** | 짧은 발화 누락 완화 |

> B는 A의 **선행 완화**일 뿐 근본이 아니다. B만으로는 §1.2대로 회귀한다. A 없이는 닫지 않는다.

---

## 6. 검증 기준 (DoD — 실통화 1회로 판정)

A 적용 빌드에서 **S10/원거리** 통화 로그가 아래를 만족해야 완료:

1. **에코 소거:** PLAYBACK 구간과 겹치는 `NATIVE_CAPTURE`의 `peak_db`가 현재 ≈0dB → **−25dB 이하**로 하락(자기 TTS 미캡처).
2. **굶김 해소:** `START_BLOCKED remote_tts_active` 비율 급감, S10 **송신 성공(SENT) ≥ 양방향 균형**.
3. **자가에코 0:** `roundtrip_self_echo`/`meter_dead_remote_playback_echo` 발동 없이도 자가 발화 재생 0건.
4. **무회귀:** §6.4 원음 차단(`suppressed:true` 적용)·§8·§9 불변식 로그 정상. 대면 동결 무접촉.

---

## 7. 위험·롤백

- **Feature flag:** `voiceCallTtsNative`(기본 on, 실패 시 expo-av 폴백). 네이티브 미가용 단말은 자동 기존 경로.
- **롤백:** 플래그 off → 즉시 build 151 동작. 네이티브 모듈은 추가일 뿐 기존 경로 미삭제.
- **단일 변경 원칙:** A-1만 먼저, 실통화 검증 후 C(가드 단축) 별도 진행.

---

## 8. 작업 순서 요약

```
[지금] 사전확인 C1–C4(코드 0줄) ──▶ A-1/A-2 확정
   │
   ├─(병행) B: worldlinco_tuning 원격 튜닝 → 지연 완화 실측
   │
   ▼
A-1 네이티브 통화-스트림 TTS 재생 구현 ──▶ 빌드 ──▶ 실통화 검증(§6 DoD)
   │  (무회귀 확인: §6.4·§8·§9·대면동결)
   ▼
C 가드 단축(원격 config) ──▶ 굶김 최종 해소 ──▶ 트래커 닫기
```

---

*작성: 2026-06-20 · 기준 설계도 §1.2·§3.1·§4.2 · 코드 증거 VoiceRelaySileroVadModule.kt L88 / VoipAudioModule.kt L42 / VoIPCallScreen.tsx L967 · 라이브 call-978201e696c5*
