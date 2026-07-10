from backend.services.sms_dispatch import dispatch_sms_otp


def test_dispatch_sms_otp_dev_log_when_twilio_not_configured(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)

    result = dispatch_sms_otp(phone="+82-10-1234-5678", code="123456", purpose="signup")

    assert result["provider"] == "dev-log"
    assert result["phone"] == "+82-10-1234-5678"
