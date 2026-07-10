from __future__ import annotations

import pytest

from backend.orchestrator.autonomous.advisory import (
    build_discuss_advisory_payload,
    fetch_discuss_web_context,
)
from backend.orchestrator.chat.models import WebGroundingItem


def test_fetch_discuss_web_context_skips_without_search_signal(monkeypatch):
    monkeypatch.setenv("WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "off")
    payload = fetch_discuss_web_context("4단계 Redis 캐시 아이디어 제안해줘")
    assert payload["web_grounding_used"] is False
    assert payload["web_results"] == []


def test_build_discuss_advisory_payload_includes_web_evidence(monkeypatch):
    sample = WebGroundingItem(
        title="Redis 7.4 release notes",
        url="https://example.com/redis",
        snippet="Redis 7.4 improves cluster failover latency.",
        domain="example.com",
        source_type="web-search-test",
        trust_score=0.8,
    )

    monkeypatch.setattr(
        "backend.orchestrator.autonomous.advisory.fetch_web_grounding",
        lambda *args, **kwargs: [sample],
    )

    payload = build_discuss_advisory_payload(
        "/search Redis cache latest trends",
        "Redis를 캐시 계층으로 두면 API latency를 줄일 수 있습니다.",
        stage_number=4,
        web_results=[sample.model_dump()],
    )
    assert payload["web_grounding_used"] is True
    assert payload["web_results"]
    assert payload["evidence_highlights"]
    assert any(item.get("source_type") == "web-search" for item in payload["evidence_highlights"])
    assert any(item.get("source") == "web" for item in payload["technology_recommendations"])
