# PR Draft: WorldLinco Marketplace 312 State Verification

## Title
`chore(worldlinco): lock marketplace install state to build 312 and attach verification evidence`

## Base Information
- Head branch: `feat/worldlinco-build331-i18n`
- Base branch: `main`

## Summary
- Reconfirmed WorldLinco distribution state at `versionCode 312`.
- Verified source/build/manifest alignment.
- Revalidated marketplace manifest endpoint and APK hash consistency.
- Added formal validation report document for traceability.

## Verification Evidence
- Version alignment:
  - `apps/mobile-nadotongryoksa/app.json` -> `312`
  - `apps/mobile-nadotongryoksa/android/app/build.gradle` -> `312`
  - `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json` -> `312`
- API/runtime result:
  - `manifest_http=200`
  - `manifest_versionCode=312`
  - `latest_hash_match=true`
  - `sha256=52438446af49c4baee69193f663dce36c86a49318e584797e408015aeb56319d`

## Report Link
- `docs/technical/worldlinco-312-validation-report-20260717.md`

## Risk / Out of Scope
- Working tree currently contains broad unrelated changes and evidence artifacts; this PR narrative is scoped to WorldLinco 312 distribution validation only.

## Checklist
- [x] Source/build/manifest version alignment checked
- [x] Marketplace manifest response checked
- [x] Marketplace latest APK hash checked
- [x] Validation report document added
