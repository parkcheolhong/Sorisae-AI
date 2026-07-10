# Sorisae Plugin Boundary Checklist

## Linked Workorder

- Four-feature isolation handoff lock SSOT: docs/worldlinco-v2/FOUR_FEATURE_ISOLATION_WORKORDER.md

## Status Legend

- [ ] not started
- [~] in progress
- [x] done (with evidence)

## Phase 0. Design Freeze

- [x] Create boundary design document
- Evidence: docs/worldlinco-v2/SORISAE_PLUGIN_BOUNDARY_DESIGN.md

## Phase 1. Sorisae Runtime Decoupling

- [x] Remove Sorisae import from voip relay paths
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/useVoiceCaptureLoop.ts
- [x] Remove Sorisae type dependency on app-level contracts
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/voiceCaptureLoopTypes.ts
- [x] Block Sorisae watchdog rearm during active VoIP runtime session
- Evidence: apps/mobile-nadotongryoksa/App.tsx
- [x] Extract Sorisae runtime adapter interface entrypoint
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/runtimeAdapter.ts
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/useSorisaeVoicePipeline.ts

## Phase 2. Relay Guard SSOT Unification

- [x] Wire VoIP audio metrics guard to shared SSOT implementation
- Evidence: apps/mobile-nadotongryoksa/src/features/voip-voice-relay/voiceRelayAudioMetrics.ts
- [x] Unify relay text guard to single SSOT path (remove duplicate implementation)
- Evidence: apps/mobile-nadotongryoksa/src/features/shared/relayTextGuards.ts
- Evidence: apps/mobile-nadotongryoksa/src/features/voip-voice-relay/voiceRelayOrchestrator.ts
- [x] Validate VoIP and Sorisae both consume same guard implementation path
- Evidence: apps/mobile-nadotongryoksa/src/screens/VoIPCallScreen.tsx
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/useVoiceCaptureLoop.ts

## Phase 3. App Plugin Boundary Split

- [x] Add Sorisae plugin facade contract in App runtime layer
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts
- [x] Route App -> Sorisae interactions through facade only
- Evidence: apps/mobile-nadotongryoksa/App.tsx (useSorisaePluginFacade + bindVoiceCaptureControls + stopVoiceInputBridgeRef)
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts (runtime adapter bridge ownership)
- [x] Remove direct App orchestration calls to Sorisae internal refs/hooks where facade can own lifecycle
- Evidence: apps/mobile-nadotongryoksa/App.tsx (useSorisaeCompanionLifecycleFacade로 arm/watchdog orchestration 흡수)
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts (useSorisaeCompanionLifecycleFacade)

## Phase 4. Safety Verification

- [x] Static error check on changed files
- Evidence: get_errors no issues on App.tsx, useVoiceCaptureLoop.ts, voiceCaptureLoopTypes.ts, voiceRelayAudioMetrics.ts
- [x] Focused tests for Sorisae + relay audio guards
- Evidence: companionVoiceCall.test.ts PASS, voiceRelayAudioMetrics.test.ts PASS
- [x] Re-run focused regression set after Phase 2/3 completion
- Evidence: src/__tests__/voiceRelayOrchestrator.test.ts PASS
- Evidence: src/__tests__/voiceRelayAudioMetrics.test.ts PASS
- Evidence: src/__tests__/companionVoiceCall.test.ts PASS
- [x] Re-run focused regression set second pass (double verification)
- Evidence: src/__tests__/voiceRelayOrchestrator.test.ts PASS (2nd)
- Evidence: src/__tests__/voiceRelayAudioMetrics.test.ts PASS (2nd)
- Evidence: src/__tests__/companionVoiceCall.test.ts PASS (2nd)

## Final Gate

- [x] No remaining duplicate relay text guard implementation paths
- Evidence: apps/mobile-nadotongryoksa/src/features/shared/relayTextGuards.ts (formatAutoRelayDelayLabel 단일 정의)
- Evidence: apps/mobile-nadotongryoksa/src/features/shared/relayTextGuards.ts (isLikelyGibberishRelayTranscript 단일 정의)
- Evidence: apps/mobile-nadotongryoksa/src/features/shared/relayTextGuards.ts (shouldRejectRemoteVoiceRelayPlayback 단일 정의)
- [x] Sorisae plugin boundary merged and verified
- Evidence: apps/mobile-nadotongryoksa/App.tsx (useSorisaePluginFacade + useSorisaeCompanionLifecycleFacade 경유)
- Evidence: apps/mobile-nadotongryoksa/src/features/sorisae/sorisaePluginFacade.ts (runtime bridge + companion lifecycle facade)
- Evidence: src/__tests__/voiceRelayOrchestrator.test.ts PASS (1st/2nd)
- Evidence: src/__tests__/voiceRelayAudioMetrics.test.ts PASS (1st/2nd)
- Evidence: src/__tests__/companionVoiceCall.test.ts PASS (1st/2nd)
- [x] Checklist fully closed with evidence lines
- Evidence: docs/worldlinco-v2/SORISAE_PLUGIN_BOUNDARY_CHECKLIST.md (Phase 0~4 + Final Gate 전 항목 [x])
