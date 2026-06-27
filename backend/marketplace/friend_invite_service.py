"""Verified friend invite — email/phone OTP before persisting Friend rows."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.contact_verification import start_verification_session, verify_session_code


def request_friend_invite_code(
    *,
    sender_user: Any,
    target_email: str,
    phone_number: Optional[str],
    display_name: Optional[str],
    verification_channel: str,
) -> Dict[str, Any]:
    sender_email = str(getattr(sender_user, "email", "") or "").strip().lower()
    normalized_email = str(target_email or "").strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("친구 이메일을 올바르게 입력해 주세요")
    if normalized_email == sender_email:
        raise ValueError("자기 자신은 친구로 추가할 수 없습니다")

    channel = str(verification_channel or "email").strip().lower()
    if channel == "phone" and not phone_number:
        raise ValueError("전화 인증을 선택한 경우 연락처를 입력해 주세요")

    return start_verification_session(
        purpose="friend_invite",
        channel=channel,
        target_email=normalized_email,
        target_phone=phone_number,
        payload={
            "senderUserId": int(sender_user.id),
            "targetEmail": normalized_email,
            "phoneNumber": phone_number,
            "displayName": display_name,
        },
    )


def consume_verified_friend_invite(session_token: str, verification_code: str) -> Dict[str, Any]:
    return verify_session_code(session_token, verification_code)
