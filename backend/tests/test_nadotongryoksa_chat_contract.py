from __future__ import annotations

from typing import Any
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import create_access_token
from backend.auth import get_current_user
from backend.database import get_db
from backend.marketplace import models
import backend.marketplace.nadotongryoksa_chat_router as chat_router_module
from backend.marketplace.database import Base
from backend.marketplace.nadotongryoksa_chat_router import (
    router as chat_router,
)
from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES


USER_MAP = {
    1: {"email": "owner@example.com", "username": "owner"},
    2: {"email": "friend@example.com", "username": "friend"},
    3: {"email": "guest@example.com", "username": "guest"},
    4: {"email": "newfriend@example.com", "username": "newfriend"},
    5: {"email": "cnfriend@example.com", "username": "cnfriend"},
    6: {"email": "frfriend@example.com", "username": "frfriend"},
    7: {"email": "hifriend@example.com", "username": "hifriend"},
    8: {"email": "vifriend@example.com", "username": "vifriend"},
    9: {"email": "thfriend@example.com", "username": "thfriend"},
}

FULL_LANGUAGE_FRIEND_IDS = {
    language_code: 100 + index
    for index, language_code in enumerate(SUPPORTED_LANGUAGES.keys())
}


def _set_current_user(client: TestClient, current_user_id: int) -> None:
    selected_user = USER_MAP.get(current_user_id)
    if selected_user is None:
        selected_user = {
            "email": f"user{current_user_id}@example.com",
            "username": f"user{current_user_id}",
        }
    app: Any = client.app
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=current_user_id,
            email=selected_user["email"],
            username=selected_user["username"],
            is_active=True,
            is_admin=False,
        )
    )


def _get_last_message_payload(
    client: TestClient, room_id: str, current_user_id: int
) -> dict:
    _set_current_user(client, current_user_id)
    messages_response = client.get(
        f"/api/mobile/chat/rooms/{room_id}/messages"
    )
    assert messages_response.status_code == 200
    payload = messages_response.json()
    assert payload["items"]
    return payload["items"][-1]


def _get_db_for_client(client: TestClient):
    app: Any = client.app
    override_db = app.dependency_overrides[get_db]
    return override_db()


def _build_auth_token(user_id: int) -> str:
    selected_user = USER_MAP.get(user_id)
    if selected_user is None:
        selected_user = {
            "email": f"user{user_id}@example.com",
            "username": f"user{user_id}",
        }
    subject = str(selected_user.get("email") or selected_user["username"])
    return create_access_token({"sub": subject})


def _build_client(current_user_id: int = 1) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all([
            models.User(
                id=1,
                email="owner@example.com",
                username="owner",
                is_active=True,
                preferred_language="ko",
                country_code="KR",
            ),
            models.User(
                id=2,
                email="friend@example.com",
                username="friend",
                is_active=True,
                preferred_language="en",
                country_code="US",
            ),
            models.User(
                id=3,
                email="guest@example.com",
                username="guest",
                is_active=True,
                preferred_language="ja",
                country_code="JP",
            ),
            models.User(
                id=4,
                email="newfriend@example.com",
                username="newfriend",
                is_active=True,
                preferred_language="en",
                country_code="US",
            ),
            models.User(
                id=5,
                email="cnfriend@example.com",
                username="cnfriend",
                is_active=True,
                preferred_language="zh",
                country_code="CN",
            ),
            models.User(
                id=6,
                email="frfriend@example.com",
                username="frfriend",
                is_active=True,
                preferred_language="fr",
                country_code="FR",
            ),
            models.User(
                id=7,
                email="hifriend@example.com",
                username="hifriend",
                is_active=True,
                preferred_language="hi",
                country_code="IN",
            ),
            models.User(
                id=8,
                email="vifriend@example.com",
                username="vifriend",
                is_active=True,
                preferred_language="vi",
                country_code="VN",
            ),
            models.User(
                id=9,
                email="thfriend@example.com",
                username="thfriend",
                is_active=True,
                preferred_language="th",
                country_code="TH",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=2,
                friend_email="friend@example.com",
                friend_username="friend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=4,
                friend_email="newfriend@example.com",
                friend_username="newfriend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=3,
                friend_email="guest@example.com",
                friend_username="guest",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=5,
                friend_email="cnfriend@example.com",
                friend_username="cnfriend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=6,
                friend_email="frfriend@example.com",
                friend_username="frfriend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=7,
                friend_email="hifriend@example.com",
                friend_username="hifriend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=8,
                friend_email="vifriend@example.com",
                friend_username="vifriend",
            ),
            models.Friend(
                user_id=1,
                friend_user_id=9,
                friend_email="thfriend@example.com",
                friend_username="thfriend",
            ),
            models.Friend(
                user_id=2,
                friend_user_id=4,
                friend_email="newfriend@example.com",
                friend_username="newfriend",
            ),
        ])
        for language_code, user_id in FULL_LANGUAGE_FRIEND_IDS.items():
            username = f"lang_{language_code.replace('-', '_')}"
            email = f"{username}@example.com"
            db.add(
                models.User(
                    id=user_id,
                    email=email,
                    username=username,
                    is_active=True,
                    preferred_language=language_code,
                    country_code=(language_code.split("-")[0] or "ZZ")
                    .upper()[:2],
                )
            )
            db.add(
                models.Friend(
                    user_id=1,
                    friend_user_id=user_id,
                    friend_email=email,
                    friend_username=username,
                )
            )
        db.commit()

    app = FastAPI()
    app.include_router(chat_router, prefix="/api")

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    _set_current_user(client, current_user_id)
    return client


