"""Orchestrate voice STT context_tags → diagnostics schema regression."""

from __future__ import annotations

import pytest

import backend.orchestrator.autonomous.router as autonomous_router_module
from backend.orchestrator.autonomous.surface_adapter import run_autonomous_surface_chat


@pytest.mark.asyncio
async def test_voice_context_tags_surface_diagnostics(tmp_path, monkeypatch):
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
        message="4단계 Redis 캐시 아이디어",
        owner_id="admin-1",
        surface="admin",
        task="voice-orchestrate",
        mode="manual_9step",
        manual_mode=True,
        context_tags=["admin-orchestrator", "voice-stt", "voice-entry"],
    )

    diagnostics = response.diagnostics
    assert diagnostics["context_tags"] == ["admin-orchestrator", "voice-stt", "voice-entry"]
    assert diagnostics["voice_entry"] is True
    assert diagnostics["voice_speaker"] == "관리자(음성)"
    assert diagnostics["voice_context_tags"] == ["voice-stt", "voice-entry"]
    assert any(item.speaker == "관리자(음성)" for item in response.conversation if item.role == "user")


@pytest.mark.asyncio
async def test_voice_context_tags_marketplace_surface(tmp_path, monkeypatch):
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
        message="진행해",
        owner_id="customer-1",
        surface="marketplace",
        task="customer-product",
        project_name="customer-product",
        mode="manual_10step",
        manual_mode=True,
        context_tags=["customer-orchestrator", "voice-stt", "voice-entry"],
    )

    diagnostics = response.diagnostics
    assert diagnostics["voice_entry"] is True
    assert diagnostics["voice_speaker"] == "고객(음성)"
    assert any(item.speaker == "고객(음성)" for item in response.conversation if item.role == "user")
