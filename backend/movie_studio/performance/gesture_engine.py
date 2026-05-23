from __future__ import annotations

from typing import Dict


def build_gesture_map(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "hero_gesture": str(payload.get("hero_gesture") or "confident hand presentation").strip() or "confident hand presentation",
        "rules": [
            "gesture must progress and not freeze",
            "hand pose must remain anatomically plausible",
            "gesture should reinforce the hero object or CTA",
        ],
    }
