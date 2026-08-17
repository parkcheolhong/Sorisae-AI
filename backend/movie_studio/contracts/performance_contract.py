from __future__ import annotations

from pydantic import BaseModel, Field


class PerformanceBeatContract(BaseModel):
    beat_id: str
    actor_id: str
    action: str
    gesture: str
    eye_line: str
    emotional_intent: str
    cta_strength: str = Field(default="none")
    walking_pattern: str = Field(default="motivated cinematic walking")
    speaking_mode: str = Field(default="dialogue_sync_required")
    lip_sync_requirement: str = Field(default="phoneme_visible")
    performance_unit: str = Field(default="full_body_human_motion")
