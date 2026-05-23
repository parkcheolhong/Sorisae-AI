from __future__ import annotations

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


def anatomy_quality_rules() -> list[QualityFailureContract]:
    return [
        QualityFailureContract(code="body_ratio_break", message="body ratio instability detected", frame_range="scene", severity="critical"),
        QualityFailureContract(code="animal_structure_break", message="animal structure instability detected", frame_range="scene", severity="critical"),
    ]
