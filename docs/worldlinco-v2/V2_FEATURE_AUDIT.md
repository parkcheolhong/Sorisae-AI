# WorldLinco V.2 — 음성/통화 기능 파일별 전수 검사 체크리스트 (SSOT)

> **용도:** 대면 통역 + VOIP 통화 hot path의 파일별 현상태·정합성 점검 결과와 조치 추적.
> **원칙:** 일관성(consistency)·정합성(integrity) 우선. 한 곳을 고치면 다른 곳이 깨지는 일을 막기 위해 **공유 로직은 단일 출처(SSOT)** 로 수렴시킨다.
> **연계:** [`FILE_MAP.md`](FILE_MAP.md) · [`WORLDLINCO_V2_ROADMAP.md`](WORLDLINCO_V2_ROADMAP.md) · [`MOBILE_CALL_TRANSLATION_ARCHITECTURE.md`](MOBILE_CALL_TRANSLATION_ARCHITECTURE.md) · [`SELF_EVOLVING_ENGINE_DESIGN.md`](SELF_EVOLVING_ENGINE_DESIGN.md)(자가 진화형 엔진 2층 설계 — 자동튜닝·연속학습·평가게이트) · [`TELEPHONY_BRIDGE_DESIGN.md`](TELEPHONY_BRIDGE_DESIGN.md)(일반 전화 착신 통역) · [`EMOTION_EXPRESSIVE_DESIGN.md`](EMOTION_EXPRESSIVE_DESIGN.md)(감성·표현형 통역)
> **최종 갱신:** 2026-06-21 · 앱 v1.0.103(build 155) 기준 · **G10** A-1 + 공정성 캡 + 재무장 타이밍 정밀화(154) + **반이중 "녹음 중 재생 무음" 레이스 차단(155)**: 수신 시 로컬 녹음 stop teardown(`stopAndUnloadAsync`)을 **재생 전 await** → 마이크 동시 오픈 시 AudioTrack이 미해제 AudioRecord와 충돌해 재생이 무음으로 죽던 문제 차단. + **발신 3~7초 창 튜닝(config v3)**: `silero_min_segment_ms`3000·`silero_safety_cap_ms`7000·`silero_silence_ms`1000(무재빌드). 계획서 `VOIP_AEC_CAPTURE_PLAN.md` §4.6~7

---

## 🔒 동결 선언 (LOCKED — 수정 불가)

> **대면 통역(Face Interpretation) — 2026-06-20 build 149 기준 완료·동결.**
>
> 사용자 지시로 **대면 통역 경로를 "수정 불가(LOCKED)"** 로 잠금한다. 아래 코드 경로는 **명시적 사용자 승인 없이는 변경 금지**(에코 가드·발화 경로·VAD·UI 포함):
>
> | 동결 대상 | 파일/위치 | 잠금 사유 |
> |-----------|-----------|-----------|
> | 대면 자동음성 핸들러 | `App.tsx` — bilingual STT→MT→TTS 루프(L8080~8400대) | 검증 완료(에코 가드 G2 + 이중발화 G8) |
> | 일반 자동발화 effect | `App.tsx` — `resultText` useEffect(L4466~) 디바이스 발화 분기 가드 | G8 수정 검증 완료 |
> | 대면 서버 TTS 재생 | `App.tsx` — `playFaceTranslationOutput`(L2150~) | 단일 발화 SSOT |
> | 대면 VAD | `face-conversation/faceConversationVadController.ts` | 동작 안정 |
>
> **규칙:** ① 다른 섹션(VOIP·G7 등) 작업이 위 대면 경로를 건드려야 하면 **먼저 사용자에게 보고·승인**받는다. ② 공유 헬퍼(`relayTextsSimilar`, `scriptLangResolver` 등)를 수정할 경우 대면 회귀가 없음을 증명한 뒤에만 진행한다. ③ 이 잠금은 사용자가 명시적으로 해제하기 전까지 유효하다.

---

## 0. 아키텍처 요약 — 같은 파이프라인, 두 개의 턴테이킹

STT→MT→TTS 파이프라인은 동일하지만 턴 제어가 **두 갈래**다. 이 분기가 정합성 갭의 근원이다.

