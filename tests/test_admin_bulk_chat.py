import pytest  # pyright: ignore[reportMissingImports]

from backend.services.admin_bulk_chat import (
    SELF_ROOM_TITLE,
    _build_chat_recipient_rows,
    preview_bulk_chat_campaign,
)
from backend.services.admin_bulk_notify_common import (
    resolve_user_notify_language,
    summarize_recipients_by_language,
)


class _FakeUser:
    def __init__(self, user_id: int, *, preferred_language=None, country_code=None):
        self.id = user_id
        self.preferred_language = preferred_language
        self.country_code = country_code


def test_build_chat_recipient_rows_no_phone_required():
    users = [
        _FakeUser(1, preferred_language="ko", country_code="KR"),
        _FakeUser(2, preferred_language=None, country_code="US"),
    ]
    rows = _build_chat_recipient_rows(users, source_text="안내", source_lang="ko")
    assert len(rows) == 2
    assert rows[0]["user_id"] == 1
    assert rows[0]["language"] == "ko"
    assert "body" in rows[0]
    assert rows[1]["language"] == "en"


def test_preview_bulk_chat_campaign_requires_text():
    with pytest.raises(ValueError, match="안내 문구"):
        preview_bulk_chat_campaign(None, source_text="   ")


def test_self_room_title_constant():
    assert SELF_ROOM_TITLE == "번역 보관함"


def test_resolve_user_notify_language_prefers_profile():
    assert resolve_user_notify_language(preferred_language="ja", country_code="KR") == "ja"


def test_resolve_user_notify_language_country_fallback():
    assert resolve_user_notify_language(preferred_language=None, country_code="JP") == "ja"
    assert resolve_user_notify_language(preferred_language=None, country_code="HK") == "zh-hk"
    assert resolve_user_notify_language(preferred_language=None, country_code="ZZ") == "en"


def test_summarize_recipients_by_language():
    summary = summarize_recipients_by_language([
        {"language": "ko", "body": "안녕", "country_code": "KR"},
        {"language": "en", "body": "Hello", "country_code": "US"},
        {"language": "ko", "body": "안녕", "country_code": "KR"},
    ])
    assert len(summary) == 2
    ko = next(item for item in summary if item["language"] == "ko")
    assert ko["count"] == 2
    assert ko["sample_body"] == "안녕"
