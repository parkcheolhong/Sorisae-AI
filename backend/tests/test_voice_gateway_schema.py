"""voice_gateway 응답 스키마 회귀 테스트.

VoiceResponse에 detected_language 필드가 누락되어(Pydantic이 extra 인자를 드롭),
모바일 자동 언어전환이 항상 undefined를 받던 버그의 회귀 방지.
"""
from backend.llm.voice_gateway import VoiceResponse


def test_voice_response_exposes_detected_language():
    resp = VoiceResponse(
        transcript="こんにちは",
        response_text="안녕하세요",
        detected_language="ja",
    )
    dumped = resp.model_dump()
    assert "detected_language" in dumped
    assert dumped["detected_language"] == "ja"


def test_voice_response_detected_language_defaults_to_none():
    resp = VoiceResponse(transcript="hi", response_text="hello")
    assert resp.detected_language is None
