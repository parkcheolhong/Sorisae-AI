from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class ReviewDecisionContract(BaseModel):
    review_id: str
    scene_id: str
    status: str
    notes: List[str] = Field(default_factory=list)
    rerender_requested: bool = False
