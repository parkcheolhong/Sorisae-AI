# Auto Mode Real Device UX Test Cases

## Scope
- Target app: `apps/mobile-nadotongryoksa`
- Feature scope:
  - Main screen auto voice translation mode
  - Inter-call manual auto relay delay mode
  - Duplicate auto-send prevention
- Device scope:
  - Android physical device (required)
  - iOS physical device (recommended)
- Delay options under test: 2.0s, 2.5s, 3.0s

## Pre-Run Setup
1. Install latest app build on physical device.
2. Confirm API connectivity to `/api/llm/voice/orchestrate` and translation API.
3. Grant microphone permission.
4. Prepare Bluetooth headset (HFP-capable) and device speaker fallback.
5. Prepare noise sources:
   - Quiet room (baseline)
   - Office/cafe ambient noise
   - Intentional burst noise (clap, keyboard, TV)
6. Prepare test scripts in 2 languages (for example Korean/English):
   - Script A: short sentence
   - Script B: medium sentence
   - Script C: repeated same sentence (for duplicate guard)

## Logging Template (fill during execution)
- Date/Time:
- Device/OS:
- App build:
- Network:
- Scenario ID:
- Delay option:
- Result: PASS/FAIL
- Evidence:
  - Screen recording path:
  - Log snippet:
  - Repro count (n/5):

## Scenario Matrix

### A. Silence Window UX

#### A-01 Auto stop after silence
- Goal: verify recording segment closes by selected delay and triggers translation.
- Steps:
  1. Enable auto voice mode.
  2. Select delay (2.0s).
  3. Speak Script A once, then stay silent.
  4. Repeat with 2.5s and 3.0s.
- Expected:
  - Status shows auto mode start and delay text.
  - Recording auto-stops near selected delay.
  - Translation appears without pressing translate button.
  - TTS output is played once.
- Fail signals:
  - Never stops automatically.
  - Stops too early before speech ends repeatedly.
  - Needs manual translate button.

#### A-02 Auto restart loop stability
- Goal: verify stop -> STT -> translate -> restart cycle.
- Steps:
  1. Keep auto mode enabled for 2 minutes.
  2. Speak Script A/B every cycle, with silence in between.
- Expected:
  - No manual tap needed between cycles.
  - No overlapping recordings.
  - CPU/thermal not causing UI freeze.
- Fail signals:
  - Mic stuck in recording state.
  - Duplicate overlapping TTS.
  - App freeze or crash.

### B. Background Noise UX

#### B-01 Ambient noise resilience
- Goal: verify noisy environment does not flood duplicate translations.
- Steps:
  1. Enable auto mode in office/cafe-like ambient noise.
  2. Speak Script B once.
  3. Leave ambient noise only for 30s.
- Expected:
  - Noise-only periods should not cause repeated same translation spam.
  - Duplicate guard status appears when same sentence is repeatedly detected.
- Fail signals:
  - Repeated same output continuously without user speech.
  - UI status does not indicate duplicate skip while spam occurs.

#### B-02 Burst noise handling
- Goal: verify sudden loud noise does not break loop.
- Steps:
  1. Enable auto mode.
  2. During silence, generate burst noise (clap/keyboard/TV).
  3. Resume normal speech (Script A).
- Expected:
  - App remains responsive.
  - After noise, normal speech translation still works.
- Fail signals:
  - Auto mode gets stuck and never recovers.
  - Mic permission/session resets unexpectedly.

### C. Bluetooth UX

#### C-01 BT headset input path
- Goal: verify BT microphone path works in auto mode.
- Steps:
  1. Connect BT headset.
  2. Enable auto mode and speak Script A/B via headset mic.
  3. Compare with device mic.
- Expected:
  - STT quality is comparable or better on BT.
  - Delay cycle behavior identical to non-BT mode.
- Fail signals:
  - No input captured with BT connected.
  - Auto mode works only on device mic.

#### C-02 BT connect/disconnect during session
- Goal: verify seamless path switching while auto mode is ON.
- Steps:
  1. Start in BT connected state.
  2. During active auto loop, disconnect BT.
  3. Reconnect BT and continue speech.
- Expected:
  - App continues translating without restart.
  - No crash or permanent recording failure.
- Fail signals:
  - Audio session deadlock after disconnect.
  - Requires app relaunch to recover.

### D. Inter-call Auto Relay UX

#### D-01 Delay selector in inter-call panel
- Goal: verify 2.0/2.5/3.0s selector affects auto relay timing.
- Steps:
  1. Start inter-call mode on mobile.
  2. Enter Script A in manual text input.
  3. Observe auto send timing for each delay option.
- Expected:
  - Status text reflects selected delay.
  - Auto relay triggers according to selected delay.
- Fail signals:
  - Always fixed at a single delay.
  - Status delay text differs from actual trigger timing.

#### D-02 Inter-call duplicate guard
- Goal: verify same sentence is not auto-relayed repeatedly.
- Steps:
  1. Keep inter-call mode active.
  2. Enter the same Script C repeatedly with small pauses.
  3. Wait for auto relay each round.
- Expected:
  - Duplicate sentence within guard window is skipped.
  - Duplicate skip status appears.
- Fail signals:
  - Same sentence relayed repeatedly in short window.

## Pass Criteria
- Each scenario must pass 5/5 runs on at least one Android real device.
- Critical scenarios A-01, B-01, C-01, D-02 must also pass 3/3 runs on iOS real device.
- No crash/ANR during full matrix run.
- Duplicate guard should reduce repeated sends in noisy conditions.

## Regression Checklist
- Manual translation button still works.
- Manual mic start/stop still works when auto mode is OFF.
- Song mode flow is unaffected.
- Web inter-call mode behavior is unchanged.

## Recommended Execution Order
1. A-01
2. A-02
3. B-01
4. B-02
5. C-01
6. C-02
7. D-01
8. D-02

## Completion Record
- Verification Round 1:
  - Date:
  - Executor:
  - Result:
  - Blocking issues:
- Verification Round 2:
  - Date:
  - Executor:
  - Result:
  - Blocking issues:
