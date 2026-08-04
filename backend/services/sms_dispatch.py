"""SMS OTP dispatch (Twilio when configured, log-only in dev)."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def _dev_mode() -> bool:
    app_env = str(os.getenv("APP_ENV") or "dev").strip().lower()
    return app_env not in {"prod", "production", "stage", "staging"}


def _mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def dispatch_sms_otp(*, phone: str, code: str, purpose: str) -> dict[str, object]:
    """Send signup/friend OTP SMS. Returns delivery metadata for audit."""
    message_body = f"[WorldLinco] {purpose} 인증 코드: {code} (15분 유효)"
    return dispatch_sms_text(phone=phone, body=message_body, purpose=purpose)


def dispatch_sms_text(*, phone: str, body: str, purpose: str) -> dict[str, object]:
    """Send arbitrary SMS text (admin announcements, OTP, etc.)."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    normalized_body = str(body or "").strip()
    if not normalized_body:
        raise ValueError("SMS 본문이 비어 있습니다.")

    if not (account_sid and auth_token and from_number):
        logger.info(
            "[SMS_TEXT] provider=dev-log purpose=%s target=%s body_length=%s",
            purpose,
            _mask_phone(phone),
            len(normalized_body),
        )
        return {
            "provider": "dev-log",
            "delivered": _dev_mode(),
            "phone": phone,
        }

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urllib.parse.urlencode(
        {
            "To": phone,
            "From": from_number,
            "Body": normalized_body,
        },
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    import base64

    request.add_header(
        "Authorization",
        f"Basic {base64.b64encode(credentials).decode('ascii')}",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = json.loads(response.read().decode("utf-8"))
        logger.info(
            "[SMS_TEXT] provider=twilio purpose=%s target=%s sid=%s",
            purpose,
            _mask_phone(phone),
            response_body.get("sid"),
        )
        return {
            "provider": "twilio",
            "delivered": True,
            "phone": phone,
            "message_sid": response_body.get("sid"),
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "[SMS_TEXT] provider=twilio purpose=%s target=%s http=%s",
            purpose,
            _mask_phone(phone),
            exc.code,
        )
        if _dev_mode():
            return {
                "provider": "twilio-failed-dev-fallback",
                "delivered": False,
                "phone": phone,
                "error": detail[:200],
            }
        raise RuntimeError("SMS 발송에 실패했습니다. 잠시 후 다시 시도하세요.") from exc
