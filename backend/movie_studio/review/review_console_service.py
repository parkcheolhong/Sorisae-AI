from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.review_contract import ReviewDecisionContract


def build_review_items(scene_ids: List[str]) -> List[ReviewDecisionContract]:
    return [
        ReviewDecisionContract(
            review_id=f"review-{index+1:02d}",
            scene_id=scene_id,
            status="pending",
            notes=[],
            rerender_requested=False,
        )
        for index, scene_id in enumerate(scene_ids)
    ]
