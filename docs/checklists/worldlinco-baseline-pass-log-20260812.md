# WorldLinco Baseline Pass Log (2026-08-12)

## Scope
- Target app: apps/mobile-nadotongryoksa
- Purpose: checklist item 0 baseline pass 1 and pass 2 (automated representative flow suites)

## Command
```powershell
Set-Location C:/Users/WORK/source/repos/parkcheolhong/codeAI/apps/mobile-nadotongryoksa
npm test -- --runInBand \
  src/__tests__/socialLogin.test.ts \
  src/__tests__/faceConversationTiming.test.ts \
  src/__tests__/voiceRelayOrchestrator.test.ts \
  src/__tests__/voiceRelayTurnController.test.ts \
  src/__tests__/chatVoiceInput.test.ts \
  src/__tests__/travelBooking.test.ts \
  src/__tests__/songLang.test.ts
```

## Mapping
- Login: src/__tests__/socialLogin.test.ts
- Face interpretation: src/__tests__/faceConversationTiming.test.ts
- VoIP: src/__tests__/voiceRelayOrchestrator.test.ts + src/__tests__/voiceRelayTurnController.test.ts
- Chat: src/__tests__/chatVoiceInput.test.ts
- Travel search: src/__tests__/travelBooking.test.ts
- Song: src/__tests__/songLang.test.ts

## Results
| Pass | Suites | Tests | Jest time | Wall time | Error rate |
|---|---:|---:|---:|---:|---:|
| 1 | 7/7 PASS | 83/83 PASS | 1.027s | 1.80s | 0% |
| 2 | 7/7 PASS | 83/83 PASS | 0.608s | 1.30s | 0% |

## Comparison
- Wall-time delta: -0.50s (pass2 faster)
- Relative delta: -27.78%
- Error-rate delta: 0% -> 0% (stable)

## Notes
- This is an automated baseline using representative feature suites.
- Device-level end-to-end timing for real UI interactions is still pending and should be recorded separately before marking checklist item 0 as complete.
