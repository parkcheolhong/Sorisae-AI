# FILE-ID: FILE-AI-MODEL-REGISTRY-PY
# SECTION-ID: SECTION-AI-MODEL-REGISTRY-PY-MAIN
# FEATURE-ID: FEATURE-AI-MODEL-REGISTRY-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-MODEL-REGISTRY-PY-001

MODEL_REGISTRY: list[dict] = []

def register_model_version(model: dict) -> None:
    MODEL_REGISTRY.append(dict(model))

def get_latest_model() -> dict:
    return MODEL_REGISTRY[-1].copy() if MODEL_REGISTRY else {'version': 'bootstrap'}
