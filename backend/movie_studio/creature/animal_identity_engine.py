from __future__ import annotations

from typing import Dict


def build_animal_identity(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "species": str(payload.get("species") or "animal").strip() or "animal",
        "identity_lock_required": True,
        "continuity_rules": [
            "ear, eye, muzzle, and tail silhouette must remain stable",
            "leg count and leg proportions must remain stable",
            "fur pattern and dominant markings must not drift",
        ],
    }
