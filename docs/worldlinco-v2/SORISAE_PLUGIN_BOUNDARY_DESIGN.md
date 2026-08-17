# Sorisae Plugin Boundary Design

## Objective

Sorisae must run as an isolated feature module. VoIP tuning or runtime changes must not alter Sorisae behavior, and Sorisae changes must not alter VoIP, face interpretation, OCR, song, travel-booking, or chat behavior.

## Scope

- Sorisae runtime isolation
- Relay guard SSOT unification
- App orchestrator plugin boundary split

## Non-Negotiable Constraints

1. Sorisae runtime must not import VoIP feature paths.
2. Sorisae watchdog/auto-arm must suspend during active VoIP runtime session.
3. Shared relay guard logic must have one authoritative implementation path.
4. App must call Sorisae through a plugin boundary contract, not direct internal refs.
5. OCR, face interpretation, song, travel-booking, chat must keep existing behavior unchanged.

## Boundary Model

### Sorisae Plugin Input Contract

- auth/profile snapshot
- locale and language snapshot
- feature flags
- capture/playback adapter interfaces
- shared relay guard interfaces

### Sorisae Plugin Output Contract

- UI state payload
- command/action events
- diagnostics events
- lifecycle hooks (start/stop/quiesce)

### Runtime Ownership

- Voice capture lease: single owner
- TTS playback lease: single owner
- Sorisae uses only plugin adapters for native/services calls

## Current Gap Summary

1. Sorisae still depends on centralized App orchestration flow for lifecycle wiring.
2. Relay text guards are still duplicated between shared and voip relay modules.
3. Plugin adapter contract file is not yet extracted as independent entrypoint.

## Workstreams

### WS1. Sorisae Runtime Adapter Isolation

- Move native/service direct calls behind Sorisae adapter interfaces
- Keep Sorisae package runnable with adapter injections only

### WS2. Relay Guard SSOT Unification

- Keep exactly one implementation for text/audio relay guards
- Make both Sorisae and VoIP import from same source path

### WS3. App Plugin Boundary Split

- Introduce Sorisae plugin facade in App
- Replace direct hook orchestration with plugin contract call sites

## Acceptance Criteria

1. Sorisae package has no direct import from voip feature path.
2. VoIP tuning changes in relay path do not require Sorisae code patch.
3. App talks to Sorisae via plugin facade contract only.
4. Focused tests for Sorisae and relay guards pass.
5. No static errors in modified files.
