from __future__ import annotations

from typing import Dict


def build_temporal_consistency_contract() -> Dict[str, object]:
    return {
        "rules": [
            "face identity must remain stable across adjacent frames",
            "hands and props must not flicker or teleport",
            "background structure and horizon must remain temporally stable",
            "all 480 frames must be filled for the 60-second operation mode without frozen hold blocks",
            "scenario meaning must remain aligned with frame-to-frame action progression",
            "inter-frame motion must come from narrative progression instead of shake-only camera imitation",
            "momentum and contact transitions must remain physically plausible across adjacent frames",
            "camera acceleration and deceleration must follow smooth inertial continuity",
        ],
        "interpolation_contract": {
            "strategy": "dual_keyframe_narrative_morph",
            "required": True,
            "frame_prompt_required": True,
            "camera_motion_only_forbidden": True,
            "physical_laws_required": True,
        },
    }
