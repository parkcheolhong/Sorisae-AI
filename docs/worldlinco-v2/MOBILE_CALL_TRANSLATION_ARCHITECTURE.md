# 모바일 통화 오디오 구조 + 통·번역부 연동 기술 레퍼런스

> 목적: WorldLinco VoIP 통역의 음성 문제(수신측 스피커 라우팅 / 에코 과증폭 / 음성 감지력)를
> "버그 땜질"이 아니라 **표준 통화 오디오 아키텍처**에 입각해 해결하기 위한 근거 문서.
> 모든 항목은 공개된 1차/2차 문서에 근거한다(하단 References).

---

## 1. 표준 모바일 통화(VoIP) 오디오 스택

통화 오디오는 항상 **두 개의 스트림**으로 나뉜다. 이것이 모든 통화 SW의 공통 골격이다. (WebRTC APM 공식 헤더 정의 — Ref [1][2])

- **Near-end (Capture / 송신)**: 내 마이크 → 처리 → 네트워크로 송신
- **Far-end (Render / 수신)**: 네트워크 수신 → 처리 → 내 스피커로 출력

```
        ┌──────────────────────── 내 단말(클라이언트) ────────────────────────┐
        │                                                                      │
 마이크 │  ┌──────────── Near-end (ProcessStream) ────────────┐                │
 ──────►│  │ HPF → AEC3 → NS → AGC2 → (VAD) → Encoder(Opus)   │ ──► 네트워크   │
        │  └───────────────────────────────────────────────────┘    송신       │
        │            ▲ (참조 신호: 에코 제거용)                                 │
        │            │ AnalyzeReverseStream(render_frame)                       │
        │  ┌─────────┴──── Far-end (ProcessReverseStream) ────┐                │
 스피커 │  │ Decoder(Opus) → Jitter Buffer → (NS) → 출력       │ ◄── 네트워크   │
 ◄──────│  └───────────────────────────────────────────────────┘    수신       │
        │                                                                      │
        └──────────────────────────────────────────────────────────────────────┘
```

### 1.1 캡처 처리 순서는 "고정"이며 순서가 중요하다
APM은 마이크 신호를 **고정된 순서**로 처리하고, 각 단계는 직전 단계가 끝났다고 가정한다. 재배치하면 깨진다. (Ref [3][5])

```
High-Pass Filter → AEC(AEC3) → Noise Suppression(NS) → Automatic Gain Control(AGC2) → VAD
```

| 단계 | 역할 | 우리 증상과의 관계 |
|------|------|--------------------|
| HPF | 저주파 제거(음성 대역 분리) | - |
| **AEC** | **스피커(far-end) 신호가 마이크로 재유입되는 에코 제거** | **"에코 과증대"의 정답 단계** |
| NS | 환경 소음 억제 | STT 환각/오탐 감소 |
| AGC | 화자별 음량 편차를 일정 레벨로 보정 | "음량이 작다/들쭉날쭉" |
| VAD | 음성 구간 검출 | **"음성 감지력 하위"의 정답 단계** |

### 1.2 AEC의 핵심 = 참조 루프(Reference Loop)
에코 제거는 마법이 아니다. **스피커로 나가는 far-end 신호를 미리 분석(`AnalyzeReverseStream`)** 해서, 그 신호가 마이크로 되돌아온 만큼을 캡처 신호에서 **빼는(subtract)** 방식이다. 그래서:

- 스피커를 크게 틀수록(우리 build 114: 스피커 ON + 볼륨 1.0) **참조 루프가 없으면 에코가 폭증**한다. → 우리가 겪은 "음량 키웠더니 에코 과증대"는 교과서적 실패 모드다.
- 즉 **스피커 음량 ↑ 와 에코 제거는 세트**여야 한다. 한쪽만 하면 반드시 회귀한다.

---

## 2. Android에서 통화 오디오를 켜는 표준 방법

플랫폼(특히 삼성 등 OEM)이 제공하는 하드웨어 3A(AEC/NS/AGC)를 끌어다 쓰는 정석. (Ref [6][7][8])

1. **녹음 시작 *전에* 통신 모드 설정** — `AudioManager.MODE_IN_COMMUNICATION`
   - 삼성 단말 AEC 활성화의 가장 중요한 조건(검증된 SO 답변 Ref [7]).
