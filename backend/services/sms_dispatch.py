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


def dispatch_sms_otp(*, phone: str, code: str, purpose: str) -> dict[str, object]:
    """Send signup/friend OTP SMS. Returns delivery metadata for audit."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    message_body = f"[WorldLinco] {purpose} 인증 코드: {code} (15분 유효)"

    if not (account_sid and auth_token and from_number):
        logger.info(
            "[SMS_OTP] provider=dev-log purpose=%s target=%s code=%s",
            purpose,
            phone,
            code,
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
            "Body": message_body,
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
            body = json.loads(response.read().decode("utf-8"))
        logger.info(
            "[SMS_OTP] provider=twilio purpose=%s target=%s sid=%s",
            purpose,
            phone,
            body.get("sid"),
        )
        return {
            "provider": "twilio",
            "delivered": True,
            "phone": phone,
            "message_sid": body.get("sid"),
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "[SMS_OTP] provider=twilio purpose=%s target=%s http=%s detail=%s",
            purpose,
            phone,
            exc.code,
            detail[:500],
        )
        if _dev_mode():
            return {
                "provider": "twilio-failed-dev-fallback",
                "delivered": False,
                "phone": phone,
                "error": detail[:200],
            }
        raise RuntimeError("SMS 발송에 실패했습니다. 잠시 후 다시 시도하세요.") from exc
