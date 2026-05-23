from __future__ import annotations

from typing import Dict

FLOW_REGISTRY: Dict[str, Dict[str, str]] = {
    "campaign_strategy": {"flow_id": "FLOW-001", "step_id": "FLOW-001-1", "action": "STRATEGY_PLAN", "route_id": "ROUTE-CAMPAIGN-STRATEGY-001", "front_block_id": "FRONT-CAMPAIGN-STRATEGY-001"},
    "campaign_audience": {"flow_id": "FLOW-001", "step_id": "FLOW-001-2", "action": "AUDIENCE_INFER", "route_id": "ROUTE-CAMPAIGN-AUDIENCE-001", "front_block_id": "FRONT-CAMPAIGN-AUDIENCE-001"},
    "campaign_variant": {"flow_id": "FLOW-001", "step_id": "FLOW-001-3", "action": "VARIANT_PLAN", "route_id": "ROUTE-CAMPAIGN-VARIANT-001", "front_block_id": "FRONT-CAMPAIGN-VARIANT-001"},
    "campaign_story_state": {"flow_id": "FLOW-001", "step_id": "FLOW-001-4", "action": "STATE_PLAN", "route_id": "ROUTE-CAMPAIGN-STATE-001", "front_block_id": "FRONT-CAMPAIGN-STATE-001"},
    "campaign_format": {"flow_id": "FLOW-001", "step_id": "FLOW-001-5", "action": "FORMAT_PLAN", "route_id": "ROUTE-CAMPAIGN-FORMAT-001", "front_block_id": "FRONT-CAMPAIGN-FORMAT-001"},
    "campaign_caption": {"flow_id": "FLOW-001", "step_id": "FLOW-001-6", "action": "CAPTION_PLAN", "route_id": "ROUTE-CAMPAIGN-CAPTION-001", "front_block_id": "FRONT-CAMPAIGN-CAPTION-001"},
    "campaign_orchestrator": {"flow_id": "FLOW-001", "step_id": "FLOW-001-9", "action": "CAMPAIGN_OUTPUT", "route_id": "ROUTE-CAMPAIGN-ORCH-001", "front_block_id": "FRONT-CAMPAIGN-ORCH-001"},
    "image_engine": {"flow_id": "FLOW-002", "step_id": "FLOW-002-4", "action": "IMAGE_OUTPUT", "route_id": "ROUTE-IMAGE-ENGINE-001", "front_block_id": "FRONT-IMAGE-ENGINE-001"},
    "video_engine": {"flow_id": "FLOW-003", "step_id": "FLOW-003-4", "action": "VIDEO_PLAN_OUTPUT", "route_id": "ROUTE-VIDEO-ENGINE-001", "front_block_id": "FRONT-VIDEO-ENGINE-001"},
    "video_engine_smoke": {"flow_id": "FLOW-003", "step_id": "FLOW-003-5", "action": "VIDEO_ENGINE_SMOKE", "route_id": "ROUTE-VIDEO-ENGINE-SMOKE-001", "front_block_id": "FRONT-VIDEO-ENGINE-SMOKE-001"},
    "image_to_video": {"flow_id": "FLOW-004", "step_id": "FLOW-004-3", "action": "IMAGE_TO_VIDEO_CONNECT", "route_id": "ROUTE-IMAGE-VIDEO-001", "front_block_id": "FRONT-IMAGE-VIDEO-001"},
    "final_render": {"flow_id": "FLOW-005", "step_id": "FLOW-005-3", "action": "FINAL_RENDER", "route_id": "ROUTE-FINAL-RENDER-001", "front_block_id": "FRONT-FINAL-RENDER-001"},
    "self_run_enqueue": {"flow_id": "FLOW-006", "step_id": "FLOW-006-1", "action": "SELF_RUN_ENQUEUE", "route_id": "ROUTE-SELF-RUN-ENQUEUE-001", "front_block_id": "FRONT-SELF-RUN-ENQUEUE-001"},
    "self_run_worker": {"flow_id": "FLOW-006", "step_id": "FLOW-006-2", "action": "SELF_RUN_WORKER", "route_id": "ROUTE-SELF-RUN-WORKER-001", "front_block_id": "FRONT-SELF-RUN-WORKER-001"},
    "self_run_status": {"flow_id": "FLOW-006", "step_id": "FLOW-006-3", "action": "SELF_RUN_STATUS", "route_id": "ROUTE-SELF-RUN-STATUS-001", "front_block_id": "FRONT-SELF-RUN-STATUS-001"},
}

def build_execution_identity(key: str) -> Dict[str, str]:
    return dict(FLOW_REGISTRY[key])
