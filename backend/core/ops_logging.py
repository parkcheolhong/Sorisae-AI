# FILE-ID: FILE-BACKEND-CORE-OPS-LOGGING-PY
# SECTION-ID: SECTION-BACKEND-CORE-OPS-LOGGING-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-OPS-LOGGING-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-OPS-LOGGING-PY-001

OPS_CHANNELS = ["audit", "runtime"]
OPS_MEMORY_BUFFER: list[dict] = []

def record_ops_log(event: str, detail: dict | None = None) -> dict:
    payload = {'event': event, 'detail': detail or {}, 'channels': list(OPS_CHANNELS)}
    OPS_MEMORY_BUFFER.append(payload)
    return payload

def list_ops_logs() -> list[dict]:
    return [dict(item) for item in OPS_MEMORY_BUFFER]