def test_chat_room_lifecycle_supports_self_room_and_translation_message(
) -> None:
    client = _build_client()

    room_response = client.post("/api/mobile/chat/rooms/self", json={})
    assert room_response.status_code == 200
    room_payload = room_response.json()
    assert room_payload["title"] == "번역 보관함"

    message_response = client.post(
        f"/api/mobile/chat/rooms/{room_payload['room_id']}/messages",
        json={
            "message_type": "translation",
            "body": "안녕하세요",
            "translated_body": "Hello",
            "source_lang": "ko",
            "target_lang": "en",
        },
    )
    assert message_response.status_code == 200
    message_payload = message_response.json()
    assert message_payload["message_type"] == "translation"
    assert message_payload["translated_body"] == "Hello"

    rooms_response = client.get("/api/mobile/chat/rooms")
    assert rooms_response.status_code == 200
    items = rooms_response.json()["items"]
    assert len(items) == 1
    assert items[0]["last_message_preview"] == "Hello"

    messages_response = client.get(
        f"/api/mobile/chat/rooms/{room_payload['room_id']}/messages"
    )
    assert messages_response.status_code == 200
    assert len(messages_response.json()["items"]) == 1


def test_direct_room_reuses_existing_room_for_same_friend_pair() -> None:
    client = _build_client()

    first_response = client.post(
        "/api/mobile/chat/rooms/direct",
        json={"friend_user_id": 2},
    )
    assert first_response.status_code == 200
    second_response = client.post(
        "/api/mobile/chat/rooms/direct",
        json={"friend_user_id": 2},
    )
    assert second_response.status_code == 200
    assert (
        first_response.json()["room_id"]
        == second_response.json()["room_id"]
    )


def test_direct_room_text_messages_auto_translate_by_counterpart_language(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    room_response = client.post(
        "/api/mobile/chat/rooms/direct",
        json={"friend_user_id": 2},
    )
    assert room_response.status_code == 200
    room_id = room_response.json()["room_id"]

    send_ko_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "안녕하세요"},
    )
    assert send_ko_response.status_code == 200
    send_ko_payload = send_ko_response.json()
    assert send_ko_payload["body_source_lang"] == "ko"
    assert send_ko_payload["body_target_lang"] == "en"
    assert send_ko_payload["translated_body"] == "ko->en:안녕하세요"
    assert send_ko_payload["translation_status"] == "done"

    _set_current_user(client, 2)
    send_en_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "Hello"},
    )
    assert send_en_response.status_code == 200
    send_en_payload = send_en_response.json()
    assert send_en_payload["body_source_lang"] == "en"
    assert send_en_payload["body_target_lang"] == "ko"
    assert send_en_payload["translated_body"] == "en->ko:Hello"
    assert send_en_payload["translation_status"] == "done"


