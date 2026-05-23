# FILE-ID: FILE-BACKEND-CORE-AUTH-PY
# SECTION-ID: SECTION-BACKEND-CORE-AUTH-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-AUTH-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-AUTH-PY-001

import os
from datetime import datetime, timedelta
from typing import Any, Dict
from jose import JWTError, jwt

JWT_SCOPES = ["program.read", "program.write"]
JWT_SECRET = os.getenv('JWT_SECRET', '').strip()
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '60'))
AUTH_SETTINGS = {
    'enabled': True,
    'algorithm': JWT_ALGORITHM,
    'scopes': list(JWT_SCOPES),
    'token_header': 'Authorization',
}

def get_auth_settings() -> Dict[str, Any]:
    return {
        **AUTH_SETTINGS,
        'JWT_SECRET': JWT_SECRET,
        'JWT_ALGORITHM': JWT_ALGORITHM,
        'JWT_EXPIRE_MINUTES': JWT_EXPIRE_MINUTES,
        'self_configurable_settings': {'JWT_SECRET': 'env', 'JWT_ALGORITHM': JWT_ALGORITHM, 'JWT_EXPIRE_MINUTES': JWT_EXPIRE_MINUTES},
    }

def create_access_token(subject: str, scopes: list[str] | None = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {'sub': subject, 'scopes': scopes or list(JWT_SCOPES), 'exp': expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        return {'valid': False, 'error': str(exc)}
    return {'valid': True, 'payload': payload}
