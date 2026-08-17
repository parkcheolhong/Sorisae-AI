from __future__ import annotations

from typing import Dict, List

from .campaign_common import normalize_text
from .execution_flow_registry import build_execution_identity


def build_caption_package(payload: Dict[str, object], variant_plan: Dict[str, object]) -> Dict[str, object]:
    title = normalize_text(str(payload.get("title") or "광고")) or "광고"
    scenario_script = normalize_text(str(payload.get("scenario_script") or ""))
    subtitle_speed = float(payload.get("subtitle_speed") or 1.0)
    variants = list(variant_plan.get("variants") or [])
    headline = title[:40]
    body = scenario_script[:140]
    cta_pool = [
        "지금 확인하세요",
        "지금 바로 시작하세요",
        "더 자세히 보기",
        "지금 문의하세요",
    ]
    captions: List[Dict[str, object]] = []
    for index, variant in enumerate(variants[:4], start=1):
        captions.append({
            "variant_id": str(variant.get("variant_id") or f"variant-{index:02d}"),
            "headline": headline,
            "body": body,
            "cta": cta_pool[(index - 1) % len(cta_pool)],
            "subtitle_speed": round(subtitle_speed, 1),
            "tone": str(variant.get("strategy_type") or "balanced"),
        })
    return {
        "captions": captions,
        "execution": build_execution_identity("campaign_caption"),
    }
