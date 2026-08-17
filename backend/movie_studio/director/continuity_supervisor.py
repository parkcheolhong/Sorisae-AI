from __future__ import annotations

from typing import Dict, List


def build_continuity_contract(project_payload: Dict[str, object]) -> List[str]:
    explicit_rules = [str(item).strip() for item in list(project_payload.get("continuity_rules") or []) if str(item).strip()]
    if explicit_rules:
        return explicit_rules
    return [
        "real human or creature identity must not drift across shots",
        "hands, anatomy, and costume must stay consistent",
        "architecture lines and horizon must remain stable",
        "lighting direction and weather continuity must stay locked",
        "CTA performance must evolve without freeze-frame behavior",
    ]
