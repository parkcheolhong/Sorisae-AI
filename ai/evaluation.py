# FILE-ID: FILE-AI-EVALUATION-PY
# SECTION-ID: SECTION-AI-EVALUATION-PY-MAIN
# FEATURE-ID: FEATURE-AI-EVALUATION-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-EVALUATION-PY-001

from typing import Dict, List

def evaluate_predictions(predictions: List[dict]) -> Dict[str, object]:
    candidate_sets = [item for item in predictions if item.get('candidate_sets')]
    average_score = round(sum(float(item.get('score', 0.0) or 0.0) for item in candidate_sets) / len(candidate_sets), 4) if candidate_sets else 0.0
    return {
        'samples': len(predictions),
        'candidate_sets': len(candidate_sets),
        'average_score': average_score,
        'quality_gate': 'pass' if candidate_sets else 'needs-data',
        'prediction-evaluation': bool(candidate_sets),
    }
