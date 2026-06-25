"""Phase5.8 — 소리새 AI 진화형 멀티도메인 동반자 페르소나/기억 주입 단위테스트.

핵심:
- `_friend_system_prompt` 가 관광 단일 정체성을 넘어 멀티도메인 동반자(지식/생활/감정)
  framing 을 포함한다(관광 전문성은 유지 — 회귀 방지).
- `_build_friend_messages` 가 persona_brief 를 시스템 컨텍스트로 주입하되, 비었으면
  기존 메시지 구성을 변경하지 않는다(무회귀, additive).
- persona_brief 는 방어적 상한(PERSONA_BRIEF_MAX_LEN)으로 잘린다.
실 네트워크/LLM 없이 순수 메시지 빌더만 검증한다.
"""

from backend.llm.voice_gateway import (
    PERSONA_BRIEF_MAX_LEN,
    _build_friend_messages,
    _friend_system_prompt,
)


def test_persona_prompt_is_multidomain_companion():
    prompt = _friend_system_prompt("ko")
    low = prompt.lower()
    # 멀티도메인 동반자 framing(지식/생활/감정).
    assert "multi-talented companion" in low or "companion who is there" in low
    assert "how-to" in low
    assert "emotional" in low
    assert "remembers them" in low
    # 관광 전문성은 유지(회귀 방지).
    assert "travel" in low


def test_persona_prompt_has_honesty_contract():
    """사장님 최우선 원칙: 거짓 안내 절대 금지 + 위험지/관습/예절 정직."""
    low = _friend_system_prompt("ko").lower()
    assert "honesty contract" in low
    assert "never" in low and ("fabricat" in low or "invent" in low)
    # 위험지역/법/관습/예절.
    assert "danger" in low
    assert "laws" in low or "law" in low
    assert "custom" in low or "etiquette" in low
    # 주식/시세/최신 — 검증된 데이터 없으면 수치 단정 금지.
    assert "stock" in low or "market" in low
    assert "live" in low or "authoritative" in low


def test_persona_prompt_has_language_pair_tutor():
    low = _friend_system_prompt("ko").lower()
    assert "language" in low and "pair" in low
    assert "pronunciation" in low


def test_persona_brief_injected_as_system_when_present():
    msgs = _build_friend_messages(
        "안녕",
        "ko",
        [],
        persona_brief="[Companion memory] likes coffee.",
    )
    systems = [m for m in msgs if m["role"] == "system"]
    assert any("Companion memory" in m["content"] for m in systems)
    # 마지막은 항상 현재 user 발화.
    assert msgs[-1] == {"role": "user", "content": "안녕"}


def test_no_persona_brief_keeps_baseline_messages():
    base = _build_friend_messages("안녕", "ko", [])
    # 페르소나 시스템 1개 + user 1개 = 2 (그라운딩/브리프 없음).
    assert len(base) == 2
    assert base[0]["role"] == "system"
    assert base[-1] == {"role": "user", "content": "안녕"}


def test_persona_brief_is_length_capped():
    huge = "x" * (PERSONA_BRIEF_MAX_LEN + 500)
    msgs = _build_friend_messages("hi", "en", [], persona_brief=huge)
    injected = [m for m in msgs if m["role"] == "system" and set(m["content"]) == {"x"}]
    assert injected, "brief system message should be present"
    assert len(injected[0]["content"]) == PERSONA_BRIEF_MAX_LEN


def test_history_and_grounding_order_preserved():
    msgs = _build_friend_messages(
        "지금 뭐해",
        "ko",
        [{"role": "user", "content": "이전 질문"}, {"role": "assistant", "content": "이전 답변"}],
        grounding_block="[web] fresh results",
        persona_brief="brief here",
    )
    roles = [m["role"] for m in msgs]
    # system(persona) → system(brief) → system(grounding) → user/assistant 히스토리 → user
    assert roles[0] == "system"
    assert msgs[-1]["content"] == "지금 뭐해"
    assert any("fresh results" in m["content"] for m in msgs if m["role"] == "system")
    assert any(m["content"] == "이전 답변" and m["role"] == "assistant" for m in msgs)
