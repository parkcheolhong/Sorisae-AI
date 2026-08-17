# Sorisae Public-Data + EAS + UI Smoke Audit (2026-08-13)

## 1) Build status polling automation
- Status: 구현됨
- Script: scripts/watch_eas_build_status.ps1
- Fix applied:
  - Removed unsupported `ConvertFrom-Json -Depth` usage for Windows PowerShell compatibility.
  - Kept `eas build:view <id> --json` parsing with JSON-first substring extraction.
- Latest successful watcher evidence:
  - docs/checklists/evidence/eas-build-watch-20260813_043054/summary.log
  - docs/checklists/evidence/eas-build-watch-20260813_043054/last-build-view.json
- Terminal-state proof line:
  - `[END] ... terminal status reached: FINISHED`

## 2) EAS CLI upgrade and submit command verification
- Status: 완료됨
- CLI version proof:
  - `eas-cli/21.8.0 win32-x64 node-v25.2.1`
- Build proof:
  - Build ID: `bd968eb2-9176-4060-8b34-4b2d5d10ca7d`
  - State: `FINISHED`
- Submit proof:
  - Submission ID: `fe0c3fd4-984a-4ffd-a7e8-64d04cfbb873`
  - State: `ERRORED`
  - Error code: `SUBMISSION_SERVICE_ANDROID_FIRST_UPLOAD_ERROR`
  - Message: first Android submission must be performed manually in Google Play Console.
- Retry proof:
  - Retry command created a new submission ID `18ab5908-3d28-4c07-8c9b-23fe5c1b0613`
  - Current state: `IN_QUEUE`
  - Same source submission ID was used for the retry flow.

## 3) UI simplification screenshot smoke (settings/chat/travel/voip)
- Status: 실패
- Capture script:
  - scripts/capture_mobile_ui_smoke_tabs.ps1
- Latest evidence bundle:
  - docs/checklists/evidence/mobile-ui-smoke-20260813-043304/manifest.json
  - docs/checklists/evidence/mobile-ui-smoke-20260813-043304/01_chat.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-043304/02_voip.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-043304/03_travel.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-043304/04_settings.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-044836/manifest.json
  - docs/checklists/evidence/mobile-ui-smoke-20260813-044836/01_chat.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-044836/02_voip.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-044836/03_travel.png
  - docs/checklists/evidence/mobile-ui-smoke-20260813-044836/04_settings.png
- Blocking evidence:
  - `demo_session_started=false`
  - `tapped_by_selector=false` for all 4 targets.
  - Device remained on login-required lobby screen, so post-login tab screen capture was not achieved.
  - Latest reruns `044416`, `044623`, and `044836` still landed on the login gate screen.
  - `051354` rerun opened the login modal, but `POST https://metanova1004.com/api/auth/login` with `119cash@naver.com / MetaNova!2026` returned `401`, so the current credential is invalid and the smoke cannot progress to actual tab screens yet.

## 4) Sorisae public-data guide and .env mapping re-audit
- Status: 구현됨
- Source mapping references:
  - backend/services/friend_public_portal.py
  - backend/admin_router.py
  - docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md
  - .env/.env
  - .env.example

### 4.1 Runtime key coverage
- VOICE_FRIEND_PUBLIC_PORTAL_GROUNDING: present (`1`) -> enabled
- VOICE_FRIEND_PUBLIC_PORTAL_URL_TEMPLATE: present
- VOICE_FRIEND_PUBLIC_PORTAL_API_KEY: present
- VOICE_FRIEND_PUBLIC_PORTAL_FLIGHT_URL_TEMPLATE: present
- VOICE_FRIEND_PUBLIC_PORTAL_FLIGHT_API_KEY: present
- VOICE_FRIEND_PUBLIC_PORTAL_TOUR_URL_TEMPLATE: present
- VOICE_FRIEND_PUBLIC_PORTAL_TOUR_API_KEY: present
- VOICE_FRIEND_PUBLIC_PORTAL_MEDICAL_URL_TEMPLATE: present
- VOICE_FRIEND_PUBLIC_PORTAL_MEDICAL_API_KEY: empty
- VOICE_FRIEND_PUBLIC_PORTAL_TRANSIT_URL_TEMPLATE: present
- VOICE_FRIEND_PUBLIC_PORTAL_TRANSIT_API_KEY: present
- SORISAE_NAVER_API_ENABLED: present (`true`)
- SORISAE_NAVER_API_BASE_URL: present
- SORISAE_NAVER_API_CLIENT_ID: present
- SORISAE_NAVER_API_CLIENT_SECRET: present
- SORISAE_NAVER_API_AUTH_MODE: absent (runtime default=`naver`)

