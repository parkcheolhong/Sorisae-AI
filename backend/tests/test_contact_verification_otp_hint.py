from __future__ import annotations

import logging

from backend.services.contact_verification import (
    expose_dev_otp_hint,
    reset_for_test,
    start_verification_session,
)
from backend.services.email_dispatch import dispatch_email_otp
from backend.services.sms_dispatch import dispatch_sms_text


def _start_recovery():
    reset_for_test()
    return start_verification_session(
        purpose="user_recovery",
        channel="email",
        target_email="user@example.com",
    )


def test_otp_hint_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("CONTACT_VERIFICATION_DEV_OTP_HINT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)

    hidden = _start_recovery()
    assert "devOtpHint" not in hidden
    assert expose_dev_otp_hint() is False

    monkeypatch.setenv("APP_ENV", "dev")
    still_hidden = _start_recovery()
    assert "devOtpHint" not in still_hidden

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CONTACT_VERIFICATION_DEV_OTP_HINT", "1")
    production = _start_recovery()
    assert "devOtpHint" not in production
    assert expose_dev_otp_hint() is False

    monkeypatch.setenv("APP_ENV", "dev")
    revealed = _start_recovery()
    assert revealed.get("devOtpHint")
    assert len(str(revealed["devOtpHint"])) == 6


def test_dispatch_logs_omit_otp_without_opt_in(monkeypatch, caplog):
    monkeypatch.delenv("CONTACT_VERIFICATION_DEV_OTP_HINT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    with caplog.at_level(logging.INFO):
        dispatch_email_otp(email="user@example.com", code="654321", purpose="user_recovery")
        dispatch_sms_text(phone="+821012345678", body="code 654321", purpose="user_recovery")

    assert "654321" not in caplog.text
