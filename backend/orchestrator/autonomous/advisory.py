"""① discuss intent — 협업·기술 제안 advisory 필드 (② chat_service 로직 SSOT re-export)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.orchestrator.chat.chat_service import (
    build_clarification_questions,
    build_evidence_highlights,
    build_new_technology_candidates,
    build_proposal_items,
    build_technology_recommendations,
)
from backend.orchestrator.chat.models import AdvisoryEvidenceItem, WebGroundingItem
from backend.orchestrator.chat.web_search import (
    build_web_grounding_block,
    fetch_web_grounding,
    should_use_web_search,
)

logger = logging.getLogger(__name__)

DEFAULT_ADVISORY_CONTROLS: Dict[str, Any] = {
    "clarification_questions_enabled": True,
    "max_clarification_questions": 3,
    "systems_thinking_enabled": True,
    "evidence_panel_enabled": True,
    "scientific_reasoning_enabled": True,
    "max_evidence_items": 5,
}


def _conversation_stage_for_stage_number(stage_number: Optional[float]) -> str:
    if stage_number is None:
        return "implementation"
    if stage_number >= 8:
        return "operations"
    if stage_number >= 4:
        return "implementation"
    return "architecture"


def _message_kind(message: str) -> str:
    text = str(message or "").strip()
    if text.startswith("/ask") or "?" in text:
        return "question"
    if text.startswith(("/search", "/news")):
        return "question"
    return "dialogue"


def _normalize_web_results(raw: Optional[List[Any]]) -> List[WebGroundingItem]:
    items: List[WebGroundingItem] = []
    for entry in raw or []:
        if isinstance(entry, WebGroundingItem):
            items.append(entry)
        elif isinstance(entry, dict):
            items.append(WebGroundingItem(**entry))
    return items


def fetch_discuss_web_context(message: str) -> Dict[str, Any]:
    """discuss · /search · /news — web grounding (G-2-2-1)."""
    message_kind = _message_kind(message)
    if not should_use_web_search(message, message_kind):
        return {
            "web_results": [],
            "web_grounding_block": "",
            "web_grounding_used": False,
        }
    web_results = fetch_web_grounding(
        message,
        max_items=5,
        timeout_sec=8.0,
        logger=logger,
    )
    return {
        "web_results": [item.model_dump() for item in web_results],
        "web_grounding_block": build_web_grounding_block(web_results),
        "web_grounding_used": bool(web_results),
    }


def build_web_evidence_highlights(
    web_results: List[WebGroundingItem],
    *,
    conversation_stage: str,
    advisory_controls: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    controls = {**DEFAULT_ADVISORY_CONTROLS, **(advisory_controls or {})}
    highlights: List[AdvisoryEvidenceItem] = []
    for item in web_results[:3]:
        highlights.append(
            AdvisoryEvidenceItem(
                title=str(item.title or "웹 검색 결과")[:120],
                source_label=str(item.domain or item.source_type or "web"),
                source_type="web-search",
                trust_score=float(item.trust_score or 0.7),
                why_it_matters=str(item.snippet or "")[:240],
                url=item.url,
            )
        )
    highlights.extend(
        build_evidence_highlights(
            conversation_stage=conversation_stage,
            advisory_controls=controls,
        )
    )
    limit = max(0, int(controls.get("max_evidence_items", 5) or 0))
    return [item.model_dump() for item in highlights[:limit]]


def build_discuss_advisory_payload(
    message: str,
    reply_content: str,
    *,
    stage_number: Optional[float] = None,
    advisory_controls: Optional[Dict[str, Any]] = None,
    web_results: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """discuss 턴 proposal/technology/clarification/evidence 필드 — surface_adapter mapper 입력."""
    controls = {**DEFAULT_ADVISORY_CONTROLS, **(advisory_controls or {})}
    conversation_stage = _conversation_stage_for_stage_number(stage_number)
    message_kind = _message_kind(message)
    normalized_web_results = _normalize_web_results(web_results)
    candidates = build_new_technology_candidates(message, conversation_stage)
    proposals = build_proposal_items(
        message,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
    )
    clarifications = build_clarification_questions(
        message,
        conversation_stage=conversation_stage,
        message_kind=message_kind,
        advisory_controls=controls,
    )
    technology = build_technology_recommendations(
        message,
        reply_content,
        web_results=normalized_web_results,
        fallback_candidates=candidates,
    )
    evidence_highlights = build_web_evidence_highlights(
        normalized_web_results,
        conversation_stage=conversation_stage,
        advisory_controls=controls,
    )
    return {
        "proposal_items": [item.model_dump() for item in proposals],
        "new_technology_candidates": candidates,
        "technology_recommendations": [item.model_dump() for item in technology],
        "clarification_questions": [item.model_dump() for item in clarifications],
        "evidence_highlights": evidence_highlights,
        "web_results": [item.model_dump() for item in normalized_web_results],
        "web_grounding_used": bool(normalized_web_results),
    }
