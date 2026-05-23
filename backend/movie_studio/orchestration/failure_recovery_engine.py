from __future__ import annotations

from typing import Dict, List


def build_failure_recovery_plan() -> Dict[str, List[str]]:
    return {
        "face_drift": ["re-run identity pass", "increase face lock weight", "replace candidate"],
        "hand_collapse": ["re-run anatomy repair", "reduce gesture complexity", "replace candidate"],
        "structure_warp": ["re-run environment pass", "tighten perspective lock", "replace candidate"],
        "background_flicker": ["re-run temporal pass", "raise temporal consistency weight", "replace candidate"],
        "scenario_progress_break": ["increase narrative motion bridge", "rebuild frame prompts", "replace candidate"],
    }
