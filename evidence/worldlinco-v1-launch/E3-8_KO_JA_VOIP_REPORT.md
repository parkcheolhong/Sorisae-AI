# E-3-8 ko↔ja VoIP 실기기 E2E — 수동 1회 (2026-06-16)

## Verdict: **PASS** (ja→ko 한국어 TTS + strict `target_lang=ko`)

| 항목 | 결과 |
|------|------|
| 빌드 | Tab·S10 **73 / v1.0.45** |
| 프로필 | deeplink `preferred_language=ja`(S10) · `ko`(Tab) |
| call_id | `call-0f44540d27f6` (8s stable) |
| S10 STT | `detected_lang=ja` · `こんにちは、よろしくお願いします。` |
| S10 relay | `source_lang=ja` · **`target_lang=ko`** · `VOIP_VOICE_RELAY_SENT` |
| 번역 | `안녕하세요, 잘 부탁드립니다.` |
| Tab playback | **PASS** — `VOIP_VOICE_RELAY_PLAYBACK` · `target_lang=ko` |
| Tab caller pair | `target_lang=ja` (callee hint) |
| Backend accept | `display_language=ko` |
| repetition | 0 |

## 증적

- Run: `evidence/worldlinco-v1-launch/ko_ja_smoke_20260616-023813/`
- Setup: `evidence/voip-voice-relay-orchestrator/manual_retest_20260616-023910/`

## build 71 → 73 fix 요약

1. **Backend accept**: callee 응답에서 invite `display_language=ko`를 caller DB `en`보다 우선
2. **Mobile accept merge**: deeplink/invite 힌트 → accept API 순 (`resolveVoipRemoteLanguageHint`)
3. **Tab initiate**: validation deeplink `callee_preferred_language=ja` → friend call API 전달
4. **Smoke stable wait**: WebRTC 지연 대비 timeout 45s → 90s

## 이전 FAIL 대비

| Run | 빌드 | 결과 | 원인 |
|-----|------|------|------|
| `ko_ja_smoke_20260616-013903` | 71 | FAIL | `target_lang=en` (accept API가 DB en 반환) |
| `ko_ja_smoke_20260616-021838` | 72 | FAIL | S10 발화 없음 |
| `ko_ja_smoke_20260616-023231` | 73 | FAIL | 8s stable 전 Tab WebRTC disconnect |
| **`ko_ja_smoke_20260616-023813`** | **73** | **PASS** | ja→ko + Tab 한국어 TTS |

## 재현

```powershell
pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 70 -StableSec 8
```

조건: Tab 무음 · 기기 1m+ · S10 `こんにちは。よろしくお願いします。` 6초+