@pytest.mark.parametrize(
    ("friend_user_id", "expected_target_lang"),
    [
        (2, "en"),
        (3, "ja"),
        (5, "zh"),
        (6, "fr"),
        (7, "hi"),
        (8, "vi"),
        (9, "th"),
    ],
)
def test_direct_room_auto_translates_for_counterpart_languages(
    monkeypatch,
    friend_user_id: int,
    expected_target_lang: str,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    room_response = client.post(
        "/api/mobile/chat/rooms/direct",
        json={"friend_user_id": friend_user_id},
    )
    assert room_response.status_code == 200
    room_id = room_response.json()["room_id"]

    send_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "안녕하세요"},
    )
    assert send_response.status_code == 200
    send_payload = send_response.json()
    assert send_payload["body_source_lang"] == "ko"
    assert send_payload["body_target_lang"] == expected_target_lang
    assert send_payload["translated_body"] == (
        f"ko->{expected_target_lang}:안녕하세요"
    )
    assert send_payload["translation_status"] == "done"


def test_direct_room_text_messages_cover_full_50_language_catalog(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    for (
        expected_target_lang,
        friend_user_id,
    ) in FULL_LANGUAGE_FRIEND_IDS.items():
        room_response = client.post(
            "/api/mobile/chat/rooms/direct",
            json={"friend_user_id": friend_user_id},
        )
        assert room_response.status_code == 200, expected_target_lang
        room_id = room_response.json()["room_id"]

        send_response = client.post(
            f"/api/mobile/chat/rooms/{room_id}/messages",
            json={"message_type": "text", "body": "안녕하세요"},
        )
        assert send_response.status_code == 200, expected_target_lang
        send_payload = send_response.json()
        assert send_payload["body_source_lang"] == "ko", expected_target_lang
        assert send_payload["body_target_lang"] == expected_target_lang, (
            expected_target_lang
        )
        if expected_target_lang == "ko":
            assert (
                send_payload["translated_body"] is None
            ), expected_target_lang
            assert send_payload["translation_status"] == "none", (
                expected_target_lang
            )
            continue
        assert send_payload["translated_body"] == (
            f"ko->{expected_target_lang}:안녕하세요"
        ), expected_target_lang
        assert send_payload["translation_status"] == "done", (
            expected_target_lang
        )


def test_direct_room_translation_does_not_fallback_to_country_code(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    db_gen = _get_db_for_client(client)
    db = next(db_gen)
    try:
        friend = db.query(models.User).filter(models.User.id == 2).first()
        assert friend is not None
        friend.preferred_language = "unsupported"
        friend.country_code = "JP"
        db.commit()
    finally:
        db_gen.close()

    room_response = client.post(
        "/api/mobile/chat/rooms/direct",
        json={"friend_user_id": 2},
    )
    assert room_response.status_code == 200
    room_id = room_response.json()["room_id"]

    send_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "안녕하세요"},
    )
    assert send_response.status_code == 200
    send_payload = send_response.json()
    assert send_payload["body_source_lang"] == "ko"
    assert send_payload["body_target_lang"] is None
    assert send_payload["translated_body"] is None
    assert send_payload["translation_status"] == "none"


def test_group_room_and_read_marker_are_persisted() -> None:
    client = _build_client()

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "여행 통역방",
            "member_user_ids": [2, 3],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    message_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "일정 공유합니다."},
    )
    assert message_response.status_code == 200
    message_id = message_response.json()["message_id"]
    message_payload = message_response.json()
    assert message_payload["translated_body"] is None
    assert message_payload["translation_status"] == "none"

    read_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/read",
        json={"last_read_message_id": message_id},
    )
    assert read_response.status_code == 200
    assert read_response.json()["last_read_message_id"] == message_id
    detail_response = client.get(f"/api/mobile/chat/rooms/{room_id}")
    assert detail_response.status_code == 200
    assert group_response.json()["member_limit"] == 10
    assert detail_response.json()["allow_member_invites"] is False
    assert detail_response.json()["member_limit"] == 10
    assert detail_response.json()["can_invite_members"] is True
    assert detail_response.json()["default_source_lang"] is None
    assert detail_response.json()["default_target_lang"] is None


