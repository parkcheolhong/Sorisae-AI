from __future__ import annotations

from typing import Dict, List

from .campaign_common import infer_action_type, infer_emotion, infer_location_type, infer_object_type, infer_role_type, normalize_text, split_sentences
from .execution_flow_registry import build_execution_identity


def build_story_states(payload: Dict[str, object], variant_plan: Dict[str, object]) -> Dict[str, object]:
    scenario_script = normalize_text(str(payload.get("scenario_script") or ""))
    sentences = split_sentences(scenario_script) or [scenario_script]
    variants = list(variant_plan.get("variants") or [])
    sections: List[Dict[str, object]] = []
    for index, sentence in enumerate(sentences, start=1):
        sections.append({
            "section_id": f"section-{index:02d}",
            "title": f"상태 섹션 {index}",
            "role_type": infer_role_type(sentence),
            "object_type": infer_object_type(sentence),
            "location_type": infer_location_type(sentence),
            "emotion": infer_emotion(sentence),
            "action": infer_action_type(sentence),
            "camera_style": "adaptive_dynamic",
            "lighting_style": "adaptive_scene",
            "continuity_rule": "identity_lock 대신 story_flow 유지",
            "allowed_changes": ["actor", "object", "background", "camera", "lighting"],
            "source_text": sentence,
            "variant_ids": [str(item.get("variant_id")) for item in variants[:3]],
        })
    return {
        "sections": sections,
        "execution": build_execution_identity("campaign_story_state"),
    }
