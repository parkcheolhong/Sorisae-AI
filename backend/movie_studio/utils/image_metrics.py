from __future__ import annotations

from typing import Dict


def empty_image_metrics() -> Dict[str, float]:
    return {
        "face_consistency": 0.0,
        "hand_integrity": 0.0,
        "detail_score": 0.0,
    }
