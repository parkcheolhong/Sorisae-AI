# PR: WorldLinco 312 Distribution Lock and Evidence

## Proposed Title
chore(worldlinco): lock marketplace install state to build 312 and attach verification evidence

## Branch
- Head: feat/worldlinco-build331-i18n
- Base: main

## Reviewer TL;DR
- Decision target: Confirm that marketplace install target is hard-locked to build 312 and reproducibly verifiable.
- Scope in this PR body: Validation and evidence packaging for distribution state.
- Acceptance signal: All checklist items below pass without manual interpretation.

## Reviewer Checklist

### 1) Scope and Intent
- [ ] This PR is interpreted as distribution-state verification for build 312 only.
- [ ] Out-of-scope features are not required for approval.

### 2) Version Lock Integrity
- [ ] apps/mobile-nadotongryoksa/app.json shows expo.android.versionCode = 312.
- [ ] apps/mobile-nadotongryoksa/android/app/build.gradle shows defaultConfig.versionCode = 312.
- [ ] uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json shows versionCode = 312.

### 3) Marketplace Runtime Integrity
- [ ] GET /api/marketplace/apk/worldlinco/manifest returns 200.
- [ ] Manifest versionCode is 312.
- [ ] /api/marketplace/latest.apk byte size equals canonical APK byte size.
- [ ] SHA256(latest.apk) equals SHA256(canonical APK).

### 4) Evidence and Traceability
- [ ] Validation report exists and is readable.
- [ ] Hash and byte-size evidence in report matches local reproduction output.

## Verified Values (Current Run)
- manifest_http: 200
- manifest_versionCode: 312
- manifest_versionName: 1.0.237
- manifest_file: nadotongryoksa-v1.apk
- latest_bytes: 88096654
- canonical_bytes: 88096654
- latest_hash_match: true
- sha256: 52438446af49c4baee69193f663dce36c86a49318e584797e408015aeb56319d

## Risks
- Primary risk: Repository working tree contains broad unrelated changes and evidence artifacts, which can distract review focus.
- Secondary risk: Reviewers may assume broader behavior changes beyond distribution lock.

## Mitigations
- Restrict approval criteria to the checklist above.
- Use explicit reproduction commands and hash equality as pass/fail gates.

## Rollback Plan
1. Restore previous marketplace artifact pointers by replacing uploads/marketplace_local/apk/nadotongryoksa-v1.apk and uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json with prior known-good pair.
2. Re-run manifest and hash verification commands.
3. Confirm manifest versionCode and hash/size parity for the restored target.

## Reproduction Commands (PowerShell)

### 1) Version lock check

```powershell
Select-String -Path apps/mobile-nadotongryoksa/app.json -Pattern '"versionCode"\s*:\s*312'
Select-String -Path apps/mobile-nadotongryoksa/android/app/build.gradle -Pattern 'versionCode\s+312'
Select-String -Path uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json -Pattern '"versionCode"\s*:\s*312'
```

### 2) Manifest and hash parity check

```powershell
$ErrorActionPreference='Stop'
$base='http://127.0.0.1:8000'
$m=Invoke-WebRequest -UseBasicParsing "$base/api/marketplace/apk/worldlinco/manifest" -TimeoutSec 30
$mj=$m.Content|ConvertFrom-Json
$latest=Join-Path $PWD '.tmp_marketplace_latest_verify.apk'
Invoke-WebRequest -UseBasicParsing "$base/api/marketplace/latest.apk" -OutFile $latest -TimeoutSec 120 | Out-Null
$canon='uploads/marketplace_local/apk/nadotongryoksa-v1.apk'
$h1=(Get-FileHash $canon -Algorithm SHA256).Hash.ToLower()
$h2=(Get-FileHash $latest -Algorithm SHA256).Hash.ToLower()
[pscustomobject]@{
   manifest_http=$m.StatusCode
   manifest_versionCode=$mj.versionCode
   latest_bytes=(Get-Item $latest).Length
   canonical_bytes=(Get-Item $canon).Length
   latest_hash_match=($h1 -eq $h2)
   sha256=$h1
} | Format-List
```

## Linked Report
- docs/technical/worldlinco-312-validation-report-20260717.md
