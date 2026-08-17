from __future__ import annotations

from typing import Dict, List

from .campaign_common import infer_action_type, normalize_text
from .execution_flow_registry import build_execution_identity


def infer_audience_profiles(payload: Dict[str, object]) -> Dict[str, object]:
    scenario_script = normalize_text(str(payload.get("scenario_script") or ""))
    audience_input = [normalize_text(str(item)) for item in list(payload.get("audience_input") or []) if normalize_text(str(item))]
    action_type = infer_action_type(scenario_script)
    profiles: List[Dict[str, object]] = []
    if audience_input:
        for index, item in enumerate(audience_input, start=1):
            profiles.append({
                "id": f"custom-{index:02d}",
                "label": item,
                "intent": "custom",
                "pain_points": ["사용자 직접 지정 타깃"],
                "tone": "adaptive",
                "cta_style": "adaptive",
            })
    else:
        profiles.append({
            "id": "broad-mass",
            "label": "범용 대중 타깃",
            "intent": "broad",
            "pain_points": ["짧은 시간 내 이해", "빠른 흥미 유도"],
            "tone": "clear",
            "cta_style": "simple",
        })
        if action_type in {"eat_drink", "react"}:
            profiles.append({
                "id": "impulse-shortform",
                "label": "충동형 숏폼 타깃",
                "intent": "impulse-buy",
                "pain_points": ["즉시 반응 필요", "비주얼 임팩트 중요"],
                "tone": "fast",
                "cta_style": "compressed",
            })
        if action_type in {"call", "showcase", "problem_solution"}:
            profiles.append({
                "id": "problem-solution",
                "label": "문제 해결형 타깃",
                "intent": "practical",
                "pain_points": ["문제 인지", "해결 근거 필요"],
                "tone": "informative",
                "cta_style": "reasoned",
            })
    return {
        "profiles": profiles,
        "execution": build_execution_identity("campaign_audience"),
    }
