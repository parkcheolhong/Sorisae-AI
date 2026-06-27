# WorldLinco build 73 — Launch Status (SSOT)

> **2026-06-16** · `1.0.45` / **versionCode 73**

## APK

| Item | Value |
|------|-------|
| versionName | **1.0.45** |
| versionCode | **73** |
| package | `com.parkcheolhong.worldlinco` |
| artifact | `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` |
| Tab | `R83W70QY11H` — installed |
| S10 | `172.30.1.19:5555` — installed |

## E-3 gates (this build)

| Gate | Status | Evidence |
|------|--------|----------|
| E-3-8 ko↔ja VoIP **strict** | **PASS** | `ko_ja_smoke_20260616-023813` · `call-0f44540d27f6` |
| E-3-8 ja→ko Tab TTS | **PASS** | `target_lang=ko` · `안녕하세요, 잘 부탁드립니다.` |
| Backend accept lang | **PASS** | `display_language=ko` on `/accept` |

## Key changes vs build 69

| Layer | Fix |
|-------|-----|
| Backend | callee `/accept` — invite `display_language` before caller DB `preferred_language` |
| Mobile | `resolveVoipRemoteLanguageHint` — deeplink/invite before accept API merge |
| Mobile | validation deeplink `callee_preferred_language=ja` → friend initiate |
| Script | incoming deeplink `display_language=ko` · smoke stable timeout **90s** |

## Resolved (was build 69 caveat)

- Tab TTS `Hello, nice to meet you.` (`target_lang=en`) → **fixed** in build 73

## Open (v1.0 DoD)

- **E-3-4** — 10 beta users → `E3-4_beta_users.csv` (use `scripts/worldlinco_e3_beta_user_record.ps1`)
- **E-3-5** — git tag **`v1.0.45`** @ build 73 (after commit)

## Reproduce E-3-8 strict

```powershell
pwsh -File scripts\worldlinco_ko_ja_voip_smoke.ps1 -MonitorSec 70 -StableSec 8
```

조건: Tab 무음 · WiFi · S10 일본어 6초+ · monitor 구간 중 발화
