from __future__ import annotations

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


def environment_quality_rules() -> list[QualityFailureContract]:
    return [
        QualityFailureContract(code="structure_warp", message="architecture or environment warping detected", frame_range="scene", severity="critical"),
        QualityFailureContract(code="lighting_jump", message="lighting direction jump detected", frame_range="scene", severity="high"),
    ]