def test_group_room_supports_inviting_new_members() -> None:
    client = _build_client()

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "확장 그룹방",
            "member_user_ids": [2],
            "allow_member_invites": True,
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]
    assert group_response.json()["allow_member_invites"] is True

    invite_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/members",
        json={"member_user_ids": [4]},
    )
    assert invite_response.status_code == 200
    invite_payload = invite_response.json()
    assert invite_payload["added_user_ids"] == [4]
    assert len(invite_payload["room"]["members"]) == 3

    messages_response = client.get(
        f"/api/mobile/chat/rooms/{room_id}/messages"
    )
    assert messages_response.status_code == 200
    messages = messages_response.json()["items"]
    assert len(messages) == 1
    assert messages[0]["message_type"] == "system_invite"
    assert "newfriend" in messages[0]["body"]


def test_group_room_member_limit_blocks_over_capacity_invites() -> None:
    client = _build_client()

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "3인 고정방",
            "member_user_ids": [2],
            "member_limit": 3,
            "allow_member_invites": True,
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]
    assert group_response.json()["member_limit"] == 3

    invite_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/members",
        json={"member_user_ids": [4]},
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["room"]["member_limit"] == 3
    assert invite_response.json()["room"]["can_invite_members"] is False

    overflow_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/members",
        json={"member_user_ids": [5]},
    )
    assert overflow_response.status_code == 400
    assert "정원은 3명" in overflow_response.json()["detail"]


def test_group_room_creation_rejects_initial_members_over_limit() -> None:
    client = _build_client()

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "초기 정원 초과방",
            "member_user_ids": [2, 3, 4],
            "member_limit": 3,
        },
    )
    assert group_response.status_code == 400
    assert "정원 3명 이하" in group_response.json()["detail"]


