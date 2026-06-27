"""Designated-language enforcement helpers."""

from __future__ import annotations

import pytest

from backend.designated_language import (
    DESIGNATED_LANGUAGE_MISMATCH_DETAIL,
    detected_language_matches_designated,
    text_matches_designated_language,
)


def test_text_matches_designated_language_korean_only():
    assert text_matches_designated_language("안녕하세요", "ko") is True
    assert text_matches_designated_language("こんにちは", "ko") is False
    assert text_matches_designated_language("안녕 hello", "ko") is False


def test_text_matches_designated_language_japanese_only():
    assert text_matches_designated_language("こんにちは", "ja") is True
    assert text_matches_designated_language("안녕하세요", "ja") is False


def test_detected_language_matches_designated():
    assert detected_language_matches_designated("ko", "ko") is True
    assert detected_language_matches_designated("ja", "ko") is False
    assert detected_language_matches_designated(None, "ko") is True


def test_mismatch_detail_is_korean():
    assert "지정 언어" in DESIGNATED_LANGUAGE_MISMATCH_DETAIL
