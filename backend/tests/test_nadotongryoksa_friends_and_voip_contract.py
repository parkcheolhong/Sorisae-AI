from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import create_access_token
from backend.auth import get_current_user
from backend.database import get_db
from backend.marketplace import models
from backend.marketplace.database import Base
import backend.marketplace.nadotongryoksa_chat_router as chat_router_module
import backend.marketplace.nadotongryoksa_friends_router as friends_router_module
import backend.marketplace.nadotongryoksa_voip_router as voip_router_module
from backend.marketplace.nadotongryoksa_friends_router import router as friends_router
from backend.marketplace.nadotongryoksa_voip_router import router as voip_router


def _build_client():
    class _FakeTranslator:
        def translate(self, text: str, *, from_lang: str, to_lang: str) -> str:
            return f"[{from_lang}->{to_lang}] {text}"

    class _FakeTranslatorProvider:
        @staticmethod
        def get_instance() -> _FakeTranslator:
            return _FakeTranslator()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        current_user = models.User(
            id=1,
            email="caller@example.com",
            username="caller",
            is_active=True,
            preferred_language="ko",
            country_code="KR",
        )
        app_user = models.User(
            id=2,
            email="callee@example.com",
            username="callee",
            is_active=True,
            preferred_language="en",
            country_code="US",
        )
        db.add_all([current_user, app_user])
        db.commit()

    app = FastAPI()
    app.include_router(friends_router, prefix="/api")
    app.include_router(voip_router, prefix="/api")

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    chat_router_module.NadoTranslator = _FakeTranslatorProvider
    voip_router_module.SessionLocal = TestingSessionLocal
    friends_router_module.MAP_DISCOVERY_USERS.clear()
    app.state.testing_session_local = TestingSessionLocal
    return TestClient(app)


def test_friends_routes_support_app_user_and_external_phone_contact():
    client = _build_client()

    app_user_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert app_user_response.status_code == 200
    assert app_user_response.json()["friendUserId"] == 2

    external_response = client.post(
        "/api/friends",
        json={"targetEmail": "external@example.com", "phoneNumber": "+82-10-3333-4444"},
    )
    assert external_response.status_code == 200
    assert external_response.json()["friendUserId"] is None

    list_response = client.get("/api/users/1/friends")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 2
    assert {item["friendEmail"] for item in payload["friends"]} == {"callee@example.com", "external@example.com"}
    app_friend = next(item for item in payload["friends"] if item["friendEmail"] == "callee@example.com")
    assert app_friend["friendVoiceId"] == "nado-000002"

    delete_response = client.delete(f"/api/friends/{external_response.json()['id']}")
    assert delete_response.status_code == 200

    after_delete = client.get("/api/users/1/friends")
    assert after_delete.json()["total"] == 1


