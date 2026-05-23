from __future__ import annotations

from typing import Dict, List

from .execution_flow_registry import build_execution_identity

def build_platform_formats(payload: Dict[str, object]) -> Dict[str, object]:
    targets = list(payload.get("platform_targets") or []) or ["youtube", "instagram_reels", "tiktok"]
    durations = list(payload.get("duration_profiles") or []) or [5, 15, 30, 60]
    presets = {
        "youtube": {"aspect_ratio": "16:9", "caption_density": "medium", "cta_density": "medium"},
        "instagram_reels": {"aspect_ratio": "9:16", "caption_density": "high", "cta_density": "high"},
        "instagram_feed": {"aspect_ratio": "1:1", "caption_density": "medium", "cta_density": "medium"},
        "facebook_feed": {"aspect_ratio": "1:1", "caption_density": "medium", "cta_density": "medium"},
        "tiktok": {"aspect_ratio": "9:16", "caption_density": "high", "cta_density": "high"},
        "blog": {"aspect_ratio": "16:9", "caption_density": "low", "cta_density": "low"},
        "commerce_thumb": {"aspect_ratio": "1:1", "caption_density": "low", "cta_density": "high"},
    }
    outputs: List[Dict[str, object]] = []
    for target in targets:
        preset = presets.get(str(target), {"aspect_ratio": "16:9", "caption_density": "medium", "cta_density": "medium"})
        outputs.append({"platform": str(target), "aspect_ratio": preset["aspect_ratio"], "caption_density": preset["caption_density"], "cta_density": preset["cta_density"], "duration_profiles": durations})
    return {"formats": outputs, "execution": build_execution_identity("campaign_format")}
