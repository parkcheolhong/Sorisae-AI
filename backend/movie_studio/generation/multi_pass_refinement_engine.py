from __future__ import annotations

from typing import Dict, List


def build_refinement_plan() -> List[Dict[str, object]]:
    return [
        {"pass": 1, "name": "base_scene_generation", "objective": "establish photoreal blocking and camera path"},
        {"pass": 2, "name": "identity_repair", "objective": "reinforce face and anatomy continuity"},
        {"pass": 3, "name": "environment_repair", "objective": "repair perspective, horizon, and lighting continuity"},
        {"pass": 4, "name": "detail_polish", "objective": "restore skin, fabric, material, and hero prop detail"},
    ]
