from __future__ import annotations

from typing import Dict


def build_interaction_contract(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "interaction_type": str(payload.get("interaction_type") or "actor-prop").strip() or "actor-prop",
        "rules": [
            "contact surfaces must remain physically plausible",
            "gaze and hand focus must support the interaction target",
            "reaction timing must remain continuous",
        ],
    }
