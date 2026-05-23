from __future__ import annotations

from typing import Dict, List


def select_best_candidate(candidates: List[Dict[str, object]]) -> Dict[str, object]:
    if not candidates:
        return {}
    return max(candidates, key=lambda item: float(item.get("score") or 0.0))
