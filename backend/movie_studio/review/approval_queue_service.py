from __future__ import annotations

from typing import Dict, List


def build_approval_queue(scene_ids: List[str]) -> Dict[str, object]:
    return {
        "pending_scene_ids": scene_ids,
        "approved_scene_ids": [],
        "rejected_scene_ids": [],
    }
