"""D-4-3: VoIP·Voice Translate 순수 함수 회귀 테스트 확대."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.marketplace.nadotongryoksa_voip_router import (
    VALID_CALL_MODES,
    _append_mode_message,
    _build_tel_url,
    _build_voice_id,
    _build_voice_translation_relay_payload,
    _build_voip_topic,
    _collapse_voice_relay_text,
    _normalize_call_mode,
    _resolve_call_language_hint,
    _serialize_voip_payload,
    _should_reject_voice_translation_relay,
    _with_signal_role,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("hello world", "hello world"),
        ("same. same. same.", "same"),
        ("repeat, repeat, repeat", "repeat"),
    ],
)
def test_collapse_voice_relay_text(text, expected):
    assert _collapse_voice_relay_text(text) == expected


@pytest.mark.parametrize(
    ("source", "target", "transcript", "translation", "reject"),
    [
        ("ko", "en", "", "hello", True),
        ("ko", "en", "안녕", "", True),
        ("ko", "en", "hello", "hello", True),
        ("ko", "en", "안녕하세요", "Hello", False),
        ("ko", "ko", "same", "same", False),
    ],
)
def test_should_reject_voice_translation_relay(source, target, transcript, translation, reject):
    assert _should_reject_voice_translation_relay(
        source_lang=source,
        target_lang=target,
        transcript=transcript,
        translated_text=translation,
    ) is reject


@pytest.mark.parametrize(
    ("raw", "has_app_target", "expected"),
    [
        ("voip_full_auto", True, "voip_full_auto"),
        ("pstn_assist", False, "pstn_assist"),
        ("", True, "voip_full_auto"),
        ("", False, "pstn_assist"),
        ("unknown", True, "voip_full_auto"),
    ],
)
def test_normalize_call_mode(raw, has_app_target, expected):
    assert _normalize_call_mode(raw, has_app_target=has_app_target) == expected


def test_valid_call_modes_contains_expected_values():
    assert VALID_CALL_MODES == {"pstn_assist", "voip_full_auto"}


def test_append_mode_message_includes_mode_and_relay_flags():
    message = _append_mode_message(
        "통화 준비",
        resolved_mode="voip_full_auto",
        auto_relay_applied=True,
        error_code=None,
    )
    assert "VoIP 완전자동" in message
    assert "자동 릴레이 활성화" in message


def test_append_mode_message_includes_fallback_error():
    message = _append_mode_message(
        "통화 준비",
        resolved_mode="pstn_assist",
        auto_relay_applied=False,
        error_code="VOIP_MODE_FALLBACK_TO_PSTN_ASSIST",
    )
    assert "일반통화 보조" in message
    assert "폴백" in message


@pytest.mark.parametrize(
    ("voice_id", "expected"),
    [
        ("nado-000042", "worldlingo_voip_nado_000042"),
        ("", ""),
        ("a.b/c", "worldlingo_voip_a_b_c"),
    ],
)
def test_build_voip_topic(voice_id, expected):
    assert _build_voip_topic(voice_id) == expected


def test_build_voice_id_formats_user():
    assert _build_voice_id(SimpleNamespace(id=7)) == "nado-000007"


@pytest.mark.parametrize(
    ("url", "role", "expected_suffix"),
    [
        ("ws://localhost/signal?call_id=1", "caller", "role=caller"),
        ("ws://localhost/signal", "callee", "?role=callee"),
    ],
)
def test_with_signal_role(url, role, expected_suffix):
    assert expected_suffix in _with_signal_role(url, role)


@pytest.mark.parametrize(
    ("phone", "expected"),
    [
        ("010-1234-5678", "tel:01012345678"),
        ("+82-10-1234-5678", "tel:+821012345678"),
    ],
)
def test_build_tel_url(phone, expected):
    assert _build_tel_url(phone) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (("ko", None), "ko"),
        (("auto", "en"), "en"),
        (("", None), None),
        (("xx", "ja"), "ja"),
    ],
)
def test_resolve_call_language_hint(values, expected):
    assert _resolve_call_language_hint(*values) == expected


def test_serialize_voip_payload_is_stable_json():
    payload = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    serialized = _serialize_voip_payload(payload)
    assert serialized == '{"a":1,"b":2,"nested":{"y":8,"z":9}}'


def test_build_voice_translation_relay_payload_rejects_identical_translation():
    payload = _build_voice_translation_relay_payload(
        {
            "transcript": "hello",
            "translated_text": "hello",
            "source_lang": "ko",
            "target_lang": "en",
        }
    )
    assert payload == {}


def test_build_voice_translation_relay_payload_accepts_valid_pair():
    payload = _build_voice_translation_relay_payload(
        {
            "transcript": "안녕하세요",
            "translated_text": "Hello",
            "source_lang": "ko",
            "target_lang": "en",
            "seq_id": 3,
        }
    )
    assert payload["type"] == "voice_translation"
    assert payload["transcript"] == "안녕하세요"
    assert payload["translated_text"] == "Hello"
    assert payload["seq_id"] == 3
