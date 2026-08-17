# Docker vs Local Route Logic Compare Checklist

## Status Rules

- Implemented: script and report path exist but verification is not closed.
- Completed: script exists, was executed at least twice, and evidence is written below.
- Failed: required compare coverage is missing or execution does not work.

## Checklist

- [x] 1. Backend admin route inventory is extracted from source of truth.
- [x] 2. Frontend admin proxy action inventory is extracted and matched against backend routes.
- [x] 3. Local-only route assumptions in canonical-site and proxy host gate are compared against docker-compose runtime wiring.
- [x] 4. A reusable script writes a machine-readable report for docker/local route-logic mismatches.
- [x] 5. The compare script is executed twice and the evidence is synchronized in this document.

## Target Files

- scripts/compare_local_docker_route_logic.py
- frontend/frontend/app/api/proxy/route.ts
- frontend/frontend/lib/canonical-site.ts
- frontend/frontend/proxy.ts
- backend/admin_router.py
- docker-compose.yml

## Planned Verification

- Run 1: `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe scripts/compare_local_docker_route_logic.py --json-output reports/docker-local-route-logic-compare.json`
- Run 2: `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe scripts/compare_local_docker_route_logic.py --json-output reports/docker-local-route-logic-compare-second.json`

## Evidence Log

- Status: Completed
- Script: `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe scripts/compare_local_docker_route_logic.py`
- JSON reports:
  - `reports/docker-local-route-logic-compare.json`
  - `reports/docker-local-route-logic-compare-second.json`
- Run results:
  - Run 1: 5 findings, route inventory matched for all targeted admin proxy actions.
  - Run 2: 5 findings, identical result reproduced.
- Detected mismatches:
  - `CANONICAL_SITE_PORT_ONLY_DEPLOY_GAP`: `frontend/frontend/lib/canonical-site.ts` switches admin/marketplace origins by port only, while docker ingress is `nginx` on 80/443.
  - `FRONTEND_ADMIN_PORT_MISMATCH`: `docker-compose.yml` sets `frontend-admin` `PORT: 3000`, not the local admin assumption `3005`.
  - `FRONTEND_MARKETPLACE_SERVICE_MISSING`: `docker-compose.yml` has no `frontend-marketplace` service, so local 3000/3005 surface separation is not mirrored in compose.
  - `DOCKER_FRONTEND_SPLIT_PORTS_MISSING`: browser-facing compose ports do not expose both 3000 and 3005 entrypoints.
  - `ADMIN_ALLOWED_HOSTS_NOT_CONFIGURED`: compose does not explicitly declare admin allowed hosts for the frontend runtime.

## Post-Fix Runs (with live probes)

- Command A:
  - `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe scripts/compare_local_docker_route_logic.py --local-base-url http://127.0.0.1:3005 --docker-base-url https://xn--114-2p7l635dz3bh5j.com --json-output reports/docker-local-route-logic-compare-after-fix.json`
- Command B:
  - `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe scripts/compare_local_docker_route_logic.py --local-base-url http://127.0.0.1:3000 --docker-base-url https://metanova1004.com --json-output reports/docker-local-route-logic-compare-after-fix-marketplace.json`
- Result summary:
  - Static findings: `0` (both runs)
  - Canonical switch mode: `port+hostname`
  - Compose summary: `frontend-admin PORT=3005`, `frontend-marketplace service present=true`
  - Route inventory: targeted admin proxy actions all matched backend routes
- Live probe notes:
  - `http://127.0.0.1:3005` was not running at check time (connection refused)
  - `http://127.0.0.1:3000` responded
  - Real domains responded; admin-proxy paths returned auth-related `401/400` where auth was not supplied, which is expected for unauthenticated probes

## Final Status

- Result: Completed
- Meaning:
  - The 5 compare findings were closed by real code/config changes in docker compose and frontend URL switching logic.
  - The compare script was executed with `--local-base-url` and `--docker-base-url` and produced post-fix JSON evidence.
  - Live probes are now included in the workflow; authenticated admin endpoint validation can be extended by adding authorization headers in a follow-up step.
