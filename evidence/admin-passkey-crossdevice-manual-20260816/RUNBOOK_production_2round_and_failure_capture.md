# Production Passkey 2-Round Validation + Failure Capture Runbook

## 0) Goal
- Close production verification with hard evidence.
- If QR does not open, capture root-cause artifacts immediately in one run.

## 1) Round Validation Template (External Chrome, Production)

### Target
- URL: `https://xn--114-2p7l635dz3bh5j.com/admin/login`
- Account: `119cash@naver.com`

### Round 1
- [ ] Open target URL in external Chrome (normal profile)
- [ ] Enter email and click `지문/패스키 로그인`
- [ ] QR sheet opens
- [ ] Phone scan + approval complete
- [ ] Redirect/login success to admin dashboard
- [ ] Save screenshot: `external-chrome-round1-success.png`
- [ ] Save time (KST): `____________________`

### Round 2
- [ ] Repeat same steps
- [ ] Save screenshot: `external-chrome-round2-success.png`
- [ ] Save time (KST): `____________________`

### Final Pass Criteria
- [ ] Round 1 success
- [ ] Round 2 success
- [ ] Two screenshots attached in the same evidence folder

## 2) Failure Instant-Capture (copy/paste)

Run this from repo root immediately after failure:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File \
  .\evidence\admin-passkey-crossdevice-manual-20260816\capture_production_passkey_failure.ps1 \
  -Domain "xn--114-2p7l635dz3bh5j.com" \
  -Email "119cash@naver.com"
```

Output folder will be printed as:
- `evidence/admin-passkey-crossdevice-manual-20260816/failure-capture-YYYYMMDD-HHMMSS`

## 3) Chrome DevTools Quick Trace (optional but recommended)

On the failing `admin/login` page, open DevTools Console and paste:
- `evidence/admin-passkey-crossdevice-manual-20260816/chrome_passkey_debug_snippet.js`

Then reproduce once. After failure, run in Console:

```javascript
window.__passkeyDebug && window.__passkeyDebug.download();
```

This downloads a JSON log including:
- passkey start/finish fetch status/body
- navigator.credentials.get/create timing + errors

## 4) Attach These Files to Close Issue
- `external-chrome-round1-success.png`
- `external-chrome-round2-success.png`
- `failure-capture-.../` directory contents (only when failed)
- `passkey-debug-*.json` from Chrome snippet (optional but preferred)
