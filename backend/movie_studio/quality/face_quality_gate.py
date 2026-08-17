from __future__ import annotations

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


def face_quality_rules() -> list[QualityFailureContract]:
    return [
        QualityFailureContract(code="face_drift", message="face identity drift detected", frame_range="scene", severity="critical"),
        QualityFailureContract(code="face_distortion", message="facial geometry distortion detected", frame_range="scene", severity="critical"),
    ]
