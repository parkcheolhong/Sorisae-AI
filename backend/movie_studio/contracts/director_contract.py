from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class StoryThemeContract(BaseModel):
    genre: str
    tone: str
    era: str
    audience: str
    realism_level: str = Field(default="photoreal")


class SequenceBeatContract(BaseModel):
    sequence_id: str
    objective: str
    emotional_state: str
    blocking_summary: str
    cta_required: bool = False


class DirectorOutputContract(BaseModel):
    project_id: str
    title: str
    theme: StoryThemeContract
    sequences: List[SequenceBeatContract] = Field(default_factory=list)
    continuity_rules: List[str] = Field(default_factory=list)
