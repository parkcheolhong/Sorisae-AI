# WorldLinco build 69 — Launch Status (SSOT)

> **2026-06-16** · `1.0.44` / **versionCode 69**

## APK

| Item | Value |
|------|-------|
| versionName | **1.0.44** |
| versionCode | **69** |
| package | `com.parkcheolhong.worldlinco` |
| artifact | `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` |
| Tab | `R83W70QY11H` — installed |
| S10 | `172.30.1.19:5555` — installed |

## E-3 gates (this build)

| Gate | Status | Evidence |
|------|--------|----------|
| E-3-8 ko↔ja VoIP | **PASS** | `ko_ja_smoke_20260616-005906` · `call-71a7256e4490` |

## Key changes vs build 68

- Deeplink `preferred_language` / `source_lang` → VoIP relay source lang
- `VOIP_DEEPLINK_PREFERRED_LANGUAGE_APPLIED` probe
- Smoke: `-SetupOnly`, call_id stable wait, ja PASS criteria

## Open (v1.0 DoD)

- **E-3-4** — 10 beta users (`E3-4_beta_users.csv`)
- **E-3-5** — git tag **`v1.0.44`** (2026-06-16, 로컬)
- ja→ko Tab TTS (`target_lang` pairing) — v1.1 tuning
