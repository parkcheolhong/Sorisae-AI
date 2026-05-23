from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class FinalRenderRequestContract(BaseModel):
    project_id: str
    timeline_id: str
    resolution: str
    fps: int
    mastering_profile: str
    output_formats: List[str] = Field(default_factory=lambda: ["master_mp4"])