def test_friend_list_includes_discovery_country_and_gender_for_app_friends():
    client = _build_client()

    app = client.app
    target_token = create_access_token({"sub": "callee@example.com"})
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace( # pyright: ignore[reportFunctionMemberAccess] # pyright: ignore[reportAttributeAccessIssue] # pyright: ignore[reportAttributeAccessIssue] # pyright: ignore[reportAttributeAccessIssue] # type: ignore
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )
    presence_response = client.post(
        "/api/friends/discovery/location",
        headers={"Authorization": f"Bearer {target_token}"},
        json={
            "latitude": 37.5670,
            "longitude": 126.9785,
            "countryCode": "JP",
            "gender": "female",
            "nickname": "sakura",
            "shareOnMap": True,
        },
    )
    assert presence_response.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace( # type: ignore
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    add_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert add_response.status_code == 200

    list_response = client.get("/api/users/1/friends")
    assert list_response.status_code == 200
    friend_payload = list_response.json()["friends"][0]
    assert friend_payload["friendVoiceId"] == "nado-000002"
    assert friend_payload["friendCountryCode"] == "JP"
    assert friend_payload["friendCountryFlag"] == "🇯🇵"
    assert friend_payload["friendGender"] == "female"


def test_voip_initiate_reports_native_dialer_when_pstn_gateway_missing(monkeypatch):
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_URL", raising=False)
    monkeypatch.delenv("SIP_TRUNK_URI", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    client = _build_client()
    response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "caller",
            "session_id": "test-session",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_dialer_required"] is True
    assert payload["call_route"] == "native_phone_dialer"
    assert payload["fallback_dial_url"] == "tel:+821011112222"
    assert "/api/v1/voip/signal" in payload["signaling_server"]


def test_voip_initiate_prefers_public_signaling_base_for_loopback_requests(monkeypatch):
    monkeypatch.setenv("VOIP_SIGNALING_PUBLIC_BASE_URL", "http://172.30.1.41:8000")

    client = _build_client()
    response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_user_id": 2,
            "caller_id": "caller",
            "session_id": "test-session-public-signal",
        },
        headers={"host": "127.0.0.1:8000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["signaling_server"].startswith("ws://172.30.1.41:8000/api/v1/voip/signal")


def test_voip_initiate_accepts_mode_and_auto_relay_without_changing_phone_route(monkeypatch):
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_URL", raising=False)
    monkeypatch.delenv("SIP_TRUNK_URI", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    client = _build_client()

    base_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "caller",
            "session_id": "test-session-base",
        },
    )
    extended_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "caller",
            "session_id": "test-session-extended",
            "mode": "voip_full_auto",
            "auto_relay": True,
        },
    )

    assert base_response.status_code == 200
    assert extended_response.status_code == 200

    base_payload = base_response.json()
    extended_payload = extended_response.json()

    assert extended_payload["call_route"] == base_payload["call_route"] == "native_phone_dialer"
    assert extended_payload["phone_dialer_required"] == base_payload["phone_dialer_required"] is True
    assert extended_payload["fallback_dial_url"] == base_payload["fallback_dial_url"] == "tel:+821011112222"
    assert extended_payload["pstn_gateway_configured"] == base_payload["pstn_gateway_configured"] is False


def test_voip_initiate_routes_to_online_friend_app_when_voice_target_is_available():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_message = presence_socket.receive_json()
        assert presence_message["type"] == "presence_ready"
        assert presence_message["voice_id"] == "nado-000002"

        response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "caller_id": "caller",
                "session_id": "friend-session",
                "mode": "voip_full_auto",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["call_route"] == "app_webrtc"
        assert payload["phone_dialer_required"] is False
        assert payload["callee_app_online"] is True
        assert payload["participant_role"] == "caller"
        assert payload["callee_voice_id"] == "nado-000002"
        assert payload["display_label"] == "callee"

        invite = presence_socket.receive_json()
        assert invite["type"] == "incoming_call"
        assert invite["participant_role"] == "callee"
        assert invite["caller_voice_id"] == "nado-000001"
        assert "/api/v1/voip/signal" in invite["signaling_server"]


def test_voip_initiate_rejects_self_app_call_targets():
    client = _build_client()

    by_user_id = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_user_id": 1,
            "caller_id": "caller",
            "session_id": "self-call-user-id",
            "mode": "voip_full_auto",
        },
    )
    by_voice_id = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_voice_id": "nado-000001",
            "caller_id": "caller",
            "session_id": "self-call-voice-id",
            "mode": "voip_full_auto",
        },
    )

    assert by_user_id.status_code == 400
    assert by_user_id.json()["detail"] == "본인 계정으로는 VoIP 통화를 걸 수 없습니다"
    assert by_voice_id.status_code == 400
    assert by_voice_id.json()["detail"] == "본인 계정으로는 VoIP 통화를 걸 수 없습니다"


