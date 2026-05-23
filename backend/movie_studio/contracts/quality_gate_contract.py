from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class QualityFailureContract(BaseModel):
    code: str
    message: str
    frame_range: str
    severity: str


class StudioQualityGateResultContract(BaseModel):
    passed: bool
    score: float
    failures: List[QualityFailureContract] = Field(default_factory=list)
    rerender_required: bool = False
