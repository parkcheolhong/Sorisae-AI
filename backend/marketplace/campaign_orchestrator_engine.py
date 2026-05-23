from __future__ import annotations

from typing import Dict

from .ad_strategy_engine import plan_ad_strategy
from .audience_profile_engine import infer_audience_profiles
from .caption_engine import build_caption_package
from .creative_variant_engine import build_creative_variants
from .execution_flow_registry import build_execution_identity
from .image_to_video_pipeline import run_image_to_video_pipeline
from .platform_formatter import build_platform_formats
from .story_state_engine import build_story_states


VIDEO_AD_OPERATION_STANDARD_SECONDS = 60


def plan_local_campaign(payload: Dict[str, object]) -> Dict[str, object]:
    strategy_plan = plan_ad_strategy(payload)
    audience_plan = infer_audience_profiles(payload)
    variant_plan = build_creative_variants(payload, strategy_plan, audience_plan)
    story_state_plan = build_story_states(payload, variant_plan)
    format_plan = build_platform_formats(payload)
    caption_plan = build_caption_package(payload, variant_plan)

    preview_duration = int((list(payload.get("duration_profiles") or [VIDEO_AD_OPERATION_STANDARD_SECONDS]) or [VIDEO_AD_OPERATION_STANDARD_SECONDS])[0])
    if preview_duration <= 0:
        preview_duration = VIDEO_AD_OPERATION_STANDARD_SECONDS
    preview_payload = {
        "title": payload.get("title") or "연속성 미리보기",
        "scenario_script": payload.get("scenario_script") or "",
        "duration_seconds": preview_duration,
        "frames_per_second": int(payload.get("preview_fps") or 8),
        "subtitle_speed": float(payload.get("subtitle_speed") or 1.0),
        "background_prompt": payload.get("background_prompt") or "",
        "caption_text": payload.get("caption_text") or "",
        "portrait_image_prompt": payload.get("portrait_image_prompt") or "",
        "product_image_prompts": list(payload.get("product_catalog") or []),
        "action_template_key": payload.get("action_template_key") or None,
        "motion_tempo": payload.get("motion_tempo") or None,
        "storyboard": list(payload.get("storyboard") or []),
    }
    pipeline = run_image_to_video_pipeline(preview_payload)
    quality_summary = dict(pipeline.get("quality_summary") or {})

    return {
        "strategy_plan": strategy_plan,
        "audience_plan": audience_plan,
        "variant_plan": variant_plan,
        "story_state_plan": story_state_plan,
        "format_plan": format_plan,
        "caption_plan": caption_plan,
        "image_line": pipeline.get("image_engine", {}).get("image_line"),
        "video_line": pipeline.get("video_engine", {}).get("video_line"),
        "quality_summary": quality_summary,
        "execution": build_execution_identity("campaign_orchestrator"),
    }
