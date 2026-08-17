# Evidence: Sorisae Dispatch Load Test (Phase 1) - 2026-05-05

## Scope
- Target endpoint: POST /api/marketplace/sorisae/dispatch
- Core engines: voice_movie, detective_dashboard, integrated_dashboard, movie_server, master, shopping
- Profile: 30 requests per engine, concurrency 18, timeout 12s

## Final Validation Results (2 Rounds)
- Round 1 file: docs/evidence/sorisae-dispatch-loadtest-round1-final-20260505.json
- Round 2 file: docs/evidence/sorisae-dispatch-loadtest-round2-final-20260505.json

### Round 1 Summary
- total: 180
- ok: 180
- fail: 0
- error_rate: 0.0%
- avg latency: 70.589 ms
- p95 latency: 89.654 ms
- throughput: 244.852 rps

### Round 2 Summary
- total: 180
- ok: 180
- fail: 0
- error_rate: 0.0%
- avg latency: 68.71 ms
- p95 latency: 83.434 ms
- throughput: 251.965 rps

## Failure Root Cause and Improvement

### Observed Failure
- When tests were run immediately after backend restart, login could fail with connection abort:
  - RemoteDisconnected: Remote end closed connection without response

### Root Cause
- Readiness race condition:
  - backend process accepted socket lifecycle changes during warm-up,
  - first login request arrived before auth path was stably ready.

### Improvement Applied
- Added retry-based readiness handling in load test runner login flow:
  - file: scripts/run_sorisae_dispatch_load_test.py
  - change: login retries up to 20 attempts with 1s interval before failing

### Revalidation After Improvement
- Same restart-then-run path was executed.
- Both final rounds completed with fail=0 and error_rate=0.0%.

## Additional Stress Diagnostic (High Load)
- Stress profile file: docs/evidence/sorisae-dispatch-loadtest-stress-20260505.json
- Configuration: 120 requests per engine, concurrency 96, timeout 6s
- Result: fail=0, error_rate=0.0%, p95=370.233 ms
- Interpretation:
  - No functional failure under elevated load.
  - Latency increases under extreme concurrency as expected.

## Verdict for Checklist Item 3
- First-phase load test requirement satisfied.
- Two-pass repeatability satisfied.
- Failure cause identified and improved with verified rerun.
