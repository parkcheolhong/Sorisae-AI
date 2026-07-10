"""① autonomous path dialogue/session tests (G-2-3-3).

Legacy ② `chat_service.answer_orchestrator_chat` dialogue tests remain in
`test_orchestrator_dialogue_mode.py` with `@pytest.mark.legacy_chat_service`.
`reverse_question` stays on ② by design (`should_route_orchestrator_chat_to_autonomous`).
"""
from __future__ import annotations

import pytest

import backend.orchestrator.autonomous.router as autonomous_router_module
from backend.orchestrator.autonomous.surface_adapter import run_autonomous_surface_chat


@pytest.mark.asyncio
async def test_autonomous_session_restore_conversation(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("AUTONOMOUS_MAX_STAGES_PER_TURN", "1")
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )
    monkeypatch.setattr(
        autonomous_router_module,
        "_build_llm_call",
        lambda: (None, {}),
    )

    first = await run_autonomous_surface_chat(
        message="첫 결정은 실행을 승인 후에만 시작하는 것입니다.",
        owner_id="owner-a",
        surface="admin",
        task="dialogue-autonomous",
        mode="manual_10step",
        manual_mode=True,
        conversation=[{"role": "user", "content": "첫 결정은 실행을 승인 후에만 시작하는 것입니다."}],
    )
    session_id = first.session_id
    assert session_id

    second = await run_autonomous_surface_chat(
        message="이전 결정을 이어서 기술 후보를 정리해줘",
        owner_id="owner-a",
        surface="admin",
        session_id=session_id,
        task="dialogue-autonomous",
        mode="manual_10step",
        manual_mode=True,
        conversation=[
            {"role": "user", "content": "첫 결정은 실행을 승인 후에만 시작하는 것입니다."},
            {"role": "assistant", "content": first.reply.content},
            {"role": "user", "content": "이전 결정을 이어서 기술 후보를 정리해줘"},
        ],
    )

    joined = "\n".join(item.content for item in second.conversation)
    assert "첫 결정은 실행을 승인 후에만 시작" in joined
    assert second.diagnostics["orchestrator_core"] == "autonomous_turn_controller"


@pytest.mark.asyncio
async def test_marketplace_surface_manual_chat_orchestrator_core(tmp_path, monkeypatch):
    """DoD-1: Marketplace customer-orchestrate path → autonomous_turn_controller."""
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("AUTONOMOUS_MAX_STAGES_PER_TURN", "1")
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )
    monkeypatch.setattr(
        autonomous_router_module,
        "_build_llm_call",
        lambda: (None, {}),
    )

    response = await run_autonomous_surface_chat(
        message="4단계 Redis 캐시 아이디어 제안해줘",
        owner_id="marketplace-owner",
        surface="marketplace",
        task="dod1-marketplace-probe",
        mode="manual_10step",
        manual_mode=True,
        conversation=[{"role": "user", "content": "4단계 Redis 캐시 아이디어 제안해줘"}],
    )
    assert response.diagnostics["orchestrator_core"] == "autonomous_turn_controller"


@pytest.mark.asyncio
async def test_autonomous_session_owner_scoped(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("AUTONOMOUS_MAX_STAGES_PER_TURN", "1")
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )
    monkeypatch.setattr(
        autonomous_router_module,
        "_build_llm_call",
        lambda: (None, {}),
    )

    first = await run_autonomous_surface_chat(
        message="owner-a의 이전 결정입니다.",
        owner_id="owner-a",
        surface="admin",
        task="dialogue-owner",
        mode="manual_10step",
        manual_mode=True,
        conversation=[{"role": "user", "content": "owner-a의 이전 결정입니다."}],
    )
    response = await run_autonomous_surface_chat(
        message="owner-b 기준으로 이어서 설명해줘",
        owner_id="owner-b",
        surface="admin",
        session_id=first.session_id,
        task="dialogue-owner",
        mode="manual_10step",
        manual_mode=True,
        conversation=[{"role": "user", "content": "owner-b 기준으로 이어서 설명해줘"}],
    )

    joined = "\n".join(item.content for item in response.conversation)
    assert "owner-a의 이전 결정입니다." not in joined


def test_reverse_question_routes_to_legacy_chat_service():
    from backend.orchestrator.autonomous.surface_adapter import should_route_orchestrator_chat_to_autonomous
    from backend.orchestrator.chat.models import OrchestratorChatRequest
    from starlette.requests import Request

    request = OrchestratorChatRequest(
        message="역질문 테스트",
        conversation_mode="reverse_question",
        manual_mode=True,
        mode="manual_10step",
    )
    http_request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/llm/orchestrate/chat",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 1234),
        }
    )
    assert should_route_orchestrator_chat_to_autonomous(request, http_request) is False
