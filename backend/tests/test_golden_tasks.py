"""Golden task probes — voice-translate smoke + VoIP health + devices/register."""
from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.llm.router import router as llm_router
from backend.tests.test_nadotongryoksa_friends_and_voip_contract import _build_client


class _FakeTranslator:
    def translate(self, text: str, *, from_lang: str, to_lang: str, region_hint=None) -> str:
        return "Hello"


def _build_voice_client() -> TestClient:
    app = FastAPI()
    app.include_router(llm_router)
    return TestClient(app)


def test_golden_voice_translate_smoke():
    with patch(
        "backend.services.nadotongryoksa.translator.NadoTranslator.get_instance",
        return_value=_FakeTranslator(),
    ):
        client = _build_voice_client()
        response = client.post(
            "/api/llm/voice-translate",
            json={
                "transcript": "안녕하세요",
                "from_lang": "ko",
                "to_lang": "en",
            },
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("translated") == "Hello"
    assert payload.get("from") in {"ko", "en"}
    assert payload.get("to") in {"ko", "en"}


def test_golden_voip_health():
    client = _build_client()
    response = client.get("/api/v1/voip/health")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("status") == "ok"
    assert "fcm_delivery_ready" in payload


def test_golden_voip_initiate_smoke():
    client = _build_client()
    response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "golden-probe",
            "session_id": "golden-probe-session",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    call_id = str(payload.get("call_id") or "").strip()
    route = str(payload.get("call_route") or "")
    signaling = str(payload.get("signaling_server") or "")
    assert call_id
    assert route in {"native_phone_dialer", "app_webrtc"} or "/api/v1/voip/signal" in signaling


def test_voip_devices_register_endpoint():
    client = _build_client()
    response = client.post(
        "/api/v1/voip/devices/register",
        json={"fcm_token": "probe-fcm-token-123", "platform": "android"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("ok") is True
    assert payload.get("registered_tokens", 0) >= 1

    health = client.get("/api/v1/voip/health")
    assert health.status_code == 200
    assert int(health.json().get("registered_device_users") or 0) >= 1
