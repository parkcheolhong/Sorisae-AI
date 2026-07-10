# Audit + Relay Diagnosis (2026-06-14 13:41–13:47)

## Setup
- Backend: `devanalysis114-backend` restarted (callee audit ACL + `call_accepted` event deployed)
- Devices: Tab `R83W70QY11H` (caller) → S10 `172.30.1.19:5555` (callee)
- Call under test: `call-9ef693088538`
- APK: build 42 / v1.0.32

## 1) Audit log (S10 / callee) — **PASS (API), UI inconclusive**

### Backend evidence
- After redeploy, **`GET /api/v1/voip/calls/call-9ef693088538/audit` → 200 OK** (many polls, **zero 403**)
- Before fix (same session, older calls): mixed `403 Forbidden` + `200 OK` on callee polls
- Example pre-fix pattern: `call-c78ce2c70905/audit` → 403 then 200 after redeploy

### S10 UI evidence
- UIAutomator dump during connected call still showed **VoIP rail incoming card** (`받기` / `거절`), not the scrolled **「통화 모드 감사 로그」** block inside `VoIPCallScreen`.
- Automated scroll + `새로고침` tap did not surface `call_initiated` / `call_accepted` text in the dump.
- **Interpretation:** callee audit API is no longer blocked; UI verification needs the full in-call screen (scroll past rail) or manual **새로고침**.

## 2) Voice relay (S10 speech probe) — **FAIL**

### Call flow (OK)
- `VOIP_INCOMING_ACCEPT_API_OK` ✅
- `connectSignaling:open` ✅
- `Connection state: connected` ✅
- `voiceRelayServerReady: true`, `auto_relay_applied: true` ✅

### Relay logcat (FAIL)
- Cleared logcat on S10, played **3×3s** speaker probe (~9s total) while call still connected (signaling pongs through 13:47)
- **No** `VOIP_VOICE_RELAY_SENT`, `VOIP_VOICE_TRANSLATE_REQUEST`, `VOIP_VOICE_TRANSLATE_RESULT`
- **No** `VOIP_VOICE_RELAY_START_BLOCKED` on this call window
- Tab caller logcat (same call): also **no** relay events

### Prior E2E hint (same devices, run_20260614-131548)
- Callee log contained: `Failed to stop voice relay segment` — expo-file-system `deleteAsync` deprecated (recording lifecycle stuck)

## Verdict

| Check | Result |
|-------|--------|
| Callee audit API 403 fixed | **PASS** (200 only for `call-9ef693088538`) |
| S10 audit UI visible | **INCONCLUSIVE** (rail card dominated UI dump) |
| S10 callee speech → relay | **FAIL** (no relay log gates) |
| voice-translate HTTP 403 | **Not observed** |

## Artifacts
- `run.log`, `call_start.log`, `incoming.log`, `accept.xml`
- `callee_audit_*.xml`, `callee_ui_now.xml`
- `callee_relay_probe.log` (post-probe window)

## Recommended next steps
1. On S10 during connected call: scroll to **통화 모드 감사 로그** → **새로고침** → confirm `call_initiated` + `call_accepted`.
2. Fix relay recording teardown (`deleteAsync` → legacy API) and re-test with **live mic speech** (speaker WAV probe is weak for VAD vs WebRTC mic path).
3. Investigate callee UI: incoming rail card persists after accept (`받기` still visible) — may block relay UX and audit visibility.
