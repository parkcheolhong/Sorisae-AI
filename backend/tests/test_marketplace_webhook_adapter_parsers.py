from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
from datetime import timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID
from jose import jwt

import pytest

from backend.marketplace.provider_adapters.apple_billing import AppleBillingAdapter
from backend.marketplace.provider_adapters.google_billing import GoogleBillingAdapter
from backend.marketplace.provider_adapters.stripe_billing import StripeBillingAdapter
from backend.marketplace.provider_adapters.base import BillingAdapterConfigurationError

# ---------------------------------------------------------------------------
# 테스트 전용 서명 키 상수 (실제 운영 시크릿 아님 · test-only, never deployed)
# ---------------------------------------------------------------------------
_TEST_STRIPE_SIGNING_KEY = "stripe-signing-key-testonly"
_TEST_APPLE_SIGNING_KEY = "apple-signing-key-testonly"
_TEST_GOOGLE_SIGNING_KEY = "google-signing-key-testonly"


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _make_hs256_jws(payload: dict, signing_key: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    head = _b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    body = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    signature = hmac.new(signing_key.encode("utf-8"), f"{head}.{body}".encode("utf-8"), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64url(signature)}"


def _make_es256_jws_with_x5c(payload: dict):
    now = _utcnow_naive()

    root_key = ec.generate_private_key(ec.SECP256R1())
    root_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Apple Root Test")])
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_subject)
        .issuer_name(root_subject)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .sign(root_key, hashes.SHA256())
    )

    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Apple Leaf Test")])
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(leaf_subject)
        .issuer_name(root_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(root_key, hashes.SHA256())
    )

    header = {
        "alg": "ES256",
        "typ": "JWT",
        "x5c": [
            base64.b64encode(leaf_cert.public_bytes(serialization.Encoding.DER)).decode("utf-8"),
            base64.b64encode(root_cert.public_bytes(serialization.Encoding.DER)).decode("utf-8"),
        ],
    }
    head = _b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    body = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    signed = f"{head}.{body}".encode("utf-8")
    signature_der = leaf_key.sign(signed, ec.ECDSA(hashes.SHA256()))
    token = f"{head}.{body}.{_b64url(signature_der)}"
    root_pem = root_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return token, root_pem


def _make_google_oidc_token(audience: str):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_numbers()
    n = public_key.n.to_bytes((public_key.n.bit_length() + 7) // 8, "big")
    e = public_key.e.to_bytes((public_key.e.bit_length() + 7) // 8, "big")
    kid = "test-kid-1"
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _b64url(n),
                "e": _b64url(e),
            }
        ]
    }
    claims = {
        "iss": "https://accounts.google.com",
        "aud": audience,
        "email": "push-sa@example.iam.gserviceaccount.com",
        "sub": "1234567890",
    }
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})
    return token, jwks


def test_stripe_parser_supports_real_signature_header(monkeypatch):
    adapter = StripeBillingAdapter()
    signing_key = _TEST_STRIPE_SIGNING_KEY
    monkeypatch.setenv("MARKETPLACE_STRIPE_WEBHOOK_SIGNING_SECRET", signing_key)
    raw_payload = {"id": "evt_001", "type": "invoice.paid"}
    raw_body = json.dumps(raw_payload, separators=(",", ":"), ensure_ascii=True)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    signature = hmac.new(signing_key.encode("utf-8"), f"{timestamp}.{raw_body}".encode("utf-8"), hashlib.sha256).hexdigest()

    result = adapter.parse_webhook(
        payload={
            "event_id": "evt_001",
            "event_type": "invoice.paid",
            "payload": {
                "raw_body": raw_body,
                "stripe_signature": f"t={timestamp},v1={signature}",
            },
        }
    )

    assert result.signature_valid is True
    assert result.verification_mode == "provider"
    assert result.verification_simulated is False


def test_apple_parser_supports_signed_payload_jws(monkeypatch):
    adapter = AppleBillingAdapter()
    signing_key = _TEST_APPLE_SIGNING_KEY
    monkeypatch.setenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET", signing_key)
    signed_date_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    token = _make_hs256_jws(
        {
            "notificationUUID": "apple-event-001",
            "notificationType": "DID_RENEW",
            "signedDate": signed_date_ms,
        },
        signing_key,
    )

    result = adapter.parse_webhook(
        payload={
            "event_type": "did_renew",
            "payload": {
                "signedPayload": token,
            },
        }
    )

    assert result.event_id == "apple-event-001"
    assert result.signature_valid is True
    assert result.verification_mode == "provider"


def test_google_parser_supports_pubsub_envelope(monkeypatch):
    adapter = GoogleBillingAdapter()
    signing_key = _TEST_GOOGLE_SIGNING_KEY
    monkeypatch.setenv("MARKETPLACE_GOOGLE_WEBHOOK_SIGNING_SECRET", signing_key)
    envelope = {
        "message": {
            "messageId": "google-msg-001",
            "data": _b64url(json.dumps({"eventType": "SUBSCRIPTION_RENEWED"}, separators=(",", ":"), ensure_ascii=True).encode("utf-8")),
        },
    }
    signature_source = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True)
    signature = hmac.new(signing_key.encode("utf-8"), signature_source.encode("utf-8"), hashlib.sha256).hexdigest()

    result = adapter.parse_webhook(
        payload={
            "event_type": "renewal_succeeded",
            "payload": {
                **envelope,
                "x-goog-signature": signature,
            },
        }
    )

    assert result.event_id == "google-msg-001"
    assert result.signature_valid is True
    assert result.verification_mode == "provider"


