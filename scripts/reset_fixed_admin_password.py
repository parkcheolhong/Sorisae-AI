"""Reset FIXED_ADMIN account password in Postgres (local verify / admin login recovery).

Usage:
  $env:FIXED_ADMIN_PASSWORD="your-new-password-min-8-chars"
  python scripts/reset_fixed_admin_password.py

Optional:
  $env:FIXED_ADMIN_EMAIL="119cash@naver.com"
  $env:DATABASE_URL="postgresql://admin:...@127.0.0.1:5432/devanalysis114"

Note: `.env` uses host `postgres` (Docker). This script rewrites it to `127.0.0.1` on the host automatically.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_project_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _configure_native_postgres() -> None:
    """Host venv runs cannot resolve docker-only hostname `postgres`."""
    if Path("/.dockerenv").exists():
        return

    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
        return

    try:
        from sqlalchemy.engine import make_url

        parsed = make_url(raw)
        host = str(parsed.host or "").strip().lower()
        if host == "postgres":
            os.environ["DATABASE_URL"] = parsed.set(host="127.0.0.1").render_as_string(
                hide_password=False
            )
    except Exception:
        if "@postgres:" in raw:
            os.environ["DATABASE_URL"] = raw.replace("@postgres:", "@127.0.0.1:")


def main() -> int:
    _load_project_env()
    _configure_native_postgres()
    email = os.getenv("FIXED_ADMIN_EMAIL", "").strip()
    password = (
        os.getenv("RESET_ADMIN_PASSWORD", "").strip()
        or os.getenv("FIXED_ADMIN_PASSWORD", "").strip()
        or os.getenv("VERIFY_ADMIN_PASSWORD", "").strip()
    )
    if not email:
        print("FIXED_ADMIN_EMAIL is not set (.env or env).", file=sys.stderr)
        return 1
    if not password:
        print(
            "Set RESET_ADMIN_PASSWORD (or FIXED_ADMIN_PASSWORD) in env, then re-run.",
            file=sys.stderr,
        )
        return 1
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1
    if password == "SET_VIA_ENV_ONLY":
        print("Refusing placeholder password.", file=sys.stderr)
        return 1

    from backend.auth import get_password_hash, verify_password
    from backend.marketplace.database import SessionLocal, _get_or_create_engine
    from backend.marketplace.models import User

    _get_or_create_engine()
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == email) | (User.username == email)
        ).first()
        if user is None:
            print(f"No user found for {email}", file=sys.stderr)
            return 1

        user.hashed_password = get_password_hash(password)
        user.is_active = True
        user.is_admin = True
        user.is_superuser = True
        if not getattr(user, "username", None):
            user.username = email
        if not getattr(user, "email", None):
            user.email = email
        db.commit()
        db.refresh(user)

        if not verify_password(password, user.hashed_password):
            print("Hash update failed verification.", file=sys.stderr)
            return 1

        print(f"OK: password reset for user id={user.id} email={user.email}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Reset failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
