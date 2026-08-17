from __future__ import annotations

from backend.marketplace.database import SessionLocal, _get_or_create_engine
from backend.marketplace.models import UserActiveSession
from backend.models import User


TARGET_EMAILS = [
    "ui.admin.round@devanalysis.local",
    "ui.pod.round.a@devanalysis.local",
    "ui.pod.round.b@devanalysis.local",
]


def main() -> None:
    _get_or_create_engine()
    session = SessionLocal()
    cleared = 0
    try:
        for email in TARGET_EMAILS:
            user = session.query(User).filter(User.email == email).first()
            if user is None:
                continue
            rows = (
                session.query(UserActiveSession)
                .filter(UserActiveSession.user_id == int(user.id))
                .all()
            )
            for row in rows:
                session.delete(row)
                cleared += 1
        session.commit()
    finally:
        session.close()

    print(f"CLEARED_ACTIVE_SESSIONS {cleared}")


if __name__ == "__main__":
    main()
