# WorldLinco Feature-Core Merge Playbook (2026-07-08)

## Goal
- Find a practical "complete" release by merging proven feature cores into the current baseline instead of searching for one historical build where everything works.
- Base release pointer: current marketplace manifest build 312.

## Why this approach
- Evidence shows no single build that is best for all domains.
- Proven peaks are split across domains:
  - Face interpretation stability: build 149
  - VoIP modern stability: build 157
  - Sorisae companion stability line: build 296
  - Legacy rails/signaling milestones: builds 90/92/113/146/150

## Non-negotiable constraints
- Keep hot path contracts unchanged (`voice-translate`, `voip-voice-relay/*`).
- Respect 1-device-1-session (Sorisae and VoIP cannot be active together).
- Do not copy Sorisae prosody/timing into VoIP paths.
- Apply smallest patch sets per feature boundary.

## Feature core map to merge into build 312
| Feature | Reference line | Merge intent into 312 |
|---|---|---|
| Face interpretation | build 149 lock line | Preserve face-only speaking/capture gates and duplicate-TTS prevention behavior |
| VoIP relay/runtime | build 157 line | Preserve AEC render path, fairness/rearm stabilization behavior |
| VoIP locale parity | build 146 line | Preserve locale resolver/coverage consistency |
| VoIP meter-dead guard | build 150 line | Preserve meter-unavailable echo fallback guard |
| Legacy travel face rail | build 92 line | Keep bilingual face route expectations for travel flow |
| Sorisae companion | build 296 freeze line | Preserve Sorisae freeze semantics and phase-C validated behavior |

## Merge method (recommended)
1. Create an integration lane: `release/312-feature-core-merge`.
2. Build per-feature patch manifests (file-level, minimal diffs only).
3. Apply patches one feature at a time in this order:
   - Face (149)
   - VoIP core (157)
   - VoIP guards/parity (150, 146)
   - Sorisae freeze behavior (296)
4. After each feature merge, run domain-specific verification twice before moving on.
5. At the end, run cross-feature conflict verification twice.

## Verification gates
- Gate A (feature-local): each merged feature passes its own checklist twice.
- Gate B (cross-feature): face, voip, sorisae all pass in one run; repeat once.
- Gate C (publish readiness): manifest/build metadata, smoke APIs, and runtime logs consistent.

## Release decision model
- If Face degrades after VoIP merge, prioritize face lock behavior from 149 and re-apply VoIP as narrower patch.
- If Sorisae degrades after VoIP merge, enforce section boundary lock and remove cross-section patch.
- If build 312 still fails cross-feature gate, cut a hybrid release candidate from 312 with only validated merged subsets.

## Deliverables
- Patch manifest per feature
- Double-run evidence for each gate
- Final promotion note with explicit pass/fail by feature
