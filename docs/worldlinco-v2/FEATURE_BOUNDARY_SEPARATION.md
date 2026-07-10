# WorldLinco Feature Boundary Separation

## Goal

각 기능은 서로의 세션 상태, 오디오 라우팅, 자동 재시작 조건을 보지 않는다.
공용 게이트는 두지 않고, 기능별 상태는 해당 기능 내부에서만 결정한다.

## Non-Negotiable Rules

1. Sorisae, VoIP, face interpretation, chat voice input, song mode, and travel UI are isolated execution domains.
2. A feature may read only its own local state, its own storage, and shared read-only constants.
3. A feature may not pause, mute, resume, or auto-stop another feature through a common gate.
4. If two features need different behavior, that difference must be encoded in separate files or separate feature-specific guards.
5. Shared helpers may exist only for pure transforms, static catalogs, or read-only SSOT values.

## Allowed Sharing

- Pure language / locale catalogs
- Pure text normalization helpers
- Read-only tuning snapshots
- Read-only identity / profile formatters
- Event payload types with no runtime control side effects

## Forbidden Sharing

- Shared runtime session gate for Sorisae and VoIP
- Shared audio mode toggles for unrelated features
- Shared auto-restart policies across feature domains
- Cross-feature write access to playback, microphone, or push state

## Separation Steps

### Step 1: Remove shared gates

Delete runtime checks that stop one feature because another feature is active.

### Step 2: Localize control flow

Each feature owns its own start, stop, recovery, and retry logic.

### Step 3: Keep shared files read-only

If a helper is reused across features, it must be pure and must not mutate runtime state.

### Step 4: Validate feature boundaries independently

Run feature-specific tests and keep regressions inside the owning feature only.

## File Ownership

- Sorisae runtime: `apps/mobile-nadotongryoksa/src/features/sorisae/*`
- VoIP runtime: `apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx`, `apps/mobile-nadotongryoksa/src/services/voipCallClient.ts`, `apps/mobile-nadotongryoksa/src/features/voip-voice-relay/*`
- Face translation playback: `apps/mobile-nadotongryoksa/src/app/appFaceVoicePlayback.ts`, `apps/mobile-nadotongryoksa/src/features/face-interpretation/*`

## Acceptance Criteria

- No Sorisae file imports a VoIP session gate for runtime control.
- No face playback file checks VoIP session state before playing or stopping.
- No VoIP relay file reads Sorisae arm/disarm state.
- Each feature keeps its own restart and suppression behavior.
