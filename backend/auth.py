import logging
import os
import bcrypt
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer


def _resolve_secret_key() -> tuple[str, bool]:
    configured = str(os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "").strip()
    if configured:
        return configured, False

    app_env = str(os.getenv("APP_ENV") or "dev").strip().lower()
    if app_env in {"prod", "production", "stage", "staging"}:
        raise RuntimeError("SECRET_KEY or JWT_SECRET must be configured outside local development")

    configured_secret_file = str(os.getenv("SECRET_KEY_FILE") or "").strip()
    candidate_paths = [
        Path(configured_secret_file) if configured_secret_file else None,
        Path(os.getenv("TEMP") or "/tmp") / "codeai_jwt_secret.key",
    ]

    for candidate in candidate_paths:
        if candidate is None:
            continue
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if candidate.exists():
                cached_secret = candidate.read_text(encoding="utf-8").strip()
                if cached_secret:
                    return cached_secret, True
            generated_secret = secrets.token_urlsafe(48)
            candidate.write_text(generated_secret, encoding="utf-8")
            return generated_secret, True
        except Exception:
            continue

    return secrets.token_urlsafe(48), True


SECRET_KEY, SECRET_KEY_IS_RUNTIME_FALLBACK = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
logger = logging.getLogger(__name__)

_ISSUED_TOKEN_SUBJECTS: dict[str, str] = {}
_ISSUED_TOKEN_LOCK = threading.Lock()
_ISSUED_TOKEN_CAP = 4096


def register_issued_token(token: str, subject: str) -> None:
    token_value = str(token or "").strip()
    subject_value = str(subject or "").strip()
    if not token_value or not subject_value:
        return
    with _ISSUED_TOKEN_LOCK:
        _ISSUED_TOKEN_SUBJECTS[token_value] = subject_value
        if len(_ISSUED_TOKEN_SUBJECTS) > _ISSUED_TOKEN_CAP:
            overflow = len(_ISSUED_TOKEN_SUBJECTS) - _ISSUED_TOKEN_CAP
            for key in list(_ISSUED_TOKEN_SUBJECTS.keys())[:overflow]:
                _ISSUED_TOKEN_SUBJECTS.pop(key, None)


def _resolve_registered_subject(token: str) -> str | None:
    token_value = str(token or "").strip()
    if not token_value:
        return None
    with _ISSUED_TOKEN_LOCK:
        return _ISSUED_TOKEN_SUBJECTS.get(token_value)


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
        # [관측성][LOW] bcrypt 는 '비밀번호 불일치' 시 예외 없이 False 를 반환한다.
        # 여기 도달했다면 저장된 해시 손상/형식 오류 같은 비정상 상황이므로(인증은 안전하게 실패),
        # 조용히 삼키지 말고 경고를 남겨 해시 손상을 진단할 수 있게 한다.
        logger.warning("[AUTH] verify_password 예외 — 손상된 해시 가능성", exc_info=True)
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


JWT_SECRET = SECRET_KEY


def resolve_token_subject(token: str) -> Optional[str]:
    token_value = str(token or "").strip()
    if not token_value:
        return None
    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if isinstance(subject, str) and subject.strip():
            return subject.strip()
    except JWTError:
        return None
    return None


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


# ── [#4] 활성 세션 Redis 캐시 (요청당 DB 부하 절감 · fail-open) ─────────────────
# 단일세션 강제를 위해 모든 인증 요청이 user_active_sessions 를 조회한다. 이를 짧은 TTL Redis
# 캐시로 줄인다. UserActiveSession 은 오직 set_active_session 으로만 변경되므로(로그아웃/삭제 경로
# 없음), 거기서 write-through 하면 캐시가 항상 권위값과 일치한다(스테일 무효화 불필요).
# Redis 미연결/비활성 시 그대로 DB 경로로 폴백(no-op).
_SESSION_CACHE_NONE = "\x00no-session"  # 'row 없음' 을 캐시하기 위한 센티넬(sid 와 충돌 불가)


def _session_cache_enabled() -> bool:
    return os.getenv("SESSION_CACHE_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
        "",
    }


def _session_cache_ttl() -> int:
    try:
        return max(1, int(os.getenv("SESSION_CACHE_TTL_SEC", "30")))
    except (TypeError, ValueError):
        return 30


def _session_cache_key(uid: int) -> str:
    return f"auth:active_session:{uid}"


def _session_cache_get(uid: int) -> tuple[bool, Optional[str]]:
    """반환: (hit, sid_or_None). hit=False 면 캐시 미스/비활성 → DB 로 폴백."""
    if not _session_cache_enabled():
        return False, None
    try:
        from backend.marketplace.cache_service import cache_service

        raw = cache_service.get(_session_cache_key(uid))
    except Exception:  # noqa: BLE001
        return False, None
    if raw is None:
        return False, None
    if raw == _SESSION_CACHE_NONE:
        return True, None
    return True, str(raw)


