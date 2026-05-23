from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.marketplace.router as marketplace_router_module
from backend.auth import get_current_user


class _FakeDb:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _build_test_client(fake_db: _FakeDb) -> TestClient:
    app = FastAPI()
    app.include_router(marketplace_router_module.router, prefix="/api/marketplace")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, email="customer@example.com")
    app.dependency_overrides[marketplace_router_module.get_db] = lambda: fake_db
    return TestClient(app)


def test_customer_orchestrate_stage_run_create_returns_initialized_payload(monkeypatch):
    fake_db = _FakeDb()
    client = _build_test_client(fake_db)

    captured: dict[str, object] = {}

    def _fake_initialize_stage_run(**kwargs):
        captured.update(kwargs)
        return {
            "run_id": "run-001",
            "current_stage_id": "ARCH-001",
            "status": "pending",
            "stages": [],
        }

    monkeypatch.setattr(
        marketplace_router_module,
        "initialize_stage_run",
        _fake_initialize_stage_run,
    )

    response = client.post(
        "/api/marketplace/customer-orchestrate/stage-runs",
        json={
            "task": "고객 주문 생성",
            "mode": "full",
            "project_name": "contract-check",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-001"
    assert payload["current_stage_id"] == "ARCH-001"
    assert captured["scope"] == "marketplace"
    assert captured["project_name"] == "contract-check"
    assert captured["mode"] == "full"
    assert captured["requested_by"] == {"id": 7, "email": "customer@example.com"}
    assert captured["metadata"] == {"task": "고객 주문 생성"}


def test_customer_orchestrate_stage_run_get_returns_saved_payload(monkeypatch):
    fake_db = _FakeDb()
    client = _build_test_client(fake_db)

    monkeypatch.setattr(
        marketplace_router_module,
        "load_stage_run",
        lambda run_id: {
            "run_id": "run-001",
            "current_stage_id": "ARCH-001",
            "status": "pending",
            "stages": [],
        },
    )

    response = client.get("/api/marketplace/customer-orchestrate/stage-runs/run-001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-001"
    assert payload["status"] == "pending"


def test_customer_orchestrate_accepted_returns_stage_run_payload(monkeypatch):
    fake_db = _FakeDb()
    client = _build_test_client(fake_db)

    monkeypatch.setattr(
        marketplace_router_module,
        "_resolve_stage_run_for_request",
        lambda request, current_user: {
            "run_id": "run-accepted-001",
            "current_stage_id": "ARCH-001",
            "status": "pending",
            "stages": [],
        },
    )

    response = client.post(
        "/api/marketplace/customer-orchestrate/accepted",
        json={
            "task": "고객 주문 생성",
            "mode": "full",
            "project_name": "contract-check",
            "stage_run_id": "run-accepted-001",
            "stage_id": "ARCH-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["run_id"] == "run-accepted-001"
    assert payload["stage_run"]["current_stage_id"] == "ARCH-001"
    assert payload["status"] == "accepted"


def test_build_customer_orchestrate_request_schedules_cleanup(monkeypatch, tmp_path):
    cleanup_calls: list[str] = []
    run_root = tmp_path / "customer_7" / "runs"
    run_root.mkdir(parents=True, exist_ok=True)
    allocated_output = run_root / "contract-check_20260503_000000"
    allocated_output.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        marketplace_router_module,
        "_schedule_marketplace_storage_cleanup",
        lambda: cleanup_calls.append("scheduled"),
    )
    monkeypatch.setattr(
        marketplace_router_module,
        "_resolve_customer_orchestrator_run_root",
        lambda user_id: run_root,
    )
    monkeypatch.setattr(
        marketplace_router_module,
        "_allocate_customer_orchestrator_output_dir",
        lambda root, project_name: allocated_output,
    )

    request = marketplace_router_module.CustomerOrchestrateRequest(
        task="고객 주문 생성",
        mode="full",
        project_name="contract-check",
        stage_id="ARCH-001",
    )

    payload = marketplace_router_module._build_customer_orchestrate_request(request, 7)

    assert cleanup_calls == ["scheduled"]
    assert payload.output_base_dir == str(run_root)
    assert payload.output_dir == str(allocated_output)
    assert payload.project_name == "contract-check"


def test_customer_orchestrate_stage_run_update_returns_updated_payload(monkeypatch):
    fake_db = _FakeDb()
    client = _build_test_client(fake_db)

    captured: dict[str, object] = {}

    def _fake_update_stage_run(**kwargs):
        captured.update(kwargs)
        return {
            "run_id": kwargs["run_id"],
            "current_stage_id": kwargs["stage_id"],
            "status": kwargs["status"],
            "stages": [],
        }

    monkeypatch.setattr(
        marketplace_router_module,
        "update_stage_run",
        _fake_update_stage_run,
    )

    response = client.post(
        "/api/marketplace/customer-orchestrate/stage-runs/update",
        json={
            "run_id": "run-001",
            "stage_id": "ARCH-002",
            "status": "passed",
            "note": "validated",
            "manual_correction": "",
            "substep_checks": {"sub-1": True},
            "revision_note": "promoted",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-001"
    assert payload["current_stage_id"] == "ARCH-002"
    assert payload["status"] == "passed"
    assert captured == {
        "run_id": "run-001",
        "stage_id": "ARCH-002",
        "status": "passed",
        "note": "validated",
        "manual_correction": "",
        "substep_checks": {"sub-1": True},
        "revision_note": "promoted",
    }