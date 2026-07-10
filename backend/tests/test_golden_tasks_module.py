"""Async golden_tasks probes against in-process ASGI app."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.orchestrator.autonomous import golden_tasks as golden_tasks_module
from backend.tests.test_golden_tasks import _FakeTranslator


def _build_asgi_app():
    from fastapi import FastAPI

    from backend.llm.router import router as llm_router
    from backend.tests.test_nadotongryoksa_friends_and_voip_contract import _build_client

    voip_app = _build_client().app
    app = FastAPI()
    for route in voip_app.routes:
        app.routes.append(route)
    app.dependency_overrides.update(voip_app.dependency_overrides)
    app.include_router(llm_router)
    return app


@pytest.mark.asyncio
async def test_golden_g2_subtasks_without_jwt(monkeypatch):
    app = _build_asgi_app()
    monkeypatch.setattr(
        "backend.services.nadotongryoksa.translator.NadoTranslator.get_instance",
        lambda: _FakeTranslator(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        voice = await golden_tasks_module._probe_voice_translate_smoke(client)
        health = await golden_tasks_module._probe_voip_health(client)
        initiate = await golden_tasks_module._probe_voip_initiate(client, headers={})
        markers = await golden_tasks_module._probe_voice_openapi_markers(client)

    assert voice["ok"] is True
    assert health["ok"] is True
    assert initiate.get("skipped") is True
    assert markers["ok"] is True


@pytest.mark.asyncio
async def test_golden_voip_initiate_probe_with_auth():
    app = _build_asgi_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initiate = await golden_tasks_module._probe_voip_initiate(
            client,
            headers={"Authorization": "Bearer stub"},
        )

    assert initiate.get("skipped") is not True
    assert initiate.get("ok") is True
    assert "call_id=" in str(initiate.get("detail") or "")
