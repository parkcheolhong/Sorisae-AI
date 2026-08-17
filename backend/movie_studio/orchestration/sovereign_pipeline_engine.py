from __future__ import annotations

from typing import Dict, List


def build_sovereign_pipeline_contract(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "external_dependency_allowed": False,
        "business_model_policy": "no external platform lock-in",
        "cost_control_policy": "gpu-capex-first, api-opex-disallowed",
        "survival_policy": "service must continue without external vendor availability",
        "coexistence_policy": "partnership allowed only when control remains internal",
        "governance_rules": [
            "core generation must stay self-hosted",
            "quality gate must stay self-hosted",
            "final editorial decisions must remain internal",
            "model replacement rights must remain internal",
            "external services cannot become mandatory for product operation",
        ],
        "gpu_scale_plan": {
            "current_targets": [str(item).strip() for item in list(payload.get("gpu_targets") or ["nvidia-rtx-primary"]) if str(item).strip()],
            "expansion_ready": True,
            "offline_operation_required": True,
        },
    }
