"""A-4-2: /api/llm/autonomous/* HTTP 레벨 테스트 (FastAPI TestClient)."""
from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
import backend.orchestrator.autonomous.router as autonomous_router_module
from backend.security_gates import require_llm_mutation_quota

TEST_USER = SimpleNamespace(
    id=42,
    email="orch@example.com",
    username="orch_user",
    is_active=True,
    is_admin=True,
)


def _build_client(tmp_path, monkeypatch) -> TestClient:
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

    app = FastAPI()
    app.include_router(autonomous_router_module.router)

    def _current_user():
        return TEST_USER

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[require_llm_mutation_quota] = _current_user
    return TestClient(app)


def test_chat_greeting_creates_session(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "안녕하세요", "mode": "semi_auto"},
    )
    assert response.status_code == 200, response.text
    assert response.headers.get("X-Orchestrator-Api-Tier") == "debug-internal"
    assert response.headers.get("X-Orchestrator-Preferred-Endpoint") == "/api/llm/orchestrate/chat"
    payload = response.json()
    assert payload["intent"] == "greeting"
    assert payload["session_id"]
    assert "멀티 에이전트" in payload["content"]


def test_chat_code_generation_semi_auto_registers_task_only(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["intent"] == "task_registered"
    assert payload["requires_approval"] is False
    assert payload["execution_state"] == "idle"
    assert payload["stages_total"] == 11
    assert payload["agent_results"] == []


def test_chat_design_after_task_registration(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    first = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    session_id = first.json()["session_id"]

    second = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "설계해줘", "session_id": session_id, "mode": "semi_auto"},
    )
    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["intent"] == "stage_design"
    assert payload["requires_approval"] is True


def test_chat_approval_happy_path(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    first = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    assert first.status_code == 200, first.text
    session_id = first.json()["session_id"]

    client.post(
        "/api/llm/autonomous/chat",
        json={"message": "설계해줘", "session_id": session_id, "mode": "semi_auto"},
    )

    second = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "승인", "session_id": session_id, "mode": "semi_auto"},
    )
    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["intent"] == "approval"
    agents = {item["agent"] for item in payload["agent_results"]}
    assert "coder" in agents
    assert "validator" in agents


def test_get_session_status_after_task_registration(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    created = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    status = client.get(f"/api/llm/autonomous/session/{session_id}")
    assert status.status_code == 200, status.text
    payload = status.json()
    assert payload["session_id"] == session_id
    assert payload["mode"] == "semi_auto"
    assert payload["approval_state"] == "none"
    assert len(payload["stages"]) == 11
    assert payload["conversation_length"] >= 1
    assert payload["agent_result_count"] == 0


def test_chat_unknown_session_returns_404(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/llm/autonomous/chat",
        json={
            "message": "승인",
            "session_id": "0000000000000000",
            "mode": "semi_auto",
        },
    )
    assert response.status_code == 404


def test_get_session_status_unknown_returns_404(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.get("/api/llm/autonomous/session/0000000000000000")
    assert response.status_code == 404


def test_chat_full_auto_skips_approval(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "full_auto"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["requires_approval"] is False
    agents = {item["agent"] for item in payload["agent_results"]}
    assert "coder" in agents


def test_chat_rejection_replans_semi_auto(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    first = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    session_id = first.json()["session_id"]
    client.post(
        "/api/llm/autonomous/chat",
        json={"message": "설계해줘", "session_id": session_id, "mode": "semi_auto"},
    )

    second = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "거절", "session_id": session_id, "mode": "semi_auto"},
    )
    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["intent"] == "rejection"
    assert payload["approval_state"] == "pending"
    assert payload["execution_state"] == "awaiting_approval"


def test_chat_returns_llm_connected_and_stages_remaining(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/llm/autonomous/chat",
        json={"message": "FastAPI로 블로그 만들어줘", "mode": "semi_auto"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["llm_connected"] is False
    assert payload["stages_remaining"] == 11
    assert payload["intent"] == "task_registered"
