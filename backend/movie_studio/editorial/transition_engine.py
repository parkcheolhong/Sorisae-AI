from __future__ import annotations

from typing import Dict


def build_transition_policy() -> Dict[str, object]:
    return {
        "default_transition": "motivated_cut",
        "rules": [
            "avoid decorative transitions unless story-motivated",
            "preserve performance continuity across transitions",
        ],
    }
