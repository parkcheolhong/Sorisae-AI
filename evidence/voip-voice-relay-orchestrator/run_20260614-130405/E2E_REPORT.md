# V-8 E2E Run 20260614-130405

## Devices
- Caller (A): `R83W70QY11H` — versionCode `42`
- Callee (B): `172.30.1.19:5555` — versionCode `42`
- APK: `1.0.32` / build `42`

## Gate results

| Gate | Caller | Callee |
|------|--------|--------|
| VOIP_INCOMING_ACCEPT_API_OK | True | (callee only) |
| connectSignaling:open | True | True |
| connected (30s+) | True | True |
| early disconnected | False | True |
| VOIP_VOICE_RELAY_SENT | False | False |
| relay + utterance_id/chunk_index/is_final | False | False |

## Verdict
- **Accept + signaling + connected**: PASS
- **Voice relay metadata**: FAIL

## Artifacts
- `caller_final.log`, `callee_final.log`, `combined_filtered.log`
- `summary.json`, `callee_before_accept.xml`, screenshots
