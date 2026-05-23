from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class SceneGenerationRequestContract(BaseModel):
    scene_id: str
    sequence_id: str
    chunk_index: int = Field(default=1)
    chunk_label: str = Field(default="clip-01")
    director_notes: List[str] = Field(default_factory=list)
    identity_refs: List[str] = Field(default_factory=list)
    environment_refs: List[str] = Field(default_factory=list)
    camera_contract_id: str
    performance_contract_ids: List[str] = Field(default_factory=list)
    target_duration_seconds: int
    target_fps: int
    target_resolution: str
    start_second: float = Field(default=0.0)
    end_second: float = Field(default=0.0)
    start_frame: int = Field(default=1)
    end_frame: int = Field(default=1)
    frame_count: int = Field(default=1)
    narrative_prompt: str = Field(default="")
    interpolation_strategy: str = Field(default="dual_keyframe_narrative_morph")
    continuity_checks: List[str] = Field(default_factory=list)
    performance_actions: List[Dict[str, str]] = Field(default_factory=list)
    physical_continuity_laws: List[str] = Field(default_factory=list)
    guidance_schedule: Dict[str, object] = Field(default_factory=dict)
    carry_over_required: bool = Field(default=False)
    realism_level: str = Field(default="photoreal")
