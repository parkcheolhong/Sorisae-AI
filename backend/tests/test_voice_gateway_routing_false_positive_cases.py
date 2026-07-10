from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from backend.llm.voice_gateway import (
    _friend_is_nearby_transcript,
    _friend_is_overview_transcript,
    _friend_prefers_far_first,
)


CASES_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "voice_gateway_routing_false_positive_cases.json"
)
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _expected_flags(route: str) -> tuple[bool, bool, bool]:
    nearby = route == "nearby"
    overview = route == "overview"
    far_first = route in {"overview", "far_first"}
    return nearby, overview, far_first


def test_routing_false_positive_casefile_has_required_50_cases() -> None:
    counts = Counter(case["expected_route"] for case in CASES)
    assert len(CASES) == 50
    assert counts == {
        "nearby": 15,
        "overview": 15,
        "far_first": 10,
        "neutral": 10,
    }


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_routing_false_positive_regression_cases(case: dict[str, str]) -> None:
    transcript = case["transcript"]
    expected_nearby, expected_overview, expected_far_first = _expected_flags(
        case["expected_route"]
    )

    nearby = _friend_is_nearby_transcript(transcript)
    overview = _friend_is_overview_transcript(transcript)
    far_first = _friend_prefers_far_first(transcript, nearby)

    assert nearby is expected_nearby
    assert overview is expected_overview
    assert far_first is expected_far_first
