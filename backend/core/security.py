# FILE-ID: FILE-BACKEND-CORE-SECURITY-PY
# SECTION-ID: SECTION-BACKEND-CORE-SECURITY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-SECURITY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-SECURITY-PY-001

import os

def get_security_profile() -> dict:
    allowed_hosts = [item.strip() for item in os.getenv('ALLOWED_HOSTS', 'localhost').split(',') if item.strip()]
    cors_allow_origins = [item.strip() for item in os.getenv('CORS_ALLOW_ORIGINS', 'https://metanova1004.com').split(',') if item.strip()]
    request_timeout_sec = float(os.getenv('REQUEST_TIMEOUT_SEC', '5'))
    return {'allowed_hosts': allowed_hosts, 'cors_allow_origins': cors_allow_origins, 'https_only': True, 'secret_manager_recommended': True, 'REQUEST_TIMEOUT_SEC': request_timeout_sec, 'request_timeout_sec': request_timeout_sec}
