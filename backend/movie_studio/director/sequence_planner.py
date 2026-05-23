from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.director_contract import DirectorOutputContract


def build_sequence_plan(director_output: DirectorOutputContract) -> List[Dict[str, object]]:
    return [
        {
            "sequence_id": beat.sequence_id,
            "objective": beat.objective,
            "emotional_state": beat.emotional_state,
            "blocking_summary": beat.blocking_summary,
            "cta_required": beat.cta_required,
            "realism_level": director_output.theme.realism_level,
        }
        for beat in director_output.sequences
    ]
