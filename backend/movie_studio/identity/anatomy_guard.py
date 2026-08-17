from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.identity_contract import ActorIdentityContract


def build_anatomy_guard(identity: ActorIdentityContract) -> Dict[str, object]:
    return {
        "actor_id": identity.actor_id,
        "enabled": identity.anatomy_lock_required,
        "prohibited_failures": identity.prohibited_failures,
        "must_check": ["hands", "arms", "legs", "eye alignment", "body ratio"],
    }
