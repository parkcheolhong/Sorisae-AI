# FILE-ID: FILE-APP-CORE-SECURITY-PY
# SECTION-ID: SECTION-APP-CORE-SECURITY-PY-MAIN
# FEATURE-ID: FEATURE-APP-CORE-SECURITY-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-CORE-SECURITY-PY-001

import os
from typing import Iterable, List

from app.core.config import get_settings

DEFAULT_ALLOWED_HOSTS = ('localhost', '127.0.0.1')
DEFAULT_CORS_ALLOW_ORIGINS = (
    'http://localhost:8000',
    'http://127.0.0.1:8000',
)
REQUEST_TIMEOUT_SEC = 30
WILDCARD_TOKEN = chr(42)


def _parse_allowed_values(env_name: str, defaults: Iterable[str]) -> List[str]:
    raw_value = os.getenv(env_name, ','.join(defaults))
    values = [item.strip() for item in raw_value.split(',') if item.strip()]
    if not values:
        values = list(defaults)
    if WILDCARD_TOKEN in values:
        raise RuntimeError(f'{env_name} must use explicit hosts or origins, not wildcard')
    return values


def get_allowed_hosts() -> List[str]:
    return _parse_allowed_values('ALLOWED_HOSTS', DEFAULT_ALLOWED_HOSTS)


def get_cors_allow_origins() -> List[str]:
    return _parse_allowed_values('CORS_ALLOW_ORIGINS', DEFAULT_CORS_ALLOW_ORIGINS)

def build_security_headers() -> dict:
    settings = get_settings()
    allowed_hosts = get_allowed_hosts()
    cors_allow_origins = get_cors_allow_origins()
    return {
        'has_secret_key': bool(settings.app_secret_key),
        'frame_options': 'DENY',
        'content_type_options': 'nosniff',
        'https_only': settings.app_env == 'production',
        'allowed_hosts': allowed_hosts,
        'cors_allow_origins': cors_allow_origins,
        'request_timeout_sec': REQUEST_TIMEOUT_SEC,
    }
