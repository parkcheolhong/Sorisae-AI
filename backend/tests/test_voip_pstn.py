"""P3-B: PSTN 다이얼아웃 공급자 어댑터 테스트(TestClient initiate 경로)."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.voip.router import router as voip_router


class _FakeUser:
    def __init__(self, uid, username):
        self.id = uid
        self.username = username
        self.email = f"{username}@example.com"
        self.is_active = True


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(voip_router)

    async def _dep(request: Request):
        return _FakeUser(4001, "alice4")

    app.dependency_overrides[get_current_user] = _dep
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _initiate_phone(client):
    return client.post("/api/v1/voip/calls/initiate",
                       json={"callee_phone": "+821012345678"}).json()


def test_default_provider_falls_back_to_dialer(client, monkeypatch):
    monkeypatch.delenv("VOIP_PSTN_PROVIDER", raising=False)
    data = _initiate_phone(client)
    assert data["call_route"] == "pstn_fallback"
    assert data["phone_dialer_required"] is True
    assert data["fallback_dial_url"] == "tel:+821012345678"
    assert data["status"] == "dialer_required"


def test_simulated_provider_routes_pstn(client, monkeypatch):
    monkeypatch.setenv("VOIP_PSTN_PROVIDER", "simulated")
    data = _initiate_phone(client)
    assert data["call_route"] == "pstn"
    assert data["phone_dialer_required"] is False
    assert data["status"] == "dialing"
    assert data["call_id"].startswith("sim_")
    assert data["resolved_mode"] == "pstn"


def test_twilio_provider_unconfigured_falls_back(client, monkeypatch):
    monkeypatch.setenv("VOIP_PSTN_PROVIDER", "twilio")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    data = _initiate_phone(client)
    assert data["call_route"] == "pstn_fallback"
    assert data["phone_dialer_required"] is True
