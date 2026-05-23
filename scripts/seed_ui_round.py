from __future__ import annotations

import sys

from backend.auth import get_password_hash
from backend.marketplace.database import SessionLocal
from backend.marketplace.models import User


def upsert_user(round_key: str) -> None:
    admin_email = 'ui.admin.round@devanalysis.local'
    admin_password = 'RoundUi!20260426'
    if round_key.upper() == 'A':
        target_email = 'ui.pod.round.a@devanalysis.local'
        target_username = 'ui_pod_round_a_20260426'
    else:
        target_email = 'ui.pod.round.b@devanalysis.local'
        target_username = 'ui_pod_round_b_20260426'

    session = SessionLocal()
    try:
        admin = session.query(User).filter(User.email == admin_email).first()
        admin_hash = get_password_hash(admin_password)
        if admin is None:
            admin = User(
                email=admin_email,
                username=admin_email,
                hashed_password=admin_hash,
                is_active=True,
                is_admin=True,
                is_superuser=True,
            )
        else:
            admin.username = admin_email
            admin.hashed_password = admin_hash
            admin.is_active = True
            admin.is_admin = True
            admin.is_superuser = True
        session.add(admin)

        user = session.query(User).filter(User.email == target_email).first()
        if user is None:
            user = User(
                email=target_email,
                username=target_username,
                hashed_password=get_password_hash('x'),
                is_active=True,
                is_admin=False,
                is_superuser=False,
            )
        else:
            user.username = target_username
            user.is_active = True
            user.is_admin = False
            user.is_superuser = False
        session.add(user)

        session.commit()
        print(f'SEEDED_{round_key.upper()} admin={admin_email} target={target_username}')
    finally:
        session.close()


if __name__ == '__main__':
    round_name = sys.argv[1] if len(sys.argv) > 1 else 'A'
    upsert_user(round_name)
