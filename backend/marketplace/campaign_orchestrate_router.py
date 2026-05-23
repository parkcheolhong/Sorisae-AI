from typing import Any

from fastapi import APIRouter, Depends, HTTPException


def build_campaign_orchestrate_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.post("/campaign-orchestrate/plan")
    def create_campaign_plan(
        request: contract.CampaignPlanRequest,
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        del current_user
        payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        try:
            result = contract.plan_local_campaign(payload)
            return {
                "success": True,
                "campaign_plan": result,
            }
        except Exception as exc:
            contract.logger.error("[campaign-orchestrate] plan_local_campaign failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"캠페인 계획 생성 실패: {exc}") from exc

    @router.get("/campaign-orchestrate/strategies")
    def get_campaign_strategies() -> dict[str, Any]:
        from .ad_strategy_engine import STRATEGY_KEYWORDS
        from .campaign_common import ACTION_KEYWORDS, EMOTION_KEYWORDS, LOCATION_KEYWORDS, ROLE_KEYWORDS

        return {
            "strategies": list(STRATEGY_KEYWORDS.keys()),
            "role_types": list(ROLE_KEYWORDS.keys()),
            "location_types": list(LOCATION_KEYWORDS.keys()),
            "emotions": list(EMOTION_KEYWORDS.keys()),
            "actions": list(ACTION_KEYWORDS.keys()),
            "campaign_goals": ["conversion", "awareness", "branding", "engagement", "traffic"],
        }

    return router