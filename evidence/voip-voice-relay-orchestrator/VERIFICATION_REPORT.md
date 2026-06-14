# VoIP Voice Relay Orchestrator — Verification Report

Updated: 2026-06-14 (run `20260614-130405`)

## APK

| Item | Value |
|------|-------|
| versionName | 1.0.32 |
| versionCode | 42 |
| Caller (Tab) | R83W70QY11H — 119cash@naver.com |
| Callee (S10) | 172.30.1.19:5555 — burumi69@gmail.com (nado-000226) |
| Install | Both devices versionCode **42** (2026-06-14 rebuild + install) |

## V-8 E2E — run_20260614-130405

### PASS — Accept + signaling + connected (35s hold)

| Gate | Evidence (callee / caller logcat) |
|------|-----------------------------------|
| `VOIP_INCOMING_ACCEPT_API_OK` | callee `call-c78ce2c70905` @ 13:05:34.858 |
| `connectSignaling:open` | caller + callee @ 13:05:25 / 13:05:34 |
| `connected` 30s+ | connected @ 13:05:34 → hold until 13:06:12 (no early hangup on active call) |
| `VOIP_FRIEND_CALL_SUCCESS` | caller auto-call deeplink (B26 shell pattern) |

Artifacts: `caller_final.log`, `callee_final.log`, `combined_filtered.log`, `summary.json`, `E2E_REPORT.md`

### FAIL (automation) — Voice relay metadata

| Gate | Result | Notes |
|------|--------|-------|
| `VOIP_VOICE_RELAY_SENT` + `utterance_id` / `chunk_index` / `is_final` | Not observed | Expo AV VAD requires **real mic speech** on caller (≥1.2s). Speaker tone playback did not trigger relay segment. |

**Manual relay re-check:** During connected call on Tab, speak Korean/English 3–5s toward mic; expect caller logcat:

- `VOIP_VOICE_TRANSLATE_RESULT` with `utterance_id`, `chunk_index`, `is_final`
- `VOIP_VOICE_RELAY_SENT` with same metadata (build 42+)

## Script

`scripts/voip_voice_relay_v8_e2e.ps1`

- B26-verified deeplink: `adb shell "am start … -d 'worldlingo://voip/open?action=validation&callee_voice_id=nado-000226'"`
- Auth wait, stale-session cleanup, accept tap, 35s hold, relay probe window

## Unit tests (unchanged)

- `apps/mobile-nadotongryoksa/src/__tests__/voiceRelayOrchestrator.test.ts` — PASS
- `backend/tests/test_voip_voice_translation_meta.py` — PASS
