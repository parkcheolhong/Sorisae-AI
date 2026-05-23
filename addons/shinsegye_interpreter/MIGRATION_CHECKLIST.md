# Migration Checklist (Shinsegye Interpreter)

Status values:

- `구현됨`: file migration implemented
- `완료됨`: implementation + verification evidence confirmed
- `실패`: blocked or failed

## Checklist

- [x] Source repository cloned at target commit (`56b7d89`) - `완료됨`
- [x] Interpreter core files copied into `addons/shinsegye_interpreter/src` - `완료됨`
- [x] Launcher copied (`run_interpreter.py`) - `완료됨`
- [x] Project dependency file copied (`requirements.txt`) - `완료됨`
- [x] Usage guide copied (`docs/INTERPRETER_GUIDE.md`) - `완료됨`
- [x] Smoke verification run #1 (`SorisaeInterpreter` init + quick translate) - `완료됨`
- [x] Smoke verification run #2 (`SorisaeInterpreter` init + quick translate) - `완료됨`
- [x] Marketplace backend interpreter router mounted (`/api/marketplace/interpreter/*`) - `완료됨`
- [x] Standalone interpreter FastAPI service added (`addons/shinsegye_interpreter/service_api.py`) - `완료됨`
- [x] Docker compose standalone service added (`interpreter-service`) - `완료됨`
- [x] Standalone service verification run #1 (`/health` + `/translate`) - `완료됨`
- [x] Standalone service verification run #2 (`/translate` UTF-8 payload`) -`완료됨`
- [x] Marketplace frontend build verification (`/marketplace/code-generator`) - `완료됨`
- [x] Marketplace frontend visual render verification (`통역 연동 패널`) - `완료됨`

## Verification Evidence

Round #1 output markers:

- `ROUND1_INIT_OK SorisaeInterpreter`
- `ROUND1_TRANSLATE Hello`

Round #2 output markers:

- `ROUND2_INIT_OK SorisaeInterpreter`
- `ROUND2_TRANSLATE Thank you`

Standalone service verification:

- `ROUND1_HEALTH ok`
- `SERVICE_UTF8_ROUND1 Hello`
- `SERVICE_UTF8_ROUND2 Thank you`

Marketplace backend route verification:

- `BACKEND_ROUTE_ROUND1 401`
- `BACKEND_ROUTE_ROUND2 401`
- `OPENAPI_INTERPRETER_ROUTE_PRESENT YES`

Marketplace frontend build verification:

- `next build` completed successfully for `frontend/frontend`
- Built output contains `통역 연동 패널` and `통역 API 호출`

Marketplace frontend visual/runtime verification:

- `http://127.0.0.1:3012/marketplace/code-generator` rendered `통역 연동 패널`
- `PROD_PANEL_VERIFY True`
- `PROD_BUTTON_VERIFY True`
- Browser click on `통역 API 호출` returned `mode: service` and `Hello`
- Root cause of the previous stale sidebar tree: Turbopack dev runtime on `3000` kept serving an old in-memory page chunk, while isolated production build/runtime served the current page correctly

## Result

- Final status: `완료됨`
- Scope: interpreter subset migration + backend/compose/frontend integration implementation
- Runtime verification: completed on isolated production runtime (`3012`)
