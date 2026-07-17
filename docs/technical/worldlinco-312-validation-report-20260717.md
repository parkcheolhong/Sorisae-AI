# WorldLinco 312 Validation Report (2026-07-17)

## Scope
- Validate marketplace distribution state for WorldLinco APK in current branch status.
- Confirm version alignment across source/build/manifest.
- Confirm API-based manifest + download consistency.
- Preserve evidence for PR submission.

## Target Branch Context
- Repository: `parkcheolhong/Sorisae-AI`
- Branch: `feat/worldlinco-build331-i18n`
- Base: `main`

## Version Alignment Check
- `apps/mobile-nadotongryoksa/app.json`
  - `expo.version`: `1.0.237`
  - `expo.android.versionCode`: `312`
- `apps/mobile-nadotongryoksa/android/app/build.gradle`
  - `defaultConfig.versionName`: `1.0.237`
  - `defaultConfig.versionCode`: `312`
- `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json`
  - `versionName`: `1.0.237`
  - `versionCode`: `312`
  - `apkFilename`: `nadotongryoksa-v1.apk`

## Runtime/API Verification (latest run)
- Command basis: local backend `http://127.0.0.1:8000`
- Result snapshot:
  - `manifest_http`: `200`
  - `manifest_versionCode`: `312`
  - `manifest_versionName`: `1.0.237`
  - `manifest_file`: `nadotongryoksa-v1.apk`
  - `latest_bytes`: `88096654`
  - `canonical_bytes`: `88096654`
  - `latest_hash_match`: `true`
  - `sha256`: `52438446af49c4baee69193f663dce36c86a49318e584797e408015aeb56319d`

## Interpretation
- Marketplace `latest.apk` and canonical APK are byte-identical.
- Manifest version and source/build version are aligned at `312`.
- Current state is ready for user-side manual installation from marketplace endpoint.

## Notes
- This report reflects current workspace/runtime state and does not imply that all unrelated working-tree changes are part of the WorldLinco 312 scope.
