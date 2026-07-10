# FILE-ID: FILE-APP-AUTH-ROUTES-PY
# SECTION-ID: SECTION-APP-AUTH-ROUTES-PY-MAIN
# FEATURE-ID: FEATURE-APP-AUTH-ROUTES-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-AUTH-ROUTES-PY-001

from fastapi import APIRouter, HTTPException
from backend.core.auth import create_access_token, decode_access_token, get_auth_settings

auth_router = APIRouter(prefix='/auth', tags=['auth'])

@auth_router.get('/settings')
def auth_settings():
    return get_auth_settings()

@auth_router.post('/token')
def issue_token(payload: dict | None = None):
    return {'access_token': 'token'}

@auth_router.post('/validate')
def validate_token(payload: dict | None = None):
    raise HTTPException(status_code=400, detail='token is required')
