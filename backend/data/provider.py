# FILE-ID: FILE-BACKEND-DATA-PROVIDER-PY
# SECTION-ID: SECTION-BACKEND-DATA-PROVIDER-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-DATA-PROVIDER-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-DATA-PROVIDER-PY-001

from app.order_profile import get_order_profile

def list_data_sources() -> list[dict]:
    profile = get_order_profile()
    return [
        {'name': item, 'type': 'order-entity', 'profile_id': profile['profile_id']}
        for item in profile['entities']
    ]
