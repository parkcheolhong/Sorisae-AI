"""P2 Redis 백엔드 VoIP 시그널링 통합 테스트.

VOIP_REDIS_URL 활성화 시: 룸 메타데이터/감사가 Redis에 저장되고, 시그널링 릴레이가
pub/sub 채널로 브리지되는지 라이브 Redis로 검증한다(라이브 Redis 미가용 시 skip).
"""
import time
from urllib.parse import urlparse

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

REDIS_TEST_URL = "redis://127.0.0.1:6380/5"


def _redis_available() -> bool:
    try:
        import redis  # noqa: F401
        client = redis.Redis.from_url(REDIS_TEST_URL)
        client.ping()
        client.flushdb()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_available(), reason="라이브 Redis(127.0.0.1:6380) 미가용")


class _FakeUser:
    def __init__(self, uid: int, username: str):
        self.id = uid
        self.username = username
        self.email = f"{username}@example.com"
        self.is_active = True


_USERS = {"alice": _FakeUser(2001, "alice2"), "bob": _FakeUser(2002, "bob2")}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("VOIP_REDIS_URL", REDIS_TEST_URL)
    # 테스트 간 잔여 상태 제거를 위해 db를 비운다.
    import redis as _redis
    _redis.Redis.from_url(REDIS_TEST_URL).flushdb()
    # 모듈 전역 캐시 초기화(다른 테스트의 인메모리 선택 영향 제거).
    import backend.voip.redis_backend as rb
    rb._client = None
    rb._redis_store = None
    rb._redis_relay = None

    from backend.auth import get_current_user
    from backend.voip.router import router as voip_router

    async def _dep(request: Request):
        key = request.headers.get("x-test-user", "alice")
        return _USERS.get(key, _USERS["alice"])

    app = FastAPI()
    app.include_router(voip_router)
    app.dependency_overrides[get_current_user] = _dep
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    rb._client = None
    rb._redis_store = None
    rb._redis_relay = None


def _ws_path(url: str) -> str:
    p = urlparse(url)
    return f"{p.path}?{p.query}"


def _initiate(client, as_user, body):
    r = client.post("/api/v1/voip/calls/initiate", json=body, headers={"X-Test-User": as_user})
    assert r.status_code == 200, r.text
    return r.json()


def test_redis_store_backs_initiate_audit_and_matching(client):
    caller = _initiate(client, "alice", {"callee_user_id": 2002})
    assert caller["participant_role"] == "caller"
    callee = _initiate(client, "bob", {"callee_user_id": 2001})
    assert callee["call_id"] == caller["call_id"]
    assert callee["participant_role"] == "callee"

    # audit가 Redis에서 조회되어야 함.
    audit = client.get(f"/api/v1/voip/calls/{caller['call_id']}/audit", headers={"X-Test-User": "alice"}).json()
    assert audit["status"] in ("ringing", "connecting")
    assert {"initiate", "accept"}.issubset({e["type"] for e in audit["events"]})


def test_redis_pubsub_relay_between_two_clients(client):
    caller = _initiate(client, "alice", {"callee_user_id": 2002})
    callee = _initiate(client, "bob", {"callee_user_id": 2001})
    call_id = caller["call_id"]

    with client.websocket_connect(_ws_path(caller["signaling_server"])) as ws_caller, \
            client.websocket_connect(_ws_path(callee["signaling_server"])) as ws_callee:
        # pub/sub 구독이 활성화될 시간을 잠시 확보.
        time.sleep(0.3)

        ws_caller.send_json({"type": "offer", "call_id": call_id, "sdp": "REDIS_OFFER"})
        got = ws_callee.receive_json()
        assert got["type"] == "offer"
        assert got["sdp"] == "REDIS_OFFER"
        assert got["from_role"] == "caller"

        ws_callee.send_json({"type": "answer", "call_id": call_id, "sdp": "REDIS_ANSWER"})
        got = ws_caller.receive_json()
        assert got["type"] == "answer"
        assert got["sdp"] == "REDIS_ANSWER"

        ws_caller.send_json({"type": "ping", "call_id": call_id})
        assert ws_caller.receive_json()["type"] == "pong"

        ws_caller.send_json({"type": "hangup", "call_id": call_id})
        assert ws_callee.receive_json()["type"] == "hangup"

    audit = client.get(f"/api/v1/voip/calls/{call_id}/audit", headers={"X-Test-User": "alice"}).json()
    types = {e["type"] for e in audit["events"]}
    assert {"offer", "answer", "ws_connected"}.issubset(types)
    assert audit["status"] == "ended"
