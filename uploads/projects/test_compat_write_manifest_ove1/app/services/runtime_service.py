# FILE-ID: FILE-APP-SERVICES-RUNTIME-SERVICE-PY
# SECTION-ID: SECTION-APP-SERVICES-RUNTIME-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-APP-SERVICES-RUNTIME-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-SERVICES-RUNTIME-SERVICE-PY-001

def build_runtime_payload(runtime_mode: str = 'default') -> dict:
    return {'runtime_mode': runtime_mode}

def list_endpoints() -> list[str]:
    return ['/health']

def summarize_health() -> dict:
    return {'status': 'ok'}
