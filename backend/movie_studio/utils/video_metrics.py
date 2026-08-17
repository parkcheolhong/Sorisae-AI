from __future__ import annotations

from typing import Dict


def empty_video_metrics() -> Dict[str, float]:
    return {
        "temporal_consistency": 0.0,
        "flicker_score": 0.0,
        "identity_stability": 0.0,
    }
