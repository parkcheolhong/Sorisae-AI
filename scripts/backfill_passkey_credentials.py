from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.marketplace import models
from backend.marketplace.database import SessionLocal, init_db
from backend.time_utils import utcnow


@dataclass
class BackfillStats:
    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


def run_backfill(dry_run: bool = False) -> BackfillStats:
    stats = BackfillStats()
    init_db()
    db = SessionLocal()
    try:
        users = db.query(models.User).filter(models.User.passkey_enabled.is_(True)).all()
        for user in users:
            stats.scanned += 1
            credential_id = str(user.passkey_credential_id or "").strip()
            public_key = str(user.passkey_public_key or "").strip()
            if not credential_id or not public_key:
                stats.skipped += 1
                continue

            existing = (
                db.query(models.PasskeyCredential)
                .filter(models.PasskeyCredential.credential_id == credential_id)
                .first()
            )
            if existing is None:
                db.add(
                    models.PasskeyCredential(
                        user_id=int(user.id),
                        credential_id=credential_id,
                        public_key=public_key,
                        device_label=str(user.passkey_device_label or "").strip() or None,
                        sign_count=int(user.passkey_sign_count or 0),
                        transports="hybrid,internal,usb,nfc,ble",
                        created_at=user.passkey_registered_at or utcnow(),
                    )
                )
                stats.inserted += 1
                continue

            changed = False
            if int(existing.user_id or 0) != int(user.id):
                existing.user_id = int(user.id)
                changed = True
            if str(existing.public_key or "") != public_key:
                existing.public_key = public_key
                changed = True

            resolved_label = str(user.passkey_device_label or "").strip() or None
            if (existing.device_label or None) != resolved_label:
                existing.device_label = resolved_label
                changed = True

            resolved_sign_count = int(user.passkey_sign_count or 0)
            if int(existing.sign_count or 0) != resolved_sign_count:
                existing.sign_count = resolved_sign_count
                changed = True

            if changed:
                db.add(existing)
                stats.updated += 1
            else:
                stats.unchanged += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _print_stats(prefix: str, stats: BackfillStats) -> None:
    print(
        f"{prefix} scanned={stats.scanned} inserted={stats.inserted} updated={stats.updated} "
        f"unchanged={stats.unchanged} skipped={stats.skipped}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill users.passkey_* rows into passkey_credentials")
    parser.add_argument("--dry-run", action="store_true", help="compute changes and rollback")
    args = parser.parse_args()

    result = run_backfill(dry_run=args.dry_run)
    _print_stats("PASSKEY_BACKFILL", result)
