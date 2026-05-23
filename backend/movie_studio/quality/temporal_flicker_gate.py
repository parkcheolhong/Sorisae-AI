from __future__ import annotations

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


def temporal_flicker_rules() -> list[QualityFailureContract]:
    return [
        QualityFailureContract(code="background_flicker", message="temporal background flicker detected", frame_range="scene", severity="critical"),
        QualityFailureContract(code="freeze_like_cta", message="CTA sequence behaves like a freeze-frame", frame_range="cta-window", severity="critical"),
    ]
