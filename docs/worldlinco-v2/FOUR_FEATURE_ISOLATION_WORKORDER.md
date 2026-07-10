# Four Feature Isolation Workorder

## Scope (Frozen)

Target features are fixed to the following four surfaces only:

1. face-translate
2. voip-call
3. pstn-assist
4. sorisae-ai

No other feature is in scope for this workorder.

## Goal

Prevent cross-feature cascade regressions by enforcing:

1. feature-local lifecycle and command handling
2. shared resource ownership through one kernel only
3. no direct feature-to-feature orchestration calls

## Hard Rules For Handoffs

1. Do not mark any milestone completed without evidence lines in this file.
2. Every handoff must append: changed files, verification commands, and results.
3. If verification is missing, status must remain "in-progress".
4. Do not create a new checklist file for the same scope; update this file only.
5. If blocked, record exact blocker and next concrete command.

## Milestone A (Completed)

Extract minimum contracts for input/output/lifecycle/resource rules, based on current code paths.

- Status: completed
- Evidence:
  - apps/mobile-nadotongryoksa/src/features/isolation/fourFeatureContracts.ts
  - apps/mobile-nadotongryoksa/src/features/isolation/fourFeatureKernel.ts
  - apps/mobile-nadotongryoksa/src/features/isolation/fourFeatureEntrypoints.ts

## Verification Log

- get_errors on isolation contract files: no errors
- get_errors on isolation entrypoint map file: no errors

## Milestone B (Completed)

Integrate each feature entrypoint into the contract runner with no-op behavior change.

- Status: completed
- Evidence:
  - apps/mobile-nadotongryoksa/src/features/isolation/fourFeatureRuntime.ts
  - apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts
  - apps/mobile-nadotongryoksa/src/features/voip-auto/useVoipAutoController.ts
  - apps/mobile-nadotongryoksa/src/features/pstn-assist/usePstnAssistController.ts
  - apps/mobile-nadotongryoksa/App.tsx

## Verification Log

- get_errors on kernel wiring files: no errors
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (pass 1): 3 suites passed, 45 tests passed
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (pass 2): 3 suites passed, 45 tests passed

## Milestone C (Completed)

Add focused integration tests for lease conflict arbitration and release paths among the four features.

- Status: completed
- Evidence:
  - apps/mobile-nadotongryoksa/src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts

## Verification Log

- get_errors on isolation integration test file: no errors
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (pass 1): 1 suite passed, 4 tests passed
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (pass 2): 1 suite passed, 4 tests passed

## Milestone D (Completed)

Enforce absolute single-active policy with deterministic quiesce ordering and rollback on transition failure.

- Status: completed
- Evidence:
  - apps/mobile-nadotongryoksa/src/features/isolation/fourFeatureRuntime.ts
  - apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts
  - apps/mobile-nadotongryoksa/src/features/voip-auto/useVoipAutoController.ts
  - apps/mobile-nadotongryoksa/src/features/pstn-assist/usePstnAssistController.ts
  - apps/mobile-nadotongryoksa/App.tsx
  - apps/mobile-nadotongryoksa/src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts

## Verification Log

- get_errors on strict-policy files: no errors
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (pass 1): 1 suite passed, 6 tests passed; includes deterministic quiesce order and rollback-on-failure case
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (pass 2): 1 suite passed, 6 tests passed; includes deterministic quiesce order and rollback-on-failure case
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (pass 1): 3 suites passed, 45 tests passed
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (pass 2): 3 suites passed, 45 tests passed

## Post-D Consistency Patch (Completed)

Resolve critical TypeScript contract drift introduced during Phase C extraction while preserving Milestone D behavior.

- Status: completed
- Evidence:
  - apps/mobile-nadotongryoksa/src/features/sorisae/voiceCaptureLoopTypes.ts
  - apps/mobile-nadotongryoksa/App.tsx

## Verification Log

- get_errors on App + sorisae capture loop files: no errors
- npm run typecheck: passed (tsc --noEmit)
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (revalidation pass 1): 1 suite passed, 6 tests passed
- npm run test -- --runInBand src/features/isolation/__tests__/fourFeatureKernel.integration.test.ts (revalidation pass 2): 1 suite passed, 6 tests passed
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (revalidation pass 1): 3 suites passed, 45 tests passed
- npm run test -- --runInBand src/__tests__/voiceRelayOrchestrator.test.ts src/__tests__/voiceRelayAudioMetrics.test.ts src/__tests__/companionVoiceCall.test.ts (revalidation pass 2): 3 suites passed, 45 tests passed
