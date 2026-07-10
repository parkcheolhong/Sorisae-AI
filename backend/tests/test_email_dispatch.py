from backend.services.email_dispatch import dispatch_email_otp


def test_dispatch_email_otp_dev_log_when_smtp_not_configured(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)

    result = dispatch_email_otp(email="user@example.com", code="123456", purpose="signup")

    assert result["provider"] == "dev-log"
    assert result["email"] == "user@example.com"
