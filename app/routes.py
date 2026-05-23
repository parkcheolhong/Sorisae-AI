# FILE-ID: FILE-APP-ROUTES-PY
# SECTION-ID: SECTION-APP-ROUTES-PY-MAIN
# FEATURE-ID: FEATURE-APP-ROUTES-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-ROUTES-PY-001

from fastapi import APIRouter
from app.services import build_runtime_payload, list_endpoints, summarize_health, build_domain_snapshot
from app.order_profile import get_order_profile, get_flow_step, list_flow_steps
from app.diagnostics import build_diagnostic_report, validate_runtime_payload

router = APIRouter()

@router.get('/health')
def health():
    return summarize_health()

@router.get('/config')
def config():
    payload = build_runtime_payload(runtime_mode='config')
    payload['validation'] = validate_runtime_payload(payload)
    return payload

@router.get('/order-profile')
def order_profile():
    return get_order_profile()

@router.get('/flow-map')
def flow_map():
    return {'items': list_flow_steps(), 'count': len(list_flow_steps())}

@router.get('/flow-map/{step_id}')
def flow_step(step_id: str):
    return {'item': get_flow_step(step_id), 'step_id': step_id}

@router.get('/workspace')
def workspace():
    return {'snapshot': build_domain_snapshot(), 'endpoints': list_endpoints()}

@router.get('/report')
def report():
    return build_diagnostic_report()

@router.post('/diagnose')
def diagnose(payload: dict | None = None):
    request_payload = payload or {}
    profile = get_order_profile()
    return {
        'status': 'accepted',
        'received_keys': sorted(request_payload.keys()),
        'profile': profile['label'],
        'requested_outcomes': profile['requested_outcomes'],
        'flow_trace': list_flow_steps(),
    }
