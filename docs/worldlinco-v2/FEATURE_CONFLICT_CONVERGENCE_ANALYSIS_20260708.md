# WorldLinco Current-vs-Core Conflict Convergence Analysis (2026-07-08)

## 1) Scope and objective
- Objective: build a practical merged release on top of current build 312 by integrating proven feature cores, because no single historical build satisfies all domains.
- Priority order requested: design first, then phased merge and verification.

## 2) Current baseline state (build 312)
- Publish pointer: build 312, version 1.0.237.
- APK baseline policy reference: build 299 with probe minimum build 296.
- Mobile feature surface currently present as modular folders under src/features:
  - face-conversation, face-interpretation
  - sorisae, ocr
  - voip, voip-voice-relay, chat
  - pstn-assist, travel-booking
  - song, travel-itinerary, sns-share, contacts
- Architectural reality: App.tsx still orchestrates many cross-feature states and imports, so feature boundaries exist but runtime coupling is still significant.

## 3) Selected reference lines and what each is best at
| Reference build/line | Best-known strength | Merge value |
|---|---|---|
| 149 (face lock line) | Face interpretation stability and duplicate-TTS prevention behavior | Stabilizes face path as a protected core |
| 157 (voip modern line) | VoIP AEC render path and rearm serialization resolution | Stabilizes modern VoIP conversation continuity |
| 150 (voip guard) | meter-unavailable fallback guard | Prevents meter-dead echo loops |
| 146 (locale parity) | client/server locale resolver alignment | Reduces multilingual routing drift |
| 296 (sorisae freeze line) | Sorisae companion freeze behavior and phase-C closure line | Stabilizes sorisae-specific semantics |
| 92/113 legacy lines | travel face bilingual and VoIP byte-growth VAD milestone | Compatibility anchors for old regression signatures |

## 4) Bottlenecks on convergence
1. Runtime orchestration concentration in App.tsx
- Even with extracted modules, many feature decisions still meet in one runtime coordinator.
- Risk: a patch intended for one feature changes shared state timing.

2. Audio ownership collisions
- Sorisae and VoIP must remain mutually exclusive in active session.
- Risk: capture/playback ownership leakage causes echo, mute races, or wrong routing.

3. Timing policy mismatch
- Face and VoIP rely on different guard/tail assumptions.
- Risk: blindly importing one timing profile into another regresses the other domain.

4. Locale and route duality
- Client and server language-route decisions are partly split.
- Risk: route mismatch can look like model quality failure while actually being policy drift.

5. Legacy compatibility pressure
- Build 92/113 expectations still appear in downstream checks and user flows.
- Risk: modernizing VoIP may unintentionally break known legacy expectations.

## 5) Conflict lines (must be controlled explicitly)
| Conflict line | Typical failure mode | Control strategy |
|---|---|---|
| Face 149 vs VoIP 157 | shared gate/timing side effects through App.tsx | patch only face-owned blocks first, then re-diff voip-owned blocks |
| VoIP 157 vs Sorisae 296 | cross-section audio/prosody leakage | enforce section boundary lock and session guard invariants |
| VoIP 150 guard vs 157 timing | over-guard causes delayed rearm or under-guard causes echo | treat 150 as narrow fallback subset only |
| 146 locale parity vs current route behavior | locale map update alters fallback behavior | apply parity with contract tests first |
| Legacy 92/113 compatibility vs modern paths | old rails assumptions conflict with modern relay | preserve as compatibility checks, not full behavior rollback |

## 6) Natural merge conditions (preconditions)
- Condition A: Feature ownership map is explicit per file/block before patching.
- Condition B: 1-device-1-session invariant validated before and after each phase.
- Condition C: Public hot path contracts unchanged.
- Condition D: Each phase has two successful feature-local runs.
- Condition E: Cross-feature run succeeds twice before promotion.

## 7) Merge architecture (design-first)
Phase 0: baseline lock
- Freeze publish pointer, policy references, branch/SHA, dirty-tree awareness.

Phase 1: Face 149 core only
- Preserve face-specific speaking/capture/duplicate-TTS behavior.
- Verify face twice with no voip/sorisae side effects.

Phase 2: VoIP 157 core
- Preserve AEC render and rearm stabilization behaviors.
- Verify voip twice.

Phase 3: VoIP guard/parity subsets (150 and 146)
- Add meter-dead fallback guard and locale parity alignment as narrow patches.
- Verify voip regression twice.

Phase 4: Sorisae 296 freeze-consistent subset
- Preserve sorisae semantics without importing voip timing/prosody.
- Verify sorisae twice.

Phase 5: Cross-feature integrity and promotion
- Integrated face+voip+sorisae run twice.
- Promote only when all gates are closed with evidence.

## 8) Practical recommendation for this repository state
- Keep build 312 as integration base.
- Treat 149 and 157 as primary cores, with 150/146 as supporting narrow subsets and 296 as sorisae semantic guardrail.
- Do not attempt a large historical rollback to one build number.
- Use patch manifests and evidence-first gates to avoid circular regressions.

## 9) Immediate next execution
1. Fill checklist section 0 evidence and lock baseline.
2. Produce Face 149 exact block manifest from current files.
3. Apply Face-only minimal patch set and run verification pass 1 and pass 2.
4. Move to VoIP 157 only after face passes both runs.
