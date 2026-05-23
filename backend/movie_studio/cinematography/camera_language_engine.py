from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.cinematography_contract import CameraShotContract


def build_camera_language(sequence_plan: List[Dict[str, object]]) -> List[CameraShotContract]:
    return [
        CameraShotContract(
            shot_id=f"{item['sequence_id']}-cam-01",
            shot_size="medium close-up",
            camera_angle="eye level",
            lens_profile="cinematic 50mm spherical",
            movement_type="motivated dolly",
            movement_path="controlled forward push with stabilised lateral correction",
            framing_priority=["identity", "hero product", "environment realism"],
            focus_subject="primary subject",
            performance_unit="walking_gesture_dialogue",
            performance_requirements=[
                "walking cadence must stay readable in frame",
                "gesture emphasis must align with emotional beats",
                "eye tracking and head turn must stay human-readable",
                "speaking performance must preserve visible lip motion",
            ],
        )
        for item in sequence_plan
    ]
