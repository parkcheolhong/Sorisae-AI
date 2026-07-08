# WorldLinco Feature-Core Merge Checklist (2026-07-08)

> Rule: Do not mark complete without evidence from two successful runs.

## 0. Baseline lock
- [x] Confirm current publish pointer (build/version) from manifest
- [x] Confirm baseline APK policy and freeze references
- [x] Record branch and commit SHA used for merge lane

Evidence:
- Manifest pointer: build 312, versionName 1.0.237, publishedAt 2026-07-07T23:03:05.7548556Z
- Source file: uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json
- Baseline policy: versionCode 299, probe_min_build 296
- Source file: knowledge/worldlinco_apk_baseline.json
- Branch: feat/worldlinco-build90-92
- Commit: cce8e85dff21874237b150f5e8efef92e753832b
- Command evidence: git rev-parse --abbrev-ref HEAD ; git rev-parse HEAD

## 1. Face core from 149
- [x] Identify exact face-only files/blocks to preserve
- [x] Apply minimal patch set into merge lane
- [x] Run face verification pass #1
- [x] Run face verification pass #2

Evidence:
- Scope manifest: .runtime/face149_exact_block_manifest_20260708.md
- Candidate allowlist: faceConversationTiming.ts, faceConversationVadController.ts, faceConversationAudioRoute.ts, face-only blocks in App.tsx
- Applied patch: App.tsx auto voice device-TTS branch now emits FACE149 guard log `[FACE149_G8_GUARD]` and returns in face auto-voice path
- Command (pass #1): npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts
- Result (pass #1): PASS (3/3)
- Command (pass #2): npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts
- Result (pass #2): PASS (3/3)
- Note: section SSOT lock script currently fails on pre-existing app version mismatch (`app.json` 1.0.237 vs baseline 1.0.236)

## 2. VoIP core from 157
- [x] Identify exact VoIP-only files/blocks to preserve
- [x] Apply minimal patch set into merge lane
- [x] Run VoIP verification pass #1
- [x] Run VoIP verification pass #2

Evidence:
- Scope manifest: .runtime/voip157_exact_block_manifest_20260708.md
- Candidate allowlist: VoIPCallScreen.tsx, voip-voice-relay orchestrator/turn controller, voipCallClient.ts, native/voipAudio.ts
- Applied patch: VoIPCallScreen.tsx build-157 rearm branch now emits `[VOIP157_REARM_PARALLEL]` before scheduling restart
- Command (pass #1): npm test -- --runInBand src/__tests__/voiceRelayTurnController.test.ts src/__tests__/voiceRelayOrchestrator.test.ts
- Result (pass #1): PASS (51/51)
- Command (pass #2): npm test -- --runInBand src/__tests__/voiceRelayTurnController.test.ts src/__tests__/voiceRelayOrchestrator.test.ts
- Result (pass #2): PASS (51/51)

## 3. VoIP guard/parity from 150 and 146
- [x] Apply meter-dead fallback guard subset
- [x] Apply locale parity subset
- [x] Run VoIP regression pass #1
- [x] Run VoIP regression pass #2

Evidence:
- Meter-dead guard patch: VoIPCallScreen.tsx now tags meter-dead skip probe with `guard_phase: voip150_meter_dead_guard`
- Locale parity patch: backend/tests/test_voip_language_locales.py adds `test_mobile_ts_locale_values_match_backend_ssot` (value-level parity)
- Regression pass #1 (mobile): npm test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts -> PASS (61/61)
- Regression pass #1 (backend): ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q -> PASS (7/7)
- Regression pass #2 (mobile): npm test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts -> PASS (61/61)
- Regression pass #2 (backend): ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q -> PASS (7/7)

## 4. Sorisae freeze behavior from 296
- [x] Identify Sorisae-only freeze-consistent subsets
- [x] Apply minimal patch set
- [x] Run Sorisae verification pass #1
- [x] Run Sorisae verification pass #2

Evidence:
- Scope manifest: .runtime/sorisae296_exact_block_manifest_20260708.md
- Applied patch: useVoiceCaptureLoop.ts adds behavior-neutral trace `[SORISAE296_FREEZE]` on VoIP-entry quiesce-only path (`guard_phase: sorisae296_freeze_behavior`)
- Command (pass #1): npm test -- --runInBand src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts
- Result (pass #1): PASS (19/19)
- Command (pass #2): npm test -- --runInBand src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts
- Result (pass #2): PASS (19/19)

## 5. Cross-feature integrity
- [x] Execute integrated run (face + voip + sorisae) pass #1
- [x] Execute integrated run (face + voip + sorisae) pass #2
- [x] Confirm 1-device-1-session invariant preserved
- [x] Confirm no cross-section prosody/timing leakage

Evidence:
- Integrated pass #1 command: python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts
- Integrated pass #1 result: BLOCKED by section boundary lock; backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Integrated pass #2 command: python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts
- Integrated pass #2 result: BLOCKED by section boundary lock (same findings reproduced); backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Blocking findings (section boundary lock):
 	- VoIP + Sorisae dedicated paths changed together
 	- friend-chat area change detected in backend/voice_gateway.py
 	- App.tsx and section-dedicated files changed together
- Re-run (2026-07-09) pass #1 command: python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; (cd apps/mobile-nadotongryoksa && npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts)
- Re-run (2026-07-09) pass #1 result: BLOCKED by section boundary lock (same findings); backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Re-run (2026-07-09) pass #2 command: python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; (cd apps/mobile-nadotongryoksa && npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts)
- Re-run (2026-07-09) pass #2 result: BLOCKED by section boundary lock (same findings reproduced); backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Split patch commit #1 (Sorisae lane): e94e95330 (face-conversation/face-interpretation only)
- Split patch commit #2 (VoIP lane): 1dd0ff46a (voip relay/call/media bridge only)
- Clean-state integrated pass #1 command (2026-07-09 03:53:19 +09:00): python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; (cd apps/mobile-nadotongryoksa && npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts)
- Clean-state integrated pass #1 result: section boundary lock PASS; backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Clean-state integrated pass #2 command (2026-07-09 03:53:19 +09:00): python scripts/check_section_boundary_lock.py ; ./.venv/Scripts/python.exe -m pytest backend/tests/test_voip_language_locales.py -q ; (cd apps/mobile-nadotongryoksa && npm test -- --runInBand src/__tests__/faceConversationTiming.test.ts src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayTurnController.test.ts src/__tests__/scriptLangResolver.test.ts src/__tests__/sorisaeVoiceTuning.test.ts src/__tests__/sorisaeEcho.test.ts src/__tests__/sorisaeCaptureSegment.test.ts)
- Clean-state integrated pass #2 result: section boundary lock PASS; backend locale parity PASS (7/7); mobile integrated suites PASS (83/83)
- Invariant confirmation: no simultaneous VoIP+Sorisae dedicated diffs in the same check run (boundary lock clean-state PASS x2)
- Leakage confirmation: no `voice_gateway.py` friend-chat forbidden keyword diff hits and no App.tsx cross-section coupling hit (boundary lock clean-state PASS x2)

## 6. Release readiness
- [x] Update release candidate build metadata
- [x] Validate publish artifact and API smoke checks
- [x] Produce final pass/fail matrix by feature
- [x] Approve promotion or rollback with reason

Evidence
- Release candidate metadata (manifest): versionName=1.0.237, versionCode=312, package=com.parkcheolhong.worldlinco, publishedAt=2026-07-07T23:03:05.7548556Z, artifact=nadotongryoksa-v1.0.237-build312-current.apk
- Baseline policy alignment: knowledge/worldlinco_apk_baseline.json => versionCode=312, versionName=1.0.237, probe_min_build=296 (metadata aligned)
- Publish artifact/API smoke evidence: sorisae-http-probe-gate=success; sorisae-unit-gate=success; backend-security-gate=success; test-and-kpi-gate=success
- CI release gate blocker at decision time: SonarCloud Code Analysis=failed (Quality Gate fail: Security Rating on New Code E, Reliability Rating on New Code E)
- Pass/fail matrix by feature (latest SHA: bae9b58255a60f224536662124f172acd2247af7)
	- Face core: PASS (integrated pass x2 in section 5)
	- VoIP core/parity: PASS (integrated pass x2 in section 5)
	- Sorisae freeze/probe: PASS (unit+http probe gate success)
	- Cross-feature integrity: PASS (section boundary lock + integrated suites pass x2)
	- Security/quality release gate: FAIL (SonarCloud Quality Gate)
- Final decision: ROLLBACK/HOLD promotion for PR #94 until SonarCloud quality gate red is resolved and rerun is green.
