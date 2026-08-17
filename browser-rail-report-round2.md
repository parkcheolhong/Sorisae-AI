# RAIL-01~06 Smoke Test Batch Report (Run 2)

## Scope
- Scenario: marketplace orchestrator smoke-test for RAIL-01~06
- URL: <http://localhost:3005/marketplace/orchestrator>
- Mode: same scenario re-validation (2nd run)

## Smoke Results (Run 2)
- RAIL-01: pass 14 / fail 6 (70%)
- RAIL-02: pass 16 / fail 4 (80%)
- RAIL-03: pass 19 / fail 1 (95%)
- RAIL-04: pass 18 / fail 2 (90%)
- RAIL-05: pass 14 / fail 6 (70%)
- RAIL-06: pass 17 / fail 3 (85%)

## 6-Rail Representative Demo
- Result: pass 6 / fail 0 (100%)
- Representative slots: 1, 21, 41, 61, 81, 101

## Pipeline Re-Validation (Run 2)
- Command: 통역-음성-보안 체인 테스트 2회차 재검증
- Blocks: 1 (interpreter), 21 (voice), 81 (security)
- API response status: 200
- Pipeline summary: pass 3 / fail 0

## sorisae_dashboard_web Reference Feature Applied
- File: backend/marketplace/extras_router.py
- Change: security experiment now includes dashboard-style security snapshot payload.
- Output key added: output_preview.dashboard_snapshot
- Snapshot fields:
  - event, severity, source_ip, security_status
  - dashboard.system_status, last_command, current_persona, creative_activities, command_count, error_count, success_rate
  - command_log.timestamp, command, status, plugin

## Notes
- Browser evidence was captured in this session for all items above (RAIL-01~06, 6-rail demo, pipeline run 2).
