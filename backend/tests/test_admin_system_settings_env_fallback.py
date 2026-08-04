from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import admin_router as admin_router_module
from backend.admin_router import router as admin_router


def _build_client(tmp_path) -> TestClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[admin_router_module.require_admin] = lambda: SimpleNamespace(
        id=1,
        email="admin@test.local",
        is_admin=True,
        is_superuser=True,
    )
    admin_router_module._ADMIN_SYSTEM_SETTINGS_CACHE.clear()
    admin_router_module._admin_workspace_root = lambda: tmp_path
    return TestClient(app)


def test_admin_system_settings_returns_payload_without_env_file(tmp_path):
    client = _build_client(tmp_path)

    response = client.get("/api/admin/system-settings")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["env_path"].endswith(".env")
    assert payload["env_path"].startswith(str(tmp_path))
    assert payload["sections"]
    assert payload["runtime_config_path"].endswith("orchestrator_runtime_config.json")


def test_admin_system_settings_fill_missing_defaults_creates_env_file(tmp_path):
    client = _build_client(tmp_path)

    response = client.post("/api/admin/system-settings/fill-missing-defaults")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["env_path"].endswith(".env")
    assert payload["applied_env_update_count"] >= 0
    assert (tmp_path / ".env").exists()
