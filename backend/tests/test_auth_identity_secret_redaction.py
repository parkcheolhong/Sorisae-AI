"""Carrier client secrets must stay on the server-to-provider call."""
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth_identity_router import router as auth_identity_router
from backend.services.auth_identity_provider import PassIdentityProvider


LIVE_SECRET = "live-pass-secret-9f3a"


def _configure_pass(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_PROVIDER", "pass")
    monkeypatch.setenv("PASS_IDENTITY_ENDPOINT", "https://identity.pass.internal/identity/start")
    monkeypatch.setenv("PASS_CLIENT_ID", "pass-live-client")
    monkeypatch.setenv("PASS_CLIENT_SECRET", LIVE_SECRET)
    monkeypatch.setenv("PASS_CALLBACK_URL", "https://metanova1004.com/api/auth/identity/providers/pass/callback")


def test_start_response_omits_client_secret_but_provider_call_keeps_it(monkeypatch):
    _configure_pass(monkeypatch)
    captured: dict = {}

    def _fake_call(self, url, payload, timeout=15.0):
        captured["url"] = url
        captured["payload"] = dict(payload)
        return {
            "tx_id": "tx-1",
            "verification_code": "482193",
            "redirect_url": f"https://identity.pass.internal/go?client_secret={LIVE_SECRET}&tx_id=tx-1",
            "client_secret": LIVE_SECRET,
        }

    monkeypatch.setattr(PassIdentityProvider, "_call_provider_api", _fake_call)

    app = FastAPI()
    app.include_router(auth_identity_router, prefix="/api/auth/identity")
    client = TestClient(app)
    response = client.post(
        "/api/auth/identity/start",
        json={"scope": "admin", "purpose": "password_reset", "user_hint": "admin@example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    rendered = response.text

    assert LIVE_SECRET not in rendered
    assert "client_secret" not in body["request_payload"]
    assert body["request_payload"]["client_id"] == "pass-live-client"
    redirect_query = parse_qs(urlsplit(body["redirect_url"]).query)
    assert "client_secret" not in redirect_query
    assert redirect_query.get("tx_id") == ["tx-1"]

    assert captured["payload"]["client_secret"] == LIVE_SECRET
    assert captured["url"] == "https://identity.pass.internal/identity/start"


def test_partial_pass_config_still_hides_secret_from_anonymous_start(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", "pass")
    monkeypatch.setenv("PASS_CLIENT_SECRET", LIVE_SECRET)
    monkeypatch.delenv("PASS_IDENTITY_ENDPOINT", raising=False)
    monkeypatch.delenv("PASS_CLIENT_ID", raising=False)

    app = FastAPI()
    app.include_router(auth_identity_router, prefix="/api/auth/identity")
    client = TestClient(app)
    response = client.post(
        "/api/auth/identity/start",
        json={"user_hint": "admin@example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert LIVE_SECRET not in response.text
    assert "client_secret" not in body["request_payload"]
    assert "client_secret" not in parse_qs(urlsplit(body["redirect_url"]).query)
