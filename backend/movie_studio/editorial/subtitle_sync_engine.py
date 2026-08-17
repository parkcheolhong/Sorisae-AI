from __future__ import annotations

from typing import Dict, List


def build_subtitle_sync(lines: List[str]) -> Dict[str, object]:
    return {
        "line_count": len(lines),
        "rules": [
            "subtitle timing must not cover the face excessively",
            "subtitle rhythm should support editorial pacing",
        ],
    }
