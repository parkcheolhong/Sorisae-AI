# FILE-ID: FILE-APP-DIAGNOSTICS-PY
# SECTION-ID: SECTION-APP-DIAGNOSTICS-PY-MAIN
# FEATURE-ID: FEATURE-APP-DIAGNOSTICS-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-DIAGNOSTICS-PY-001

from app.runtime import build_runtime_context, describe_runtime_profile
from app.services import build_runtime_payload
from app.order_profile import get_order_profile

def list_diagnostic_checks() -> list[str]:
    profile = get_order_profile()
    return [
        f"profile:{profile['profile_id']}",
        'flow-map-ready',
        'runtime-payload-ready',
        'metadata-ready',
        'ai-runtime-contract-ready',
        'ai-health-report-validated',
    ]

def validate_runtime_payload(payload: dict) -> dict:
    missing = [key for key in ('service', 'runtime_mode', 'order_profile', 'profile') if key not in payload]
    return {'ok': not missing, 'missing': missing}

def build_diagnostic_report() -> dict:
    payload = build_runtime_payload(runtime_mode='diagnostics')
    payload['profile'] = describe_runtime_profile()
    payload['runtime_context'] = build_runtime_context()
    payload['checks'] = list_diagnostic_checks()
    payload['validation'] = validate_runtime_payload(payload)
    payload['ai_validation'] = payload.get('ai_runtime_contract', {}).get('validation', {'ok': False})
    return payload
