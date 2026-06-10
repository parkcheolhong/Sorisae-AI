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

@router.get('/order-profile')
def order_profile():
    return get_order_profile()

@router.get('/report')
def report():
    return build_diagnostic_report()

@router.post('/diagnose')
def diagnose(payload: dict | None = None):
    return {'status': 'accepted'}
