# E-3-8 ko↔ja VoIP 실기기 E2E — 수동 1회 (2026-06-16)

## Verdict: **PASS** (일본어 STT + Tab playback)

| 항목 | 결과 |
|------|------|
| 빌드 | Tab·S10 **69 / v1.0.44** |
| 프로필 | deeplink `preferred_language=ja`(S10) · `ko`(Tab) — build 69 |
| call_id | `call-71a7256e4490` (8s stable) |
| S10 STT | `detected_lang=ja` · `こんにちは、よろしくお願いします。` |
| S10 relay | `source_lang=ja` · `VOIP_VOICE_RELAY_SENT` |
| Tab playback | **PASS** — `VOIP_VOICE_RELAY_PLAYBACK` |
| repetition | 0 |

## 증적

- Run: `evidence/worldlinco-v1-launch/ko_ja_smoke_20260616-005906/`
- Setup: `evidence/voip-voice-relay-orchestrator/manual_retest_20260616-010003/`

## 이전 FAIL 대비 변경

1. build **69**: deeplink `preferred_language` → VoIP `effectiveVoipSourceLang` 반영
2. 스크립트: `-SetupOnly` · call_id 8s stable · logcat filter by call_id
3. S10 build 69 설치 후 `source_lang=ja` 세그먼트 확인

## 알려진 한계 (후속)

- Tab TTS 문구: `Hello, nice to meet you.` (relay `target_lang=en`) — ja→**ko** 한국어 TTS는 프로필 페어링(`remote preferred=ko`) tuning 잔여
- API `/auth/me` PATCH는 로컬 `.runtime/secrets` 없으면 skip; deeplink로 대체

## 재현

```powershell
pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 70 -StableSec 8
```

조건: Tab 무음 · 기기 1m+ · S10 `こんにちは。よろしくお願いします。` 6초+
