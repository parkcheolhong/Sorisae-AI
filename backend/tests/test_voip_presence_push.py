"""P3-A: 디바이스 등록 + presence + 콜리 착신 FCM 푸시 테스트(인메모리, 푸시 모킹)."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import backend.voip.router as voip_router_module
from backend.auth import get_current_user
from backend.voip import push
from backend.voip.presence import get_presence
from backend.voip.router import router as voip_router


class _FakeUser:
    def __init__(self, uid, username):
        self.id = uid
        self.username = username
        self.email = f"{username}@example.com"
        self.is_active = True


_USERS = {"alice": _FakeUser(3001, "alice3"), "bob": _FakeUser(3002, "bob3")}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(voip_router)

    async def _dep(request: Request):
        return _USERS.get(request.headers.get("x-test-user", "alice"), _USERS["alice"])

    app.dependency_overrides[get_current_user] = _dep
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset():
    import asyncio
    from backend.voip.registry import registry
    from backend.voip.signaling import hub
    registry._rooms.clear()
    hub._rooms.clear()
    # 인메모리 presence 초기화
    p = get_presence()
    p._devices.clear()
    p._presence.clear()
    yield


def test_device_register_stores_token_and_marks_online(client):
    import asyncio
    resp = client.post("/api/v1/voip/devices/register",
                       json={"fcm_token": "tok-bob-1", "platform": "android"},
                       headers={"X-Test-User": "bob"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    p = get_presence()
    devices = asyncio.get_event_loop().run_until_complete(p.get_devices(3002))
    assert "tok-bob-1" in devices
    online = asyncio.get_event_loop().run_until_complete(p.is_online(3002))
    assert online is True


def test_initiate_sends_incoming_call_push_to_callee(client, monkeypatch):
    captured = {}

    async def _fake_push(tokens, *, call_id, caller_label="", data=None):
        captured["tokens"] = list(tokens)
        captured["call_id"] = call_id
        captured["caller_label"] = caller_label
        return {"sent": len(tokens), "skipped": False, "reason": None}

    monkeypatch.setattr(push, "send_incoming_call_push", _fake_push)

    # 콜리(bob) 디바이스 등록 → 토큰/presence 확보
    client.post("/api/v1/voip/devices/register",
                json={"fcm_token": "tok-bob-1"}, headers={"X-Test-User": "bob"})

    # 발신자(alice) → 콜리(bob) 통화 개시
    resp = client.post("/api/v1/voip/calls/initiate",
                       json={"callee_user_id": 3002}, headers={"X-Test-User": "alice"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    call_id = data["call_id"]

    # 푸시가 콜리 토큰으로, call_id와 함께 전송되었는지
    assert captured.get("call_id") == call_id
    assert captured.get("tokens") == ["tok-bob-1"]
    assert data["callee_app_online"] is True  # bob이 방금 등록 → 온라인

    # audit에 push_sent 기록
    audit = client.get(f"/api/v1/voip/calls/{call_id}/audit", headers={"X-Test-User": "alice"}).json()
    assert "push_sent" in {e["type"] for e in audit["events"]}


def test_initiate_offline_callee_no_tokens_push_skipped(client, monkeypatch):
    captured = {}

    async def _fake_push(tokens, *, call_id, caller_label="", data=None):
        captured["called"] = True
        captured["tokens"] = list(tokens)
        return {"sent": 0, "skipped": True, "reason": "no_tokens"}

    monkeypatch.setattr(push, "send_incoming_call_push", _fake_push)

    # bob 미등록 → 토큰 없음, presence 없음
    resp = client.post("/api/v1/voip/calls/initiate",
                       json={"callee_user_id": 3002}, headers={"X-Test-User": "alice"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["callee_app_online"] is False
    assert captured.get("tokens") == []
    audit = client.get(f"/api/v1/voip/calls/{data['call_id']}/audit", headers={"X-Test-User": "alice"}).json()
    assert "push_skipped" in {e["type"] for e in audit["events"]}


def test_accept_call_joins_as_callee(client):
    # 발신자 통화 개시 → 콜리가 push로 받은 call_id로 accept 합류.
    init = client.post("/api/v1/voip/calls/initiate",
                       json={"callee_user_id": 3002}, headers={"X-Test-User": "alice"}).json()
    call_id = init["call_id"]

    resp = client.post(f"/api/v1/voip/calls/{call_id}/accept", headers={"X-Test-User": "bob"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["call_id"] == call_id
    assert data["participant_role"] == "callee"
    assert "role=callee" in data["signaling_server"]

    audit = client.get(f"/api/v1/voip/calls/{call_id}/audit", headers={"X-Test-User": "alice"}).json()
    assert "accept" in {e["type"] for e in audit["events"]}


def test_accept_unknown_call_returns_404(client):
    resp = client.post("/api/v1/voip/calls/c_nonexistent/accept", headers={"X-Test-User": "bob"})
    assert resp.status_code == 404


def test_push_adapter_skips_when_not_configured(monkeypatch):
    import asyncio
    monkeypatch.delenv("FCM_ENABLED", raising=False)
    result = asyncio.get_event_loop().run_until_complete(
        push.send_incoming_call_push(["tok"], call_id="c_1", caller_label="alice")
    )
    assert result["skipped"] is True
    assert result["reason"] == "not_configured"
