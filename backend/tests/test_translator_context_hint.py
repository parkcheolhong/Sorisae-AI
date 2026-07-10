"""translator.translate(context_hint=...) 동작 테스트 (LLM 비의존).

검증:
- context_hint 가 _llm_translate 로 그대로 전달된다.
- context_hint 제공 시 원격 캐시를 우회한다(턴 특이적).
- context_hint=None(기본)이면 기존 동작(캐시 사용)과 동일 → 대면/기존 호출부 무회귀.
"""

from __future__ import annotations

from backend.services.nadotongryoksa.translator import NadoTranslator


def _fresh_translator(monkeypatch):
    t = NadoTranslator.get_instance()
    # 캐시 격리.
    with t._cache_lock:
        t._cache.clear()
    # googletrans 폴백이 호출되지 않도록 방어.
    monkeypatch.setattr(t, "_googletrans", lambda *a, **k: None)
    return t


def test_context_hint_passed_through(monkeypatch):
    t = _fresh_translator(monkeypatch)
    seen = {}

    def fake_llm(text, from_lang, to_lang, context_hint=None):
        seen["context_hint"] = context_hint
        return "RESULT"

    monkeypatch.setattr(t, "_llm_translate", fake_llm)
    out = t.translate("회의 시작", from_lang="ko", to_lang="ja", context_hint="박 대표님 -> パク代表")
    assert out == "RESULT"
    assert seen["context_hint"] == "박 대표님 -> パク代表"


def test_context_hint_bypasses_cache(monkeypatch):
    t = _fresh_translator(monkeypatch)
    calls = {"n": 0}

    def fake_llm(text, from_lang, to_lang, context_hint=None):
        calls["n"] += 1
        return f"R{calls['n']}"

    monkeypatch.setattr(t, "_llm_translate", fake_llm)
    # 맥락 주입 2회 → 캐시 우회로 매번 LLM 호출.
    t.translate("같은문장", from_lang="ko", to_lang="ja", context_hint="ctx1")
    t.translate("같은문장", from_lang="ko", to_lang="ja", context_hint="ctx2")
    assert calls["n"] == 2


def test_no_context_uses_cache(monkeypatch):
    t = _fresh_translator(monkeypatch)
    calls = {"n": 0}

    def fake_llm(text, from_lang, to_lang, context_hint=None):
        calls["n"] += 1
        assert context_hint is None
        return "CACHED"

    monkeypatch.setattr(t, "_llm_translate", fake_llm)
    t.translate("문장A", from_lang="ko", to_lang="ja")
    t.translate("문장A", from_lang="ko", to_lang="ja")
    # 두 번째는 캐시 적중 → LLM 1회만.
    assert calls["n"] == 1