def test_apple_parser_supports_es256_x5c_chain(monkeypatch):
    adapter = AppleBillingAdapter()
    signed_date_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    token, root_pem = _make_es256_jws_with_x5c(
        {
            "notificationUUID": "apple-event-es256-001",
            "notificationType": "DID_RENEW",
            "signedDate": signed_date_ms,
        }
    )
    monkeypatch.delenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.setenv("MARKETPLACE_APPLE_WEBHOOK_ENABLE_X5C_VERIFY", "true")
    monkeypatch.setenv("MARKETPLACE_APPLE_ROOT_CA_PEM", root_pem)

    result = adapter.parse_webhook(
        payload={
            "event_type": "did_renew",
            "payload": {"signedPayload": token},
        }
    )

    assert result.event_id == "apple-event-es256-001"
    assert result.signature_valid is True
    assert result.verification_mode == "provider"


def test_google_parser_supports_oidc_pubsub_chain(monkeypatch):
    adapter = GoogleBillingAdapter()
    audience = "https://example.com/pubsub/push"
    token, jwks = _make_google_oidc_token(audience)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_WEBHOOK_ENABLE_OIDC_VERIFY", "true")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE", audience)
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_SERVICE_ACCOUNT", "push-sa@example.iam.gserviceaccount.com")
    monkeypatch.setattr(GoogleBillingAdapter, "_fetch_google_jwks", classmethod(lambda cls, url: jwks))

    result = adapter.parse_webhook(
        payload={
            "event_id": "google-oidc-msg-001",
            "event_type": "renewal_succeeded",
            "payload": {
                "oidc_token": token,
            },
        }
    )

    assert result.event_id == "google-oidc-msg-001"
    assert result.signature_valid is True
    assert result.verification_mode == "provider"


def test_apple_parser_supports_es256_x5c_chain_with_root_ca_file(monkeypatch, tmp_path):
    adapter = AppleBillingAdapter()
    signed_date_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    token, root_pem = _make_es256_jws_with_x5c(
        {
            "notificationUUID": "apple-event-es256-file-001",
            "notificationType": "DID_RENEW",
            "signedDate": signed_date_ms,
        }
    )
    root_ca_file = tmp_path / "apple_root_ca.pem"
    root_ca_file.write_text(root_pem, encoding="utf-8")

    monkeypatch.delenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("MARKETPLACE_APPLE_ROOT_CA_PEM", raising=False)
    monkeypatch.setenv("MARKETPLACE_APPLE_WEBHOOK_ENABLE_X5C_VERIFY", "true")
    monkeypatch.setenv("MARKETPLACE_APPLE_ROOT_CA_PEM_FILE", str(root_ca_file))

    result = adapter.parse_webhook(
        payload={
            "event_type": "did_renew",
            "payload": {"signedPayload": token},
        }
    )

    assert result.event_id == "apple-event-es256-file-001"
    assert result.signature_valid is True
    assert result.verification_mode == "provider"


def test_google_parser_requires_audience_in_production_oidc(monkeypatch):
    adapter = GoogleBillingAdapter()
    audience = "https://example.com/pubsub/push"
    token, jwks = _make_google_oidc_token(audience)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_WEBHOOK_ENABLE_OIDC_VERIFY", "true")
    monkeypatch.delenv("MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE", raising=False)
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER", "https://accounts.google.com")
    monkeypatch.setattr(GoogleBillingAdapter, "_fetch_google_jwks", classmethod(lambda cls, url: jwks))

    with pytest.raises(BillingAdapterConfigurationError):
        adapter.parse_webhook(
            payload={
                "event_id": "google-oidc-prod-missing-aud",
                "event_type": "renewal_succeeded",
                "payload": {
                    "oidc_token": token,
                },
            }
        )


def test_google_parser_requires_issuer_in_production_oidc(monkeypatch):
    adapter = GoogleBillingAdapter()
    audience = "https://example.com/pubsub/push"
    token, jwks = _make_google_oidc_token(audience)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_WEBHOOK_ENABLE_OIDC_VERIFY", "true")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE", audience)
    monkeypatch.delenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER", raising=False)
    monkeypatch.setattr(GoogleBillingAdapter, "_fetch_google_jwks", classmethod(lambda cls, url: jwks))

    with pytest.raises(BillingAdapterConfigurationError):
        adapter.parse_webhook(
            payload={
                "event_id": "google-oidc-prod-missing-issuer",
                "event_type": "renewal_succeeded",
                "payload": {
                    "oidc_token": token,
                },
            }
        )


def test_apple_parser_rejects_invalid_jws_signature(monkeypatch):
    adapter = AppleBillingAdapter()
    monkeypatch.setenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET", "apple-test-secret")
    bad_token = _make_hs256_jws(
        {
            "notificationUUID": "apple-event-bad",
            "notificationType": "DID_RENEW",
        },
        "different-secret",
    )

    with pytest.raises(ValueError):
        adapter.parse_webhook(
            payload={
                "event_type": "did_renew",
                "payload": {"signedPayload": bad_token},
            }
        )