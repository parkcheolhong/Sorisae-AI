"""[#4] 활성 세션 Redis 캐시 단위 테스트 (fail-open · write-through 일관성).

실제 Redis 없이 fake 캐시로 라운드트립/센티넬/비활성/캐시-히트 단락을 검증한다.
"""
from __future__ import annotations

import importlib

import pytest

import backend.auth_router
from backend import auth
from backend.marketplace import cache_service as cache_mod


class _FakeCache:
    """cache_service 인터페이스 모사 — 인메모리 dict, TTL 무시."""

    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.set_calls = 0
        self.get_calls = 0

    def get(self, key):
        self.get_calls += 1
        return self.store.get(key)

    def set(self, key, value, ttl=300):
        self.set_calls += 1
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return True


@pytest.fixture
def fake_cache(monkeypatch):
    fake = _FakeCache()
    monkeypatch.setattr(cache_mod, "cache_service", fake, raising=True)
    monkeypatch.setenv("SESSION_CACHE_ENABLED", "1")
    return fake


def test_cache_service_init_skips_blocking_ping(monkeypatch):
    calls = {"from_url": 0, "ping": 0}

    class _NoPingRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            calls["from_url"] += 1
            return _NoPingRedis()

        def ping(self):
            calls["ping"] += 1
            raise AssertionError("blocking Redis ping should not run during cache initialization")

    monkeypatch.setattr(cache_mod, "Redis", _NoPingRedis, raising=True)
    reloaded = importlib.reload(cache_mod)

    assert calls["from_url"] >= 1
    assert calls["ping"] == 0
    assert reloaded.cache_service.client is None


def test_put_get_roundtrip_sid(fake_cache):
    auth._session_cache_put(42, "sid-abc-123")
    hit, sid = auth._session_cache_get(42)
    assert hit is True
    assert sid == "sid-abc-123"


def test_put_get_none_sentinel(fake_cache):
    # 'row 없음'(None)도 센티넬로 캐시되어 미스와 구분된다.
    auth._session_cache_put(7, None)
    hit, sid = auth._session_cache_get(7)
    assert hit is True
    assert sid is None


def test_cache_miss_returns_false(fake_cache):
    hit, sid = auth._session_cache_get(999)
    assert hit is False
    assert sid is None


def test_disabled_bypasses_cache(fake_cache, monkeypatch):
    monkeypatch.setenv("SESSION_CACHE_ENABLED", "0")
    auth._session_cache_put(42, "should-not-store")
    assert fake_cache.set_calls == 0
    hit, sid = auth._session_cache_get(42)
    assert hit is False and sid is None


def test_lookup_active_session_short_circuits_on_hit(fake_cache, monkeypatch):
    # 캐시 히트 시 DB 를 만지지 않아야 한다 — SessionLocal 이 호출되면 폭발하도록 심어둔다.
    auth._session_cache_put(15, "cached-sid")

    def _boom():  # pragma: no cover - 호출되면 안 됨
        raise AssertionError("DB should not be touched on cache hit")

    monkeypatch.setattr("backend.database.SessionLocal", _boom, raising=False)
    sid, failed = auth._lookup_active_session(15)
    assert sid == "cached-sid"
    assert failed is False


def test_has_active_session_detects_existing_session(fake_cache):
    auth._session_cache_put(21, "sid-keep-1")
    assert auth.has_active_session(21) is True
    assert auth.has_active_session(999) is False


def test_login_rejects_when_user_already_has_active_session(monkeypatch):
    from fastapi import HTTPException
    from fastapi.security import OAuth2PasswordRequestForm

    class _FakeQuery:
        def __init__(self, entity):
            self.entity = entity

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.entity

    class _FakeUser:
        id = 33
        email = "dup@example.com"
        username = "dup-user"
        hashed_password = "hashed"

    fake_user = _FakeUser()
    fake_db = type("FakeDB", (), {"query": lambda self, *args, **kwargs: _FakeQuery(fake_user)})()

    monkeypatch.setattr("backend.auth_router.verify_password", lambda *args, **kwargs: True)
    monkeypatch.setattr("backend.auth_router._has_active_session_in_db", lambda _db, user_id: user_id == fake_user.id)
    monkeypatch.setattr("backend.auth_router._set_active_session_in_db", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException, match="로그인 상태가 남아 있습니다"):
        backend.auth_router.login(
            form_data=OAuth2PasswordRequestForm(username="dup@example.com", password="pw"),
            db=fake_db,
            _login_quota=None,
        )


def test_logout_clears_only_matching_active_session(monkeypatch):
    class _FakeUser:
        id = 41

    calls: dict[str, object] = {}

    monkeypatch.setattr("backend.auth_router.resolve_token_session_id", lambda token: "sid-41")

    def _capture_clear(user_id: int, *, expected_session_id: str | None = None):
        calls["user_id"] = user_id
        calls["expected_session_id"] = expected_session_id
        return True

    monkeypatch.setattr("backend.auth_router.clear_active_session", _capture_clear)

    response = backend.auth_router.logout(token="fake.jwt.token", current_user=_FakeUser())

    assert response.status_code == 204
    assert calls["user_id"] == 41
    assert calls["expected_session_id"] == "sid-41"


def test_recovery_clear_active_session_uses_verified_reset_token(monkeypatch):
    class _FakeQuery:
        def __init__(self, entity):
            self.entity = entity

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.entity

    class _FakeUser:
        id = 55

    fake_user = _FakeUser()
    fake_db = type("FakeDB", (), {"query": lambda self, *args, **kwargs: _FakeQuery(fake_user)})()

    monkeypatch.setattr(
        "backend.auth_router._assert_verified_recovery_reset_token",
        lambda *_args, **_kwargs: ("reset-session-token", {"user_id": 55, "scope": "admin"}),
    )

    calls: dict[str, object] = {}

    def _capture_clear(user_id: int, *, expected_session_id: str | None = None):
        calls["user_id"] = user_id
        calls["expected_session_id"] = expected_session_id
        return True

    monkeypatch.setattr("backend.auth_router.clear_active_session", _capture_clear)

    response = backend.auth_router.clear_active_session_via_recovery(
        payload=backend.auth_router.PasswordRecoveryClearSessionRequest(
            scope="admin",
            reset_token="reset-token-value",
        ),
        db=fake_db,
    )

    assert response["cleared"] is True
    assert response["must_relogin"] is True
    assert calls["user_id"] == 55
    assert calls["expected_session_id"] is None
