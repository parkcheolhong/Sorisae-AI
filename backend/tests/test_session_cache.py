"""[#4] 활성 세션 Redis 캐시 단위 테스트 (fail-open · write-through 일관성).

실제 Redis 없이 fake 캐시로 라운드트립/센티넬/비활성/캐시-히트 단락을 검증한다.
"""
from __future__ import annotations

import pytest

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
