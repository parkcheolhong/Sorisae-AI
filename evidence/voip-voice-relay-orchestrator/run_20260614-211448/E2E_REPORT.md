# V-8 E2E Run 20260614-211448

## Devices
- Caller (A): `R83W70QY11H` — versionCode `62`
- Callee (B): `172.30.1.19:5555` — versionCode `62`
- APK: `1.0.37` / build `62`

## Gate results

| Gate | Caller | Callee |
|------|--------|--------|
| VOIP_INCOMING_ACCEPT_API_OK | False | (callee only) |
| connectSignaling:open | False | False |
| connected (30s+) | False | False |
| early disconnected | False | False |
| VOIP_VOICE_RELAY_SENT | False | False |
| relay + utterance_id/chunk_index/is_final | False | False |
| SILERO_STARTED | True | True |
| SILERO_SPEECH_END | True | True |
| SEGMENT_FLUSH(silence) | True | True |
| RELAY_PLAYBACK | False | False |

## Verdict
- **Accept + signaling + connected**: FAIL
- **Voice relay sent**: FAIL
- **Silero VAD POC**: PASS
- **Voice relay metadata**: FAIL

## Artifacts
- `caller_final.log`, `callee_final.log`, `combined_filtered.log`
- `summary.json`, `callee_before_accept.xml`, screenshots
