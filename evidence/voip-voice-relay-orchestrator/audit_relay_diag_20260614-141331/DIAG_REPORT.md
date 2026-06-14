# Audit + Relay Diagnosis 20260614-141331

## Backend
- `devanalysis114-backend` restarted with callee audit ACL fix

## Call flow
- Accept API: `True`
- Signaling open (callee): `False`

## S10 audit (after 새로고침)
- logcat VOIP_CALL_MODE_AUDIT_LOADED: `False`
- call_initiated visible: `False`
- call_accepted visible: `False`
- HTTP 403 error text: `False`

## Callee relay logcat (8s mic window on S10)
- VOIP_VOICE_RELAY_SENT: `False`
- relay + utterance_id: `False`
- VOIP_VOICE_TRANSLATE_REQUEST: `False`
- VOIP_VOICE_TRANSLATE_RESULT: `False`
- VOIP_VOICE_RELAY_START_BLOCKED: `False`
- VOIP_CALL_MODE_AUDIT_LOADED: `False`
- VOIP_INCOMING_CALL_SUPPRESSED_ACTIVE_SESSION: `False`

## Caller relay logcat (same window)
- VOIP_VOICE_RELAY_SENT: `False`
- VOIP_VOICE_TRANSLATE_REQUEST: `False`

## Verdict
- Audit fix on S10: FAIL / INCONCLUSIVE
- Relay on callee speech probe: FAIL