def test_group_room_member_can_invite_when_room_policy_allows_it() -> None:
    client = _build_client()
    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "멤버 초대 허용방",
            "member_user_ids": [2],
            "allow_member_invites": True,
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    _set_current_user(client, 2)
    detail_response = client.get(f"/api/mobile/chat/rooms/{room_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["can_invite_members"] is True

    invite_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/members",
        json={"member_user_ids": [4]},
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["added_user_ids"] == [4]


def test_group_room_owner_can_update_invite_policy_after_creation() -> None:
    client = _build_client()

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "설정 변경방",
            "member_user_ids": [2],
            "allow_member_invites": False,
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]
    assert group_response.json()["allow_member_invites"] is False

    update_response = client.patch(
        f"/api/mobile/chat/rooms/{room_id}/settings",
        json={"allow_member_invites": True},
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["allow_member_invites"] is True
    assert payload["can_invite_members"] is True

    _set_current_user(client, 2)
    detail_response = client.get(f"/api/mobile/chat/rooms/{room_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["allow_member_invites"] is True
    assert detail_response.json()["can_invite_members"] is True


def test_group_room_text_messages_cover_full_50_language_catalog(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    for (
        expected_target_lang,
        friend_user_id,
    ) in FULL_LANGUAGE_FRIEND_IDS.items():
        _set_current_user(client, 1)
        group_response = client.post(
            "/api/mobile/chat/rooms/group",
            json={
                "title": f"full-matrix-{expected_target_lang}",
                "member_user_ids": [friend_user_id],
            },
        )
        assert group_response.status_code == 200, expected_target_lang
        room_id = group_response.json()["room_id"]

        message_response = client.post(
            f"/api/mobile/chat/rooms/{room_id}/messages",
            json={
                "message_type": "text",
                "body": "단체방 공지입니다.",
                "request_translation": True,
            },
        )
        assert message_response.status_code == 200, expected_target_lang
        message_payload = message_response.json()
        assert (
            message_payload["body_source_lang"] == "ko"
        ), expected_target_lang
        assert message_payload["delivery_summary"]["recipient_count"] == 1

        recipient_payload = _get_last_message_payload(
            client,
            room_id,
            friend_user_id,
        )
        assert recipient_payload["body_source_lang"] == "ko"
        assert recipient_payload["body_target_lang"] == expected_target_lang
        assert recipient_payload["viewer_translation"]["target_lang"] == (
            expected_target_lang
        )
        if expected_target_lang == "ko":
            assert (
                recipient_payload["translated_body"] is None
            ), expected_target_lang
            assert recipient_payload["translation_status"] == "skipped", (
                expected_target_lang
            )
            continue
        assert recipient_payload["translated_body"] == (
            f"ko->{expected_target_lang}:단체방 공지입니다."
        ), expected_target_lang
        assert recipient_payload["translation_status"] == "done", (
            expected_target_lang
        )


def test_group_room_text_translation_requires_explicit_request(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "명시 번역 그룹방",
            "member_user_ids": [2],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    no_translate_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={"message_type": "text", "body": "자동 번역 없음"},
    )
    assert no_translate_response.status_code == 200
    no_translate_payload = no_translate_response.json()
    assert no_translate_payload["translated_body"] is None
    assert no_translate_payload["translation_status"] == "none"

    recipient_no_translate = _get_last_message_payload(client, room_id, 2)
    assert recipient_no_translate["viewer_translation"] is None

    _set_current_user(client, 1)

    translate_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={
            "message_type": "text",
            "body": "명시 번역",
            "request_translation": True,
        },
    )
    assert translate_response.status_code == 200
    translate_payload = translate_response.json()
    assert translate_payload["body_source_lang"] == "ko"
    assert translate_payload["translation_status"] == "done"
    assert translate_payload["delivery_summary"]["done_count"] == 1

    recipient_translate = _get_last_message_payload(client, room_id, 2)
    assert recipient_translate["body_target_lang"] == "en"
    assert recipient_translate["translated_body"] == "ko->en:명시 번역"
    assert recipient_translate["viewer_translation"] == {
        "target_lang": "en",
        "translated_body": "ko->en:명시 번역",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }


def test_group_room_translation_fans_out_to_each_recipient_language(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "혼합 언어 그룹방",
            "member_user_ids": [2, 3],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    translate_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={
            "message_type": "text",
            "body": "혼합 언어 테스트",
            "request_translation": True,
        },
    )
    assert translate_response.status_code == 200
    translate_payload = translate_response.json()
    assert translate_payload["body_source_lang"] == "ko"
    assert translate_payload["translation_status"] == "done"
    assert translate_payload["delivery_summary"] == {
        "recipient_count": 2,
        "pending_count": 0,
        "done_count": 2,
        "failed_count": 0,
        "skipped_count": 0,
        "status": "done",
    }

    english_payload = _get_last_message_payload(client, room_id, 2)
    assert english_payload["body_source_lang"] == "ko"
    assert english_payload["body_target_lang"] == "en"
    assert english_payload["translated_body"] == "ko->en:혼합 언어 테스트"
    assert english_payload["viewer_translation"] == {
        "target_lang": "en",
        "translated_body": "ko->en:혼합 언어 테스트",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }

    japanese_payload = _get_last_message_payload(client, room_id, 3)
    assert japanese_payload["body_source_lang"] == "ko"
    assert japanese_payload["body_target_lang"] == "ja"
    assert japanese_payload["translated_body"] == "ko->ja:혼합 언어 테스트"
    assert japanese_payload["viewer_translation"] == {
        "target_lang": "ja",
        "translated_body": "ko->ja:혼합 언어 테스트",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }


def test_group_room_partial_failure_exposes_summary_and_viewer_status(
    monkeypatch,
) -> None:
    client = _build_client()

    class _PartiallyFailingTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            if to_lang == "ja":
                raise RuntimeError("ja translation unavailable")
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _PartiallyFailingTranslator()),
    )

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "부분 실패 그룹방",
            "member_user_ids": [2, 3],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    translate_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={
            "message_type": "text",
            "body": "부분 실패 테스트",
            "request_translation": True,
        },
    )
    assert translate_response.status_code == 200
    translate_payload = translate_response.json()
    assert translate_payload["translation_status"] == "partial_failed"
    assert translate_payload["delivery_summary"] == {
        "recipient_count": 2,
        "pending_count": 0,
        "done_count": 1,
        "failed_count": 1,
        "skipped_count": 0,
        "status": "partial_failed",
    }

    english_payload = _get_last_message_payload(client, room_id, 2)
    assert english_payload["translation_status"] == "done"
    assert english_payload["viewer_translation"] == {
        "target_lang": "en",
        "translated_body": "ko->en:부분 실패 테스트",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }
    assert english_payload["delivery_summary"]["status"] == "partial_failed"

    japanese_payload = _get_last_message_payload(client, room_id, 3)
    assert japanese_payload["translation_status"] == "failed"
    assert japanese_payload["translated_body"] is None
    assert japanese_payload["viewer_translation"] == {
        "target_lang": "ja",
        "translated_body": None,
        "translation_status": "failed",
        "failure_code": "translation_error",
        "failure_detail": "ja translation unavailable",
    }


