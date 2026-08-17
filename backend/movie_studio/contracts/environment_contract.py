from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class EnvironmentContract(BaseModel):
    environment_id: str
    environment_type: str
    location_summary: str
    lighting_direction: str
    time_of_day: str
    weather_mode: str
    perspective_lock: bool = True
    horizon_lock: bool = False
    prohibited_failures: List[str] = Field(default_factory=lambda: [
        "perspective_break",
        "background_flicker",
        "lighting_jump",
        "structure_warp",
    ])