def _session_cache_put(uid: int, sid: Optional[str]) -> None:
    """활성 sid(또는 'row 없음' 센티넬)를 캐시에 기록. 실패 시 스테일 방지를 위해 키 삭제."""
    if not _session_cache_enabled():
        return
    try:
        from backend.marketplace.cache_service import cache_service

        value = sid if sid is not None else _SESSION_CACHE_NONE
        ok = cache_service.set(_session_cache_key(uid), value, _session_cache_ttl())
        if not ok:
            cache_service.delete(_session_cache_key(uid))
    except Exception:  # noqa: BLE001
        logger.debug("[AUTH] 세션 캐시 기록 실패 user_id=%s", uid, exc_info=True)


def set_active_session(user_id: int, session_id: str) -> None:
    """로그인 시 계정의 활성 세션을 새 sid 로 덮어쓴다(단일 세션). best-effort."""
    uid = int(user_id or 0)
    sid = str(session_id or "").strip()
    if uid <= 0 or not sid:
        return
    try:
        from backend.database import SessionLocal
        from backend.marketplace.models import UserActiveSession

        db = SessionLocal()
        try:
            row = (
                db.query(UserActiveSession)
                .filter(UserActiveSession.user_id == uid)
                .first()
            )
            if row is None:
                db.add(UserActiveSession(user_id=uid, session_id=sid))
            else:
                row.session_id = sid
            db.commit()
        finally:
            db.close()
        # write-through: DB 커밋 성공 후에만 캐시 갱신(권위값과 일치 보장).
        _session_cache_put(uid, sid)
    except Exception:  # noqa: BLE001
        logger.warning("[AUTH] set_active_session 실패 user_id=%s", uid, exc_info=True)
        # DB 실패 시 캐시가 스테일이 되지 않도록 무효화(다음 조회는 DB 재시도).
        try:
            from backend.marketplace.cache_service import cache_service

            cache_service.delete(_session_cache_key(uid))
        except Exception:  # noqa: BLE001
            pass


def _lookup_active_session(user_id: int) -> tuple[Optional[str], bool]:
    """활성 세션 sid 를 조회한다. 반환: (sid_or_None, lookup_failed).

    - (sid, False): 활성 세션이 기록돼 있음.
    - (None, False): 활성 세션 row 가 없음(단일세션 미적용 상태) — 정상.
    - (None, True): DB 조회 자체가 실패함 — 호출측이 admin 여부에 따라 fail-open/closed 결정.
    """
    uid = int(user_id or 0)
    if uid <= 0:
        return None, False
    # [#4] 캐시 우선 조회 — 히트 시 DB 왕복 생략.
    hit, cached_sid = _session_cache_get(uid)
    if hit:
        return cached_sid, False
    try:
        from backend.database import SessionLocal
        from backend.marketplace.models import UserActiveSession

        db = SessionLocal()
        try:
            row = (
                db.query(UserActiveSession)
                .filter(UserActiveSession.user_id == uid)
                .first()
            )
            resolved = str(row.session_id) if row is not None else None
            # 성공 조회만 캐시(실패는 캐시 금지). 'row 없음'(None)도 센티넬로 캐시.
            _session_cache_put(uid, resolved)
            return resolved, False
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[AUTH] 활성 세션 조회 실패 user_id=%s", uid, exc_info=True)
        return None, True


def _get_active_session_id(user_id: int) -> Optional[str]:
    # 하위호환 래퍼 — 조회 실패와 'row 없음'을 구분하지 않는다(기존 호출부 보존).
    sid, _failed = _lookup_active_session(user_id)
    return sid


def has_active_session(user_id: int) -> bool:
    """동일 사용자에게 이미 활성 세션이 존재하면 True."""
    uid = int(user_id or 0)
    if uid <= 0:
        return False
    active_sid, lookup_failed = _lookup_active_session(uid)
    if lookup_failed:
        return False
    return active_sid is not None


def clear_active_session(user_id: int, *, expected_session_id: Optional[str] = None) -> bool:
    """명시적 로그아웃 시 활성 세션을 해제한다.

    expected_session_id 가 주어지면 현재 활성 sid 와 일치할 때만 해제해,
    다른 기기의 최신 세션을 실수로 지우지 않도록 보호한다.
    """
    uid = int(user_id or 0)
    if uid <= 0:
        return False
    expected = str(expected_session_id or "").strip()
    try:
        from backend.database import SessionLocal
        from backend.marketplace.models import UserActiveSession

        db = SessionLocal()
        try:
            row = (
                db.query(UserActiveSession)
                .filter(UserActiveSession.user_id == uid)
                .first()
            )
            if row is None:
                _session_cache_put(uid, None)
                return True
            if expected and str(row.session_id or "") != expected:
                return False
            db.delete(row)
            db.commit()
            _session_cache_put(uid, None)
            return True
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[AUTH] clear_active_session 실패 user_id=%s", uid, exc_info=True)
        return False