def test_voip_pending_incoming_endpoint_returns_ringing_call_without_live_presence(monkeypatch):
    monkeypatch.delenv("FCM_SERVER_KEY", raising=False)
    monkeypatch.delenv("FCM_PROJECT_ID", raising=False)

    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    initiate_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "caller_id": "caller",
            "session_id": "friend-session-pending-fetch",
            "mode": "voip_full_auto",
        },
    )

    assert initiate_response.status_code == 200
    initiate_payload = initiate_response.json()
    assert initiate_payload["status"] == "callee_offline"
    assert initiate_payload["callee_app_online"] is False

    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )

    pending_response = client.get(
        "/api/v1/voip/calls/pending-incoming",
        headers={"Authorization": f"Bearer {create_access_token({'sub': 'callee@example.com'})}"},
    )

    assert pending_response.status_code == 200
    pending_payload = pending_response.json()
    assert pending_payload["call_id"] == initiate_payload["call_id"]
    assert pending_payload["participant_role"] == "callee"
    assert pending_payload["caller_voice_id"] == "nado-000001"
    assert pending_payload["status"] == "callee_offline"
    assert "/api/v1/voip/signal" in pending_payload["signaling_server"]


def test_voip_active_current_endpoint_returns_latest_resumable_call_for_current_user(monkeypatch):
    monkeypatch.delenv("FCM_SERVER_KEY", raising=False)
    monkeypatch.delenv("FCM_PROJECT_ID", raising=False)

    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    initiate_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "caller_id": "caller",
            "session_id": "friend-session-active-fetch",
            "mode": "voip_full_auto",
        },
    )

    assert initiate_response.status_code == 200
    initiate_payload = initiate_response.json()

    active_response = client.get(
        f"/api/v1/voip/calls/active-current?last_call_id={initiate_payload['call_id']}",
    )

    assert active_response.status_code == 200
    active_payload = active_response.json()
    assert active_payload["call_id"] == initiate_payload["call_id"]
    assert active_payload["participant_role"] == "caller"
    assert active_payload["display_label"] == "callee"
    assert active_payload["status"] == initiate_payload["status"]
    assert "/api/v1/voip/signal" in active_payload["signaling_server"]


def test_voip_active_current_endpoint_prunes_stale_connecting_call_without_participants(monkeypatch):
    monkeypatch.delenv("FCM_SERVER_KEY", raising=False)
    monkeypatch.delenv("FCM_PROJECT_ID", raising=False)

    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    initiate_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "caller_id": "caller",
            "session_id": "friend-session-active-stale-prune",
            "mode": "voip_full_auto",
        },
    )

    assert initiate_response.status_code == 200
    call_id = initiate_response.json()["call_id"]
    call_state = voip_router_module.call_states[call_id]
    stale_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=voip_router_module.STALE_RESUMABLE_CALL_TTL_SECONDS + 5,
    )
    call_state.set_status("connecting")
    call_state.created_at = stale_at
    call_state.updated_at = stale_at
    call_state.status_changed_at = stale_at
    voip_router_module.call_participants.pop(call_id, None)

    active_response = client.get(
        f"/api/v1/voip/calls/active-current?last_call_id={call_id}",
    )

    assert active_response.status_code == 200
    assert active_response.json() is None
    assert voip_router_module.call_states[call_id].status == "ended"
    assert voip_router_module.call_states[call_id].error_code == "STALE_SESSION_PRUNED"


def test_voip_active_current_endpoint_does_not_fallback_to_older_call_when_last_call_id_is_missing(monkeypatch):
    monkeypatch.delenv("FCM_SERVER_KEY", raising=False)
    monkeypatch.delenv("FCM_PROJECT_ID", raising=False)

    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    initiate_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "caller_id": "caller",
            "session_id": "friend-session-active-fetch-no-fallback",
            "mode": "voip_full_auto",
        },
    )

    assert initiate_response.status_code == 200

    active_response = client.get(
        "/api/v1/voip/calls/active-current?last_call_id=call-does-not-exist",
    )

    assert active_response.status_code == 200
    assert active_response.json() is None


def test_voip_initiate_applies_auto_relay_for_app_webrtc_calls_when_full_auto_requested():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_socket.receive_json()

        response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "callee_phone": "+82-10-1111-2222",
                "caller_id": "caller",
                "session_id": "friend-session-auto-relay",
                "mode": "voip_full_auto",
                "auto_relay": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["call_route"] == "app_webrtc"
        assert payload["requested_mode"] == "voip_full_auto"
        assert payload["resolved_mode"] == "voip_full_auto"
        assert payload["auto_relay_requested"] is True
        assert payload["auto_relay_applied"] is True


