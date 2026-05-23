from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.cinematography_contract import CameraShotContract


def build_shot_plan(sequence_plan: List[Dict[str, object]]) -> List[CameraShotContract]:
    shots: List[CameraShotContract] = []
    for sequence in sequence_plan:
        sequence_id = str(sequence.get("sequence_id") or "seq-01")
        shots.append(
            CameraShotContract(
                shot_id=f"{sequence_id}-shot-01",
                shot_size="medium close-up",
                camera_angle="eye level",
                lens_profile="cinematic 50mm",
                movement_type="motivated dolly",
                movement_path="forward reveal with subtle lateral correction",
                framing_priority=["actor face", "hero product", "environment realism"],
                focus_subject="primary actor",
                performance_unit="walking_gesture_dialogue",
                performance_requirements=[
                    "full-body walking motion must remain physically plausible",
                    "hand gesture must support spoken intent",
                    "eye-line must react to target and camera motivation",
                    "mouth shape must remain compatible with speaking performance",
                ],
            )
        )
    return shots
