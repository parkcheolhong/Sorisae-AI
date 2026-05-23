# FILE-ID: FILE-APP-API-ROUTES-HEALTH-PY
# SECTION-ID: SECTION-APP-API-ROUTES-HEALTH-PY-MAIN
# FEATURE-ID: FEATURE-APP-API-ROUTES-HEALTH-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-API-ROUTES-HEALTH-PY-001

from fastapi import APIRouter

router = APIRouter()

@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': 'customer-order-generator'}
