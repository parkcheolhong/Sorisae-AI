from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from backend.movie_studio.contracts.identity_contract import ActorIdentityContract, IdentityReferenceAsset


def build_actor_identity(payload: Dict[str, object]) -> ActorIdentityContract:
    references = [
        IdentityReferenceAsset(
            asset_id=f"ref-{index+1:02d}",
            asset_type=str(item.get("asset_type") or "image"),
            path=str(item.get("path") or "").strip(),
            angle=str(item.get("angle") or "").strip() or None,
            expression=str(item.get("expression") or "").strip() or None,
        )
        for index, item in enumerate(list(payload.get("references") or []))
        if str(item.get("path") or "").strip()
    ]
    return ActorIdentityContract(
        actor_id=str(payload.get("actor_id") or f"actor-{uuid4().hex[:10]}"),
        display_name=str(payload.get("display_name") or payload.get("title") or "lead actor").strip() or "lead actor",
        species=str(payload.get("species") or "human").strip() or "human",
        references=references,
    )
