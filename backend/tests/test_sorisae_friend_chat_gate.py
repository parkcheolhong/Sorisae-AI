from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VOICE_GATEWAY = REPO_ROOT / "backend" / "llm" / "voice_gateway.py"


def _voice_gateway_source() -> str:
    return VOICE_GATEWAY.read_text(encoding="utf-8", errors="replace")


def test_friend_chat_endpoint_stays_separate_from_orchestrator():
    source = _voice_gateway_source()

    assert '@router.post("/voice/friend-chat"' in source
    assert "무거운 개발 오케스트레이터(/voice/orchestrate)와 100% 분리" in source
    assert "voice_orchestrate" in source


def test_friend_chat_prompt_keeps_travel_and_honesty_guards():
    source = _voice_gateway_source()

    assert "expert worldwide travel guide" in source
    assert "never switch languages or translate" in source
    assert "BUT do NOT fabricate specific local facts" in source
    assert "invent it" in source


def test_friend_chat_keeps_noise_and_speech_sanitizers():
    source = _voice_gateway_source()

    assert "_friend_is_noise_or_hallucination" in source
    assert "_sanitize_friend_reply_for_speech" in source
    assert "no markdown, no asterisks, no bullet lists" in source
