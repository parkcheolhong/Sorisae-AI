# PR #111 Follow-up (2026-08-16 05:25 UTC)

## Scope
- Settings tab and friend invite QR auth-invalid issue hardening
- seed/playwright duplicate task label cleanup (keep legacy aliases)
- Mobile real-device Sorisae probe execution evidence

## Checklist Status
- [x] Apply mobile token-normalization patch for referral/friends API calls
- [x] Remove exact duplicate labels in .vscode/tasks.json while preserving legacy aliases
- [x] Run compatibility tasks after dedupe (`playwright-round-a`, `seed-round-a-users-final`)
- [x] Execute real-device probe and collect report.json evidence
- [ ] Close Sorisae runtime silent-graceful + adb runtime failures

## Files Changed
- apps/mobile-nadotongryoksa/src/features/shared/authToken.ts
- apps/mobile-nadotongryoksa/src/services/worldlincoReferral.ts
- apps/mobile-nadotongryoksa/src/api/friends.ts
- apps/mobile-nadotongryoksa/src/services/voipPresence.ts
- apps/mobile-nadotongryoksa/App.tsx
- backend/llm/voice_gateway.py
- .vscode/tasks.json

## Implementation Notes
1) Token normalization hardening
- Added shared helper:
  - `normalizeAuthToken(raw)` strips whitespace and leading `Bearer` (case-insensitive).
  - `buildBearerAuthHeader(raw)` ensures one canonical `Authorization: Bearer <token>`.
- Applied to friend APIs so invite/friends/map/request calls no longer send malformed double-bearer or whitespace tokens.

1) Referral API fallback retry
- `fetchReferralMe(token)` now:
  - normalizes incoming token,
  - appends stored secure auth token candidate (`loadStoredAuthState`) when available,
  - retries on 401/403 across candidates,
  - returns server detail if still failed.
- Purpose: absorb in-memory token drift and malformed token strings without changing backend contracts.

1) Duplicate task label cleanup
- Removed only exact duplicate entries:
  - `playwright-round-a` (one duplicate removed)
  - `rebuild-frontend-admin-container` (one duplicate removed)
  - `seed-round-a-users` (one duplicate removed)
- All legacy labels remain usable.

## Verification Logs
### A) Task alias compatibility checks
1. `shell: playwright-round-a`
- Result: PASS
- Key lines:
  - `1 passed`
  - `RESULT PASS`
  - `[POLICY-SUITE] PASS legacy=playwright-round-a`

1. `shell: seed-round-a-users-final`
- Result: PASS
- Key lines:
  - `1 passed` (pre)
  - `SEEDED_A admin=ui.admin.round@devanalysis.local target=ui_pod_round_a_20260426`
  - `1 passed` (post)
  - `[POLICY-SEED-SUITE] PASS legacy=seed-round-a-users-final round=A`

### B) Real-device probe
Command:
- `python scripts/run_sorisae_friend_chat_probe.py --base-url https://metanova1004.com --adb-device R83W70QY11H`

Result:
- Overall: FAIL (exit code 1)
- Report path:
  - `evidence/sorisae-friend-chat-probe-20260816-051145/report.json`

Passed checks:
- `health`
- `marketplace_manifest`
- `friend_chat_model_route`
- `friend_chat_text_llm`
- `m4a_normalize_ssot`
- `friend_chat_audio_speech_m4a`
- `adb_apk_build`

Failed checks:
- `friend_chat_audio_silent_graceful`
  - detail: `status=200 detail=`
- `adb_sorisae_runtime`
  - detail: `segment_200=False tight_preupload_loop=False hallucination_422=False`

Observed runtime evidence (from report log tail):
- repeated `pending_call_poll` 401 and VoIP presence reconnect/close 1006 loop signals.

## Round 2 Runtime Patch (2026-08-16 05:40 UTC)
### Additional implementation
1. Mobile VoIP auth-path unification
- `App.tsx`
  - Social callback now accepts only normalized token and requires successful `/auth/me` verification before applying session.
  - Pending incoming poll uses canonical bearer header and adds 10s auth backoff on HTTP 401 to prevent reconnect storm.
  - VoIP presence websocket now uses normalized token only.
  - Active-call resume uses canonical bearer header.
- `src/services/voipPresence.ts`
  - register/unregister/missed-calls/accept endpoints all use shared token normalization + canonical bearer header.

1. Friend-chat silent-audio guard hardening
- `backend/llm/voice_gateway.py`
  - friend-chat STT failure now maps no-speech conditions to graceful 422 (`음성이 감지되지 않았습니다. 다시 말씀해 주세요.`).
  - low-trust STT path is rejected unless Korean-safe acceptance condition passes.
  - single-token hallucination phrases (e.g., `You`, `Thanks`) are explicitly treated as noise.

### Re-run evidence (same probe command)
Command:
- `python scripts/run_sorisae_friend_chat_probe.py --base-url https://metanova1004.com --adb-device R83W70QY11H`

Run #2 report:
- `evidence/sorisae-friend-chat-probe-20260816-053405/report.json`
- FAIL (`friend_chat_audio_silent_graceful`, `adb_sorisae_runtime`)

Run #3 report:
- `evidence/sorisae-friend-chat-probe-20260816-053608/report.json`
- FAIL (`friend_chat_audio_silent_graceful`, `adb_sorisae_runtime`)

### Root-cause trace confirmation
- Silent audio endpoint response on production still returns HTTP 200 with hallucinated transcript:
  - `transcript: "You"`
  - `response_text: "I'm here to help! ..."`
- Device log still shows repeated loop:
  - `pending_call_initial/poll` -> `REQUEST_RESULT status=401`
  - `VOIP_PRESENCE_CLOSED code=1006` -> retry scheduled

## Current Conclusion
- Auth-invalid hardening patch and duplicate label cleanup are implemented and compatibility-verified.
- Additional mobile/backend runtime patches for the two fail gates are implemented in source.
- Real-device Sorisae runtime probe against `https://metanova1004.com` remains unresolved because the running production/runtime binary still exhibits old behavior (`silent=200 hallucination`, `401/1006 loop`).
- Runtime quality gate is therefore still not closed; next required step is deploy/reinstall patched backend+mobile build and re-run the same probe until fail=0.
