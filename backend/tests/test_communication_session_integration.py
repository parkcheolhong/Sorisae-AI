"""Session Core ↔ hot path 얇은 연결(integration) 테스트.

검증: flag off no-op / flag on 기록 / 예외 안전(절대 throw 안 함) / contract 단순 스칼라.
"""

from __future__ import annotations

import pytest

from backend.communication.session import integration


@pytest.fixture(autouse=True)
def _reset_manager(monkeypatch):
    # 각 테스트 전후 매니저 싱글턴 초기화(환경변수 토글 반영).
    integration.reset_manager_for_test()
    yield
    monkeypatch.delenv("COMM_V2_SESSION_CORE", raising=False)
    integration.reset_manager_for_test()


def test_record_call_init_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_SESSION_CORE", raising=False)
    integration.reset_manager_for_test()
    integration.record_call_init("s1", call_id="c1", source_lang="ko", target_lang="ja")
    mgr = integration._get_manager()
    assert mgr.enabled is False
    assert mgr.get("s1") is None  # off → no-op


def test_record_call_init_and_relay_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_SESSION_CORE", "1")
    integration.reset_manager_for_test()

    integration.record_call_init(
        "s1",
        call_id="c1",
        source_lang="ko",
        target_lang="ja",
        participants=[("caller@x", "ko"), ("9", "ja")],
    )
    mgr = integration._get_manager()
    ctx = mgr.get("s1")
    assert ctx is not None
    assert ctx.call_id == "c1"
    assert (ctx.language_pair.source, ctx.language_pair.target) == ("ko", "ja")
    assert set(ctx.participants) == {"caller@x", "9"}

    integration.record_relay_turn(
        "s1",
        call_id="c1",
        source_lang="ko",
        target_lang="ja",
        source_text="안녕",
        translated_text="こんにちは",
    )
    turns = mgr.recent_turns("s1")
    assert len(turns) == 1
    assert turns[0].source_text == "안녕"
    assert turns[0].translated_text == "こんにちは"


def test_no_session_id_is_noop(monkeypatch):
    monkeypatch.setenv("COMM_V2_SESSION_CORE", "1")
    integration.reset_manager_for_test()
    integration.record_call_init(None, call_id="c1", source_lang="ko", target_lang="ja")
    integration.record_relay_turn("", source_lang="ko", target_lang="ja", source_text="x")
    mgr = integration._get_manager()
    assert mgr.store.count() == 0


def test_relay_without_language_pair_is_noop(monkeypatch):
    monkeypatch.setenv("COMM_V2_SESSION_CORE", "1")
    integration.reset_manager_for_test()
    integration.record_relay_turn("s1", source_lang=None, target_lang="ja", source_text="x")
    mgr = integration._get_manager()
    # 언어쌍 불완전 → 턴 미기록(세션도 생성 안 함).
    assert mgr.get("s1") is None


def test_build_context_hint(monkeypatch):
    monkeypatch.setenv("COMM_V2_SESSION_CORE", "1")
    integration.reset_manager_for_test()
    # off→on 후 턴 누적.
    integration.record_relay_turn(
        "s1", source_lang="ko", target_lang="ja", source_text="박 대표님", translated_text="パク代表"
    )
    integration.record_relay_turn(
        "s1", source_lang="ko", target_lang="ja", source_text="회의 시작", translated_text="会議開始"
    )
    hint = integration.build_context_hint("s1", max_turns=4)
    assert hint is not None
    assert "박 대표님 -> パク代表" in hint
    assert "회의 시작 -> 会議開始" in hint


def test_build_context_hint_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_SESSION_CORE", raising=False)
    integration.reset_manager_for_test()
    assert integration.build_context_hint("s1") is None


def test_never_raises_even_on_bad_input(monkeypatch):
    monkeypatch.setenv("COMM_V2_SESSION_CORE", "1")
    integration.reset_manager_for_test()
    # 비정상 타입을 넣어도 hot path 로 예외가 새지 않아야 한다.
    integration.record_call_init(123, call_id=object(), source_lang=5, target_lang=[])  # type: ignore[arg-type]
    integration.record_relay_turn(  # type: ignore[arg-type]
        {"bad": 1}, source_lang=object(), target_lang=object(), source_text=None
    )
    # 예외 없이 도달하면 성공.
    assert True
