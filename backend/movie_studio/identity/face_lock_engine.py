from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.identity_contract import ActorIdentityContract


def build_face_lock(identity: ActorIdentityContract) -> Dict[str, object]:
    return {
        "actor_id": identity.actor_id,
        "face_lock_required": identity.face_lock_required,
        "reference_count": len(identity.references),
        "rules": [
            "eye geometry must remain stable",
            "nose-mouth alignment must remain stable",
            "face shape must remain stable across shots",
        ],
    }
