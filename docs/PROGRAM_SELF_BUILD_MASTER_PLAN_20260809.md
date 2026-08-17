# Program Self-Build Master Plan (2026-08-09)

## Scope
This plan executes four tracks in order:
1. Build new overall structure from the repository baseline.
2. Extend core features based on existing production code.
3. Build deployment and verification pipeline first.
4. Close PR #111 follow-up checklist items with runtime evidence.

## Current Baseline
- Active branch: `feat/worldlinco-build331-i18n`
- Active PR: #111
- Completed follow-up verifications:
  - travel partner funnel seed/verify (2 rounds)
  - admin KPI Playwright one-shot
  - admin frontend build

## Target Structure (Top-Level)
- `backend/`: API domain services, admin/kpi routes, auth, integrations.
- `frontend/frontend/`: admin and marketplace UI runtime.
- `scripts/`: operational verification and pipeline scripts.
- `docs/`: runbooks, checklists, and decision records.
- `.github/workflows/`: CI quality gates and regression lanes.

## Core Feature Extension Tracks
1. Travel Partner Revenue Pipeline
- stabilize recommendation -> click -> booking -> settlement -> refund chain.
- keep KPI and SLA cards synchronized with backend contract.

2. Admin Operations Reliability
- keep one-shot Playwright and panel API flow green.
- tighten failure diagnostics in evidence artifacts.

3. Checklist-to-Execution Synchronization
- every checklist close requires executable evidence.
- pipeline output must produce report artifacts and evidence paths.

## Deployment and Verification Pipeline
- Entry point: `scripts/run_pr111_followup_pipeline.ps1`
- Stages:
  1) funnel seed/verification (`verify_travel_partner_funnel_section7.py`)
  2) admin KPI one-shot (`verify_admin_travel_kpi_playwright_once.ps1`)
  3) admin build (`npm run build:admin`)
- Output:
  - funnel evidence JSON in `evidence/`
  - pipeline summary markdown in `reports/`

## Execution Order
1. Keep PR #111 follow-up checklist evidence updated.
2. Run pipeline script and attach report/evidence.
3. Expand structure and core features only after stage 1-2 are green.
4. Promote pipeline to workflow-level automation after repeated local pass.

## Definition of Done (This Phase)
- PR #111 follow-up tasks are executable from one script.
- checklist contains fresh evidence lines with output file names.
- build and verification results are reproducible from repository root.
