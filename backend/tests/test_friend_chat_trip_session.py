"""friend-chat ↔ trip_sessions / conversation_turns persistence."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.marketplace.database import Base
from backend.marketplace.friend_chat_trip_session import (
    ensure_friend_chat_trip_session,
    record_friend_chat_turn,
)
from backend.marketplace.models import ConversationTurn, TripSession


def test_ensure_and_record_friend_chat_turns() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[TripSession.__table__, ConversationTurn.__table__],
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        pk, session_id = ensure_friend_chat_trip_session(
            db,
            trip_session_id=None,
            user_id=42,
            country_code="KR",
            latitude=37.5,
            longitude=127.0,
        )
        assert pk is not None
        assert session_id.startswith("sorisae-")

        record_friend_chat_turn(
            db,
            trip_session_pk=pk,
            user_utterance="근처 맛집 추천해줘",
            assistant_utterance="이 근처에 현지식당이 있어요.",
            language_code="ko",
            correlation_id="corr-1",
        )
        turns = db.query(ConversationTurn).filter(ConversationTurn.trip_session_id == pk).all()
        assert len(turns) == 2
        assert turns[0].role == "user"
        assert turns[1].role == "assistant"
        assert turns[0].intent == "friend_chat"

        pk2, session_id2 = ensure_friend_chat_trip_session(
            db,
            trip_session_id=session_id,
            user_id=42,
        )
        assert pk2 == pk
        assert session_id2 == session_id
    finally:
        db.close()
