# FILE-ID: FILE-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY
# SECTION-ID: SECTION-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-MAIN
# FEATURE-ID: FEATURE-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-001

from app.core.config import get_settings

def build_status_client_summary() -> dict:
    settings = get_settings()
    return {
        'endpoint': settings.status_endpoint,
        'configured': bool(settings.status_endpoint),
    }
