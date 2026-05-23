from __future__ import annotations

from typing import Dict


def build_camera_path(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "movement_type": str(payload.get("movement_type") or "motivated dolly").strip() or "motivated dolly",
        "movement_path": str(payload.get("movement_path") or "stable cinematic push-in").strip() or "stable cinematic push-in",
        "rules": [
            "camera acceleration must remain smooth",
            "camera must not float unpredictably",
            "motion path must remain readable and story-motivated",
        ],
    }
