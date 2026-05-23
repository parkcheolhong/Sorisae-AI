# FILE-ID: FILE-BACKEND-CORE-RUNTIME-PY
# SECTION-ID: SECTION-BACKEND-CORE-RUNTIME-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-RUNTIME-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-RUNTIME-PY-001

from app.order_profile import get_order_profile

def build_scaffold_runtime() -> dict:
    profile = get_order_profile()
    return {
        'profile_id': profile['profile_id'],
        'project_name': profile['project_name'],
        'layer': 'core',
    }