def resolve_token_session_id(token: str) -> Optional[str]:
    token_value = str(token or "").strip()
    if not token_value:
        return None
    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        sid = payload.get("sid")
        if isinstance(sid, str) and sid.strip():
            return sid.strip()
    except JWTError:
        return None
    return None


def get_current_user(token: str = Depends(oauth2_scheme)):
    return _resolve_current_user_from_token(token)


def get_current_user_flexible(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme_optional),
    access_token: Optional[str] = Query(None, alias="token"),
):
    """Bearer header or ?token= query (EventSource / WebSocket clients)."""
    effective = str(token or access_token or request.query_params.get("token") or "").strip()
    if not effective:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 유효하지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _resolve_current_user_from_token(effective)


# ── [#6] WebSocket 인증 토큰 추출 (Sec-WebSocket-Protocol 우선 · ?token= 호환) ──────
# 토큰을 URL 쿼리에 실으면 Nginx/프록시 액세스 로그·Referer 등으로 유출될 수 있다(이미 로그는
# 스크럽 처리했으나 다중 경로 노출 위험 잔존). 표준 방식은 Sec-WebSocket-Protocol 서브프로토콜로
# 토큰을 전달하는 것. 클라이언트가 `Sec-WebSocket-Protocol: bearer, <jwt>` 로 연결하면 헤더에서
# 추출하고, 미전환 레거시 클라이언트는 기존 ?token= 쿼리로 폴백한다(무중단 점진 전환).
_WS_TOKEN_SCHEMES = {"bearer", "access_token", "authorization", "jwt"}


def resolve_ws_token(websocket, query_token: Optional[str] = None) -> tuple[str, Optional[str]]:
    """WS 인증 토큰 추출. 반환: (token, accept_subprotocol).

    우선순위:
      1) Sec-WebSocket-Protocol: "<scheme>, <token>" (scheme ∈ bearer/access_token/...)
         → 토큰이 URL 에 노출되지 않음(권장).
      2) 레거시 ?token= 쿼리(기존 클라이언트 호환).

    `accept_subprotocol` 은 헤더 협상이 일어난 경우 `websocket.accept(subprotocol=...)` 에
    그대로 echo 해야 하는 값(브라우저 핸드셰이크 요건). 협상이 없으면 None.
    """
    raw = ""
    try:
        raw = websocket.headers.get("sec-websocket-protocol", "") or ""
    except Exception:  # noqa: BLE001
        raw = ""
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) >= 2 and parts[0].lower() in _WS_TOKEN_SCHEMES:
            return parts[1], parts[0]
    if query_token is not None:
        legacy = str(query_token or "").strip()
    else:
        try:
            legacy = str(websocket.query_params.get("token") or "").strip()
        except Exception:  # noqa: BLE001
            legacy = ""
    return legacy, None


def _resolve_current_user_from_token(token: str):
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

    token_sid = payload.get("sid")

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
        # 단일 세션 강제: 계정에 활성 sid 가 기록돼 있고 토큰 sid 와 다르면,
        # 다른 단말/웹에서 새로 로그인한 것이므로 이 토큰은 무효(401) → 자동 로그아웃.
        active_sid, lookup_failed = _lookup_active_session(int(user.id))
        if lookup_failed:
            # [보안 보강][#4] 세션 검증 DB 조회 실패 시:
            #  - admin/superuser 는 fail-closed(503) — 유출 토큰이 검증 우회로 무한 사용되는 것 방지.
            #  - 일반 사용자는 가용성 우선 fail-open(기존 동작 유지) — 단일세션은 best-effort.
            is_privileged = bool(
                getattr(user, "is_admin", False) or getattr(user, "is_superuser", False)
            )
            if is_privileged:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="세션 검증을 일시적으로 수행할 수 없습니다. 잠시 후 다시 시도해주세요.",
                )
        elif active_sid is None and str(token_sid or "").strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그아웃된 세션입니다. 다시 로그인해주세요.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif active_sid is not None and str(token_sid or "") != active_sid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="다른 기기에서 로그인되어 이 세션은 만료되었습니다.",
                headers={"WWW-Authenticate": "Bearer", "X-Session-Superseded": "1"},
            )
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
