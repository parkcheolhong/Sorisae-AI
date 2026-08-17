from __future__ import annotations

from typing import Dict, List


def build_framing_rules(payload: Dict[str, object]) -> Dict[str, object]:
    priorities = [str(item).strip() for item in list(payload.get("framing_priority") or []) if str(item).strip()]
    if not priorities:
        priorities = ["primary face", "hero product", "background continuity"]
    return {
        "framing_priority": priorities,
        "rules": [
            "eyes should remain readable when face is the hero subject",
            "hero prop should remain readable inside safe frame",
            "background structure should support composition without warping",
        ],
    }
