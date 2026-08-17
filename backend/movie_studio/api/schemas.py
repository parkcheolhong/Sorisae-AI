from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MovieStudioProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    synopsis: str = Field(min_length=1, max_length=4000)
    genre: str = Field(default="commercial cinema", min_length=1, max_length=120)
    tone: str = Field(default="premium photoreal", min_length=1, max_length=120)
    era: str = Field(default="contemporary", min_length=1, max_length=120)
    audience: str = Field(default="general", min_length=1, max_length=120)
    realism_level: str = Field(default="photoreal", min_length=1, max_length=120)
    species: str = Field(default="human", min_length=1, max_length=120)
    environment_type: str = Field(default="studio", min_length=1, max_length=120)
    location_summary: Optional[str] = Field(default=None, max_length=1000)
    background_prompt: Optional[str] = Field(default=None, max_length=2000)
    target_duration_seconds: int = Field(default=60, ge=1, le=600)
    target_fps: int = Field(default=24, ge=1, le=120)
    target_resolution: str = Field(default="1280x720", min_length=3, max_length=40)
    voice_track: Optional[str] = Field(default=None, max_length=500)
    music_track: Optional[str] = Field(default=None, max_length=500)
    continuity_rules: List[str] = Field(default_factory=list)
    wardrobe: List[str] = Field(default_factory=list)
    hero_props: List[str] = Field(default_factory=list)
    sequence_beats: List[Dict[str, Any]] = Field(default_factory=list)
    references: List[Dict[str, Any]] = Field(default_factory=list)
    identity_references: List[str] = Field(default_factory=list)
    environment_references: List[str] = Field(default_factory=list)
    pose_references: List[str] = Field(default_factory=list)
    camera_references: List[str] = Field(default_factory=list)
    quality_prompt: Optional[str] = Field(default=None, max_length=4000)
    local_model_stack: List[str] = Field(default_factory=list)
    gpu_targets: List[str] = Field(default_factory=list)
    operator_note: Optional[str] = Field(default=None, max_length=1000)


class MovieStudioProjectResponse(BaseModel):
    project_id: str
    scene_root: str
    review_root: str
    director_output: Dict[str, Any]
    sequence_plan: List[Dict[str, Any]]
    shot_plan: List[Dict[str, Any]]
    continuity_contract: List[str]
    actor_identity: Dict[str, Any]
    environment_contract: Dict[str, Any]
    camera_language: List[Dict[str, Any]]
    blocking_plan: List[Dict[str, Any]]
    sovereign_pipeline_contract: Dict[str, Any]
    internal_runtime_policy: Dict[str, Any]
    self_hosted_generation_bundle: Dict[str, Any]
    local_gpu_runtime_plan: Dict[str, Any]
    local_shot_sequence_plan: Dict[str, Any]
    scene_generation_requests: List[Dict[str, Any]]
    quality_result: Dict[str, Any]
    self_hosted_quality_requirements: Dict[str, Any]
    local_quality_runtime_plan: Dict[str, Any]
    editorial_timeline: Dict[str, Any]
    review_items: List[Dict[str, Any]]
    approval_queue: Dict[str, Any]
    refinement_plan: List[Dict[str, Any]]
    temporal_consistency: Dict[str, Any]
    upscale_plan: Dict[str, Any]
    frames_manifest: Optional[Dict[str, Any]] = None
    render_manifest: Optional[Dict[str, Any]] = None
    quality_runtime_manifest: Optional[Dict[str, Any]] = None
    output_mp4_path: Optional[str] = None