2. **녹음 소스를 VoIP용으로** — `MediaRecorder.AudioSource.VOICE_COMMUNICATION`
   - 공식 문서: "echo cancellation 또는 automatic gain control 을 가능하면 활용한다" (Ref [6]).
3. **출력 라우팅 = 내장 스피커** — API 31+ `setCommunicationDevice(TYPE_BUILTIN_SPEAKER)`, 이하 `isSpeakerphoneOn = true` (Ref [8]).
4. **명시적 이펙트(선택)** — `AcousticEchoCanceler.create(sessionId)`, `NoiseSuppressor`, `AutomaticGainControl` 를 녹음 세션 ID에 붙여 강제 활성화 (Ref [7]).
5. **통신 모드의 음량은 미디어 음량이 아니라 `STREAM_VOICE_CALL`** 을 따른다 → 최대로 올려 "음량 작음" 회귀 차단.

> ⚠️ **expo-av 한계(중요)**: 현재 캡처는 `expo-av Audio.Recording`(기본 MIC 소스)이라 **VOICE_COMMUNICATION 도, AEC 도 적용되지 않는다.** 이것이 우리 에코 문제의 구조적 원인이다. 따라서 통화 동안 **네이티브에서 통신 모드를 강제**하거나, 장기적으로 **네이티브 AudioRecord(VOICE_COMMUNICATION) 캡처로 교체**해야 한다.

---

## 3. 통·번역부 연동 구조 (Speech Translation Layer)

업계 표준은 **캐스케이드 파이프라인**이다. (Ref [9][10][11][12][13])

```
[Near-end 캡처 PCM (AEC 이후!)]
        │
        ▼
  VAD 엔드포인팅 ──(음성 구간 chunk)──►  비동기 큐
        │                                   │
        ▼                                   ▼
  STT(ASR, 스트리밍)  ──► MT(번역, Simultaneous) ──► TTS(스트리밍)
        │ chunk N            │ chunk N-1            │ chunk N-2
        └──────── 파이프라인 병렬 실행(asyncqueue) ──────┘
                                                    │
                                                    ▼
                          상대 단말의 Far-end 출력(스피커)에 "병렬 오디오 트랙"으로 합류
```

### 3.1 연동 지점(어디서 오디오를 가로채는가)
- **입력 탭(tap)은 반드시 AEC 이후의 near-end PCM**에서 한다. AEC 전 신호를 STT로 보내면 자기 스피커 소리까지 받아써서 환각·반복 루프가 생긴다. (우리가 겪은 그 문제)
- **출력은 상대(far-end)의 렌더 경로에 병렬 트랙으로 합류**시킨다. = "말한 사람의 번역 음성은 들어야 할 상대 스피커로." (방향성 원칙)

### 3.2 지연 예산 (Latency Budget)
| 시나리오 | 목표 지연 | 근거 |
|----------|-----------|------|
| 대화형(양방향 통화) | **총 체감 ≤ 500ms** | Ref [11] |
| Glass-to-glass(실제 영상통화 번역) | 1.2 ~ 3.0s | Ref [13] |
| 강의/방송 | 2 ~ 3s 허용 | Ref [11] |

핵심 설계 규칙(검증됨):
1. **스트리밍 ASR 필수** — 오프라인 ASR(전체 발화 대기)은 3.6s+ 로 폭증. 스트리밍은 5초 입력에 272~284ms. (Ref [11])
2. **비동기 큐로 단계 분리** — STT(N) / MT(N-1) / TTS(N-2) 동시 실행 → 최대 3.1배 지연 감소. (Ref [11])
3. **스트리밍 TTS** — 비스트리밍 TTS는 +4,200ms, 스트리밍 전환 시 475ms. 지연 예산의 대부분을 여기서 회수. (Ref [11])
4. **VAD 엔드포인팅의 침묵 타임아웃은 "환원 불가 지연"** — 너무 길면 응답이 굼뜨고, 너무 짧으면 말 중간을 자름. → "음성 감지력" 튜닝 포인트.

### 3.3 캐스케이드 vs End-to-End
- **캐스케이드(ASR→MT→TTS)**: 단계별 텍스트/오디오가 검사 가능(관측성·감사·PII), 전문 어휘 정확도↑, 벤더 유연성↑. 2026년에도 대부분의 상용은 캐스케이드. (Ref [13])
- **End-to-End(SeamlessM4T v2, DeepL Voice, Translatotron)**: 지연·운율(prosody) 유리, 그러나 디버깅/감사 어려움.
- **WorldLinco 권장**: 현재처럼 **캐스케이드 유지**(우리 백엔드 STT/번역/TTS 분리가 정확히 이 구조). 단계별 로그(우리의 `VOIP_VOICE_RELAY_SENT/PLAYBACK`)가 곧 관측성 자산.

