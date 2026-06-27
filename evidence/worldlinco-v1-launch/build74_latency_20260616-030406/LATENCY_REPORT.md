# Build 74 latency 실측 — ko↔ja smoke

> **2026-06-16** · build **74** · `call-2c3cc24922c0` · smoke **PASS**

## 요약

| 구간 | build 73 (`call-0f44540d27f6`) | build **74** (`call-2c3cc24922c0`) |
|------|-------------------------------|-------------------------------------|
| Silero `silence_duration_ms` | 1100 | **950** (−150ms) |
| S10 ja→ko `translate_duration_ms` (seq 1) | 3024 | 3556 |
| S10 ja→ko `segment_duration_ms` (seq 1) | 3056 | 3597 |
| S10 `relay_duration_ms` (seq 1) | 3062 | 3602 |
| Tab `PLAYBACK` target_lang=ko | ✅ ~1.1s after RELAY_SENT | ✅ ~1.1s after RELAY_SENT |
| E-3-8 strict | PASS | **PASS** |

## 해석

- **클라이언트 VAD trim 확인:** Silero trailing silence **1100→950ms** 반영됨.
- **서버 STT+번역 ~3.0–3.6s**가 여전히 지배 — build 74에서도 `translate_duration_ms` ≈ 3.5s.
- **End-to-end (S10 speech_end → Tab KO TTS):** seq1 기준 ~**4.8s** (발화 길이·환경에 따라 변동).
- **Turn controller trim** (`playbackMinMs` 2800→2200 등)은 echo guard 구간 — 다음 발화 수신 대기에 적용; 이번 smoke는 측정 로그에 직접 노출되지 않음.

## 증적

- `../ko_ja_smoke_20260616-030406/` (s10.log · tab.log · summary.json)
- 비교 baseline: `../ko_ja_smoke_20260616-023813/` (build 73)

## 후속 (v1.1)

- streaming partial STT / server-side latency profiling
- `voice-translate` GPU batch 튜닝
