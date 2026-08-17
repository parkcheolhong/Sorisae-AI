from __future__ import annotations

import httpx

from backend.llm.voice_gateway import _friend_chat_base_url


def test_friend_chat_base_url_falls_back_when_dedicated_base_is_unreachable(monkeypatch):
    monkeypatch.setenv("LLM_VOICE_FRIEND_BASE_URL", "http://host.docker.internal:8009/v1")
    monkeypatch.setenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1")

    def fake_get(url: str, timeout: float = 5):  # noqa: ARG001
        if url.startswith("http://host.docker.internal:8009/v1/models"):
            raise httpx.ConnectError("boom", request=None)
        raise AssertionError(f"unexpected probe url: {url}")

    monkeypatch.setattr("httpx.get", fake_get)

    assert _friend_chat_base_url() == "http://host.docker.internal:8008/v1"