---

## 4. WorldLinco 현재 구조 매핑 & 격차

| 표준 구성요소 | WorldLinco 현재 | 상태 |
|---------------|------------------|------|
| Near-end AEC/NS/AGC | expo-av 기본 MIC (3A 없음) | ❌ **격차 — 에코 원인** |
| 출력 라우팅(내장 스피커) | `playThroughEarpieceAndroid` (Issue #8465 로 불안정) | ⚠️ 불안정 → 네이티브 모듈로 대체 중 |
| VAD 엔드포인팅 | byte-growth VAD(프론트) | ⚠️ 감지력 튜닝 필요 |
| STT(ASR) | 백엔드 Faster-Whisper (chunk) | △ 스트리밍화 여지 |
| MT | 백엔드 번역 | ✅ |
| TTS | `expo-speech` 디바이스 TTS | △ 비스트리밍 |
| 단계별 관측성 | `VOIP_VOICE_RELAY_*` 로그 | ✅ 강점 |
| 방향성(상대 스피커 재생) | 라우팅 로직 정상(build 115 검증) | ✅ |

### 4.1 적용 중인 조치 (이 작업 분기)
- **네이티브 `VoipAudioModule`** 추가: 통화 시 `MODE_IN_COMMUNICATION` + 내장 스피커 라우팅 + `STREAM_VOICE_CALL` 음량 최대화 → 삼성 하드웨어 AEC 활성 + "수신측 내장 스피커" 보장 + "음량 작음" 회귀 차단. (§2의 1·3·5)
- 두 테스트 단말(Tab, S10)이 모두 **삼성**이라, §2의 통신모드 조건이 즉시 효과가 있을 가능성이 높다.

### 4.2 남은 로드맵(우선순위)
1. (단기) 네이티브 통신모드 적용 후 실기기에서 에코/음량/스피커 검증.
2. (중기) VAD 임계값 튜닝(침묵 타임아웃·증가율) — 감지력 개선.
3. (장기) 캡처를 **네이티브 AudioRecord(VOICE_COMMUNICATION + AEC/NS/AGC)** 로 교체해 expo-av 한계 제거. 필요 시 `react-native-webrtc`(APM 내장) 도입 검토.

---

## 5. 튜닝 정밀도 레퍼런스 (VAD / 엔드포인팅)

"음성 감지력 하위"는 임계값·구간 파라미터의 정밀 튜닝 문제다. 공개 문서 기준값과 우리 설정을 매핑한다.

### 5.1 Silero VAD 표준 파라미터 (Ref [14][15][16][17])
`faster-whisper`의 기본 VAD. 16kHz 기준, `get_speech_timestamps` 시그니처의 기본값:

| 파라미터 | 기본값 | 의미 | 튜닝 가이드 |
|----------|--------|------|-------------|
| `threshold` | **0.5** | 이 확률 이상이면 음성 | 소음 환경 **0.6–0.8**(오탐↓), 낮추면 미검출↓·오탐↑ |
| `neg_threshold` | threshold−0.15 | 구간 진입 후 이탈 임계(히스테리시스) | 끊김 방지용 이력 |
| `min_speech_duration_ms` | **250** | 이보다 짧은 음성은 버림 | 팬 소음 등 짧은 잡음엔 300 |
| `min_silence_duration_ms` | **100** | 이만큼 침묵해야 구간 분리 | 자연 멈춤에 말이 잘리면 **300–500** |
| `speech_pad_ms` | **30** | 구간 앞뒤 패딩 | 어두 잘림 방지 **100** |
| `window_size_samples` | **512** | 입력 청크 크기 | 16kHz는 **512/1024/1536만** 허용(그 외 성능 저하) |
| `max_speech_duration_s` | inf | 초과 시 마지막 침묵에서 분할 | 너무 긴 발화 방지 |

정확도는 **31.25ms 청크 단위** ROC-AUC로 측정되고, 단일 라벨 데이터셋에선 "연속 100ms 이상 음성"이면 음성으로 간주한다(Ref [16]).

### 5.2 WebRTC VAD (대안/보조) (Ref [18][19][20])
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `aggressiveness` | 0–3 (기본 2) | 높을수록 "음성이라 보고할 확률↑(보수적)" → **미검출률도 동반 상승** |
| `frame_duration_ms` | **10 / 20 / 30 만** | 짧을수록 저지연·고정밀, 길수록 효율적 |
| sample rate | 8000/16000/32000 | 16비트 모노 PCM만 |
| 실시간 엔드포인팅 | `SILENCE_LIMIT 15–20` 프레임 / `ONSET_CHUNKS 3` | 발화 종료 판정 / 발화 시작 트리거 (Ref [17]) |

### 5.3 WorldLinco 현재값 ↔ 권장 매핑
현재 `voiceRelaySegmentBoundary.ts` / 백엔드 `worldlinco_tuning`(silero_*):

| 우리 키 | 현재값 | 대응 표준 | 진단 & 권장 |
|---------|--------|-----------|-------------|
| `speechMs`(onset) | 120ms | min_speech_duration 250 | 120ms는 **민감**(미검출↓). "감지력 하위"가 onset 문제면 유지/하향(80~120). |
| `silenceMs`(hangover) | 950ms | min_silence 100~500 | **과다** → 발화 종료 지연(체감 지연↑). 대화형 ≤500ms 목표면 **600~750**로 단계 하향 권장. |
| `minSegmentMs` | 2800ms | — | 최소 세그먼트 길이. 짧은 인사말이 늦으면 **2200~2500**. |
| `minSpeechSpanMs` | 1800ms | — | 누적 음성 최소. 짧은 발화 누락 의심 시 **1200~1500**. |
| `safetyCapMs` | 14000ms | max_speech_duration | 너무 길면 분할 지연. 유지 가능. |
| Silero `threshold` | (네이티브 기본 0.5) | 0.5 | 에코/소음 오탐이면 **0.6**, 미검출이면 **0.4**. |

> ✅ **핵심**: 이 silero_* 값들은 **백엔드 `worldlinco_tuning` 으로 원격 조정**되므로 **APK 재빌드 없이** 정밀 튜닝/회귀 복구가 가능하다. → "한 번 고정하면 회귀 없어야 한다"는 요구와 정합. 기준값을 SSOT로 박고, 실측(로그의 silence_ms/speech_ms/min_segment_ms 이벤트)으로 미세 조정한다.

### 5.4 정밀 튜닝 절차(권장)
1. 한 변수만 바꾼다(예: `silenceMs` 950→700). 동시 변경 금지(원인 분리).
2. 실기기 30초 대화 → 로그에서 onset 지연 / 미검출 / 끊김 / 에코 카운트.
3. 31.25ms 단위 정확도 개념대로, "연속 100ms 음성" 미달 발화가 잘리는지 확인.
4. 목표: 대화형 총 체감 ≤ 500ms(§3.2) 안에서 미검출 0 우선.

## 6. [고정] 통역 통화에서 원음(WebRTC raw)이 새던 근본 원인과 수정 — build 117

### 6.1 증상(사용자 보고)
> "발신자가 원음으로 말하는데 **원음이 바로 수신 스피커에서 같이 들리고 조금 있다 통역음이 들린다**."
즉 통역(풀오토) 통화인데 상대의 **원본 음성(WebRTC raw audio)** 이 번역 TTS와 **동시에** 수신측 스피커로 재생됨. (음향 누화/크로스토크 아님 — SW 경로 문제)

### 6.2 근본 원인 (로그로 확정)
통역 통화에서 원음 차단은 **2중 안전장치**로 설계돼 있었다.
1. **송신측**: `suspendLocalAudioForVoiceRelay()` — 내 마이크 트랙 `stop()` + `sender.replaceTrack(null)` → 송신 영구 중단. (정상 동작, 로그 `KEEP_SUSPENDED` 43회 확인)
2. **수신측**: `setRemoteAudioSuppressed(true)` → `client.setRemoteAudioEnabled(false)` → 원격 오디오 트랙 `enabled=false`.

**버그**: 2번이 **연결 직후 1회성**으로 호출되는데, 그 시점엔 react-native-webrtc 의 **원격 오디오 트랙이 아직 도착하지 않았다**(`ontrack` 이 연결 후 수 초 뒤 발생). 따라서 `setRemoteAudioEnabled(false)` 가 **빈 스트림에 대한 no-op** 으로 끝나고, 이후 도착한 원격 트랙은 **기본값 `enabled=true`** 그대로 살아 원음을 재생. 트랙 도착 시 음소거를 **재적용하는 코드가 없었다.**

- 증거(과거 빌드 로그, call-13cfc04cc365): `VOIP_REMOTE_AUDIO_SUPPRESSION suppressed:true` 1회 발생했으나 `[VoIP][Diag] setRemoteAudioEnabled` 로그는 **0회**(=실제 트랙에 한 번도 적용 안 됨). `ontrack`(audio)은 그보다 **약 26초 뒤** 발생.
- 결과적으로 원음 차단은 **오직 송신측 mic suspend 에만** 의존, 수신측 안전장치는 죽어 있었음. 한쪽이라도 suspend 가 늦거나 비대칭이면 원음이 그대로 샘.

### 6.3 수정 (build 117)
- `voipCallClient.ts`: 클라이언트에 **억제 상태를 영구 저장**(`remoteAudioSuppressed`). `setRemoteAudioEnabled()` 는 트랙이 없어도 상태를 기억. **`onaddstream`/`ontrack` 콜백에서 `applyRemoteAudioSuppression()` 을 매번 호출** → 늦게 도착한 트랙에도 즉시 `enabled=false` 재적용.
- `VoIPCallScreen.tsx`: 연결 시 억제 조건에서 `voiceRelayServerReady` 를 제거 → 통역 모드(`voiceRelayEnabled`)면 **연결 즉시** 원음 차단(서버 준비 대기 윈도우 제거). 해제는 통역 모드에서 끝까지 막음(`releaseRemoteAudioSuppressionIfAllowed` 가드 유지).

### 6.4 검증 증거 (build 117, call-8f1d1480739c, 2026-06-18)
- **Tab(발신)**: 연결 시 `setRemoteAudioEnabled enabled:false, trackCount:0, hadStream:false` → 4초 뒤 `ontrack` → `applyRemoteAudioSuppression reason:ontrack, enabled:false, trackCount:1, **changed:true**`(트랙을 실제로 enabled→disabled 전환) → `Remote stream update: hasAudio:false`.
- **S10(수신)**: 트랙 선도착 → `setRemoteAudioEnabled enabled:false, trackCount:1, hadStream:true` 즉시 적용.
- **통화 전 구간 억제 해제 0회**: Tab `enabled:true`=0, `suppressed:false`=0 / S10 `suppressed:false`=0.
- 송신측 `KEEP_SUSPENDED`(mic 영구 정지) 유지. → **WebRTC 원음 경로가 송·수신 양방향 + 통화 전 구간 완전 차단.**

> ⚠️ 회귀 방지 원칙: 통역(풀오토) 통화에서 원격 오디오 트랙은 **트랙 도착 시점(ontrack)에 반드시 재음소거**해야 한다. 1회성 호출로만 끄면 react-native-webrtc 의 늦은 ontrack 때문에 원음이 살아난다. `applyRemoteAudioSuppression` 호출을 ontrack/onaddstream 에서 제거하지 말 것.

---

## 7. "음성이 반대로 / TAB 발화 안됨" 진단 + 무음 환각 차단 강화 (build 118)

### 7.1 사용자 신고
- "음성이 반대로 나온다 / 발신에서 음성이 나온다 / 수신에서 나와야 한다 / TAB에서 음성발화를 못한다."

### 7.2 실측 진단 (call-1e66d81124d0, 2026-06-18)
| 방향 | 클라이언트 SENT | 상대 PLAYBACK | 서버 relay |
|---|---|---|---|
| Tab(ko)→S10 | 6 | **S10: 6 (정상)** | 정상 |
| S10(ja)→Tab | 4 | **Tab: 1 (저하)** | callee→caller 일부만 |

- **라우팅 방향은 코드대로 정상**: "발신이 말하면 수신에서 발화"가 검증됨(Tab 발화 → S10 6/6 재생). `_relay_app_signal` 이 `from_role` 을 정확히 찍어 상대에게만 전달 → `isLocal` 오분류 아님. **방향을 뒤집는 수정은 정상 경로(Tab→S10)를 깨므로 금지.**
- 진짜 원인: **두 폰이 같은 방·스피커 상태** → S10 마이크가 친구 목소리 대신 에코/무음을 잡고 → Whisper 가 "ご視聴ありがとうございました"(→"시청해주셔서 감사합니다"), 반복 "안녕하세요" 같은 **무음 환각**을 생성 → 채널 오염 + 422 폭주 → Tab 에 정상 발화가 거의 안 도착 → "TAB이 발화 못한다"로 체감.

### 7.3 수정 (build 118)
- `voiceRelayOrchestrator.ts` `SILENCE_HALLUCINATION_PATTERNS` 에 **일본어(`ja`) 무음 환각 패턴 추가**("ご視聴ありがとうございました/ありがとうございます/チャンネル登録お願いします/おやすみ/バイバイ/はい/えーと/あの/ん" 계열)와 **한국어 아웃트로 패턴 보강**("시청해 주셔서 감사합니다/감사합니다/구독·좋아요 부탁" 계열). `ja` 1글자 이하도 무음 환각 처리.
- 적용 위치: 캡처측 전송 직전 게이트 `isLikelySilenceHallucination(transcript, sourceLang) && silenceCapture`. **마이크 무음(`silenceCapture`)일 때만** 드롭하므로 실제 발화는 통과 — 회귀 위험 최소.

> ⚠️ 회귀 방지 원칙: 같은 방 테스트는 에코/환각의 물리적 원인이므로 **분리 환경(다른 방/이어폰) 검증을 기준**으로 한다. 무음 환각 패턴은 캡처측에서 `silenceCapture` 와 AND 로만 적용하고, 원격 재생 경로(§6.x의 NOTE)에서는 인사말을 막지 말 것(대화 핵심 손실 방지).

---

## 8. "발신이 자기 발화를 되듣는다" — 라운드트립 셀프 에코 차단 (build 119)

### 8.1 사용자 요구(설계 불변식)
- "발신은 녹음→전송만, 발화는 수신에서만. 발신부에서 저혼자 듣고 발화하면 안 된다."
- 즉 **발신 폰은 자기 발화의 (되돌아온) 통역을 절대 재생하면 안 된다.**

### 8.2 원인
- 발신측 캡처/전송 경로(`processVoiceRelaySegment`)에는 로컬 TTS 재생이 **없음**(발신이 자기 번역을 직접 발화하진 않음). 그러나 **라운드트립 에코 루프**가 존재:
  1. Tab(ko) 발화 → S10 에 일본어 전송
  2. S10 이 일본어 TTS 재생 → **S10 마이크가 그 TTS 를 다시 캡처**
  3. S10 이 ja→ko 재번역 → Tab 으로 전송
  4. Tab 이 재생 → **발신자가 자기 발화의 ko 에코를 되들음**
- 기존 caller 전용 `acoustic_echo_relay` 가드는 **내 '번역문'(상대 언어=ja) vs 들어온 번역문(ko)** 을 비교해 언어가 달라 **절대 매칭되지 않아 무력**했다.

### 8.3 수정 (build 119)
- `VoIPCallScreen.tsx`: `lastLocalRelayTranscriptRef`(내가 인식한 **원문 전사**, 내 언어) 신규 추가. 전송 시 기록.
- 원격 relay 수신 시, **들어온 번역문(translatedText)을 내 원문 전사와 같은 언어로 비교**해 유사하면 `roundtrip_self_echo` 로 드롭. **caller/callee 양방향 적용**(루프는 양쪽 모두 발생). 15초 윈도우 + 단어 50% 겹침/포함 관계로 판정.

> ⚠️ 회귀 방지 원칙: 셀프 에코 판정은 반드시 **들어온 번역문 vs 내 '원문 전사'(동일 언어)** 로 비교한다. 내 '번역문'(상대 언어)과 비교하면 언어가 달라 영구 무력화된다. 이 가드를 caller 전용으로 되돌리지 말 것(callee 도 동일 루프에 노출).

---

## 9. "발신측에서도 신호음이 울린다" — 자기발신 자가-수신 차단 (build 120)

### 9.1 증상
- 발신자가 통화를 걸면 수신자와 **동시에 발신자 폰에서도 신호음이 울림**.

### 9.2 원인 (로그: Tab `VOIP_INCOMING_CALL_SUPPRESSED_ACTIVE_SESSION`)
- `applyIncomingVoipPayload`(App.tsx)에 자기발신 차단 로직(`isSelfIncomingPayload`)이 **존재했지만, 링 트리거(pending-call 블록 `startIncomingVoipAlert`)보다 뒤(아래)에 위치**해 너무 늦게 실행됨.
- 발신 직후 **세션 등록 전(`voipCallInitResponseRef` 미설정) 타이밍**에 발신자의 수신 폴링(`pending_call_poll`)이 자기가 만든 통화를 되받아 → active-session 억제도 안 되고 → 링이 먼저 울린 뒤에야 늦은 self-check 로 무시됨.

### 9.3 수정 (build 120)
- `applyIncomingVoipPayload` 진입부(`missing_call_payload` 체크 직후, **active-session 억제·링 로직보다 앞**)에 자기발신 가드 신규 배치: `caller_user_id == userInfo.id`(숫자) 우선 + `caller_voice_id == nado-XXXXXX`(보조) 비교로 자기 통화면 `self_originated_outgoing_call` 로 즉시 무시 + 알림 정리(`stopIncomingVoipAlert`/`setPendingIncomingVoipCall(null)`).

> ⚠️ 회귀 방지 원칙: 자기발신 차단은 **링/세션 로직보다 반드시 먼저** 수행한다. 발신자는 어떤 경우에도 자기 통화로 인해 수신 신호음이 울려선 안 된다. 늦은 위치의 self-check 만 의존하지 말 것.

---

## References

1. WebRTC APM 공식 헤더 — `audio_processing.h` (near-end/far-end, ProcessStream/AnalyzeReverseStream, VAD/AGC 정의). chromium.googlesource.com
2. Android-Audio-Processing-Using-WebRTC (near-end 처리 순서: HPF→AEC→NS→AES→VAD→AGC). github.com/mail2chromium
3. Gaudio Lab — WebRTC APM 서브모듈/스트림 설명(ProcessReverseStream 의 AEC 참조 역할).
4. RG4.NET — APM 사용 예시(AnalyzeReverseStream → set_stream_delay_ms → ProcessStream).
5. ForaSoft — "The WebRTC audio pipeline end-to-end" (고정 순서 HPF→AEC3→NS→AGC2, AGC chase 실패 모드).
6. Android 공식 — `MediaRecorder.AudioSource.VOICE_COMMUNICATION` ("echo cancellation/AGC 활용"). developer.android.com
7. StackOverflow 46560814 — 삼성 AEC: `MODE_IN_COMMUNICATION` 을 AudioRecord 생성 전에 설정 + `VOICE_COMMUNICATION` + `AcousticEchoCanceler`/`NoiseSuppressor`.
8. StackOverflow 13960313 — STREAM_VOICE_CALL/STREAM_MUSIC, `MODE_IN_COMMUNICATION` + `setSpeakerphoneOn` 라우팅.
9. arXiv 2407.11010 — Cascaded streaming speech translation(실시간 ASR + Simultaneous MT + TTS/display).
10. arXiv 2306.01201 — Simultaneous S2ST, Whisper 온라인 질의 + 발화 정책(speak/discard) + 멀티스레드 파이프라인.
11. Deepgram — Real-Time S2S Translation Architecture Guide(≤500ms, async queue 3.1x, 스트리밍 TTS 4200→475ms, 스트리밍 ASR 필수).
12. expo-av `setAudioModeAsync` / Issue #8465(부분 옵션이 audio sink 를 in-call/이어피스로 바꿈), PR #8474(`playThroughEarpieceAndroid` 기본 false).
13. ForaSoft — Real-Time Speech Translation 2026(캐스케이드 vs E2E 트레이드오프, glass-to-glass 1.2~3.0s).
14. snakers4/silero-vad Discussion #562 — `get_speech_timestamps` 기본값(threshold 0.5, min_speech 250, min_silence 100, speech_pad 30, window 512).
15. snakers4/silero-vad DeepWiki Advanced Usage — neg_threshold = threshold−0.15(히스테리시스), max_speech_duration_s 분할.
16. snakers4/silero-vad Wiki Quality Metrics — 31.25ms 청크 ROC-AUC, "연속 100ms 음성=음성".
17. VAD Troubleshooting(itsvasugrover) — 소음 환경 threshold 0.6~0.8, min_silence 500/ speech_pad 100, SILENCE_LIMIT 15~20 / ONSET_CHUNKS 3.
18. py-webrtcvad DeepWiki — aggressiveness 0~3(0 보수적·오탐多, 3 공격적·미검출多), frame 10/20/30ms.
19. WebRTC `webrtc_vad.h` 공식 — set_mode 동작/유효 rate·frame 조합.
20. jhj0517/Whisper-WebUI Wiki — faster-whisper Silero VAD 파라미터 설명(window 512/1024/1536 권장).
