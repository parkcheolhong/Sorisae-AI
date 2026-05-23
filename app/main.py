# FILE-ID: FILE-APP-MAIN-PY
# SECTION-ID: SECTION-APP-MAIN-PY-MAIN
# FEATURE-ID: FEATURE-APP-MAIN-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-MAIN-PY-001

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.auth_routes import auth_router
from app.ops_routes import ops_router
from app.routes import router
from app.services import build_runtime_payload, summarize_health
from app.diagnostics import build_diagnostic_report
from app.order_profile import get_order_profile
from ai.router import router as ai_router
from backend.llm.router import router as llm_status_router
from backend.llm.orchestrator import router as llm_orchestrator_router
from backend.database import ensure_traceability_schema
from backend.admin_router import router as admin_router
from backend.marketplace.router import ensure_marketplace_runtime_schema, router as marketplace_router
from backend.marketplace.stats_router import router as marketplace_stats_router


class Utf8JsonResponse(JSONResponse):
    media_type = 'application/json; charset=utf-8'

def create_application() -> FastAPI:
    ensure_traceability_schema()
    ensure_marketplace_runtime_schema()

    app = FastAPI(
        title='오케스트레이터-자가개선-실험-즉시-실행-원본-대상-경로-C-Use-88b347d566',
        version='0.1.0',
        default_response_class=Utf8JsonResponse,
    )
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(ops_router)
    app.include_router(admin_router)
    app.include_router(ai_router)
    app.include_router(llm_status_router)
    app.include_router(llm_orchestrator_router)
    app.include_router(marketplace_router, prefix='/api/marketplace')
    app.include_router(marketplace_stats_router, prefix='/api/marketplace')

    mandatory_routes = {'/api/llm/status'}
    registered_paths = {route.path for route in app.routes} # type: ignore
    missing_routes = sorted(mandatory_routes - registered_paths)
    if missing_routes:
        raise RuntimeError(f"mandatory routes missing at startup: {', '.join(missing_routes)}")

    @app.get('/')
    def root():
        profile = get_order_profile()
        return {
            'status': 'ok',
            'project': profile['project_name'],
            'profile': profile['label'],
            'mode': 'customer-order-generator',
        }

    @app.get('/runtime')
    def runtime():
        payload = build_runtime_payload(runtime_mode='runtime')
        payload['health'] = summarize_health()
        payload['diagnostics'] = build_diagnostic_report()
        return payload

    return app

app = create_application()
