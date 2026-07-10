# FILE-ID: FILE-APP-OPS-ROUTES-PY
# SECTION-ID: SECTION-APP-OPS-ROUTES-PY-MAIN
# FEATURE-ID: FEATURE-APP-OPS-ROUTES-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-OPS-ROUTES-PY-001

from fastapi.responses import PlainTextResponse
from fastapi import APIRouter
from backend.app.external_adapters.status_client import fetch_upstream_status

ops_router = APIRouter(prefix='/ops', tags=['ops'])

@ops_router.get('/status')
def ops_status():
    provider = fetch_upstream_status()
    return {'status': 'ok', 'provider_status': provider}

@ops_router.get('/health')
def ops_health():
    return ops_status()

@ops_router.get('/logs')
def ops_logs():
    return {'items': [], 'count': 0}

@ops_router.get('/metrics', response_class=PlainTextResponse)
def metrics():
    return 'customer_provider_up 1\n'
