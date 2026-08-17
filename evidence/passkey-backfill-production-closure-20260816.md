# Passkey Backfill Production Closure Report (2026-08-16)

## 1) Scope
- Objective: Legacy user passkey fields (`users.passkey_*`) backfill verification into `passkey_credentials`.
- Environment: Production domains
  - <https://xn--114-2p7l635dz3bh5j.com>
  - <https://metanova1004.com>

## 2) Execution Log Snapshot (Actual)

```text
=== RUN: health-xn
HTTP:200
=== RUN: health-metanova
HTTP:200
=== RUN: backfill-apply
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: backfill-dryrun
PASSKEY_BACKFILL scanned=1 inserted=0 updated=0 unchanged=1 skipped=0
=== RUN: passkey-start-xn
HTTP:200
=== RUN: passkey-start-metanova
HTTP:200
```

## 3) Checkpoints and Result
- [x] Health check: both production domains return 200.
- [x] Backfill apply run completed without exception.
- [x] Idempotency re-check passed (`inserted=0`, `updated=0`, `unchanged=1`).
- [x] Passkey login start API returned 200 on both domains.

## 4) Interpretation
- The migration state is stable and already converged.
- Backfill apply does not produce additional writes in current production state.
- Re-running dry-run confirms idempotent behavior.

## 5) Final Closure Decision
- Status: 완료됨
- Reason:
  - Runtime health 정상(2개 도메인)
  - 백필 적용/재검증 성공
  - 멱등성 확인 완료
  - 운영 패스키 시작 API 정상

## 6) Commands Used (Repro)

```powershell
python scripts/backfill_passkey_credentials.py
python scripts/backfill_passkey_credentials.py --dry-run

$body = @{ email = '119cash@naver.com' } | ConvertTo-Json -Compress
Invoke-WebRequest -UseBasicParsing -Uri 'https://xn--114-2p7l635dz3bh5j.com/api/auth/passkey/login/start' -Method Post -ContentType 'application/json' -Body $body
Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/api/auth/passkey/login/start' -Method Post -ContentType 'application/json' -Body $body
```

## 7) Real Device Reinstall and Runtime Verification (2026-08-16)

### 7.1 Reinstall result (actual device)
- Device: `172.30.1.15:5555`
- Reinstall target: `uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk`
- Install result: `Success`
- Installed package:
  - `com.parkcheolhong.worldlinco`
  - `versionName=1.0.246`
  - `versionCode=331`
  - `lastUpdateTime=2026-08-16 05:22:48`

### 7.2 Passkey callback re-verification (real token callback path)
- Script: `scripts/verify_passkey_callback_real_token.ps1`
- Result: `PASS`
- Evidence directory:
  - `evidence/apk-passkey-real-token-e2e-20260816-052348`
- Validation summary includes:
  - callback reinjection per round (initial + retry)
  - `PASSKEY_LOGIN_CALLBACK_SUCCESS`
  - `SOCIAL_LOGIN_CALLBACK_SUCCESS`

### 7.3 Runtime launch/log validation
- Evidence directory:
  - `evidence/device-runtime-check-20260816-052451`
- Key observations from filtered log:
  - App launch confirmed (`Running "main"`)
  - Production base URL loaded: `https://metanova1004.com`
  - Remote tuning loaded (`[WORLDLINGCO_TUNING] remote_loaded`)
  - `silero_probe supported=false` on current device

### 7.4 Production API connectivity re-check
- `GET /api/marketplace/worldlinco/tuning` -> `200`
- `GET /api/marketplace/worldlinco/tourism-promo?...` -> `200`
  - payload example: `{"enabled":false,"reason":"gps_country_required"...}`
- `GET /api/marketplace/latest-apk-metadata` -> `200`
  - `version_name=1.0.246`, `build_number=331`, `size_bytes=58227497`

### 7.5 Audio route / Bluetooth state (settings-related)
- Device Bluetooth global state: `0` (off)
- `dumpsys audio` snapshot:
  - `mBluetoothHeadset: null`
  - `mBluetoothHeadsetDevice: null`
  - `mA2dp: null`
  - `mScoAudioState: SCO_STATE_INACTIVE`
  - historical route events show `setSpeakerphoneOn(true)` calls from `com.parkcheolhong.worldlinco`

### 7.6 Interpretation
- Reinstall + package/version integrity: 정상
- Production API/tuning/metadata reachability: 정상
- Passkey callback path on real device: 정상(PASS)
- Current no-speech symptom likely tied to runtime capture path on this device (`silero_probe supported=false`) and requires focused Sorisae voice capture/TTS path debugging with the same device profile.

## 8) Sorisae Forced 1-shot Timeline + Settings Refresh UI Evidence (2026-08-16)

### 8.1 Forced 1-shot Sorisae probe execution
- Command:
  - `python scripts/run_sorisae_friend_chat_probe.py --base-url http://127.0.0.1:8000 --adb-device 172.30.1.15:5555`
- Evidence directory:
  - `evidence/sorisae-friend-chat-probe-20260815-203946`
- Probe output (`report.json`) summary:
  - `friend_chat_text_llm`: PASS
  - `friend_chat_audio_speech_m4a`: PASS (transcript recognized)
  - `adb_sorisae_runtime`: FAIL (`segment_200=False`)

### 8.2 Tagged timeline extraction (capture -> STT/TTS markers)
- Raw full log:
  - `evidence/sorisae-friend-chat-probe-20260815-203946/logcat-full.log`
- Filtered tag timeline:
  - `evidence/sorisae-friend-chat-probe-20260815-203946/sorisae-tagged-timeline.log`
- Observed timeline facts:
  - `ReactNativeJS [FACE_CONVERSATION] {"event":"silero_probe","supported":false}` 확인
  - Samsung TTS 엔진 로드/가용 이벤트 확인
  - 이번 강제 1회 시도 구간에서는 `FACE_CAPTURE_TRACE post_start`, `response_received`, `segment_response`가 로그에 나타나지 않음
- Interpretation:
  - 앱 런타임/오디오 엔진 로드는 살아 있으나, 실제 캡처 세그먼트 업로드-응답(TTS 재생 포함) 구간이 동일 실행창에서 확정되지 않음

### 8.3 Settings refresh immediate UI string capture
- Evidence directory:
  - `evidence/sorisae-settings-audio-route-20260815-1`
- Snapshot files:
  - `ui-home.xml`
  - `ui-settings-after-refresh-1s.xml`
  - `ui-settings-after-refresh-3s.xml`
  - `audio-route-live-status.txt`
- Extracted UI string after refresh tap (`worldlinco-settings-refresh-audio-route`):
  - `실시간 상태: 스피커 OFF · BT 미연결` (1s/3s snapshot 동일)

### 8.4 Closure status for this request
- Forced 1-shot timeline: 실행 및 증적 수집 완료 (단, 캡처 세그먼트 200 구간은 미관측)
- Settings refresh UI string capture: 완료 (문자열 고정 증적 확보)
