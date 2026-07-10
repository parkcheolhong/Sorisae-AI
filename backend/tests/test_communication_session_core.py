"""Session Core (얇은 버전) 단위 테스트.

검증: 플래그 off no-op / on 동작 / 언어쌍 기억 / 턴 캡 / TTL 만료 / LRU evict / thread-safe.
hot path 무접촉 보장(플래그 off 기본).
"""

from __future__ import annotations

import threading
import time

from backend.communication.session.config import SessionCoreConfig
from backend.communication.session.manager import SessionManager
from backend.communication.session.models import LanguagePair, Participant, TurnRecord
from backend.communication.session.store import InMemorySessionStore


def _enabled_config(**kw) -> SessionCoreConfig:
    base = dict(enabled=True, ttl_sec=3600, max_turns=50, max_sessions=10000)
    base.update(kw)
    return SessionCoreConfig(**base)


def test_disabled_by_default_is_noop():
    mgr = SessionManager(config=SessionCoreConfig(enabled=False))
    assert mgr.enabled is False
    assert mgr.get_or_create("s1", call_id="c1") is None
    assert mgr.update_language_pair("s1", "ko", "ja") is None
    assert mgr.record_turn("s1", TurnRecord(direction=LanguagePair("ko", "ja"))) is None
    assert mgr.language_pair("s1") is None
    assert mgr.recent_turns("s1") == []
    assert mgr.purge_expired() == 0
    assert mgr.store.count() == 0


def test_enabled_get_or_create_and_idempotent():
    mgr = SessionManager(config=_enabled_config())
    ctx = mgr.get_or_create("s1", call_id="c1")
    assert ctx is not None
    assert ctx.session_id == "s1"
    assert ctx.call_id == "c1"
    # 재호출은 동일 인스턴스 반환(중복 생성 없음).
    again = mgr.get_or_create("s1")
    assert again is ctx
    assert mgr.store.count() == 1


def test_language_pair_memory_and_normalization():
    mgr = SessionManager(config=_enabled_config())
    mgr.update_language_pair("s1", " KO ", "JA")
    pair = mgr.language_pair("s1")
    assert pair == LanguagePair("ko", "ja")
    # 갱신되면 최신값 기억.
    mgr.update_language_pair("s1", "ja", "ko")
    assert mgr.language_pair("s1") == LanguagePair("ja", "ko")


def test_record_turn_updates_language_and_caps_history():
    mgr = SessionManager(config=_enabled_config(max_turns=3))
    for i in range(5):
        mgr.record_turn(
            "s1",
            TurnRecord(
                direction=LanguagePair("ko", "ja"),
                source_text=f"src{i}",
                translated_text=f"dst{i}",
            ),
        )
    turns = mgr.recent_turns("s1")
    assert len(turns) == 3  # max_turns 캡
    assert [t.source_text for t in turns] == ["src2", "src3", "src4"]
    # 턴 기록이 언어쌍도 갱신.
    assert mgr.language_pair("s1") == LanguagePair("ko", "ja")


def test_recent_turns_limit():
    mgr = SessionManager(config=_enabled_config())
    for i in range(10):
        mgr.record_turn("s1", TurnRecord(direction=LanguagePair("ko", "en"), source_text=str(i)))
    assert len(mgr.recent_turns("s1", limit=4)) == 4
    assert mgr.recent_turns("s1", limit=4)[-1].source_text == "9"


def test_participants_upsert():
    mgr = SessionManager(config=_enabled_config())
    mgr.upsert_participant("s1", Participant(user_ref="u1", preferred_language="ko"))
    mgr.upsert_participant("s1", Participant(user_ref="u2", preferred_language="ja"))
    ctx = mgr.get("s1")
    assert set(ctx.participants) == {"u1", "u2"}
    # 같은 user_ref 갱신.
    mgr.upsert_participant("s1", Participant(user_ref="u1", preferred_language="en"))
    assert mgr.get("s1").participants["u1"].preferred_language == "en"


def test_end_session_removes_context():
    mgr = SessionManager(config=_enabled_config())
    mgr.get_or_create("s1")
    assert mgr.store.count() == 1
    mgr.end_session("s1")
    assert mgr.store.count() == 0
    assert mgr.get("s1") is None


def test_ttl_purge_expired():
    store = InMemorySessionStore()
    mgr = SessionManager(store=store, config=_enabled_config(ttl_sec=0))
    mgr.get_or_create("s1")
    time.sleep(0.01)
    purged = mgr.purge_expired()
    assert purged == 1
    assert mgr.store.count() == 0


def test_lru_evict_on_capacity():
    mgr = SessionManager(config=_enabled_config(max_sessions=2))
    mgr.get_or_create("s1")
    time.sleep(0.01)
    mgr.get_or_create("s2")
    time.sleep(0.01)
    mgr.get_or_create("s3")  # s1(가장 오래됨) evict
    assert mgr.store.count() == 2
    assert mgr.get("s1") is None
    assert mgr.get("s2") is not None
    assert mgr.get("s3") is not None


def test_thread_safe_concurrent_writes():
    mgr = SessionManager(config=_enabled_config(max_sessions=10000))

    def worker(n: int) -> None:
        for i in range(50):
            mgr.record_turn(
                f"s{n}",
                TurnRecord(direction=LanguagePair("ko", "ja"), source_text=str(i)),
            )

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert mgr.store.count() == 8
    for n in range(8):
        assert len(mgr.recent_turns(f"s{n}")) == 50
