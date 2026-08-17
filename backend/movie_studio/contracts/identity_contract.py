from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class IdentityReferenceAsset(BaseModel):
    asset_id: str
    asset_type: str
    path: str
    angle: Optional[str] = None
    expression: Optional[str] = None


class ActorIdentityContract(BaseModel):
    actor_id: str
    display_name: str
    species: str = Field(default="human")
    face_lock_required: bool = True
    anatomy_lock_required: bool = True
    costume_lock_required: bool = True
    references: List[IdentityReferenceAsset] = Field(default_factory=list)
    prohibited_failures: List[str] = Field(default_factory=lambda: [
        "face_drift",
        "hand_collapse",
        "eye_misalignment",
        "body_ratio_break",
    ])
