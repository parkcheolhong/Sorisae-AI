import logging
import os
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)


def _resolve_secret_key() -> tuple[str, bool]:
    configured = str(os.getenv("SECRET_KEY") or "").strip()
    if configured:
        return configured, False

    configured_file = str(os.getenv("SECRET_KEY_FILE") or "").strip()
    if configured_file:
        fallback_path = Path(configured_file).expanduser()
        try:
            if not fallback_path.exists():
                logger.error(
                    "SECRET_KEY_FILE is configured but does not exist: %s. Falling back to ephemeral runtime secret.",
                    str(fallback_path),
                )
            elif not fallback_path.is_file():
                logger.error(
                    "SECRET_KEY_FILE is configured but is not a file: %s. Falling back to ephemeral runtime secret.",
                    str(fallback_path),
                )
            else:
                cached_secret = fallback_path.read_text(encoding="utf-8").strip()
                if cached_secret:
                    return cached_secret, True
                logger.error(
                    "SECRET_KEY_FILE is configured but empty: %s. Falling back to ephemeral runtime secret.",
                    str(fallback_path),
                )
        except Exception:
            logger.exception(
                "Failed to read SECRET_KEY_FILE at %s. Falling back to ephemeral runtime secret.",
                str(fallback_path),
            )
    else:
        logger.error(
            "SECRET_KEY/SECRET_KEY_FILE is not configured; generating ephemeral runtime secret that invalidates tokens on restart."
        )
    return secrets.token_urlsafe(48), True


SECRET_KEY, SECRET_KEY_IS_RUNTIME_FALLBACK = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    no_expiry: bool = False,
) -> str:
    to_encode = data.copy()
    if not no_expiry:
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "change-me"


def is_weak_secret_key() -> bool:
    normalized_secret = str(SECRET_KEY or JWT_SECRET or "").strip()
    if not normalized_secret:
        return True

    if SECRET_KEY_IS_RUNTIME_FALLBACK and len(normalized_secret) >= 32:
        return False

    lowered = normalized_secret.lower()
    weak_markers = (
        "change-me",
        "changeme",
        "change_in_production",
        "change-in-production",
        "default",
        "demo",
        "test",
        "local-secret",
        "devanalysis114-secret-key-change-in-production",
    )
    return len(normalized_secret) < 32 or any(
        marker in lowered for marker in weak_markers
    )


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # DB에서 유저 조회
    from backend.database import SessionLocal
    from backend.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        if user is None or not getattr(user, "is_active", False):
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[AUTH] 사용자 조회 실패: sub=%s error=%s",
            username,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 사용자 조회 중 데이터베이스 연결이 불안정합니다. 잠시 후 다시 시도해주세요.",
        )
    finally:
        db.close()
