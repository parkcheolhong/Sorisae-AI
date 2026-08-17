from __future__ import annotations

import sys

from backend.auth import get_password_hash
from backend.marketplace.database import SessionLocal, _get_or_create_engine
from backend.marketplace.models import User


def upsert(round_key: str) -> None:
    _get_or_create_engine()
    admin_email = 'ui.admin.round@devanalysis.local'
    admin_password = 'RoundUi!20260426'
    target_map = {
        'A': ('ui.pod.round.a@devanalysis.local', 'ui_pod_round_a_20260426'),
        'B': ('ui.pod.round.b@devanalysis.local', 'ui_pod_round_b_20260426'),
    }
    target_email, target_username = target_map.get(round_key.upper(), target_map['A'])

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == admin_email).first()
        if admin is None:
            admin = User(
                email=admin_email,
                username=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_active=True,
                is_admin=True,
                is_superuser=True,
            )
        admin.username = admin_email
        admin.hashed_password = get_password_hash(admin_password)
        admin.is_active = True
        _extracted_from_upsert_26(True, admin, db)
        target = db.query(User).filter(User.email == target_email).first()
        if target is None:
            target = User(
                email=target_email,
                username=target_username,
                hashed_password=get_password_hash('x'),
                is_active=True,
                is_admin=False,
                is_superuser=False,
            )
        target.username = target_username
        target.is_active = True
        _extracted_from_upsert_26(False, target, db)
        db.commit()
        print(f'SEEDED_{round_key.upper()} admin={admin_email} target={target_username}')
    finally:
        db.close()


# TODO Rename this here and in `upsert`
def _extracted_from_upsert_26(arg0, arg1, db):
    arg1.is_admin = arg0
    arg1.is_superuser = arg0
    db.add(arg1)


if __name__ == '__main__':
    upsert(sys.argv[1] if len(sys.argv) > 1 else 'A')