def test_voip_initiate_defaults_auto_relay_for_full_auto_app_calls():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_socket.receive_json()

        response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "caller_id": "caller",
                "session_id": "friend-session-auto-relay-default",
                "mode": "voip_full_auto",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        invite_payload = presence_socket.receive_json()

    assert payload["call_route"] == "app_webrtc"
    assert payload["requested_mode"] == "voip_full_auto"
    assert payload["resolved_mode"] == "voip_full_auto"
    assert payload["auto_relay_requested"] is True
    assert payload["auto_relay_applied"] is True
    assert invite_payload["auto_relay_requested"] is True
    assert invite_payload["auto_relay_applied"] is True


def test_voip_initiate_logs_matching_prepared_publish_and_response_payloads(caplog):
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with caplog.at_level(logging.INFO, logger="backend.marketplace.nadotongryoksa_voip_router"):
        with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
            presence_socket.receive_json()

            response = client.post(
                "/api/v1/voip/calls/initiate",
                json={
                    "friend_id": friend_id,
                    "caller_id": "caller",
                    "session_id": "friend-session-log-trace",
                    "mode": "voip_full_auto",
                    "auto_relay": True,
                },
            )

            assert response.status_code == 200
            response_payload = response.json()
            invite_payload = presence_socket.receive_json()

    call_id = response_payload["call_id"]
    log_text = caplog.text

    assert f"Incoming invite prepared | call_id={call_id}" in log_text
    assert f"Publishing incoming invite | voice_id=nado-000002 | call_id={call_id}" in log_text
    assert f"Call initiate response | call_id={call_id}" in log_text
    assert '"requested_mode":"voip_full_auto"' in log_text
    assert '"resolved_mode":"voip_full_auto"' in log_text
    assert '"auto_relay_requested":true' in log_text
    assert '"auto_relay_applied":true' in log_text
    assert invite_payload["requested_mode"] == response_payload["requested_mode"] == "voip_full_auto"
    assert invite_payload["resolved_mode"] == response_payload["resolved_mode"] == "voip_full_auto"
    assert invite_payload["auto_relay_requested"] == response_payload["auto_relay_requested"] is True
    assert invite_payload["auto_relay_applied"] == response_payload["auto_relay_applied"] is True


def test_voip_initiate_prefers_pstn_route_when_pstn_assist_is_requested(monkeypatch):
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_URL", raising=False)
    monkeypatch.delenv("SIP_TRUNK_URI", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "caller",
            "session_id": "friend-session-pstn-assist",
            "mode": "pstn_assist",
            "auto_relay": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["call_route"] == "native_phone_dialer"
    assert payload["requested_mode"] == "pstn_assist"
    assert payload["resolved_mode"] == "pstn_assist"
    assert payload["auto_relay_requested"] is True
    assert payload["auto_relay_applied"] is False


def test_voip_audit_endpoint_returns_initiate_and_end_events(monkeypatch):
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("VOIP_PSTN_GATEWAY_URL", raising=False)
    monkeypatch.delenv("SIP_TRUNK_URI", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    client = _build_client()
    initiate_response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "callee_phone": "+82-10-1111-2222",
            "caller_id": "caller",
            "session_id": "audit-session-1",
            "mode": "voip_full_auto",
            "auto_relay": True,
        },
    )
    assert initiate_response.status_code == 200
    call_id = initiate_response.json()["call_id"]

    end_response = client.post(
        f"/api/v1/voip/calls/{call_id}/end",
        json={"duration_sec": 42, "call_quality": "good"},
    )
    assert end_response.status_code == 200

    audit_response = client.get(f"/api/v1/voip/calls/{call_id}/audit")
    assert audit_response.status_code == 200
    events = audit_response.json()
    assert [event["event_type"] for event in events] == ["call_initiated", "call_ended"]
    assert events[0]["requested_mode"] == "voip_full_auto"
    assert events[0]["resolved_mode"] == "pstn_assist"
    assert events[0]["auto_relay_requested"] is True
    assert events[0]["auto_relay_applied"] is False
    assert events[1]["duration_sec"] == 42
    assert events[1]["call_quality"] == "good"


