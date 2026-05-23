# FILE-ID: FILE-APP-RUNTIME-PY
# SECTION-ID: SECTION-APP-RUNTIME-PY-MAIN
# FEATURE-ID: FEATURE-APP-RUNTIME-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-RUNTIME-PY-001

from datetime import datetime
from app.order_profile import get_order_profile

def build_runtime_context() -> dict:
    profile = get_order_profile()
    return {
        'environment': 'compat',
        'generated_at': datetime.utcnow().isoformat(),
        'profile_id': profile['profile_id'],
        'requested_stack': profile['requested_stack'],
    }

def describe_runtime_profile() -> dict:
    profile = get_order_profile()
    return {
        'profile': profile['label'],
        'summary': profile['summary'],
        'requested_stack': profile['requested_stack'],
    }
