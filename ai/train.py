# FILE-ID: FILE-AI-TRAIN-PY
# SECTION-ID: SECTION-AI-TRAIN-PY-MAIN
# FEATURE-ID: FEATURE-AI-TRAIN-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-TRAIN-PY-001

from typing import Any, Dict, List

from ai.features import build_feature_set
from ai.model_registry import register_model_version

MANDATORY_ENGINE_CONTRACTS = ["engine-core", "feature-pipeline", "training-pipeline", "inference-runtime", "evaluation-report", "service-integration"]
ADAPTER_TARGETS = ["score", "decision", "recommendation"]

def train_model(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    feature_payload = build_feature_set({'records': dataset})
    windows = feature_payload.get('feature_windows') or []
    ranking = []
    if windows:
        field_scores = dict(windows[-1].get('field_scores') or {})
        ranking = sorted(field_scores.items(), key=lambda item: (-float(item[1]), item[0]))[:12]
    model = {
        'version': f'domain-model-{len(dataset)}',
        'status': 'trained' if dataset else 'needs-data',
        'trained_records': len(dataset),
        'feature_windows': len(windows),
        'candidate_ranking': [{'target': key, 'weight': value} for key, value in ranking],
        'mandatory_engine_contracts': list(MANDATORY_ENGINE_CONTRACTS),
        'adapter_targets': list(ADAPTER_TARGETS),
        'engine-core': True,
    }
    register_model_version(model)
    return model
