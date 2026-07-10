# WorldLinco build 74 — Launch Status (SSOT)

> **2026-06-16** · `1.0.45` / **versionCode 74**

## Marketplace

| Item | Value |
|------|-------|
| APK | `uploads/marketplace_local/apk/nadotongryoksa-v1.apk` |
| Manifest | `nadotongryoksa-v1.manifest.json` |
| Version API | `GET /api/marketplace/apk/worldlinco/manifest` |
| UI | `/marketplace/nadotongryoksa` — 동적 `v1.0.45 · build 74` 표기 |

## Changes vs build 73

- Voice relay latency trim (~600–800ms client-side turn gap reduction)
- Marketplace manifest + version endpoint
- E-3-4 beta 10 users **ON HOLD**

## Latency defaults (build 74)

| Param | build 73 | build 74 |
|-------|----------|----------|
| `playbackMinMs` | 2800 | **2200** |
| `silenceFlushMs` | 1900 | **1500** |
| `remoteListenHoldMs` | 2500 | **2100** |
| Silero `minSegmentMs` | 3200 | **2800** |
| Silero `silenceMs` | 1100 | **950** |

Server STT+translate (~3s)는 별도 — v1.1 streaming partial STT 검토.

## LTE 베타 보안 (v1.0)

- 앱: WiFi-only **차단 없음** · WSS/TLS only
- APK: 로그인 + 7일 HMAC test_token
- v1.1: LTE QA 매트릭스 · TURN short token · 데이터 사용량 UI

## Latency 실측 (2026-06-16)

| Run | call_id | 결과 |
|-----|---------|------|
| `ko_ja_smoke_20260616-030406` | `call-2c3cc24922c0` | **PASS** · Silero silence **950ms** · translate ~3.5s |

상세: `evidence/worldlinco-v1-launch/build74_latency_20260616-030406/LATENCY_REPORT.md`

## Publish

```powershell
pwsh -File scripts\publish_worldlinco_apk.ps1
docker compose restart backend
```
