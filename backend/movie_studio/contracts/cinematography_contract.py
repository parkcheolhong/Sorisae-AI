from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class CameraShotContract(BaseModel):
    shot_id: str
    shot_size: str
    camera_angle: str
    lens_profile: str
    movement_type: str
    movement_path: str
    framing_priority: List[str] = Field(default_factory=list)
    focus_subject: Optional[str] = None
    performance_unit: str = Field(default="walking_gesture_dialogue")
    performance_requirements: List[str] = Field(default_factory=list)