def test_group_message_created_event_uses_viewer_specific_payload(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "이벤트 페이로드 그룹방",
            "member_user_ids": [2, 3],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    message_response = client.post(
        f"/api/mobile/chat/rooms/{room_id}/messages",
        json={
            "message_type": "text",
            "body": "이벤트 테스트",
            "request_translation": True,
        },
    )
    assert message_response.status_code == 200
    message_id = message_response.json()["message_id"]

    db_gen = _get_db_for_client(client)
    db = next(db_gen)
    try:
        room = (
            db.query(models.ChatRoom)
            .filter(models.ChatRoom.room_uuid == room_id)
            .first()
        )
        assert room is not None
        message = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.message_uuid == message_id)
            .first()
        )
        assert message is not None

        english_event = chat_router_module._serialize_message_created_event(
            db,
            room,
            message,
            2,
        )
        japanese_event = chat_router_module._serialize_message_created_event(
            db,
            room,
            message,
            3,
        )
    finally:
        db_gen.close()

    assert english_event["type"] == "message_created"
    assert english_event["room_id"] == room_id
    assert english_event["viewer_user_id"] == 2
    assert english_event["message"]["viewer_translation"] == {
        "target_lang": "en",
        "translated_body": "ko->en:이벤트 테스트",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }
    assert english_event["message"]["delivery_summary"]["status"] == "done"

    assert japanese_event["viewer_user_id"] == 3
    assert japanese_event["message"]["viewer_translation"] == {
        "target_lang": "ja",
        "translated_body": "ko->ja:이벤트 테스트",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }


def test_group_room_websocket_pushes_viewer_specific_message_created(
    monkeypatch,
) -> None:
    client = _build_client()

    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint=None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        chat_router_module.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    group_response = client.post(
        "/api/mobile/chat/rooms/group",
        json={
            "title": "웹소켓 그룹방",
            "member_user_ids": [2, 3],
        },
    )
    assert group_response.status_code == 200
    room_id = group_response.json()["room_id"]

    token_user_2 = _build_auth_token(2)
    token_user_3 = _build_auth_token(3)

    with client.websocket_connect(
        f"/api/mobile/chat/rooms/{room_id}/ws?token={token_user_2}"
    ) as ws_user_2, client.websocket_connect(
        f"/api/mobile/chat/rooms/{room_id}/ws?token={token_user_3}"
    ) as ws_user_3:
        ready_user_2 = ws_user_2.receive_json()
        ready_user_3 = ws_user_3.receive_json()
        assert ready_user_2["type"] == "chat_room_ready"
        assert ready_user_3["type"] == "chat_room_ready"

        _set_current_user(client, 1)
        message_response = client.post(
            f"/api/mobile/chat/rooms/{room_id}/messages",
            json={
                "message_type": "text",
                "body": "실시간 그룹 메시지",
                "request_translation": True,
            },
        )
        assert message_response.status_code == 200

        user_2_event = ws_user_2.receive_json()
        user_3_event = ws_user_3.receive_json()

    assert user_2_event["type"] == "message_created"
    assert user_2_event["viewer_user_id"] == 2
    assert user_2_event["message"]["viewer_translation"] == {
        "target_lang": "en",
        "translated_body": "ko->en:실시간 그룹 메시지",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }
    assert user_2_event["message"]["delivery_summary"]["status"] == "done"

    assert user_3_event["type"] == "message_created"
    assert user_3_event["viewer_user_id"] == 3
    assert user_3_event["message"]["viewer_translation"] == {
        "target_lang": "ja",
        "translated_body": "ko->ja:실시간 그룹 메시지",
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }
