from __future__ import annotations

from typing import Dict


def build_retry_policy() -> Dict[str, object]:
    return {
        "max_scene_rerenders": 3,
        "max_identity_repairs": 2,
        "max_environment_repairs": 2,
        "fail_fast_conditions": [
            "face_drift",
            "hand_collapse",
            "body_ratio_break",
            "structure_warp",
        ],
    }
