"""Email OTP dispatch (SMTP when configured, log-only in dev)."""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def _dev_mode() -> bool:
    app_env = str(os.getenv("APP_ENV") or "dev").strip().lower()
    return app_env not in {"prod", "production", "stage", "staging"}


def dispatch_email_otp(*, email: str, code: str, purpose: str) -> dict[str, object]:
    """Send signup/friend OTP email. Returns delivery metadata."""
    subject = "[WorldLinco] 인증 코드 안내"
    body = (
        f"WorldLinco {purpose} 인증 코드입니다.\n\n"
        f"인증 코드: {code}\n"
        f"유효 시간: 15분\n\n"
        "본인이 요청하지 않았다면 이 메일을 무시해 주세요."
    )

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587") or "587")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from = os.getenv("SMTP_FROM", smtp_user).strip()

    if not (smtp_host and smtp_from):
        logger.info(
            "[EMAIL_OTP] provider=dev-log purpose=%s target=%s code=%s",
            purpose,
            email,
            code,
        )
        return {
            "provider": "dev-log",
            "delivered": _dev_mode(),
            "email": email,
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            if smtp_user and smtp_password:
                smtp.starttls()
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        logger.info(
            "[EMAIL_OTP] provider=smtp purpose=%s target=%s",
            purpose,
            email,
        )
        return {
            "provider": "smtp",
            "delivered": True,
            "email": email,
        }
    except Exception as exc:
        logger.error(
            "[EMAIL_OTP] provider=smtp purpose=%s target=%s error=%s",
            purpose,
            email,
            exc,
        )
        if _dev_mode():
            return {
                "provider": "smtp-failed-dev-fallback",
                "delivered": False,
                "email": email,
                "error": str(exc)[:200],
            }
        raise RuntimeError("이메일 발송에 실패했습니다. 잠시 후 다시 시도하세요.") from exc
