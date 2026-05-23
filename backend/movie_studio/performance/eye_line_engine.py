from __future__ import annotations

from typing import Dict


def build_eye_line_map(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "eye_line_primary": str(payload.get("eye_line_primary") or "camera-primary").strip() or "camera-primary",
        "rules": [
            "eye contact shifts must remain motivated",
            "gaze target should not jitter across frames",
            "CTA gaze must support conversion intent",
        ],
    }
