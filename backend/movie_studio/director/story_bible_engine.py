from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from backend.movie_studio.contracts.director_contract import (
    DirectorOutputContract,
    SequenceBeatContract,
    StoryThemeContract,
)


def build_story_bible(payload: Dict[str, object]) -> DirectorOutputContract:
    title = str(payload.get("title") or "untitled photoreal studio project").strip() or "untitled photoreal studio project"
    synopsis = str(payload.get("synopsis") or payload.get("prompt") or "").strip()
    beats = [
        SequenceBeatContract(
            sequence_id=f"seq-{index+1:02d}",
            objective=objective,
            emotional_state=str(item.get("emotional_state") or "controlled realism").strip() or "controlled realism",
            blocking_summary=str(item.get("blocking_summary") or objective).strip() or objective,
            cta_required=bool(item.get("cta_required", False)),
        )
        for index, item in enumerate(list(payload.get("sequence_beats") or []))
        for objective in [str(item.get("objective") or f"sequence {index+1}: {synopsis or title}").strip() or f"sequence {index+1}: {title}"]
    ]
    if not beats:
        beats = [
            SequenceBeatContract(
                sequence_id="seq-01",
                objective=synopsis or title,
                emotional_state="controlled realism",
                blocking_summary="photoreal main sequence staging",
                cta_required=True,
            )
        ]
    return DirectorOutputContract(
        project_id=str(payload.get("project_id") or f"studio-{uuid4().hex[:12]}"),
        title=title,
        theme=StoryThemeContract(
            genre=str(payload.get("genre") or "commercial cinema"),
            tone=str(payload.get("tone") or "premium photoreal"),
            era=str(payload.get("era") or "contemporary"),
            audience=str(payload.get("audience") or "general"),
            realism_level=str(payload.get("realism_level") or "photoreal"),
        ),
        sequences=beats,
        continuity_rules=list(payload.get("continuity_rules") or [
            "real human face continuity",
            "hand anatomy preservation",
            "environment realism lock",
            "cinematic camera continuity",
        ]),
    )
