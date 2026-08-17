from __future__ import annotations

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


def hand_quality_rules() -> list[QualityFailureContract]:
    return [
        QualityFailureContract(code="hand_collapse", message="hand anatomy collapse detected", frame_range="scene", severity="critical"),
        QualityFailureContract(code="finger_count_error", message="finger count or finger structure error detected", frame_range="scene", severity="critical"),
    ]
