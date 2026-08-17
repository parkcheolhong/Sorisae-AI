# FILE-ID: FILE-BACKEND-API-ROUTER-PY
# SECTION-ID: SECTION-BACKEND-API-ROUTER-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-API-ROUTER-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-API-ROUTER-PY-001

from backend.core.flow_registry import find_registered_step
from backend.service.application_service import build_service_overview

def get_router_snapshot() -> dict:
    overview = build_service_overview()
    return {
        'layer': 'api',
        'flow_count': len(overview['flow_steps']),
        'source_count': len(overview['sources']),
        'trace_lookup': find_registered_step('FLOW-001-1'),
    }

def get_ai_runtime_snapshot(features: dict | None = None) -> dict:
    overview = build_service_overview()
    strategy_service = overview.get('strategy_service') or {}
    inference_runtime = strategy_service.get('inference_runtime') or {}
    model_registry = strategy_service.get('model_registry') or {}
    training_pipeline = strategy_service.get('training_pipeline') or {}
    evaluation_report = strategy_service.get('evaluation_report') or {}
    return {
        'model_registry': model_registry,
        'training_pipeline': training_pipeline,
        'inference_runtime': inference_runtime,
        'evaluation_report': evaluation_report,
        'input_features': features or {},
    }