### 4.2 Interpretation
- Medical API key is empty, but runtime code falls back to `VOICE_FRIEND_PUBLIC_PORTAL_API_KEY`.
- `.env.example` does not include the full public-portal key block, so environment bootstrap drift risk exists for fresh setups.

### 4.3 Security risk note
- `.env/.env` currently contains non-redacted API credentials/secrets.
- If this file is shared/exported, rotate affected keys and move secrets to secret manager-backed injection.

## 5) Rebuild + device re-run + marketplace upload (demo button removal verification)
- Status: 구현됨
- Build/publish script:
  - scripts/publish_worldlinco_apk.ps1
- Fix applied:
  - Added Android SDK auto-detection and `local.properties` auto-generation for both roots:
    - `apps/mobile-nadotongryoksa/android/local.properties`
    - `C:\wlnc\android/local.properties`
- Build proof:
  - `BUILD SUCCESSFUL in 43s`
  - APK outputs updated at `2026-08-13 05:33`:
    - `uploads/marketplace_local/apk/nadotongryoksa-v1.apk`
    - `uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk`
    - `uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json`
  - Manifest confirmation:
    - `versionName=1.0.246`
    - `versionCode=331`
    - `downloadPath=/api/marketplace/apk/nadotongryoksa-v1.apk`
- Device redeploy proof:
  - Forced reinstall command succeeded: `adb -s 172.30.1.15:5555 install -r .../nadotongryoksa-v1.apk` -> `Success`
