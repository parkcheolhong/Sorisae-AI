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

### E1) Scope and Intent
- [ ] This PR is interpreted as distribution-state verification for build 312 only.
- [ ] Out-of-scope features are not required for approval.

### E2) Version Lock Integrity
- [ ] apps/mobile-nadotongryoksa/app.json shows expo.android.versionCode = 312.
- [ ] apps/mobile-nadotongryoksa/android/app/build.gradle shows defaultConfig.versionCode = 312.
- [ ] uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json shows versionCode = 312.

### E3) Marketplace Runtime Integrity
- [ ] GET /api/marketplace/apk/worldlinco/manifest returns 200.
- [ ] Manifest versionCode is 312.
- [ ] /api/marketplace/latest.apk byte size equals canonical APK byte size.
- [ ] SHA256(latest.apk) equals SHA256(canonical APK).

### E4) Evidence and Traceability
- [ ] Validation report exists and is readable.
- [ ] Hash and byte-size evidence in report matches local reproduction output.

## Maintainer Execution Status (Checklist-Based)

### E5) Review Thread Closure
- [x] Copilot unresolved review thread on PR draft doc is resolved.
- 근거: review thread PRRT_kwDOR_seGs6RwqQX resolved via GitHub GraphQL mutation.
- [x] Copilot unresolved review thread on validation report doc is resolved.
- 근거: review thread PRRT_kwDOR_seGs6RwqQ2 resolved via GitHub GraphQL mutation.

Status: completed

### 1) Scope and Intent
- [x] This PR is interpreted as distribution-state verification for build 312 only.
- 근거: PR title and current body both target build 312 distribution-state verification only.
- [x] Out-of-scope features are not required for approval.
- 근거: PR changed files are docs-only (2 files): docs/technical/worldlinco-312-pr-draft-20260717.md, docs/technical/worldlinco-312-validation-report-20260717.md.

### 2) Version Lock Integrity
- [x] apps/mobile-nadotongryoksa/app.json shows expo.android.versionCode = 312.
- 근거: pass1=true, pass2=true.
- [x] apps/mobile-nadotongryoksa/android/app/build.gradle shows defaultConfig.versionCode = 312.
- 근거: pass1=true, pass2=true.
- [x] uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json shows versionCode = 312.
- 근거: pass1=true, pass2=true.

### 3) Marketplace Runtime Integrity
- [x] GET /api/marketplace/apk/worldlinco/manifest returns 200.
- 근거: pass1 manifest_http=200, pass2 manifest_http=200.
- [x] Manifest versionCode is 312.
- 근거: pass1 manifest_versionCode=312, pass2 manifest_versionCode=312.
- [x] /api/marketplace/latest.apk byte size equals canonical APK byte size.
- 근거: pass1 latest_bytes=88096654 and canonical_bytes=88096654, pass2 latest_bytes=88096654 and canonical_bytes=88096654.
- [x] SHA256(latest.apk) equals SHA256(canonical APK).
- 근거: pass1 latest_hash_match=true, pass2 latest_hash_match=true.

### 4) Evidence and Traceability
- [x] Validation report exists and is readable.
- 근거: docs/technical/worldlinco-312-validation-report-20260717.md present and readable.
- [x] Hash and byte-size evidence in report matches local reproduction output.
- 근거: pass1/pass2 sha256=52438446af49c4baee69193f663dce36c86a49318e584797e408015aeb56319d, latest_bytes=88096654, canonical_bytes=88096654.

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

## Review Comment Templates

### Approve/Request changes Criteria Table

Hard-gate rule: if even one review item is fail, the review outcome is automatically Request changes.

| Review Item | Approve if | Request changes if |
| --- | --- | --- |
| Scope and intent | PR scope is clearly limited to distribution-state verification for build 312 | Scope is ambiguous or implies broader feature changes |
| Version lock integrity | app.json, build.gradle, and manifest are all 312 | Any one of the three is not 312 |
| Marketplace manifest check | /api/marketplace/apk/worldlinco/manifest returns 200 and versionCode 312 | Endpoint fails or versionCode is not 312 |
| Artifact parity | latest.apk byte size and SHA256 match canonical APK | Size or SHA256 mismatch |
| Evidence quality | Validation report includes reproducible values and matches rerun output | Evidence is missing, stale, or non-reproducible |
| Rollback readiness | Rollback procedure is concrete and executable | Rollback is vague or unverified |

Decision policy:
- All items pass: Approve.
- One or more items fail: Request changes (automatic, no exception).

### Approve Comment Template

```markdown
Approve

Reason
- Scope is appropriately constrained to WorldLinco build 312 distribution-state verification.
- Version lock is consistent across app.json, build.gradle, and marketplace manifest.
- Marketplace manifest endpoint and latest artifact parity checks pass.
- Evidence and rollback guidance are sufficient for operational safety.

Verified checkpoints
- manifest_http=200
- manifest_versionCode=312
- latest_hash_match=true
- sha256=52438446af49c4baee69193f663dce36c86a49318e584797e408015aeb56319d

Conclusion
- Approved.
```

### Request changes Comment Template

```markdown
Request changes

Blocking findings
- [ ] Scope mismatch: PR body must remain strictly distribution-state verification for build 312.
- [ ] Version mismatch detected in one or more lock files (app.json, build.gradle, manifest).
- [ ] Manifest endpoint validation failed (non-200 or wrong versionCode).
- [ ] latest.apk parity failed (byte size or SHA256 mismatch).
- [ ] Evidence/rollback instructions are incomplete or not reproducible.

Required fixes
1. Re-run version lock and parity checks, then paste fresh results in the PR body.
2. Update verified values and align all lock targets to 312.
3. Ensure rollback steps are executable and explicitly ordered.

Re-review condition
- Convert every blocking item above to pass state with reproducible output.
```
