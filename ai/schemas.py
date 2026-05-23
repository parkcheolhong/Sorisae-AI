# FILE-ID: FILE-AI-SCHEMAS-PY
# SECTION-ID: SECTION-AI-SCHEMAS-PY-MAIN
# FEATURE-ID: FEATURE-AI-SCHEMAS-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-SCHEMAS-PY-001

from typing import Any, Dict, List
from pydantic import BaseModel, Field

class InferenceRequest(BaseModel):
    signal_strength: float = 0.0
    features: Dict[str, Any] = Field(default_factory=dict)

class TrainingRequest(BaseModel):
    dataset: List[Dict[str, Any]] = Field(default_factory=list)

class EvaluationRequest(BaseModel):
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
