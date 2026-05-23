from __future__ import annotations

from typing import Dict, List


def build_rerender_request(scene_id: str, reasons: List[str]) -> Dict[str, object]:
    return {
        "scene_id": scene_id,
        "reasons": reasons,
        "priority": "critical",
    }
