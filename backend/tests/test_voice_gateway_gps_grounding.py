import sys
from types import ModuleType

from backend.llm.voice_gateway import _friend_fetch_index_grounding


def test_index_grounding_formats_distance_proximity_and_direction_and_prioritizes_nearby(monkeypatch):
    fake_module = ModuleType("backend.services.tourism_kb")

    def _fake_search_tourism_places(query, limit, latitude=None, longitude=None, country_code=None):
        return [
            {
                "name": "Far Museum",
                "address": "Far road 1",
                "lat": 37.95,
                "lon": 127.25,
                "category": "museum",
            },
            {
                "name": "Near Cafe",
                "address": "Near street 2",
                "lat": 37.5669,
                "lon": 126.9785,
                "category": "cafe",
            },
        ]

    fake_module.search_tourism_places = _fake_search_tourism_places  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backend.services.tourism_kb", fake_module)

    block = _friend_fetch_index_grounding(
        "카페 추천",
        latitude=37.5665,
        longitude=126.9780,
        max_items=5,
        country_code="KR",
        prefer_far_first=True,
    )

    lines = [line for line in block.splitlines() if line.startswith("-")]
    assert lines, "grounding lines should exist"
    # 로컬 좌표가 있으면 far-first 요청이 있어도 near-first를 우선한다.
    assert lines[0].startswith("- Near Cafe")
    assert "거리:" in lines[0]
    assert "근접도:" in lines[0]
    assert "방향:" in lines[0]
