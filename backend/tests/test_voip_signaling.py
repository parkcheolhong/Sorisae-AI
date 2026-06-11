"""VoIP 시그널링 P1 통합 테스트 — TestClient 2-클라이언트 릴레이.

REST initiate(앱↔앱 자동매칭) → WebSocket offer/answer/candidate/chat/voice_translation
릴레이 + ping/pong + hangup 을 caller/callee 두 소켓으로 E2E 검증한다.
"""
import asyncio
import time
from urllib.parse import urlparse, parse_qs

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user
from backend.voip.presence import get_presence
from backend.voip.router import router as voip_router
from backend.voip.registry import registry


class _FakeUser:
    def __init__(self, uid: int, username: str):
        self.id = uid
        self.username = username
        self.email = f"{username}@example.com"
        self.is_active = True


_USERS = {
    "alice": _FakeUser(1001, "alice"),
    "bob": _FakeUser(1002, "bob"),
}


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _override_user_from_header(request_user_header: str):
    # 의존성 오버라이드: X-Test-User 헤더로 호출자를 구분.
    from fastapi import Request

    async def _dep(request: Request):
        key = request.headers.get("x-test-user", "alice")
        return _USERS.get(key, _USERS["alice"])

    return _dep


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(voip_router)
    app.dependency_overrides[get_current_user] = _override_user_from_header("")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_registry(monkeypatch):
    from backend.voip.signaling import hub
    monkeypatch.delenv("VOIP_REDIS_URL", raising=False)
    registry._rooms.clear()
    hub._rooms.clear()
    _run(get_presence().clear())
    yield
    registry._rooms.clear()
    hub._rooms.clear()
    _run(get_presence().clear())


def _ws_path_from_signaling_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.path}?{parsed.query}"


def _initiate(client, *, as_user: str, body: dict) -> dict:
    resp = client.post(
        "/api/v1/voip/calls/initiate",
        json=body,
        headers={"X-Test-User": as_user},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_initiate_creates_room_and_matches_callee(client):
    caller = _initiate(client, as_user="alice", body={"callee_user_id": 1002})
    assert caller["call_id"]
    assert caller["participant_role"] == "caller"
    assert caller["call_route"] == "app"
    assert caller["signaling_server"].startswith("ws")

    callee = _initiate(client, as_user="bob", body={"callee_user_id": 1001})
    assert callee["call_id"] == caller["call_id"], "bob은 alice의 ringing room에 callee로 합류해야 함"
    assert callee["participant_role"] == "callee"


def test_pstn_only_falls_back_to_dialer(client):
    resp = _initiate(client, as_user="alice", body={"callee_phone": "+821012345678"})
    assert resp["call_route"] == "pstn_fallback"
    assert resp["phone_dialer_required"] is True
    assert resp["fallback_dial_url"] == "tel:+821012345678"


def test_initiate_response_has_turn_servers(client):
    resp = _initiate(client, as_user="alice", body={"callee_user_id": 1002})
    assert len(resp["turn_servers"]) >= 1
    assert any("stun:" in u for s in resp["turn_servers"] for u in s["urls"])


def test_full_signaling_relay_between_two_clients(client, monkeypatch):
    monkeypatch.setenv("VOIP_PRESENCE_TTL_SEC", "1")
    caller = _initiate(client, as_user="alice", body={"callee_user_id": 1002})
    callee = _initiate(client, as_user="bob", body={"callee_user_id": 1001})
    call_id = caller["call_id"]

    caller_path = _ws_path_from_signaling_url(caller["signaling_server"])
    callee_path = _ws_path_from_signaling_url(callee["signaling_server"])
    assert "role=caller" in caller_path
    assert "role=callee" in callee_path

    with client.websocket_connect(caller_path) as ws_caller, \
            client.websocket_connect(callee_path) as ws_callee:
        # 1) caller -> offer -> callee 수신
        ws_caller.send_json({"type": "offer", "call_id": call_id, "sdp": "SDP_OFFER"})
        received = ws_callee.receive_json()
        assert received["type"] == "offer"
        assert received["sdp"] == "SDP_OFFER"
        assert received["from_role"] == "caller"

        # 2) callee -> answer -> caller 수신
        ws_callee.send_json({"type": "answer", "call_id": call_id, "sdp": "SDP_ANSWER"})
        received = ws_caller.receive_json()
        assert received["type"] == "answer"
        assert received["sdp"] == "SDP_ANSWER"

        # 3) candidate 양방향 릴레이
        ws_caller.send_json({"type": "candidate", "call_id": call_id, "candidate": "cand-A", "sdpMid": "0", "sdpMLineIndex": 0})
        received = ws_callee.receive_json()
        assert received["type"] == "candidate"
        assert received["candidate"] == "cand-A"
        assert received["sdpMid"] == "0"

        # 4) chat_message 릴레이
        ws_callee.send_json({"type": "chat_message", "call_id": call_id, "text": "안녕하세요"})
        received = ws_caller.receive_json()
        assert received["type"] == "chat_message"
        assert received["text"] == "안녕하세요"
        assert received["from_role"] == "callee"

        # 5) voice_translation 릴레이
        ws_caller.send_json({
            "type": "voice_translation", "call_id": call_id,
            "transcript": "Hello", "translated_text": "안녕",
            "source_lang": "en", "target_lang": "ko",
        })
        received = ws_callee.receive_json()
        assert received["type"] == "voice_translation"
        assert received["translated_text"] == "안녕"

        # 6) ping -> pong (송신자에게), presence TTL 갱신
        time.sleep(1.1)
        ws_caller.send_json({"type": "ping", "call_id": call_id})
        pong = ws_caller.receive_json()
        assert pong["type"] == "pong"
        online = _run(get_presence().is_online(1001))
        assert online is True

        # 7) hangup -> 상대 수신
        ws_caller.send_json({"type": "hangup", "call_id": call_id})
        received = ws_callee.receive_json()
        assert received["type"] == "hangup"

    # 통화 종료 후 audit에 핵심 이벤트가 기록되어야 함
    audit = client.get(f"/api/v1/voip/calls/{call_id}/audit", headers={"X-Test-User": "alice"}).json()
    event_types = {e["type"] for e in audit["events"]}
    assert {"initiate", "accept", "offer", "answer", "ws_connected"}.issubset(event_types)
    assert audit["status"] == "ended"


def test_ws_rejects_invalid_token(client):
    caller = _initiate(client, as_user="alice", body={"callee_user_id": 1002})
    call_id = caller["call_id"]
    from fastapi import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/voip/ws/{call_id}?token=bogus&role=caller") as ws:
            ws.receive_json()
