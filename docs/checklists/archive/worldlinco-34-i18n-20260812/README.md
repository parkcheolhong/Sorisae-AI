# worldlinco-34 i18n separation archive (2026-08-12)

## 1) Scoped workset (intentional changes)
- apps/mobile-nadotongryoksa/App.tsx
- apps/mobile-nadotongryoksa/src/features/song/useVoiceCaptureManager.ts
- apps/mobile-nadotongryoksa/src/features/i18n/featureUiCatalog.ts
- docs/checklists/worldlinco-app-improvement-checklist-20260812.md

Patch snapshot:
- docs/checklists/archive/worldlinco-34-i18n-20260812/changes.patch

## 2) Excluded as generated outputs (non-workset)
- frontend/frontend/.next-build/**
- frontend/frontend/test-results/**
- other unrelated modified/untracked files from parallel tasks

## 3) Verification (2 passes)
Pass A:
- npm run typecheck
- npm test -- --runInBand src/__tests__/userLanguageWiring.test.ts
- log: docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passA/typecheck.txt
- log: docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passA/userLanguageWiring.txt

Pass B:
- npm run typecheck
- npm test -- --runInBand src/__tests__/userLanguageWiring.test.ts
- log: docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passB/typecheck.txt
- log: docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/passB/userLanguageWiring.txt

## 4) Real-device local test
Device visibility:
- adb devices -> R83W70QY11H (device), 10.202.94.167:5555 (device), 172.30.1.15:5555 (device)

Executed:
- npm run verify:kws:device
- ANDROID_SERIAL=R83W70QY11H npm run verify:kws:device
- adb -s R83W70QY11H uninstall com.parkcheolhong.worldlinco
- adb -s R83W70QY11H install -r apps/mobile-nadotongryoksa/tmp/device-apk/worldlinco-current-base.apk
- powershell -NoProfile -File ./scripts/verify_on_device_kws.ps1 -LaunchApp -DurationSec 120 -DeviceSerial R83W70QY11H
- npm run verify:kws:device:trigger -- -DeviceSerial R83W70QY11H -DurationSec 90 (pass1)
- npm run verify:kws:device:trigger -- -DeviceSerial R83W70QY11H -DurationSec 90 (pass2)

Evidence:
- docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-verify.txt
- docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-verify-single.txt
- docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-verify-after-script-fix.txt
- docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass1-rerun.txt
- docs/checklists/archive/worldlinco-34-i18n-20260812/evidence/device-kws-trigger-pass2-rerun.txt

Observed result:
- Script was updated to support explicit device selection (`-DeviceSerial` / `ANDROID_SERIAL`) and launch fallback.
- Script was updated to include companion-arm trigger scenario with lobby fallback (`worldlinco-demo-session-start-button-inline`).
- After reinstall + rerun, app launch succeeded on primary start attempt.
- Two repeated trigger measurements on the same device both reported: `GATE: FAIL (no companion marker observed - trigger path may not be reached)`.
- UI dump confirms current build starts at login lobby and companion toggle (`worldlinco-companion-voicecall-toggle`) is not exposed in that state.

## 5) Frozen marker gate (runtime track)

Gate rule (fixed):
- PASS: `native_started` observed in the same capture window.
- FAIL-A: `native_skip` observed before `native_started`.
- FAIL-B: no `COMPANION_KWS` and no `COMPANION_VOICE_CALL` markers observed.
- FAIL-C: companion marker observed but `native_started` missing.

Current runtime-track result (R83W70QY11H, 2-pass repeat):
- pass1: FAIL-B
- pass2: FAIL-B

Conclusion:
- Source-level i18n normalization verification is PASS (2 passes).
- 3-4 is provisionally approved at source-verification level.
- Real-device KWS runtime validation is separated as a follow-up track (runtime diagnostics), because launchability blocker is resolved but marker-level runtime signal is still missing.
