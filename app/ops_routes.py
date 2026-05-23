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
    return {'status': 'ok' if provider.get('reachable') else 'degraded', 'provider_status': provider}

@ops_router.get('/health')
def ops_health():
    return ops_status()

@ops_router.get('/logs')
def ops_logs():
    provider = fetch_upstream_status()
    return {'items': provider.get('providers', []), 'count': len(provider.get('providers', []))}

@ops_router.get('/metrics', response_class=PlainTextResponse)
def metrics():
    provider = fetch_upstream_status()
    reachable = sum(1 for item in provider.get('providers', []) if item.get('reachable'))
    lines = ['# HELP customer_provider_up Reachable customer providers', '# TYPE customer_provider_up gauge', f'customer_provider_up {reachable}']
    return '\n'.join(lines) + '\n'