- Fresh device UI evidence:
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/manifest.json`
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/dump-login.xml`
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/01_chat.png`
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/02_voip.png`
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/03_travel.png`
  - `docs/checklists/evidence/mobile-ui-smoke-20260813-053446/04_settings.png`
- Demo button removal verification:
  - `Select-String` over fresh XML dumps returned `DEMO_BUTTON_NOT_FOUND` for patterns:
    - `worldlinco-demo-session-start-button`
    - `데모 세션`
- Note:
  - 4-tab screenshots were captured, but selectors are still not detected in XML (`tapped_by_selector=false`) and fallback taps were used, indicating login-gated surface remains for tab-identifiable UI state in this run.

## 6) Face one-tap device evidence after APK rebuild/reinstall (2-run validation)
- Status: 실패
- Validation script:
  - scripts/collect_face_capture_evidence.ps1
- Target device:
  - `R83W70QY11H`
- Rebuild/reinstall baseline:
  - `scripts/publish_worldlinco_apk.ps1` build succeeded (`BUILD SUCCESSFUL`).
  - Forced reinstall succeeded (`adb install -r ...` -> `Success`).

### 6.1 Run #1 (post-reinstall)
- Evidence:
  - docs/checklists/evidence/face-capture-pass1-postreinstall-20260813-055842/summary.json
  - docs/checklists/evidence/face-capture-pass1-postreinstall-20260813-055842/face-capture-trace.txt
- Result:
  - `pass=false`
  - Missing required events:
    - `start_tap`
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.2 Run #2 (post-reinstall)
- Evidence:
  - docs/checklists/evidence/face-capture-pass2-postreinstall-20260813-060213/summary.json
  - docs/checklists/evidence/face-capture-pass2-postreinstall-20260813-060213/face-capture-trace.txt
- Result:
  - `pass=false`
  - Missing required events:
    - `start_tap`
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.3 Root-cause narrowing snapshot
- Release bundle includes the expected instrumentation tokens (`FACE_CAPTURE_TRACE`, `start_tap`, `capture_started`, `payload_prepared`, `post_start`, `response_received`, `blocked_peer_language_required`) at least once each.
- Therefore, current blocker is runtime path non-entry (auto-mode capture branch not reached in device scenario), not missing build artifacts.
- Most likely gate: face conversation flow exits before `startVoiceInput({ autoMode: true })` due to same-language guard or UI state mismatch at tap time.

### 6.4 Marketplace upload progression gate
- This round does **not** satisfy the required "same scenario 2 passes" condition.
- Marketplace upload progression is blocked until two consecutive `pass=true` evidence runs are collected.

### 6.5 Auto-flow script hardening (this turn)
- Script update:
  - `scripts/collect_face_capture_evidence.ps1` was upgraded to deterministic UI-flow automation:
    - login surface detection + modal open + email/password input + submit
    - `worldlinco-home-face-hero` open
    - peer-language picker open (`worldlinco-face-screen-lang` / `worldlinco-face-peer-lang*`)
    - peer-language option tap
    - mic tap (`worldlinco-face-screen-mic`)
  - Summary now records `login` and `flow` stage flags (`faceHomeOpened`, `langPickerOpened`, `peerLangSelected`, `faceMicTapped`).

- New run evidence after hardening:
  - docs/checklists/evidence/face-capture-autoflow-smoke3-20260813-061155/summary.json
  - docs/checklists/evidence/face-capture-autoflow-smoke3-20260813-061155/face-capture-trace.txt
  - docs/checklists/evidence/face-capture-altdev-smoke1-20260813-061630/summary.json

- Current blocker (hard evidence):
  - Both devices ended in `login_not_completed`, so face-flow stages stayed false.
  - API checks for account `119cash@naver.com` returned `401` for known candidate passwords (`space0215@`, `changeme-probe-local`, `MetaNova!2026`, `RoundUi!20260426`).
  - Without a valid login (or already-authenticated session), auto-mode capture path cannot be entered; required face-capture events remain absent.

### 6.6 Operator UX regression fix (progress visibility + fast-fail)
- Status: 구현됨
- Script behavior improvement:
  - `scripts/collect_face_capture_evidence.ps1` now prints step-by-step progress logs (`logcat cleared`, `app launch requested`, `login state`, `face/lang/mic flow`, `result`).
  - Added fail-fast on login block: when login is not ready, script exits immediately with `blocked=login_not_ready` instead of waiting through full capture flow.
  - Added `LoginMode` option (`auto` / `skip`) to make runtime intent explicit during operator runs.

- Latest fast-fail evidence:
  - docs/checklists/evidence/face-capture-fastfail-check-20260813-062543/summary.json
  - docs/checklists/evidence/face-capture-fastfail-check-20260813-062543/face-capture-trace.txt
  - Console proof lines include:
    - `[06:26:24] login state: ok=False attempted=True reason=login_not_completed`
    - `[06:26:24] blocked early: login not ready`
    - `FAIL: login not ready (reason=login_not_completed)`

### 6.7 Login-state-preserved consecutive rerun (requested flow)
- Status: 실패
- Mode:
  - `LoginMode=skip` (keep current device login session and do not attempt auto-login)

### 6.7.1 Precheck
- Device state check before rerun:
  - `HAS_LOGIN_MODAL=False`
  - `HAS_HOME_FACE=True`

### 6.7.2 Pass #1 (session kept)
- Evidence:
  - docs/checklists/evidence/face-capture-pass1-session-kept-20260813-063114/summary.json
  - docs/checklists/evidence/face-capture-pass1-session-kept-20260813-063114/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=true`
  - `langPickerOpened=false`
  - `peerLangSelected=false`
  - `faceMicTapped=false`
- Result:
  - `pass=false`
  - Missing required events: `start_tap`, `capture_started`, `payload_prepared`, `post_start`, `response_received`