def test_voip_records_and_lists_recent_missed_calls_for_callee():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_socket.receive_json()

        initiate_response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "caller_id": "caller",
                "session_id": "missed-call-session",
                "mode": "voip_full_auto",
            },
        )
        assert initiate_response.status_code == 200
        call_id = initiate_response.json()["call_id"]
        presence_socket.receive_json()

    end_response = client.post(
        f"/api/v1/voip/calls/{call_id}/end",
        json={"duration_sec": 0, "call_quality": "poor"},
    )
    assert end_response.status_code == 200

    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        preferred_language="en",
        country_code="US",
        is_active=True,
        is_admin=False,
    )
    missed_response = client.get("/api/v1/voip/calls/missed/recent")
    assert missed_response.status_code == 200
    missed_payload = missed_response.json()
    assert missed_payload[0]["callId"] == call_id
    assert missed_payload[0]["callerLabel"] == "caller"
    assert missed_payload[0]["status"] == "missed"


def test_voip_initiate_uses_push_fallback_when_friend_socket_is_offline(monkeypatch):
    client = _build_client()
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    push_calls = []

    async def fake_push_invite(callee_voice_id: str, payload: dict) -> bool:
        push_calls.append((callee_voice_id, payload))
        return True

    monkeypatch.setattr(
        "backend.marketplace.nadotongryoksa_voip_router._send_incoming_call_push_invite",
        fake_push_invite,
    )

    response = client.post(
        "/api/v1/voip/calls/initiate",
        json={
            "friend_id": friend_id,
            "caller_id": "caller",
            "session_id": "friend-session",
            "mode": "voip_full_auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["call_route"] == "app_webrtc"
    assert payload["phone_dialer_required"] is False
    assert payload["callee_app_online"] is False
    assert payload["status"] == "ringing"
    assert "수신 알림" in payload["user_message"]
    assert push_calls[0][0] == "nado-000002"
    assert push_calls[0][1]["type"] == "incoming_call"


def test_send_incoming_call_push_invite_supports_fcm_v1_service_account(monkeypatch):
    monkeypatch.delenv("FCM_SERVER_KEY", raising=False)
    monkeypatch.setenv("FCM_PROJECT_ID", "metanova-voip-test")

    post_calls = []

    def fake_load_service_account() -> dict[str, str]:
        return {
            "project_id": "metanova-voip-test",
            "client_email": "voip-test@metanova-voip-test.iam.gserviceaccount.com",
        }

    def fake_post_fcm_v1(service_account_info: dict, project_id: str, payload: dict) -> tuple[int, str]:
        post_calls.append((service_account_info, project_id, payload))
        return 200, '{"name":"projects/metanova-voip-test/messages/123"}'

    monkeypatch.setattr(
        voip_router_module,
        "_load_fcm_service_account_info",
        fake_load_service_account,
    )
    monkeypatch.setattr(voip_router_module, "_post_fcm_v1", fake_post_fcm_v1)

    success = asyncio.run(
        voip_router_module._send_incoming_call_push_invite(
            "nado-000002",
            {
                "type": "incoming_call",
                "caller_voice_id": "nado-000001",
                "caller_label": "caller",
                "call_id": "call-service-account",
            },
        )
    )

    assert success is True
    assert post_calls[0][0]["project_id"] == "metanova-voip-test"
    assert post_calls[0][1] == "metanova-voip-test"
    assert post_calls[0][2]["message"]["topic"] == "worldlingo_voip_nado_000002"
    assert post_calls[0][2]["message"]["android"]["priority"] == "HIGH"


def test_voip_signal_relays_realtime_chat_messages_between_app_participants():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_message = presence_socket.receive_json()
        assert presence_message["type"] == "presence_ready"

        response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "caller_id": "caller",
                "session_id": "friend-chat-session",
                "mode": "voip_full_auto",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        call_id = payload["call_id"]

        invite = presence_socket.receive_json()
        assert invite["type"] == "incoming_call"

        with client.websocket_connect(f"/api/v1/voip/signal?call_id={call_id}&role=caller") as caller_socket:
            with client.websocket_connect(f"/api/v1/voip/signal?call_id={call_id}&role=callee") as callee_socket:
                caller_socket.send_json({
                    "type": "chat_message",
                    "text": "안녕하세요, 지금 바로 연결 중입니다.",
                    "sent_at": "2026-05-13T10:00:00Z",
                })

                caller_ack = caller_socket.receive_json()
                first_message = callee_socket.receive_json()
                assert caller_ack["type"] == "chat_message"
                assert caller_ack["from_role"] == "caller"
                assert caller_ack["text"] == "안녕하세요, 지금 바로 연결 중입니다."
                assert caller_ack["client_sent_at"] == "2026-05-13T10:00:00Z"
                assert caller_ack["room_id"]
                assert caller_ack["message_id"]
                assert first_message["type"] == "chat_message"
                assert first_message["from_role"] == "caller"
                assert first_message["text"] == "안녕하세요, 지금 바로 연결 중입니다."
                assert first_message["call_id"] == call_id
                assert first_message["translated_text"]
                assert first_message["translated_text"] != first_message["text"]
                assert first_message["source_lang"] == "ko"
                assert first_message["target_lang"] == "en"
                assert first_message["translation_status"] == "done"
                assert first_message["room_id"]
                assert first_message["message_id"]
                assert first_message["room_id"] == caller_ack["room_id"]
                assert first_message["message_id"] == caller_ack["message_id"]

                callee_socket.send_json({
                    "type": "chat_message",
                    "text": "네, 채팅도 확인됐어요.",
                    "sent_at": "2026-05-13T10:00:05Z",
                })

                callee_ack = callee_socket.receive_json()
                reply_message = caller_socket.receive_json()
                assert callee_ack["type"] == "chat_message"
                assert callee_ack["from_role"] == "callee"
                assert callee_ack["text"] == "네, 채팅도 확인됐어요."
                assert callee_ack["client_sent_at"] == "2026-05-13T10:00:05Z"
                assert callee_ack["room_id"]
                assert callee_ack["message_id"]
                assert reply_message["type"] == "chat_message"
                assert reply_message["from_role"] == "callee"
                assert reply_message["text"] == "네, 채팅도 확인됐어요."
                assert reply_message["translated_text"]
                assert reply_message["source_lang"] == "en"
                assert reply_message["target_lang"] == "ko"
                assert reply_message["room_id"] == callee_ack["room_id"]
                assert reply_message["message_id"] == callee_ack["message_id"]


def test_voip_signal_relays_voice_translation_messages_between_app_participants():
    client = _build_client()
    token = create_access_token({"sub": "callee@example.com"})
    friend_response = client.post(
        "/api/friends",
        json={"targetEmail": "callee@example.com", "phoneNumber": "+82-10-1111-2222"},
    )
    assert friend_response.status_code == 200
    friend_id = friend_response.json()["id"]

    with client.websocket_connect(f"/api/v1/voip/presence?token={token}") as presence_socket:
        presence_message = presence_socket.receive_json()
        assert presence_message["type"] == "presence_ready"

        response = client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "friend_id": friend_id,
                "caller_id": "caller",
                "session_id": "friend-voice-translation-session",
                "mode": "voip_full_auto",
                "auto_relay": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        call_id = payload["call_id"]

        invite = presence_socket.receive_json()
        assert invite["type"] == "incoming_call"

        with client.websocket_connect(f"/api/v1/voip/signal?call_id={call_id}&role=caller") as caller_socket:
            caller_socket.send_json(
                {
                    "type": "voice_translation",
                    "transcript": "안녕하세요",
                    "translated_text": "Hello",
                    "source_lang": "ko",
                    "target_lang": "en",
                    "audio_url": "https://example.com/hello.wav",
                    "audio_base64": "UklGRg==",
                    "audio_format": "audio/wav",
                    "sent_at": "2026-05-15T10:00:00Z",
                }
            )

            with client.websocket_connect(f"/api/v1/voip/signal?call_id={call_id}&role=callee") as callee_socket:
                first_message = callee_socket.receive_json()
                assert first_message["type"] == "voice_translation"
                assert first_message["from_role"] == "caller"
                assert first_message["transcript"] == "안녕하세요"
                assert first_message["translated_text"] == "Hello"
                assert first_message["source_lang"] == "ko"
                assert first_message["target_lang"] == "en"
                assert first_message["audio_url"] == "https://example.com/hello.wav"
                assert first_message["audio_base64"] == "UklGRg=="
                assert first_message["audio_format"] == "audio/wav"
                assert first_message["call_id"] == call_id


def test_map_discovery_nearby_users_returns_gender_country_and_google_maps_url():
    client = _build_client()

    caller_presence = client.post(
        "/api/friends/discovery/location",
        json={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "countryCode": "KR",
            "gender": "male",
            "nickname": "caller-map",
            "shareOnMap": True,
        },
    )
    assert caller_presence.status_code == 200

    token = create_access_token({"sub": "callee@example.com"})
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )
    callee_presence = client.post(
        "/api/friends/discovery/location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 37.5670,
            "longitude": 126.9785,
            "countryCode": "JP",
            "gender": "female",
            "nickname": "sakura",
            "shareOnMap": True,
        },
    )
    assert callee_presence.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    response = client.get(
        "/api/friends/discovery/nearby",
        params={"lat": 37.5665, "lon": 126.9780, "radius_m": 500},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["total"] == 1
    assert payload["users"][0]["nickname"] == "sakura"
    assert payload["users"][0]["gender"] == "female"
    assert payload["users"][0]["countryCode"] == "JP"
    assert payload["users"][0]["countryFlag"] == "🇯🇵"
    assert payload["users"][0]["googleMapsUrl"].startswith("https://www.google.com/maps/search/")


def test_map_discovery_nearby_users_without_radius_returns_all_sorted_by_distance():
    client = _build_client()

    caller_presence = client.post(
        "/api/friends/discovery/location",
        json={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "countryCode": "KR",
            "gender": "male",
            "nickname": "caller-map",
            "shareOnMap": True,
        },
    )
    assert caller_presence.status_code == 200

    token = create_access_token({"sub": "callee@example.com"})
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )
    callee_presence = client.post(
        "/api/friends/discovery/location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 42.0,
            "longitude": 130.0,
            "countryCode": "JP",
            "gender": "female",
            "nickname": "far-away",
            "shareOnMap": True,
        },
    )
    assert callee_presence.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    response = client.get(
        "/api/friends/discovery/nearby",
        params={"lat": 37.5665, "lon": 126.9780},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["radiusM"] is None
    assert payload["total"] == 1
    assert payload["users"][0]["nickname"] == "far-away"
    assert payload["users"][0]["distanceM"] > 500_000


def test_friend_request_accept_creates_mutual_friend_links():
    client = _build_client()

    sender_presence = client.post(
        "/api/friends/discovery/location",
        json={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "countryCode": "KR",
            "gender": "male",
            "nickname": "caller-map",
            "shareOnMap": True,
        },
    )
    assert sender_presence.status_code == 200

    request_response = client.post("/api/friends/requests", json={"receiverUserId": 2})
    assert request_response.status_code == 200
    request_id = request_response.json()["request"]["requestId"]

    app = client.app
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )

    incoming = client.get("/api/friends/requests/incoming")
    assert incoming.status_code == 200
    assert incoming.json()["total"] == 1
    assert incoming.json()["requests"][0]["senderNickname"] == "caller-map"

    accept_response = client.post(f"/api/friends/requests/{request_id}/accept")
    assert accept_response.status_code == 200
    accepted_payload = accept_response.json()
    assert accepted_payload["friend"]["friendUserId"] == 1
    assert accepted_payload["friend"]["friendVoiceId"] == "nado-000001"

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    caller_friends = client.get("/api/users/1/friends")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace( # type: ignore
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )
    callee_friends = client.get("/api/users/2/friends")
    assert caller_friends.status_code == 200
    assert callee_friends.status_code == 200
    assert caller_friends.json()["total"] == 1
    assert callee_friends.json()["total"] == 1

    with client.app.state.testing_session_local() as db:  # type: ignore[attr-defined]
        stored_request = (
            db.query(models.FriendRequest)
            .filter(models.FriendRequest.request_id == request_id)
            .first()
        )
        assert stored_request is not None
        assert stored_request.status == "accepted"
        assert stored_request.responded_at is not None


