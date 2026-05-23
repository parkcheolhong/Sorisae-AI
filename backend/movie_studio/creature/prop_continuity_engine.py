from __future__ import annotations

from typing import Dict, List


def build_prop_continuity(payload: Dict[str, object]) -> Dict[str, object]:
    props = [str(item).strip() for item in list(payload.get("hero_props") or []) if str(item).strip()]
    return {
        "hero_props": props,
        "rules": [
            "hero props must not teleport between shots",
            "product scale must remain stable",
            "interaction contact points must remain readable",
        ],
    }