### 6.7.3 Pass #2 (session kept)
- Evidence:
  - docs/checklists/evidence/face-capture-pass2-session-kept-20260813-063252/summary.json
  - docs/checklists/evidence/face-capture-pass2-session-kept-20260813-063252/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=true`
  - `langPickerOpened=false`
  - `peerLangSelected=false`
  - `faceMicTapped=false`
- Result:
  - `pass=false`
  - Missing required events: `start_tap`, `capture_started`, `payload_prepared`, `post_start`, `response_received`

### 6.7.4 Gate outcome
- Requested "same device, consecutive 2 pass=true" condition is still not met.
- Marketplace upload progression remains blocked for this checklist item.

### 6.8 Language-picker target fix rerun (same device, 2 consecutive)
- Status: 실패
- Mode:
  - `LoginMode=skip`
- Script patch in this turn:
  - `scripts/collect_face_capture_evidence.ps1`
  - Added deterministic fallback taps from live dump coordinates:
    - face hero fallback: `(400,650)`
    - language control fallback: `(469,70)`
    - mic fallback: `(400,676)`
  - Added picker-open detection by visible texts:
    - `상대 언어 (GPS/수동)`
    - `GPS 우선 · 필요 시 수동`

### 6.8.1 Pass #1 (target-fix)
- Evidence:
  - docs/checklists/evidence/face-capture-pass1-targetfix-20260813-063740/summary.json
  - docs/checklists/evidence/face-capture-pass1-targetfix-20260813-063740/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=false`
  - `langPickerOpened=true`
  - `peerLangSelected=true`
  - `faceMicTapped=true`
- Result:
  - `pass=false`
  - Missing required events:
    - `start_tap`
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.8.2 Pass #2 (target-fix)
- Evidence:
  - docs/checklists/evidence/face-capture-pass2-targetfix-20260813-063952/summary.json
  - docs/checklists/evidence/face-capture-pass2-targetfix-20260813-063952/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=false`
  - `langPickerOpened=false`
  - `peerLangSelected=false`
  - `faceMicTapped=true`
- Trace-specific observation:
  - `start_tap` appeared once, immediately followed by `FACE_CAPTURE_BLOCK` with `code=capture_busy`.
  - Therefore, chain progression stopped before `capture_started/payload_prepared/post_start/response_received`.
- Result:
  - `pass=false`
  - Missing required events:
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.8.3 Gate outcome
- Requested "same device, consecutive 2 pass=true" condition is still not met after selector target fix.
- Marketplace upload progression remains blocked.

### 6.9 capture_busy 예방 전처리(강제 중지 후 재진입) + 2회 연속 재실행
- Status: 실패
- Mode:
  - `LoginMode=skip`
- Script preprocessing added:
  - `scripts/collect_face_capture_evidence.ps1`
  - Pre-step: `am force-stop` + cooldown + HOME keyevent + relaunch

### 6.9.1 Pass #1 (resetfix)
- Evidence:
  - docs/checklists/evidence/face-capture-pass1-resetfix-20260813-143709/summary.json
  - docs/checklists/evidence/face-capture-pass1-resetfix-20260813-143709/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=false`
  - `langPickerOpened=false`
  - `peerLangSelected=false`
  - `faceMicTapped=true`
- Result:
  - `pass=false`
  - Missing required events:
    - `start_tap`
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.9.2 Pass #2 (resetfix)
- Evidence:
  - docs/checklists/evidence/face-capture-pass2-resetfix-20260813-143931/summary.json
  - docs/checklists/evidence/face-capture-pass2-resetfix-20260813-143931/face-capture-trace.txt
- Key flow flags:
  - `faceHomeOpened=false`
  - `langPickerOpened=false`
  - `peerLangSelected=false`
  - `faceMicTapped=true`
- Result:
  - `pass=false`
  - Missing required events:
    - `start_tap`
    - `capture_started`
    - `payload_prepared`
    - `post_start`
    - `response_received`

### 6.9.3 Gate outcome
- Requested condition("same device, 2 consecutive pass=true") is not satisfied.
- Therefore checklist is not closed and marketplace upload progression is not executed.
