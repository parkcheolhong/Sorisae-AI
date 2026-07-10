# WorldLinco 오디오·세션 섹션 SSOT (고정선)

> **기준일:** 2026-07-02 · **APK:** build 297 (`1.0.234`) — freeze `worldlinco_section_freeze.json`  
> **정책:** 이 문서와 `knowledge/worldlinco_section_freeze.json` 이 **단일 진실원천**이다.  
> 의도적 재기준화 PR 없이 섹션 간 값을 옮기거나 양파 패치를 금지한다.

---

## 1. 헌법: 1기기 · 1세션

```
ACTIVE_SESSION ∈ { idle, sorisae, voip }
금지: sorisae ∧ voip 동시 활성 (마이크·AudioManager·TTS 라우팅 단일)
```

| 전이 | 동작 (이미 구현된 SSOT) |
|------|-------------------------|
| → voip | `quiesceNonVoipAudioForVoipSession` · `revokeCurrentVoiceCapture` · `isVoipSessionActive()` |
| voip 중 소리새 | STT/업로드/발화 **차단** (`useVoiceCaptureLoop`, `voipSessionGuard`) |
| voip → idle | VoIP teardown 후 companion arm 재평가 (dormant/홈) |

**다시 손대지 않을 것:** VoIP 튜닝을 소리새 TTS 패치로 “맞추려” 하지 않는다. 세션이 겹치면 둘 다 깨진다.

---

## 2. 섹션 경계 (건드려도 다른 섹션 불변)

| 섹션 | 코드 루트 | 오디오 출력 | TTS 운율 SSOT |
|------|-----------|-------------|----------------|
| **소리새** | `features/sorisae/*`, `appFaceVoicePlayback.ts` | `STREAM_MUSIC` / ExoPlayer | `feature_id=face.interpret` → **+18%, rate -1%** |
| **VoIP** | `VoIPCallScreen.tsx`, `voip/media_bridge.py` | `VoipTtsPlayer` / `VOICE_CALL` | `_synthesize_tts` **기본** → **+6%** |
| **대면 통역** | `face-interpretation/*` | 소리새와 동일 재생 경로 | `face.interpret` |
| **공유 (읽기 전용)** | `voipSessionGuard.ts`, `voiceCaptureLease.ts` | 세션 판별·마이크 lease만 | **섹션별 값 복사 금지** |

### 소리새 고정 상수 (build 296)

| 항목 | 값 | 파일 |
|------|-----|------|
| `playback_cap_ms` | **50_000** | `faceConversationTiming.ts`, `worldlincoTuningConfig.ts` |
| TTS safety cap | `min(90s, max(8s, len×170+6s))` | `computeFaceTtsSafetyCapMs()` |
| synthesize 타임아웃 | **30s** | `appFaceVoicePlayback.ts` |
| server TTS | **필수** (`null,null` 우회 금지) | `sorisaeCaptureSegment.ts` |
| 통화 중 | `enableVoipAudio(false)` **호출 금지** | `isVoipSessionActive()` 가드 |

### VoIP 고정 (아침 튜닝선)

- **스피커 기본 OFF** — `globalSettings.voipSpeakerDefaultOn`(기본 false), 통화 화면 🔊 토글로만 ON
- 스피커 ON 시에만 `enableVoipAudio(true, maximizeVolume=true)` (STREAM_VOICE_CALL 최대)
- `media_bridge` → `_synthesize_tts` without `face.interpret` feature_id
- **소리새 전역 볼륨을 VoIP에 올리지 않는다**

---

## 3. 백엔드 라우팅 고정

| 경로 | 포트 | 모델 |
|------|------|------|
| 소리새 friend-chat | **8009** | `Qwen/Qwen3-8B-AWQ` |
| 일반 번역 LLM | 8008 | Qwen2.5-Coder-14B (소리새와 분리) |

env 변경 후 `docker compose up -d --force-recreate backend` (restart만으로 env 미반영).

---

## 4. 변경 절차 (한 번 맞추고 끝)

1. **어느 섹션**인지 먼저 분류 (sorisae / voip / face / shared).
2. `knowledge/worldlinco_section_freeze.json` 에서 해당 섹션만 수정.
3. `python scripts/check_worldlinco_section_ssot_lock.py` PASS.
4. `make sorisae-gate` PASS.
5. APK 빌드: `python scripts/sync_android_version.py` → `C:\wlnc\android` Gradle → `publish_worldlinco_apk.ps1`.

**금지:** VoIP 파일에서 소리새 타이밍 복사 · `actress_soft` 전역 볼륨만 올려 “소리 크게” 해결 · `30_000` safety cap 재도입.

---

## 5. 회귀 게이트

```powershell
python scripts/check_worldlinco_section_ssot_lock.py
python scripts/check_sorisae_regression_lock.py
make sorisae-gate
```

CI/머지 전 위 3개 PASS 없으면 배포하지 않는다.

---

## 6. 체감 볼륨 (코드 변경 없이)

- 태블릿 **미디어 볼륨 15/15**
- 백엔드 배포 후 `face.interpret` 합성 **+18%** (freeze 고정)
- 그래도 부족하면 **freeze 갱신 PR**로 `edge_tts_prosody_ko` 만 조정 (VoIP 기본선은 유지)

---

## 7. VoIP 튜닝 SSOT 대조표 (2026-07-02)

작업 전 **반드시** 본 절·`knowledge/worldlinco_tuning_config.json`·`knowledge/worldlinco_section_freeze.json` 를 읽는다.

| 항목 | 기술서·SSOT 값 | 조정 경로 | 금지 |
|------|----------------|-----------|------|
| VoIP TTS 운율 | `+6%` (기본, `face.interpret` 미사용) | `worldlinco_section_freeze.json` → `sections.voip` | 소리새 `+18%` 를 VoIP에 복사 |
| 브리지 대화 템포 | `min_speech_ms=600`, `live_echo_guard_ms=700` 등 | `worldlinco_tuning_config.json` → `voip_bridge` | 코드에 PLC·가짜 패딩·지터 prefill 임의 추가 |
| 모바일 relay VAD | `remote_echo_guard_ms=4800`, `speaker_echo_guard_ms=5800` | `worldlinco_tuning_config.json` → `voip` | 에코 가드 창을 코드에서 임의 단축 |
| 클라 통화 오디오 | `enableVoipAudio(speaker, maximizeVolume=speaker)` 기본 스피커 OFF | `VoIPCallScreen` — 사용자 🔊 토글·설정만 | 통화/TTS에서 `speaker=true` 강제·8초 reapply |
| ICE disconnected grace | **2500ms** (`voipCallClient.ts`) | 명시 PR + 실통화 근거 | 미문서 4000ms 등 임의 변경 |
| 브리지 STT 최소 길이 | `voip_bridge.min_speech_ms` (600) | `media_bridge` → `_run_faster_whisper(min_segment_ms=…)` | relay 기본 2400ms 를 브리지에 강제 |
| Freecess 방지 | 포그라운드 서비스 + 배터리 예외 (MB-11) | `VoIPCallScreen` mount | — |

**회귀 사례(금지 패치):** PLC 홀드·`push_timeline_pad`·다운링크 prefill → 지글거림·로봇 음성 악화. 통화 중 `reapplyVoipCallAudioStack` 8초 루프 → WebRTC·AudioManager 경합.

---
