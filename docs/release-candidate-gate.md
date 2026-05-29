# Release Candidate Gate - 2026-05-28

## Purpose

This document is the single authoritative source for repository-wide
deployment status and release-candidate closure.

- README is a summary view only.
- `docs/system-cleanup-checklist.md` is a supporting cleanup analysis.
- `docs/risk-analysis-allscan-20260427.md` is a historical all-scan ledger.
- Mobile and VoIP documents remain product-slice evidence, not repository-wide
  release approval.

## Current Verdict

- Repository-wide release candidate: `실패`
- Web production slice: `구현됨`
- Mobile and VoIP slice: release scope excluded until mandatory real-device
  verification is completed

## Why The Repository-Wide Verdict Is Fail

1. Mobile and VoIP still require real-device closure for call, push, and
  background incoming behavior before that slice can re-enter repository-wide
  release scope.

## Release Scope Policy

### Included In The Current Web Release Slice

- Public marketplace and admin web entry points
- Backend core web APIs and gateway paths that passed current HTTP-level
  production verification
- Current CORS and chunk-load recovery checks already verified on production

### Excluded From Release Candidate Until Separate Sign-Off

- `apps/mobile-nadotongryoksa/**`
- VoIP call flows, background push, and physical-device signaling validation
- Google Play submission and mobile store-distribution steps
- Any mobile evidence or temporary automation artifacts not rebuilt inside an
  isolated candidate worktree

If the excluded mobile and VoIP scope is reintroduced into the release
candidate, the repository-wide verdict remains `실패` until the mandatory field
validation gates below are closed.

## Mandatory Gates To Include Mobile And VoIP Again

1. Two-device real call initiation and receive validation
2. Samsung background incoming UI confirmation with current production backend
3. VoIP push path closure with fresh authenticated caller rerun evidence
4. Region-hint real-device rounds completed for the production mobile build
5. Distribution path closure for the intended delivery channel

## Open Repository-Wide Blockers

### Scope Blockers

- Mobile and VoIP remain outside the current release candidate until the
  mandatory field gates below are closed.

## Closure Criteria For A Repository-Wide Release Candidate

1. Keep mobile and VoIP excluded, or complete all mandatory field gates above.
2. Keep README and supporting checklists aligned to this document only.

## Evidence Used For This Gate

- `python scripts/check_checklist_consistency.py --all` passed on 2026-05-28.
- `powershell -NoProfile -File .\final_production_verification.ps1` passed
  HTTP-level production checks on 2026-05-28.
- `pytest tests/test_r1_r8_security_gates.py -q` passed on 2026-05-28.
- `python -m pytest tests/test_r6_r7_operational_risk_scan.py -q` passed twice
  on 2026-05-28.
- `python scripts/compare_local_docker_route_logic.py` returned `Findings: 0`
  twice on 2026-05-28.
- `scan_python_security_policy(Path('backend'))` returned findings 0, errors 0,
  warnings 0 twice on 2026-05-28.
- `.venv\Scripts\python.exe -m compileall app backend tests ai` plus
  `.venv\Scripts\python.exe -m pytest -q -s tests/test_health.py
  tests/test_routes.py tests/test_runtime.py tests/test_security_runtime.py`
  passed twice with `DATABASE_URL=sqlite:///./test_integration.db` on
  2026-05-28.
- A dedicated `codeAI-release-candidate` worktree was reduced to the intended
  candidate slice on 2026-05-28.
- Existing mobile evidence documents still declare real-device and push-related
  blockers.
