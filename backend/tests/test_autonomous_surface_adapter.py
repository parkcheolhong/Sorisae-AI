"""① surface_adapter — 관리자·마켓 대화창 SSOT 통합 테스트."""
from __future__ import annotations

import pytest

import backend.orchestrator.autonomous.router as autonomous_router_module
from backend.orchestrator.autonomous.surface_adapter import (
    orchestration_payload_to_response,
    resolve_autonomous_mode,
    run_autonomous_surface_chat,
    run_autonomous_surface_execution,
)


@pytest.mark.parametrize(
    ("mode", "manual_mode", "expected"),
    [
        ("full", True, "full_auto"),
        ("full_auto", False, "full_auto"),
        ("advisory", True, "advisory"),
        ("manual_10step", True, "semi_auto"),
        ("manual_9step", True, "semi_auto"),
    ],
)
def test_resolve_autonomous_mode(mode, manual_mode, expected):
    assert resolve_autonomous_mode(mode=mode, manual_mode=manual_mode) == expected


@pytest.mark.asyncio
async def test_run_autonomous_surface_chat_greeting(tmp_path, monkeypatch):
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
        message="안녕하세요",
        owner_id="user-7",
        surface="marketplace",
        task="customer-product",
        project_name="customer-product",
        mode="manual_10step",
        manual_mode=True,
        context_tags=["customer"],
    )

    assert response.session_id
    assert response.reply.content
    assert response.diagnostics["orchestrator_core"] == "autonomous_turn_controller"
    assert response.diagnostics["surface"] == "marketplace"
    assert response.reply.speaker == "오케스트레이터"
    assert any(item.speaker == "고객" for item in response.conversation if item.role == "user")


@pytest.mark.asyncio
async def test_run_autonomous_surface_chat_code_generation_requires_approval(tmp_path, monkeypatch):
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
        message="FastAPI로 블로그 API 만들어줘",
        owner_id="admin-1",
        surface="admin",
        task="blog-api",
        mode="manual_9step",
        manual_mode=True,
    )

    assert response.diagnostics["autonomous_intent"] == "task_registered"
    assert response.conversation_stage == "idle"
    assert "설계해줘" in response.reply.content


@pytest.mark.asyncio
async def test_run_autonomous_surface_execution_full_auto(tmp_path, monkeypatch):
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

    from types import SimpleNamespace

    request = SimpleNamespace(
        task="FastAPI 헬스체크 API 만들어줘",
        mode="full",
        project_name="stream-test",
        output_dir=str(tmp_path / "output"),
        run_id="run-stream-test",
    )
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)

    payload = await run_autonomous_surface_execution(
        request,
        owner_id="customer-9",
    )

    assert payload["diagnostics"]["orchestrator_core"] == "autonomous_turn_controller"
    assert payload["completion_judge"]["orchestrator_core"] == "autonomous_turn_controller"
    assert payload["run_id"] == "run-stream-test"
    assert payload["pipeline"][0] == "autonomous_turn_controller"


def test_orchestration_payload_to_response_maps_admin_shape():
    payload = {
        "task": "hello-api",
        "mode": "full_auto",
        "run_id": "run-admin-1",
        "pipeline": ["autonomous_turn_controller"],
        "results": [{"agent": "coder", "output": "print('ok')"}],
        "final_output": "print('ok')",
        "applied": False,
        "written_files": [],
        "postcheck_ran": True,
        "postcheck_ok": True,
        "completion_gate_ok": True,
        "completion_summary": "done",
        "completion_judge": {"orchestrator_core": "autonomous_turn_controller"},
    }

    response = orchestration_payload_to_response(payload)

    assert response.task == "hello-api"
    assert response.run_id == "run-admin-1"
    assert len(response.results) == 1
    assert response.results[0].agent == "coder"
    assert response.results[0].model == "autonomous"
    assert response.completion_judge["orchestrator_core"] == "autonomous_turn_controller"

