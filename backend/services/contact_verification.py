"""Email/phone OTP verification sessions (signup, friend invite)."""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from secrets import randbelow
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

OTP_TTL = timedelta(minutes=15)
MAX_VERIFY_ATTEMPTS = 5
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dev_mode() -> bool:
    app_env = str(os.getenv("APP_ENV") or "dev").strip().lower()
    return app_env not in {"prod", "production", "stage", "staging"}


def _mask_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if "@" not in normalized:
        return "***"
    local, domain = normalized.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[:1]}*"
    else:
        masked_local = f"{local[:2]}***"
    return f"{masked_local}@{domain}"


def _mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    if phone is None:
        return None
    cleaned = str(phone).strip()
    return cleaned or None


def _dispatch_email_otp(email: str, code: str, purpose: str) -> None:
    from backend.services.email_dispatch import dispatch_email_otp

    try:
        dispatch_email_otp(email=email, code=code, purpose=purpose)
    except RuntimeError:
        raise
    except Exception as exc:
        logger.exception(
            "[CONTACT_OTP] channel=email purpose=%s target=%s dispatch_error=%s",
            purpose,
            email,
            exc,
        )
        raise RuntimeError("이메일 발송에 실패했습니다. 잠시 후 다시 시도하세요.") from exc


def _dispatch_phone_otp(phone: str, code: str, purpose: str) -> None:
    from backend.services.sms_dispatch import dispatch_sms_otp

    try:
        dispatch_sms_otp(phone=phone, code=code, purpose=purpose)
    except RuntimeError:
        raise
    except Exception as exc:
        logger.exception(
            "[CONTACT_OTP] channel=phone purpose=%s target=%s dispatch_error=%s",
            purpose,
            phone,
            exc,
        )
        raise RuntimeError("SMS 발송에 실패했습니다. 잠시 후 다시 시도하세요.") from exc


def _purge_expired_sessions() -> None:
    now = _utcnow()
    for key, session in list(_SESSIONS.items()):
        expires_at = session.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at <= now:
            _SESSIONS.pop(key, None)


def start_verification_session(
    *,
    purpose: str,
    channel: str,
    target_email: Optional[str] = None,
    target_phone: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _purge_expired_sessions()
    normalized_channel = str(channel or "email").strip().lower()
    email = str(target_email or "").strip().lower() or None
    phone = _normalize_phone(target_phone)

    if normalized_channel == "email":
        if not email or "@" not in email:
            raise ValueError("이메일 인증을 위해 유효한 이메일이 필요합니다")
    elif normalized_channel == "phone":
        if not phone or len(re.sub(r"\D", "", phone)) < 8:
            raise ValueError("전화 인증을 위해 유효한 연락처가 필요합니다")
    else:
        raise ValueError("verificationChannel 은 email 또는 phone 이어야 합니다")

    code = str(randbelow(1000000)).zfill(6)
    session_token = f"{purpose}_{uuid4().hex}"
    expires_at = _utcnow() + OTP_TTL
    _SESSIONS[session_token] = {
        "purpose": purpose,
        "channel": normalized_channel,
        "email": email,
        "phone": phone,
        "verification_code": code,
        "attempts": 0,
        "expires_at": expires_at,
        "verified": False,
        "payload": dict(payload or {}),
    }

    if normalized_channel == "email" and email:
        try:
            _dispatch_email_otp(email, code, purpose)
        except RuntimeError as exc:
            _SESSIONS.pop(session_token, None)
            raise exc
    if normalized_channel == "phone" and phone:
        try:
            _dispatch_phone_otp(phone, code, purpose)
        except RuntimeError as exc:
            _SESSIONS.pop(session_token, None)
            raise exc

    response: Dict[str, Any] = {
        "sessionToken": session_token,
        "verificationChannel": normalized_channel,
        "expiresAt": expires_at.isoformat(),
        "maskedTarget": _mask_email(email) if normalized_channel == "email" else _mask_phone(phone or ""),
    }
    if _dev_mode():
        response["devOtpHint"] = code
    return response


def verify_session_code(session_token: str, verification_code: str) -> Dict[str, Any]:
    _purge_expired_sessions()
    session = _SESSIONS.get(str(session_token or "").strip())
    if not session:
        raise LookupError("인증 세션을 찾을 수 없습니다")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at <= _utcnow():
        _SESSIONS.pop(str(session_token), None)
        raise TimeoutError("인증 세션이 만료되었습니다")

    attempts = int(session.get("attempts") or 0)
    if attempts >= MAX_VERIFY_ATTEMPTS:
        _SESSIONS.pop(str(session_token), None)
        raise PermissionError("인증 시도 횟수를 초과했습니다")

    expected = str(session.get("verification_code") or "")
    if str(verification_code or "").strip() != expected:
        session["attempts"] = attempts + 1
        if session["attempts"] >= MAX_VERIFY_ATTEMPTS:
            _SESSIONS.pop(str(session_token), None)
            raise PermissionError("인증 시도 횟수를 초과했습니다")
        raise ValueError("인증 코드가 올바르지 않습니다")

    session["verified"] = True
    payload = dict(session.get("payload") or {})
    payload["_verification"] = {
        "channel": session.get("channel"),
        "email": session.get("email"),
        "phone": session.get("phone"),
        "verifiedAt": _utcnow().isoformat(),
    }
    _SESSIONS.pop(str(session_token), None)
    return payload


def allow_unverified_signup() -> bool:
    return str(os.getenv("ALLOW_UNVERIFIED_SIGNUP", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def allow_unverified_friend_add() -> bool:
    return str(os.getenv("ALLOW_UNVERIFIED_FRIEND_ADD", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
