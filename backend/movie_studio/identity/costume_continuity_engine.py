from __future__ import annotations

from typing import Dict, List


def build_costume_continuity(payload: Dict[str, object]) -> Dict[str, object]:
    wardrobe = [str(item).strip() for item in list(payload.get("wardrobe") or []) if str(item).strip()]
    return {
        "costume_lock_required": True,
        "wardrobe_items": wardrobe,
        "continuity_rules": [
            "costume silhouette must remain stable",
            "hair silhouette must remain stable",
            "accessories must not disappear between shots",
        ],
    }
