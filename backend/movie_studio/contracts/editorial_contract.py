from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class EditorialTimelineItemContract(BaseModel):
    item_id: str
    scene_id: str
    start_tc: str
    end_tc: str
    transition: str
    start_frame: int = 1
    end_frame: int = 1
    frame_count: int = 1
    subtitle_track_mode: Optional[str] = None
    music_track_mode: Optional[str] = None
    subtitle_track: Optional[str] = None
    audio_track: Optional[str] = None


class EditorialTimelineContract(BaseModel):
    project_id: str
    items: List[EditorialTimelineItemContract] = Field(default_factory=list)
