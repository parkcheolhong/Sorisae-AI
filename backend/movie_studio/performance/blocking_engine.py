from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.performance_contract import PerformanceBeatContract


def build_blocking_plan(sequence_plan: List[Dict[str, object]], actor_id: str) -> List[PerformanceBeatContract]:
    return [
        PerformanceBeatContract(
            beat_id=f"{item['sequence_id']}-perf-01",
            actor_id=actor_id,
            action=str(item.get("objective") or "hero blocking").strip() or "hero blocking",
            gesture="motivated hand and arm gesture progression",
            eye_line="camera-primary with target-reactive gaze shifts",
            emotional_intent=str(item.get("emotional_state") or "controlled realism").strip() or "controlled realism",
            cta_strength="high" if item.get("cta_required") else "medium",
            walking_pattern="full-body motivated walking with weight transfer and stride continuity",
            speaking_mode="spoken performance with visible facial articulation",
            lip_sync_requirement="mouth shape progression required across speaking beats",
            performance_unit="full_body_human_motion",
        )
        for item in sequence_plan
    ]
