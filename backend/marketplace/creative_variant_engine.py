from __future__ import annotations

from typing import Dict, List

from .execution_flow_registry import build_execution_identity


def build_creative_variants(payload: Dict[str, object], strategy_plan: Dict[str, object], audience_plan: Dict[str, object]) -> Dict[str, object]:
    requested_modes = list(payload.get("creative_modes") or [])
    profiles = list(audience_plan.get("profiles") or [])
    primary = str(strategy_plan.get("primary_strategy") or "dramatic")
    base_modes = requested_modes or [primary, "informative", "cta_compressed"]
    variants: List[Dict[str, object]] = []
    for mode_index, mode in enumerate(base_modes, start=1):
        for profile in profiles[:3] or [{"id": "broad-mass", "label": "범용 대중 타깃"}]:
            variants.append({
                "variant_id": f"variant-{mode_index:02d}-{str(profile.get('id') or 'broad')}",
                "strategy_type": mode,
                "hook_style": "fast_hook" if mode in {"dramatic", "cta_compressed", "comparison"} else "warm_hook",
                "narrative_style": "sectional_continuity",
                "cta_style": "compressed" if mode == "cta_compressed" else "balanced",
                "platform_target": "multi",
                "audience_id": str(profile.get("id") or "broad-mass"),
                "audience_label": str(profile.get("label") or "범용 대중 타깃"),
            })
    return {
        "variants": variants[:6],
        "execution": build_execution_identity("campaign_variant"),
    }
