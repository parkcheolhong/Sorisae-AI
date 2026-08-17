from __future__ import annotations

from typing import Dict, List

from .campaign_common import normalize_text
from .execution_flow_registry import build_execution_identity


STRATEGY_KEYWORDS = {
    "comparison": ["비교", "대신", "더 낫", "차이"],
    "testimonial": ["후기", "리뷰", "추천", "경험"],
    "problem_solution": ["문제", "불편", "해결", "개선"],
    "emotional": ["감성", "추억", "감동", "느낌"],
    "dramatic": ["상황극", "전화", "대화", "오라고", "드라마"],
}


def plan_ad_strategy(payload: Dict[str, object]) -> Dict[str, object]:
    scenario_script = normalize_text(str(payload.get("scenario_script") or ""))
    campaign_goal = normalize_text(str(payload.get("campaign_goal") or "conversion")) or "conversion"
    creative_modes = list(payload.get("creative_modes") or [])
    primary_strategy = "dramatic"
    rationale: List[str] = []
    for strategy, keywords in STRATEGY_KEYWORDS.items():
        if any(keyword in scenario_script for keyword in keywords):
            primary_strategy = strategy
            rationale.append(f"시나리오에 {strategy} 신호가 포함됨")
            break
    if campaign_goal in {"awareness", "branding"} and primary_strategy == "dramatic":
        primary_strategy = "emotional"
        rationale.append("브랜드/인지형 목표이므로 emotional 우선")
    hook_style = "fast_hook" if primary_strategy in {"dramatic", "comparison", "problem_solution"} else "warm_hook"
    alternatives = [strategy for strategy in ["dramatic", "problem_solution", "comparison", "testimonial", "emotional"] if strategy != primary_strategy]
    if creative_modes:
        alternatives = [mode for mode in creative_modes if mode != primary_strategy] + [item for item in alternatives if item not in creative_modes]
    return {
        "primary_strategy": primary_strategy,
        "alternatives": alternatives[:4],
        "hook_style": hook_style,
        "campaign_goal": campaign_goal,
        "rationale": rationale or ["기본 dramatic 전략 적용"],
        "execution": build_execution_identity("campaign_strategy"),
    }
