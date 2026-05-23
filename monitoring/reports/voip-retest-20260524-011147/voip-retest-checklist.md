# VoIP Presence Error Root Cause + 2-Device Revalidation

## Root Cause Trace (Device2)

- [x] Device2 runtime emits FCM initialization failure before VoIP presence close.
 	- Evidence: `No Firebase App '[DEFAULT]' has been created` in [monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log](monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log#L1)
 	- Evidence: subscribe failure in [monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log](monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log#L2)

- [x] Device2 runtime emits `VOIP_PRESENCE_ERROR` and immediately closes flow.
 	- Evidence: `VOIP_PRESENCE_ERROR` in [monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log](monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log#L7)
 	- Evidence: `VOIP_PRESENCE_CLOSED` in [monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log](monitoring/reports/voip-live-20260524-010509/device2_voip_key_events.log#L8)

- [x] Installed runtime binary lineage differs from current workspace mobile config lineage.
 	- Evidence: installed package used in revalidation is `com.parkcheolhong.worldling` (ADB package metadata check during this run).
 	- Evidence: workspace Expo Android package is `com.Shinsegye.nadotongryoksa` in [apps/mobile-nadotongryoksa/app.json](apps/mobile-nadotongryoksa/app.json#L29)
 	- Evidence: workspace Android app ID also `com.Shinsegye.nadotongryoksa` in [apps/mobile-nadotongryoksa/android/app/build.gradle](apps/mobile-nadotongryoksa/android/app/build.gradle#L127)
 	- Evidence: expected runtime log strings (`VOIP_PRESENCE_ERROR`, `voip`) are not found in workspace source tree during this investigation.

## 2-Device Revalidation Session

- Session folder: [monitoring/reports/voip-retest-20260524-011147](monitoring/reports/voip-retest-20260524-011147)
- Raw logs:
 	- [monitoring/reports/voip-retest-20260524-011147/device1.log](monitoring/reports/voip-retest-20260524-011147/device1.log)
 	- [monitoring/reports/voip-retest-20260524-011147/device2.log](monitoring/reports/voip-retest-20260524-011147/device2.log)
- Filtered key logs:
 	- [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log)
 	- [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log)

## Gate Checklist (Requested Signals)

- [ ] `VOIP_START_CALL_PRESS`
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log#L1)
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log#L1)

- [ ] `[VoIP] Offer sent`
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log#L1)
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log#L1)

- [ ] `[VoIP] Answer applied`
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log#L1)
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log#L1)

- [ ] `[VoIP] Connection state: connected`
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log#L1)
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log#L1)

- [ ] `[VoIPScreen] Stopping tone - call accepted/connected`
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device1_key.log](monitoring/reports/voip-retest-20260524-011147/device1_key.log#L1)
 	- Evidence: not present in [monitoring/reports/voip-retest-20260524-011147/device2_key.log](monitoring/reports/voip-retest-20260524-011147/device2_key.log#L1)

## Lineage Alignment Build/Reinstall Status

- [ ] Workspace source APK build completed (`apps/mobile-nadotongryoksa/android`) and reinstall to both devices.
 	- Evidence (full log, initial blocker pair): [monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0130.log](monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0130.log)
 	- Evidence (key lines, initial blocker pair): [monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0130-key.log](monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0130-key.log#L1)
 	- Evidence (full log, latest JDK17 attempt): [monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0138.log](monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0138.log)
 	- Evidence (key lines, latest JDK17 attempt): [monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0138-key.log](monitoring/reports/voip-retest-20260524-011147/build-attempt-20260524-0138-key.log#L1)
	- Evidence (focused configure retry): `:expo-av:configureCMakeDebug[arm64-v8a]` still fails with `CXX1210 No compatible library found` after cache reset and prefab seed workaround.
	- Evidence (version pin): `expo-av` pinned to `14.0.6` in [apps/mobile-nadotongryoksa/package.json](apps/mobile-nadotongryoksa/package.json#L23).
	- Evidence (module local patch): `expo-av` local arm64 prefab seed and native stub workaround applied in [apps/mobile-nadotongryoksa/node_modules/expo-av/android/build.gradle](apps/mobile-nadotongryoksa/node_modules/expo-av/android/build.gradle), [apps/mobile-nadotongryoksa/node_modules/expo-av/android/CMakeLists.txt](apps/mobile-nadotongryoksa/node_modules/expo-av/android/CMakeLists.txt), [apps/mobile-nadotongryoksa/node_modules/expo-av/android/src/main/cpp/expo_av_stub.cpp](apps/mobile-nadotongryoksa/node_modules/expo-av/android/src/main/cpp/expo_av_stub.cpp).
	- Evidence (scope shift): after expo-av mitigation, blocker moved to `:expo-modules-core:configureCMakeDebug[arm64-v8a]` with same `CXX1210` during local assembleDebug.
	- Evidence (EAS fallback start): development profile remote build created: `1e773cbc-5025-4735-945f-5228a6065ee9` (status currently `IN_PROGRESS`).
	- Evidence (EAS prerequisite): `expo-dev-client` installed to satisfy development profile requirement in [apps/mobile-nadotongryoksa/package.json](apps/mobile-nadotongryoksa/package.json#L27).
	- Current blocker: local arm64 native configure now blocks at `expo-modules-core` with `CXX1210`, and EAS fallback APK artifact is still pending (`IN_PROGRESS`).
 	- Resolved on latest run: `expo-updates:kaphDebugKotlin`의 `C:\Windows\sqlite-...dll.lck` 권한 에러는 JDK 17 적용 후 재현되지 않음.
	- Resolved on latest run: Expo dependency doctor gate no longer fails on pinned `expo-av` after adding `expo.install.exclude=["expo-av"]` in [apps/mobile-nadotongryoksa/package.json](apps/mobile-nadotongryoksa/package.json).
	- Resolved on latest run: Metro doctor gate cleared by adding Expo default metro config in [apps/mobile-nadotongryoksa/metro.config.js](apps/mobile-nadotongryoksa/metro.config.js).
	- Result: 동일 소스 APK를 아직 확보하지 못해 2대 재설치/재실검 게이트 통과 검증으로 진행 불가 (EAS 산출물 대기 중).

## Revalidation Verdict

- Result: **FAIL (blocked before call signaling path)**
- Blocker summary:
 	- Device2 has confirmed VoIP presence failure path with FCM default app initialization error in the runtime currently installed.
 	- Current installed runtime package lineage (`com.parkcheolhong.worldling`) does not match workspace mobile Android package lineage (`com.Shinsegye.nadotongryoksa`), and source APK build is blocked by native/kaph build errors, so source-level FCM/presence patching in this workspace cannot yet be validated against a freshly reinstalled runtime.
