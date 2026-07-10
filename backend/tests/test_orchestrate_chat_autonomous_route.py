"""G-1-1: Admin orchestrate/chat → autonomous surface routing."""
from __future__ import annotations

from starlette.requests import Request

from backend.orchestrator.autonomous.surface_adapter import should_route_orchestrator_chat_to_autonomous
from backend.orchestrator.chat.models import OrchestratorChatRequest


def _request(path: str = "/api/llm/orchestrate/chat") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 1234),
        }
    )


def test_should_route_manual_mode_to_autonomous():
    request = OrchestratorChatRequest(
        message="설계해줘",
        mode="manual_9step",
        manual_mode=True,
    )
    assert should_route_orchestrator_chat_to_autonomous(request, _request()) is True


def test_should_not_route_lightweight_to_autonomous():
    request = OrchestratorChatRequest(
        message="ping",
        lightweight=True,
        manual_mode=True,
    )
    assert should_route_orchestrator_chat_to_autonomous(request, _request()) is False


def test_should_not_route_light_path_to_autonomous():
    request = OrchestratorChatRequest(
        message="ping",
        manual_mode=True,
    )
    assert should_route_orchestrator_chat_to_autonomous(
        request,
        _request("/api/llm/orchestrate/chat/light"),
    ) is False


def test_should_not_route_reverse_question_to_autonomous():
    request = OrchestratorChatRequest(
        message="기술 후보 비교해줘",
        manual_mode=True,
        conversation_mode="reverse_question",
    )
    assert should_route_orchestrator_chat_to_autonomous(request, _request()) is False


def test_should_route_manual_10step_marketplace_mode():
    request = OrchestratorChatRequest(
        message="4단계 Redis 캐시 아이디어 제안해줘",
        mode="manual_10step",
        manual_mode=True,
    )
    assert should_route_orchestrator_chat_to_autonomous(request, _request()) is True
