# FILE-ID: FILE-AI-ADAPTERS-PY
# SECTION-ID: SECTION-AI-ADAPTERS-PY-MAIN
# FEATURE-ID: FEATURE-AI-ADAPTERS-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-ADAPTERS-PY-001

ADAPTER_TARGETS = ["score", "decision", "recommendation"]

def resolve_adapter() -> dict:
    return {
        'decision_key': list(ADAPTER_TARGETS)[0] if ADAPTER_TARGETS else 'score',
        'default_decision': 'REVIEW',
        'model_endpoint': 'local://automation_service-adapter',
        'adapter_targets': list(ADAPTER_TARGETS),
    }