| 구분 | 대면(App.tsx) | VOIP(VoIPCallScreen + voip-voice-relay/*) |
|------|---------------|-------------------------------------------|
| 캡처 | 이산형: 녹음→VAD flush→정지/언로드→STT | 연속 캡처 + 턴 컨트롤러 |
| 반이중 | **OS 레벨**(녹음기 정지 + `allowsRecordingIOS:false`) + `faceSpeakingRef` 게이트 | **소프트웨어 suppress 창**만(재생 중에도 마이크 녹음 유지) |
| 에코 차단 | 공유 가드 + 자체 추가 가드(`substringEcho`/`outputLangEcho`/silence) | 공유 가드 + 인라인 `roundtrip_self_echo` |
| 재생 쿨다운 | 게이트 1500ms 유지 | suppress 4800/5800ms |

---

## 1. 클라이언트 파일별 점검 (`apps/mobile-nadotongryoksa`)

| 파일 | 영역 | 역할 | 정합성 위험/갭 | 상태 |
|------|------|------|----------------|------|
| `App.tsx` (대면 섹션) | 대면 | 대면 자동음성 루프: 캡처·bilingual STT·에코필터·TTS 게이트 | `outputLangEcho`가 **STT 라벨(`data.from`)에 의존** → 오판정 시 정상 발화 오차단 위험 / 에코는 라벨이 ko로 와서 못 막던 케이스 | ⚠️ 잔존(아래 G2) |
| `src/features/voip-voice-relay/voiceRelayOrchestrator.ts` | 공유 | 언어 비의존 에코/지비리시/반복/무음 가드 + VAD 상태머신 | `maxSegmentMs=7000` 폴백이 런타임 SSOT(12000)와 불일치 | ✅ 에코 가드 보강(아래 F1) |
| `voiceRelayTurnController.ts` | VOIP | 반이중 턴 상태머신, 재생 후 청취 홀드, 원격 dedupe | `remoteListenHoldMs=2100` 폴백 vs SSOT 2600 불일치 | ⚠️ 잔존(G1) |
| `voiceRelaySegmentBoundary.ts` | VAD | Silero 종단→flush 게이트 | `safetyCapMs=7000`/`silenceMs=1000` 폴백 vs SSOT 12000/1400 | ⚠️ 잔존(G1) |
| `voiceRelayAudioMetrics.ts` | VAD | meter-dead RMS 추정 | 기본 -58 vs 대면 -50 vs voip -52 — 임계 3종 | ⚠️ 잔존(G1) |
| `voiceRelayPlaybackQueue.ts` | VOIP | 원격 재생 seq 순서 FIFO | 최대 길이/staleness 캡 없음, 대면엔 대응 큐 없음 | 🔵 향후 |
| `face-conversation/faceConversationVadController.ts` | VAD | 대면 meter-poll VAD(파일 증가율 의사 VAD) | bytes/sec 휴리스틱(1800/0.5/0.6) 하드코딩·대면 전용 | 🔵 향후 |
| `src/screens/VoIPCallScreen.tsx` | VOIP | VOIP relay 전 과정 UI·캡처·전송·재생·suppress | 인라인 `roundtrip_self_echo`가 `relayTextsSimilar` 재구현(중복) / 재생 중 마이크 유지 | ⚠️ 잔존(G3) |
| `src/services/voipCallClient.ts` | VOIP | WebRTC peer·시그널링·relay 원장 | sticky remoteAudioSuppressed(레이스 픽스됨) | ✅ 양호 |
| `src/api/translate.ts` | STT/MT/TTS | HTTP 클라이언트 | `synthesizeSpeech` 기본 6000ms → 대면 12000ms 오버라이드, VOIP는 기본 6000ms (불일치) | ✅ 기본 12000ms 정합(아래 F2) |
| `src/native/voiceRelaySileroVad.ts` | VAD | Android 네이티브 Silero 브리지 | **Android 전용** — iOS/대면은 미적용 | 🔵 플랫폼 분기 |
| `src/services/worldlincoTuningConfig.ts` | 공유 | 런타임 튜닝 SSOT(원격+캐시+기본) | 폴백 파일들의 "정렬" 주석이 실제 SSOT(12000)와 모순 | ⚠️ 잔존(G1) |
| `src/constants/voipLanguageLocales.ts` | TTS | 50개 BCP-47 매핑(단말 폴백) | 스크립트 누수 보정 없음(세 번째 로케일 리졸버) | ✅ text 인식 교정 추가(G5) |
| `src/utils/scriptLangResolver.ts` | TTS | **(신설)** 9-스크립트 우세 판정 단일 SSOT(백엔드 미러) | 대면/voip 로케일 교정 단일화 출처 | ✅ G5 |

---

## 2. 백엔드 파일별 점검

| 파일 | 영역 | 역할 | 정합성 위험/갭 | 상태 |
|------|------|------|----------------|------|
| `backend/llm/router.py` | STT/MT | voice-translate 엔드포인트·bilingual 라우팅·지비리시 가드 | `_is_likely_silence_hallucination` **데드코드**(미호출) / 지비리시 비율 0.35(백엔드) vs 0.40(클라) 불일치 | ⚠️ 잔존(G4) |
| `backend/llm/voice_gateway.py` | STT/TTS | faster-whisper STT·STT 신뢰도·edge-tts 합성 | 기본 모델 `tiny/cpu/int8`(서버 env로만 구제) / 스크립트 감지 폴백 9종 | ✅ 스크립트 폴백 추가(아래 F3) |
| `backend/voip_language_locales.py` | TTS/STT | 50개 로케일·edge 보이스·whisper 힌트 + `assert_voip_locale_coverage()` | 클라이언트 로케일과 **자동 동기화 검사 없음**(수동) | 🔵 향후 |
| `backend/services/nadotongryoksa/translator.py` | MT | LLM+googletrans 폴백·`identify_language` | `_has_residual_source_script`가 한글/가나만 검사(48개어 미검) / 실패는 캐시 안 함(양호) | ✅ 캐시 정합 양호 |

---

## 3. 핵심 질문 답변(설계 근거)

1. **대면에서 자가 TTS 캡처를 막는 게 `faceSpeakingRef` 뿐인가?** 아니다. ① STT/TTS 전 녹음기 완전 정지·언로드 ② `allowsRecordingIOS:false` ③ `faceSpeakingRef`가 `startVoiceInput`과 재시작 `beginCapture` 양쪽에서 검사 ④ 재생 종료 후 1500ms 추가 유지 ⑤ 사후 에코 가드. **연속 캡처 우회 경로 없음.** 반면 VOIP는 재생 중 마이크 유지 → suppress 창+AEC에만 의존(약한 보장).
2. **대면/VOIP 에코 가드 공유?** 코어(`isLikelyVoiceRelayEcho`/`relayTextsSimilar`)는 공유하나, 대면은 `substringEcho`/`outputLangEcho`/silence 추가, VOIP는 인라인 `roundtrip_self_echo` 별도 구현(중복).
3. **재생 드레인/쿨다운:** 대면=게이트 1500ms 유지+재시작 250ms(재생캡 10000ms); VOIP=재생시작 `playbackMs+700`, 원격 도착 시 4800/5800ms, 턴 컨트롤러 550/2600ms.
4. **STT 라벨을 에코 판정에 신뢰하는 곳?** 대면 `outputLangEcho`(L8170)가 `data.from` 라벨에 의존 → **이번 에코 핑퐁의 직접 원인**. VOIP는 명시 designated 라벨+텍스트 유사도라 라벨 비의존.

---

## 4. 정합성/무결성 갭 — 우선순위 트래커

| ID | 갭 | 영향 | 우선 | 상태 |
|----|----|------|------|------|
| **F1** | 에코 유사도가 공백 없는 CJK에서 무력 → 일본어 에코 미차단(핑퐁 근원) | 🔴 높음 | P0 | ✅ **완료** — `relayTextsSimilar`에 문자 바이그램(Dice≥0.55) 추가, 단위테스트 18/18 |
| **F2** | `synthesizeSpeech` 타임아웃 대면 12s vs VOIP 6s → VOIP 단말폴백(붙여읽기) 잦음 | 🟠 중간 | P0 | ✅ **완료** — 기본값 12000ms로 SSOT 정합 |
| **F3** | 서버 TTS가 텍스트/보이스 언어 불일치 시 오디오 거부 → 단말 폴백 | 🟠 중간 | P0 | ✅ **완료** — `_synthesize_edge_tts` 스크립트 감지 보이스 폴백 |
| **G1** | 폴백 상수 vs 런타임 SSOT 불일치(safetyCap 7000 vs 12000 등) | 🟠 중간 | P1 | ✅ **완료**(2026-06-20) — 폴백을 SSOT로 정합(maxSegment/safetyCap 12000·silence 1400·silenceFlush 1500·remoteListenHold 2600) + boundary config 타입 number화. jest 47/47 |
| **G2** | 대면 `outputLangEcho`가 불신 STT 라벨 의존(오차단 위험·이번 에코엔 무효) | 🟠 중간 | P1 | ✅ **완료·동결(2026-06-20, build 148→149)** — `outputLangEcho`에 F1 공유 `relayTextsSimilar`(CJK 바이그램 Dice≥0.55) AND 조건 추가: '출력 언어로 되돌아옴' + '방금 발화 출력문과 텍스트 닮음'일 때만 차단, 닮지 않은 정상 발화는 통과. lint clean. **실통화(build 149) 다수 세그먼트에서 정상 ko 발화 오차단 0건** 확인 → 대면 **🔒 동결 선언**에 포함되어 종료(추가 비-모국어 입력 경로 검증은 동결 해제 시에만) |
| **G3** | VOIP 인라인 `roundtrip_self_echo`가 공유 헬퍼 재구현(드리프트) | 🟡 낮음 | P2 | ✅ **완료**(2026-06-20) — 인라인 단어겹침 제거, 공유 `relayTextsSimilar`(F1 CJK 바이그램 포함) 수렴. jest 47/47 |
| **G4** | 지비리시 임계 0.35/0.40 불일치, 백엔드 데드코드 silence 함수 | 🟡 낮음 | P2 | ✅ **완료**(2026-06-20) — 클라 임계 0.40→0.35(백엔드 정합, 오차단만 감소) + `_is_likely_silence_hallucination` 데드코드 제거. jest 18/18·backend gibberish 통과 |
| **G5** | TTS 로케일 리졸버 3종(대면 5스크립트/백엔드 9/voip 0) | 🟡 낮음 | P2 | ✅ **완료**(2026-06-20, build 146) — 공유 SSOT `src/utils/scriptLangResolver.ts`(백엔드 9-스크립트 미러) 신설, 대면 `inferTtsLanguage`(5→9 위임, 기존 5종 로케일 보존) + `resolveVoipTtsLocale`(text 인식 교정, 하위호환) 수렴. jest 16/16. **실통화 확인됨**(call-624f6b60ac75, ko↔ja) → 섹션 종료 |
| **G6** | 클라/백엔드 로케일 SSOT 자동 동기화 검사 부재 | 🟡 낮음 | P3 | ✅ **완료**(2026-06-20) — `test_voip_language_locales.py`에 모바일 `voipLanguageLocales.ts`↔백엔드 `SUPPORTED_LANGUAGES` 파싱·단언 추가(드리프트 시 CI 실패). 6/6 |
| **G8** | **대면 이중 발화 — 중복 TTS 경로** 대면 자동음성(bilingual)에서 한 세그먼트가 **두 번 발화**된다(사용자: "1차 자체발화 후 뒤따라서 팝업창 발화"). 원인은 **에코 아님**(라이브 로그상 두 세그먼트 모두 detected=ko 단일 발화). `resultText` 변경 감지 `useEffect`(App.tsx L4466~)의 **일반 자동발화(디바이스 Expo `Speech.speak`)** 와, 대면 핸들러의 `playFaceTranslationOutput`(서버 뉴럴 TTS)가 **동일 번역문을 각각 발화** → 1차 디바이스 + 2차 서버 오디오 중복 | 🟠 중간 | P1 | ✅ **완료(2026-06-20, build 149)** — 해당 effect의 **디바이스 발화 분기에서만** `autoVoiceModeEnabledRef.current`면 `return`(대면은 `playFaceTranslationOutput` 서버 오디오 1회만 발화). 수동 번역(autoVoiceMode=false)·노래 미리듣기(voice preview 분기)는 **미접촉**. lint clean. **실통화 검증**: build 149 S10 대면 3세그먼트 모두 `[FACE_TTS]` 1회·`[AUTO_VOICE_TTS]` 0건 → 이중 발화 해소 |
| **G7** | **(신규 등재)** meter-dead 시 음향 에코 누수 — 마이크 미터가 `null`(−160dB)이면 RMS 기반 에코 억제가 무력화되고, `mode=designated`가 입력을 강제로 `from=ko` 라벨링하기 때문에 **원격 TTS 재생이 마이크로 재캡처되면 일본어 오디오가 ko로 오판→ko→ja 재번역→재전송**되는 되먹임 1건 발생 | 🟠 중간 | P1 | ✅ **코드 완료(2026-06-20, build 150)·실통화 무회귀 확인** — 증거: `call-e9f79e51ba99` 백엔드 `cid=…38ukj2 from=ko to=ja detected=ko transcript='雲さん、ここで…'`(직전 ja 재생문 재캡처) + 단말 `METER_UNAVAILABLE poll_misses:5 last_meter_db:null` · `SEGMENT_FLUSH reason=max_duration peak_meter_db:-160`. **수정(옵션 A·VOIP 국한·대면 동결 무영향):** `VoIPCallScreen.tsx` 송신 경로 에코 결정 직후, `meterUnavailable`일 때만 캡처문/번역문을 직전 재생 상대 출력(`lastRemotePlaybackTranslatedRef`)과 **공유 `relayTextsSimilar`(F1 CJK 바이그램 포함)** 로 비교해 닮으면 `meter_dead_remote_playback_echo`로 차단(타이밍 창 비의존). **검증(build 150 `call-f86de35d52d3`·~4분20초):** meter_unavailable 3회 재현에도 자가-에코 재전송 0건(가드 백스톱은 서버 VAD가 선차단해 미발동). |
| **G9** | **VOIP 원격 트랙 억제 누수 — `ontrack`/`onRemoteStream` 콜백 누락 시 원음+TTS 이중음**(가설). | 🟠 중간 | P1 | ⚠️ **가설 기각(2026-06-20, 원거리 실측)** — build 151 `call-978201e696c5`(S10=caller, Tab 10m 원거리) 분석: 통화 중 원격 트랙 **미존재**(강제 mute 미발동)이라 이 모드 증상 원인 아님. 코드는 무해 백스톱으로 잔존. 실제 원인은 **G10**(AEC 참조 경로 불일치). |
| **G10** | **VOIP caller 굶김 + 자기 TTS 음향 재캡처 — AEC 참조 루프 불일치(근본).** 캡처는 네이티브 `AudioRecord(VOICE_COMMUNICATION)`(HW AEC ON, `VoiceRelaySileroVadModule.kt` L88)인데 **TTS 재생은 expo-av `Audio.Sound`(미디어 스트림, `VoIPCallScreen.tsx` L967)** 라 HW AEC **참조 루프(통화 렌더) 밖**으로 나감 → AEC가 자기 TTS를 못 지움 → 마이크가 peak≈0dB로 재캡처 → caller 턴 굶김(10분 송신 0건·`START_BLOCKED remote_tts_active` 146회). `VoipAudioModule.kt`은 `AcousticEchoCanceler.create()` **0회 호출**(이펙트 미attach). | 🔴 높음 | P0 | ✅ **해결·검증 완료(2026-06-21).** A-1(통화 렌더 TTS) + 공정성 캡(barge-in). **(1) build 152 `call-a3f9bf002ea8`(3분20초):** TTS **4/4 `server_audio_voicecall_native`**, S10 송신 2건(이전 굶김 0건 대비), `remote_tts_active` 17회 실제 재생에만 국한, 자가에코/반복 0 → **사용자 체감 끊김·이중발화·지연 해소 확인**. **(2) build 153 `call-0d3e2e4f332e`(~6분, 공정성 캡 탑재):** TTS **9/9 `server_audio_voicecall_native`**, 송신 4·수신 9, `FAIRNESS_BARGE_IN` 0(대화 균형→안전망 미발동·정상), 무음 세그 peak avg **-46dB**(자기 TTS 재캡처 없음), 자가에코/반복 **0**, 무회귀. 증거: `evidence/s10-g10-152-livecall-call-a3f9bf002ea8.log`·`evidence/s10-g10-153-fairness-call-0d3e2e4f332e.log`. — 신규 네이티브 모듈 `VoipTtsPlayerModule`(`AudioTrack` `USAGE_VOICE_COMMUNICATION`/`CONTENT_TYPE_SPEECH`, MediaCodec 디코드)로 서버 TTS 를 **통화 렌더 경로**에서 재생 → HW AEC 참조 루프 합류. `VoIPCallScreen.playVoiceRelayOutput`은 네이티브 우선·expo-av 폴백(`voiceCallTtsNativeEnabledRef` 플래그). 사전확인 C1–C4 완료(2026-06-20, 코드 0줄)·A-1 확정 — C1: STT 업로드=네이티브 VOICE_COMMUNICATION WAV(AEC 적용 소스 ✓, `VoIPCallScreen.tsx` L1690-1718). C2: TTS=expo-av USAGE_MEDIA/STREAM_MUSIC(AEC 참조 밖, L967). C3: S10 `audio_effects_sec.xml`의 `aec`는 **`voice_communication` 캡처 전용·"fake" 스텁**(실상쇄=HAL이 통화 RX 참조) → **A-2 단독 무의미**. C4: 캡처+`AudioTrack` 렌더 공존 저위험(과거 차단=동시 캡처 한정). **결론: A-1 채택**(TTS→네이티브 `AudioTrack` `USAGE_VOICE_COMMUNICATION`/STREAM_VOICE_CALL 렌더). 상세·결과표: [`VOIP_AEC_CAPTURE_PLAN.md` §3.1](VOIP_AEC_CAPTURE_PLAN.md). 설계도 §1.2·§3.1 정합. 보존 불변식(§6.4·§8·§9·대면동결) 무접촉. 병행 B(무재빌드 VAD 원격 튜닝)는 완화. **G7/G9 텍스트·억제 가드는 "버그 땜질"로 재분류.** **(3) build 154 — 재무장 타이밍 정밀화(개발자 보고 교정):** 기존 `voiceRelaySuppressUntilRef`가 재생 **시작 시점 추정치**(`playbackMs+700`)로 고정돼, 추정 > 실제 길이일 때 재무장이 추정창에 묶여 마이크가 최대 수초 늦게 열림("발화 끝 ↔ 마이크 열림 불일치"). 수정: `settleOnce`(실제 재생 종료=`await playVoiceCallTts` resolve)에서 억제창을 **실측 종료 기준 에코 꼬리**로 collapse(네이티브 250ms/폴백 700ms) → 재무장 = 실제 종료 + max(턴가드 550, 꼬리). 재생 중 캡처는 종전대로 `remote_tts_active` 차단(실제 녹음 0). **(4) build 155 — 반이중 무음 레이스 차단 + config v3 VAD(3~7s·1s 무음).** 실측(build 156 계측) 무음 사망 0건. **(5) build 156 — 재무장 셋업 단계별 타이밍 계측(`REARM_TIMING`).** 분해: 셋업 ~0.7s(silero재초기화 ~430ms 최대), 그러나 **로컬 발화→마이크 재무장이 번역 완료(SENT)에 직렬로 묶여 ~3s 텀**(`SILERO_STOPPED`→`SILERO_STARTED` 마이크 OFF). 근본원인: 캡처-재시작 `useEffect`(L3088) 의존성 `voiceRelayBusy` 토글이 클린업으로 `segment_buffered` 즉시-재무장 타이머를 취소+busy 중 재예약 거부 → 재무장이 번역에 직렬화. **(6) build 157 — 재무장 직렬화 해소(승인 후):** `useEffect`에서 `!voiceRelayBusy` 게이트 + `voiceRelayBusy` 의존성 제거 → 재무장 = 녹음종료 +220ms(번역과 병렬, 설계의도 L1829). 큐 워커 독립·네이티브 캡처 flush 시 해제로 안전. 예상 텀 ~3.5s→~2.2s(번역 ~1.3s 단축). **오프라인 하니스(`eval/worldlinco/`) 검증: config v2 J=0.848(거절68%) vs v3 J=0.652(거절19%) → v3 데이터 최적 확인.** **(7) build 157 실통화 검증 완료(2026-06-21, `call-a2f66c6bd918`·~503s):** 하니스 결과 flush_rearm **3032→1819ms(−1213ms·−40%)** = 예측한 번역 직렬 대기(~1.3s) 제거 실측 확인, **J 0.652→0.476**. 사용자 체감 **S10 ≥80%**(텀 단축 뚜렷), **Tab 편차**(단말 HW 차이 추정→기기 계층화). ⚠️ 단일통화 reject% 19→44(빈 세그먼트 전송 추정)는 **n=1 변동** → "10통화당 1회 조정" 케이던스(`SELF_EVOLVING_ENGINE_DESIGN.md` §3.6)로 추세 확정 후 config v4 판단. **→ G10 종결.** |

> **V.2 작업 범위:** P0(F1·F2·F3) + 정합성 갭 **G1~G10 전부 완료**(대면 build 149·🔒 동결, VOIP G10 build 157 검증 종결). **항목 #1 VoIP 통역 안정화 = 안정화 달성**(잔여: build 157 reject% 추세를 10통화 케이던스로 감시). G9 가설 기각(무해 잔존), G7/G9 텍스트·억제 가드는 "버그 땜질"로 재분류. **진행 트랙(2026-06-21 부트스트랩 완료):** #2 Session Core·#3 Call Orchestrator 얇은 버전 + 자가 진화 P2 스캐폴드([`eval/worldlinco/optimize.py`](../../eval/worldlinco/optimize.py)) + 전화 T0([타당성 리포트](TELEPHONY_T0_FEASIBILITY.md)) + 감정 E0([`backend/communication/emotion/`](../../backend/communication/emotion/)). **hot path 정합성:** `nadotongryoksa_voip_router` 에 추가된 것은 **best-effort·완전 가드·flag-off no-op** 훅 2개(`orchestrator_integration.on_call_init`/`on_call_end`, Session Core `record_call_init`와 동일 패턴)뿐 — public contract·relay 타이밍·보존 불변식 무변경. 회귀 76/76. **잔여:** P2 데이터 ~10통화 누적 후 의사결정 · 전화 T1(PoC) · 감정 E1(register 제어). 한 번에 하나·실통화 DoD 검증.
>
> **T2(에코가드 단축) 원복(2026-06-20 12:20):** 사용자 확인 빌드 147 이후 라이브로만 적용했던 T2(`remote 4800→3000·speaker 5800→4000`)가 실통화에서 **self-echo 회귀**(S10이 자기 발화를 자기에게 재생)를 유발 → **4800/5800으로 원복**(코드 폴백과도 일치, 재빌드 불필요). T2는 무효 처리하며, 턴 지연 단축은 에코 억제 창을 건드리지 않는 별도 방식으로만 추후 재시도한다.

---

## 5. 검증 기록

| 항목 | 방법 | 결과 |
|------|------|------|
| F1 에코 가드 | jest `voiceRelayOrchestrator.test.ts` (CJK 에코 차단 + 정상 응답 미차단 케이스 추가) | 18/18 통과 |
| F2 타임아웃 정합 | 코드 리뷰(대면/VOIP 동일 12000ms) | 정합 확인 |
| F3 서버 TTS 폴백 | 백엔드 리로드 후 `/api/llm/voice/synthesize` 한국어텍스트+ja타깃 | `device_speech`→`server_audio`(23040 bytes) |
| 회귀 | 정상 일본어+ja타깃 | `server_audio`(24768 bytes) |
| 빌드 | gradle assembleRelease arm64 → 마켓 퍼블리시 | v1.0.84 build 136 (F1+F2+F3 반영) |
| 실통화 | 1.0.83 양 기기 설치 → 대면/VOIP 1회 | ⏳ 진행 예정(C 단계) |
| **G1 폴백 정합** | jest `voiceRelaySegmentBoundary`·`voiceRelayOrchestrator`·`voiceRelayTurnController` | **47/47 통과** |
| **G3 에코 수렴** | jest(인라인 제거 후 공유 `relayTextsSimilar` 사용) | **47/47 통과** |
| **G4 임계/데드코드** | jest 18/18 + `pytest backend/tests/test_voice_translate_stt.py -k gibberish` | **통과** (router.py import 정상) |
| **G6 로케일 동기화 가드** | `pytest backend/tests/test_voip_language_locales.py` (모바일 TS↔백엔드 단언 추가) | **6/6 통과** |
| **G5 로케일 리졸버 단일화** | jest `scriptLangResolver.test.ts`(9스크립트 감지·대면 5종 회귀 보존·신규 4종·voip text 교정 하위호환) | **16/16 통과** (전체 src 10 스위트 회귀 없음) |
| **G5 실통화** | build 146 양 기기 설치 → VOIP/대면 1회(타 언어 발화 로케일 확인) | ✅ 진행됨(call-624f6b60ac75, ko↔ja) |
| **T1 반복 환청 relay 차단** | 실통화 logcat 분석: `"통역 문장"→"翻訳文"`(seq 4·6·9 반복)·자막 크레딧 환청이 relay돼 상대 중복 발화 → 백엔드 `_WHISPER_HALLUCINATION_SIGNATURES` + 모바일 `SILENCE_HALLUCINATION_PATTERNS.ko` 에 시그니처 추가 | jest 18/18 · backend 13/13 · build 147 |
| **T1 실통화** | build 147 → ko↔ja 1회 | ✅ 중복 발화 해소 확인(사용자) |
| **T2 턴 핸드백 지연 단축** | 에코가드 suppress 창 단축 `remote 4800→3000·speaker 5800→4000`(JSON 라이브 SSOT) | ❌ **원복(무효)** — 실통화 self-echo 회귀(S10 자기발화 자기재생) |
| **T2 원복** | 라이브 SSOT `remote 3000→4800·speaker 5800` 복귀(코드 폴백과 일치) | ✅ 서버 라이브 반영·재빌드 불필요 — 빌드147 상태로 복귀 |
| **T2 원복 실통화 검증** | `call-e9f79e51ba99`(84s·quality=good) logcat+백엔드: S10 한국어→Tab 일본어 재생 정상(`'실험 종료 끝 로그 확인해'→'実験終了しました。ログを確認してください。'`), START_BLOCKED 사유 `remote_tts_active`/`recording_in_progress`만(정상 반이중) | ✅ **self-echo 폭주 해소 확인** — 다만 meter-dead 에코 1건 잔존(→G7) |
| **G7 meter-dead 에코 누수(등재)** | 동일 통화 백엔드 `cid=…38ukj2` 자기 ja 재생문 재캡처 ko→ja 재번역 + 단말 `meter_unavailable·peak_meter_db:-160·max_duration` | 🆕 등재만(미수정) — 수정은 승인 후 |
| **G8 대면 이중 발화 — 라이브 재현/원인 확정** | S10(build 148) 대면 1회 라이브 logcat: seg1 `transcript='안녕하세요…' from=ko to=ja translated='こんにちは…'` → `[AUTO_VOICE_TTS_…](디바이스 speak)` **그리고** `[FACE_TTS] played server_audio` 둘 다 발화. seg2도 동일 패턴. **두 세그먼트 모두 detected=ko**(에코 아님) | ✅ 원인 확정 — 중복 TTS 경로(effect 디바이스 speak + `playFaceTranslationOutput` 서버 오디오) |
| **G8 수정** | App.tsx 자동발화 effect 디바이스 분기에 `if (autoVoiceModeEnabledRef.current) return;` 추가 → 대면은 서버 오디오 1회만 | ✅ 코드 완료·lint clean·build 149 |
| **G8 실통화 검증** | build 149 S10 대면 라이브 logcat 3세그먼트(ko→en·ko→ja·ko→ja): 각 세그먼트 `[FACE_TTS] played server_audio` **1회만**, `[AUTO_VOICE_TTS]` **0건**(build 148 대비 중복 디바이스 경로 소멸). 에코 세그먼트(detected≠ko) 없음 | ✅ **완료** — 이중 발화 해소 확인, 섹션 종료 |
