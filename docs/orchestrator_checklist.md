# 오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-9b4c2cd6f4 orchestrator checklist

## Required verification

# Orchestrator Restoration Checklist

## Scope

- [x] Runtime verification no longer scans virtualenv or site-packages trees.
- [x] Runtime verification syntax check no longer writes `.pyc` files during verification.
- [x] Marketplace popup bridge no longer hijacks `admin-llm` full-page bridge payloads.
- [x] Marketplace bridge helper restores concrete builder functions for admin handoff.
- [x] Admin home exposes a real admin orchestrator entry again.
- [x] Admin LLM page can hand off to marketplace full-page orchestrator.
- [x] Admin LLM page can hand off to AI sheet popup flow.
- [x] Admin home restoration phase 1 adds a visible control hub, board stack, and marketplace bridge cards.
- [x] Admin LLM page is highlighted as its own admin rail section instead of sharing the generic home state.
- [x] Marketplace home restoration phase 1 restores admin orchestrator CTA and top-level bridge deck links.
- [x] Admin home restoration phase 2 recreates overview, manual orchestrator, and auto-connect role sections with current live routes.
- [x] Admin home restoration phase 3 adds quick links, top-projects, and health-analysis visuals using current live endpoints.
- [x] Admin home restoration phase 4 restores the sticky top action header layer under the current AdminOpsShell layout.
- [x] Admin home restoration phase 5 restores QuickLinks, LLM control, and Sample Products as current-root management panels.
- [x] Admin home restoration phase 6 restores AutoConnect graph and AdOrders as current-root heavy panel layers.
- [x] Admin and marketplace data routes no longer fail on the missing runtime-verification bridge or the dashboard-mode runtime timeout.
- [x] Marketplace home restoration phase 2 brings back a denser intro/header panel, tighter filter guidance, and old-style project card density.
- [x] Marketplace home restoration phase 2 restores a bottom top-projects section similar to the earlier main layout.
- [x] Marketplace home restoration phase 3 retunes copy, top actions, and CTA labels toward the earlier main/snapshot tone.
- [ ] Restore the pre-regression rich admin home UI instead of the current reduced shell.
- [ ] Audit and restore any remaining marketplace home regressions beyond bridge routing.

## Evidence

- [x] `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -c "from pathlib import Path; from backend.admin.orchestrator.debug_validation_jobs import _collect_python_files; ..."`
 Result: `bad_count = 0`, virtualenv and `site-packages` paths excluded from runtime verification scan.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after bridge helper restoration, popup routing fix, admin home phase-1/phase-2 restoration, admin rail update, and marketplace bridge-deck/header/filter/card-density restoration.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after admin home phase-3 quick-links/top-projects/health-analysis restoration and marketplace copy/CTA tone refinement.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after admin home phase-4 sticky top action header restoration.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after admin home phase-5/phase-6 panel restoration for QuickLinks, LLM control, Sample Products, AutoConnect graph, and AdOrders.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after current-root ad-orders slice/type migration so the admin home now accepts richer ad-order monitor/settlement payloads without TypeScript regressions.
- [x] `Invoke-RestMethod http://127.0.0.1:3000/api/proxy?action=marketplace-stats-overview` and `Invoke-RestMethod http://127.0.0.1:3000/api/proxy?action=marketplace-stats-top-projects&limit=6`
 Result: both Next proxy marketplace endpoints return JSON successfully once the profiler backend is running again, so the earlier marketplace `502` path is no longer blocked by missing route wiring.
- [x] `Measure-Command { Invoke-RestMethod -Method Post http://127.0.0.1:8013/api/admin/orchestrator/runtime-verification -ContentType 'application/json' -Body '{"project_root":"","worker_log_path":"","mode":"dashboard"}' }`
 Result: dashboard runtime verification dropped from about `29.845s` to about `0.05s` after removing self-HTTP from the dashboard bundle and now returns `gate_status.final_status = passed`.
- [x] `Invoke-RestMethod -Method Post http://127.0.0.1:3000/api/admin/orchestrator/runtime-verification -Headers @{ Authorization = 'Bearer ...' } -ContentType 'application/json' -Body '{"project_root":"","worker_log_path":"","mode":"dashboard"}'`
 Result: the new Next bridge route now returns JSON instead of the prior `404`, and the dashboard-mode response reports `health`, `marketplace-overview`, `marketplace-top-projects`, `worker-log-tail`, and `gate-final-status` as `passed`.
- [x] `npx tsc --noEmit` in `frontend/frontend`
 Result: passes after current-root `use-admin-auto-connect-controller` / `use-admin-sample-products-controller` wiring replaced the inline lookup/sample handlers in `app/admin/page.tsx`.
- [x] `c:/Users/WORK/source/repos/parkcheolhong/codeAI/.venv/Scripts/python.exe -c "from fastapi.testclient import TestClient; from backend.operational_validation_app import create_operational_validation_app; ..."`
 Result: in-process validation now seeds marketplace sample data on first read, `GET /api/marketplace/projects?limit=2` returns `total = 6`, `GET /api/marketplace/stats/overview` returns `projects = 6`, and `POST /api/marketplace/projects` now exists and returns `401` without auth instead of missing the route.
- [x] `Invoke-WebRequest http://127.0.0.1:3000/api/proxy?action=marketplace-projects&limit=2` plus `marketplace-stats-overview` and `marketplace-stats-top-projects&limit=2`
 Result: the live Next proxy now returns populated marketplace payloads (`projects` rows, `projects = 6`, non-empty top-projects) instead of the earlier `0 items` empty-state data.

## Notes

- Runtime verification bundle still has unrelated harness assumptions when called directly without the app's real helper callables. The `.pyc` permission crash is the part fixed in this pass.
- The current admin home now includes current-route versions of overview, manual orchestrator, auto-connect, quick links, top-projects, health-analysis, and the sticky top action header layer, but it is still not the full historical dashboard composition with the old controller/helper graph.
- The current admin home now also restores QuickLinks, LLM control, Sample Products, AutoConnect graph, and AdOrders as current-root panel layers. In this pass, the sample-product and auto-connect lookup panels moved off the inline page handlers onto current-root controller files, while the richer historical dashboard composition is still not fully restored.
- The direct `404` and `504` blockers for admin home runtime verification are closed, and the earlier marketplace `0 items` regression was traced to missing current-runtime marketplace seed/creation paths. The current backend now repopulates sample catalog data on read and exposes `POST /api/marketplace/projects` again.
- Browser revalidation for `/marketplace` should now show populated catalog/stat data because the live proxy returns non-empty marketplace payloads again. `/admin` sparse runtime evidence is still a separate remaining gap.
- Marketplace home now restores the denser intro/header panel, filter-first flow, bottom top-projects strip, denser project cards, and closer main/snapshot copy tone, but some pre-regression layout details may still remain to be matched exactly.
