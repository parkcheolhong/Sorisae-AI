from __future__ import annotations

from typing import Dict
from uuid import uuid4

from .execution_flow_registry import build_execution_identity
from .local_designer_engine import render_local_designer_sequence

DEFAULT_BACKEND_TYPE = "local_svg_storyboard"
DEFAULT_CONTINUITY_MODE = "story_flow"

def run_image_generation_engine(payload: Dict[str, object]) -> Dict[str, object]:
    image_line = render_local_designer_sequence(payload)
    return {"engine_id": f"image-engine-{uuid4().hex[:10]}", "backend_type": DEFAULT_BACKEND_TYPE, "continuity_mode": DEFAULT_CONTINUITY_MODE, "image_line": image_line, "execution": build_execution_identity("image_engine")}
