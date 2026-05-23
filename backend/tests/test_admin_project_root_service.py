from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import HTTPException

import backend.admin_router as admin_router_module
from backend.admin.orchestrator import project_root_service


def test_resolve_admin_project_root_rejects_empty_by_default():
    with pytest.raises(HTTPException) as exc_info:
        project_root_service.resolve_admin_project_root("")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "project_root가 필요합니다."


def test_resolve_admin_project_root_uses_workspace_root_when_allowed(monkeypatch):
    workspace_root = Path("c:/workspace/codeAI")
    monkeypatch.setattr(project_root_service, "admin_workspace_root", lambda: workspace_root)

    resolved = project_root_service.resolve_admin_project_root("", allow_workspace_default=True)

    assert resolved == workspace_root.resolve()


def test_runtime_verification_route_accepts_empty_project_root(monkeypatch):
    workspace_root = Path("c:/workspace/codeAI")
    captured: dict[str, object] = {}

    app = FastAPI()
    app.include_router(admin_router_module.router)
    app.dependency_overrides[admin_router_module.require_admin] = lambda: SimpleNamespace(id=1, email="ops-admin@example.com", is_admin=True, is_superuser=True)
    app.dependency_overrides[admin_router_module.get_db] = lambda: object()

    monkeypatch.setattr(project_root_service, "admin_workspace_root", lambda: workspace_root)

    def _fake_build_runtime_verification_response(**kwargs):
        captured.update(kwargs)
        return {
            "project_root": str(kwargs["project_root"]),
            "verification_items": [],
            "gate_policy": {},
            "operational_evidence": {},
            "operational_targets_by_id": {},
            "operational_evidence_summary": {},
            "context": {},
            "gate_status": {"final_status": "not_run", "final_pass": False},
        }

    monkeypatch.setattr(admin_router_module, "build_runtime_verification_response", _fake_build_runtime_verification_response)

    client = TestClient(app)
    response = client.post(
        "/api/admin/orchestrator/runtime-verification",
        headers={"Authorization": "Bearer test-token"},
        json={"project_root": "", "worker_log_path": ""},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_root"] == str(workspace_root.resolve())
    assert payload["gate_status"] == {"final_status": "not_run", "final_pass": False}
    assert captured["project_root"] == workspace_root.resolve()


def test_subscription_monitor_summary_route_returns_helper_payload(monkeypatch):
    app = FastAPI()
    app.include_router(admin_router_module.router)
    app.dependency_overrides[admin_router_module.require_admin] = lambda: SimpleNamespace(id=1, email="ops-admin@example.com", is_admin=True, is_superuser=True)
    app.dependency_overrides[admin_router_module.get_db] = lambda: object()

    expected = {
        "totals": {
            "total_subscriptions": 3,
            "active_subscriptions": 2,
            "failed_payment_count": 1,
            "refunds_count": 1,
        },
        "filters": {"period_days": 7, "status": "active"},
        "status_breakdown": [{"status": "active", "count": 2}],
        "recent_state_transitions": [],
        "recent_webhook_failures": [],
    }

    captured: dict[str, object] = {}

    def _fake_build_summary(_db, *, period_days=30, status_filter=None):
        captured["period_days"] = period_days
        captured["status_filter"] = status_filter
        return expected

    monkeypatch.setattr(
        admin_router_module,
        "_build_admin_subscription_monitor_summary_payload",
        _fake_build_summary,
    )

    client = TestClient(app)
    response = client.get(
        "/api/admin/subscription-monitor-summary?period_days=7&status=active",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert captured["period_days"] == 7
    assert captured["status_filter"] == "active"