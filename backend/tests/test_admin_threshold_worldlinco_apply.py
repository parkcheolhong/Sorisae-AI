from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.admin_router as admin_router_module
import backend.marketplace.worldlinco_tuning as worldlinco_tuning_module


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(admin_router_module.router)
    app.dependency_overrides[admin_router_module.require_admin] = lambda: SimpleNamespace(
        id=1,
        email="ops-admin@example.com",
        is_admin=True,
        is_superuser=True,
    )
    app.dependency_overrides[admin_router_module.get_db] = lambda: object()
    return TestClient(app)


def test_apply_worldlinco_approved_accepts_current_baseline_payload(monkeypatch):
    monkeypatch.setattr(
        admin_router_module,
        "_load_threshold_analysis_payload",
        lambda: {
            "safe_gate": {"worldlinco_auto_apply_allowed": True},
            "recommendations": {
                "worldlinco": {
                    "voip": {"silero_safety_cap_ms": 7000},
                    "chat": {"message_latency_budget_ms": 1600},
                }
            },
        },
    )

    captured = {}

    def _fake_apply(update, updated_by="admin"):
        captured["payload"] = update.model_dump(exclude_none=True)
        captured["updated_by"] = updated_by
        return {
            "updated_at": "2026-07-05T00:00:00Z",
            "updated_by": updated_by,
            **captured["payload"],
        }

    monkeypatch.setattr(worldlinco_tuning_module, "apply_worldlinco_tuning_update", _fake_apply)

    client = _build_client()
    response = client.post(
        "/api/admin/threshold-analysis/apply-worldlinco-approved",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied"] is True
    assert payload["updated_by"] == "ops-admin@example.com"
    assert captured["payload"]["voip"]["silero_safety_cap_ms"] == 7000


def test_apply_worldlinco_approved_returns_400_with_validation_detail(monkeypatch):
    monkeypatch.setattr(
        admin_router_module,
        "_load_threshold_analysis_payload",
        lambda: {
            "safe_gate": {"worldlinco_auto_apply_allowed": True},
            "recommendations": {
                "worldlinco": {
                    "voip": {"silero_safety_cap_ms": 6500},
                }
            },
        },
    )

    client = _build_client()
    response = client.post(
        "/api/admin/threshold-analysis/apply-worldlinco-approved",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "승인된 월드린코 추천값 검증 실패" in detail
    assert "silero_safety_cap_ms" in detail