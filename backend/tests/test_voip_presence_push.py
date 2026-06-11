"""P3-A: 디바이스 등록 + presence + 콜리 착신 FCM 푸시 테스트(인메모리, 푸시 모킹)."""
import asyncio

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


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
    import backend.voip.redis_backend as rb
    from backend.voip.redis_backend import get_store
    from backend.voip.signaling import hub

    def _reset_redis_cache():
        rb._client = None
        rb._redis_store = None
        rb._redis_relay = None

    _reset_redis_cache()
    _run(get_store().clear())
    hub._rooms.clear()
    _run(get_presence().clear())
    _reset_redis_cache()
    yield


def test_device_register_stores_token_and_marks_online(client):
    resp = client.post("/api/v1/voip/devices/register",
                       json={"fcm_token": "tok-bob-1", "platform": "android"},
                       headers={"X-Test-User": "bob"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    p = get_presence()
    devices = _run(p.get_devices(3002))
    assert "tok-bob-1" in devices
    online = _run(p.is_online(3002))
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


def test_initiate_records_zero_delivery_push_as_skipped(client, monkeypatch):
    async def _fake_push(tokens, *, call_id, caller_label="", data=None):
        return {"sent": 0, "skipped": False, "reason": None}

    monkeypatch.setattr(push, "send_incoming_call_push", _fake_push)

    client.post("/api/v1/voip/devices/register",
                json={"fcm_token": "tok-bob-1"}, headers={"X-Test-User": "bob"})

    resp = client.post("/api/v1/voip/calls/initiate",
                       json={"callee_user_id": 3002}, headers={"X-Test-User": "alice"})
    assert resp.status_code == 200, resp.text

    call_id = resp.json()["call_id"]
    audit = client.get(f"/api/v1/voip/calls/{call_id}/audit", headers={"X-Test-User": "alice"}).json()
    event_types = {e["type"] for e in audit["events"]}
    assert "push_skipped" in event_types
    assert "push_sent" not in event_types


def test_push_adapter_skips_when_not_configured(monkeypatch):
    monkeypatch.delenv("FCM_ENABLED", raising=False)
    result = _run(push.send_incoming_call_push(["tok"], call_id="c_1", caller_label="alice"))
    assert result["skipped"] is True
    assert result["reason"] == "not_configured"
