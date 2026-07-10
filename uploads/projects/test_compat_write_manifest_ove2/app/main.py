# FILE-ID: FILE-APP-MAIN-PY
# SECTION-ID: SECTION-APP-MAIN-PY-MAIN
# FEATURE-ID: FEATURE-APP-MAIN-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-MAIN-PY-001

from fastapi import FastAPI
from app.services import build_runtime_payload, summarize_health

def create_application() -> FastAPI:
    app = FastAPI()
    return app

app = create_application()