def test_friend_request_auto_accepts_when_both_users_are_nearby():
    client = _build_client()
    app = client.app

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    sender_presence = client.post(
        "/api/friends/discovery/location",
        json={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "countryCode": "KR",
            "gender": "male",
            "nickname": "caller-map",
            "shareOnMap": True,
        },
    )
    assert sender_presence.status_code == 200

    token = create_access_token({"sub": "callee@example.com"})
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )
    callee_presence = client.post(
        "/api/friends/discovery/location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 37.5666,
            "longitude": 126.9781,
            "countryCode": "JP",
            "gender": "female",
            "nickname": "sakura",
            "shareOnMap": True,
        },
    )
    assert callee_presence.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )
    request_response = client.post("/api/friends/requests", json={"receiverUserId": 2})
    assert request_response.status_code == 200
    payload = request_response.json()
    assert payload["autoAccepted"] is True
    assert payload["request"]["status"] == "accepted"

    caller_friends = client.get("/api/users/1/friends")
    assert caller_friends.status_code == 200
    assert caller_friends.json()["total"] == 1


def test_friend_request_outgoing_list_exposes_pending_requests_for_sender():
    client = _build_client()

    app = client.app
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace( # pyright: ignore[reportFunctionMemberAccess] # type: ignore
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )

    receiver_presence = client.post(
        "/api/friends/discovery/location",
        json={
            "latitude": 35.1796,
            "longitude": 129.0756,
            "countryCode": "KR",
            "gender": "female",
            "nickname": "busan-friend",
            "shareOnMap": True,
        },
    )
    assert receiver_presence.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace( # type: ignore
        id=1,
        email="caller@example.com",
        username="caller",
        is_active=True,
        is_admin=False,
    )

    request_response = client.post("/api/friends/requests", json={"receiverUserId": 2})
    assert request_response.status_code == 200

    outgoing = client.get("/api/friends/requests/outgoing")
    assert outgoing.status_code == 200
    payload = outgoing.json()
    assert payload["total"] == 1
    assert payload["requests"][0]["receiverUserId"] == 2
    assert payload["requests"][0]["receiverNickname"] == "busan-friend"
    assert payload["requests"][0]["receiverVoiceId"] == "nado-000002"
    assert payload["requests"][0]["status"] == "pending"


def test_friend_request_reject_persists_rejected_status():
    client = _build_client()

    request_response = client.post("/api/friends/requests", json={"receiverUserId": 2})
    assert request_response.status_code == 200
    request_id = request_response.json()["request"]["requestId"]

    app = client.app
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="callee@example.com",
        username="callee",
        is_active=True,
        is_admin=False,
    )

    reject_response = client.post(f"/api/friends/requests/{request_id}/reject")
    assert reject_response.status_code == 200

    with client.app.state.testing_session_local() as db:  # type: ignore[attr-defined]
        stored_request = (
            db.query(models.FriendRequest)
            .filter(models.FriendRequest.request_id == request_id)
            .first()
        )
        assert stored_request is not None
        assert stored_request.status == "rejected"
        assert stored_request.responded_at is not None
