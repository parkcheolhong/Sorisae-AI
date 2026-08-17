from __future__ import annotations

import base64
from datetime import datetime, timezone
import hmac
import hashlib
import json
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from .base import AdapterVerificationResult, AdapterWebhookResult, BillingAdapterConfigurationError, default_period_end
from ..subscription_state_machine import SubscriptionEventType


class AppleBillingAdapter:
    provider = "apple"
    WEBHOOK_EVENT_TYPE_MAP = {
        "purchase_verified": SubscriptionEventType.PURCHASE_VERIFIED,
        "did_renew": SubscriptionEventType.RENEWAL_SUCCEEDED,
        "renewal_failed": SubscriptionEventType.RENEWAL_FAILED,
        "grace_expired": SubscriptionEventType.GRACE_EXPIRED,
        "cancel_scheduled": SubscriptionEventType.CANCEL_SCHEDULED,
        "cancel_revoked": SubscriptionEventType.CANCEL_REVOKED,
        "expired": SubscriptionEventType.PERIOD_ENDED,
        "refund_applied": SubscriptionEventType.REFUND_APPLIED,
        "subscription_suspended": SubscriptionEventType.SUBSCRIPTION_SUSPENDED,
        "subscription_restored": SubscriptionEventType.SUBSCRIPTION_RESTORED,
    }

    APPLE_NOTIFICATION_EVENT_MAP = {
        "subscribed": "purchase_verified",
        "did_renew": "did_renew",
        "did_fail_to_renew": "renewal_failed",
        "grace_period_expired": "grace_expired",
        "expired": "expired",
        "refund": "refund_applied",
    }

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _resolve_root_ca_pem() -> str | None:
        inline_value = str(os.getenv("MARKETPLACE_APPLE_ROOT_CA_PEM") or "").strip()
        if inline_value:
            return inline_value

        for env_name in ("MARKETPLACE_APPLE_ROOT_CA_PEM_FILE", "MARKETPLACE_APPLE_PINSET_FILE"):
            configured = str(os.getenv(env_name) or "").strip()
            if not configured:
                continue
            pem_path = Path(configured).expanduser()
            if not pem_path.is_file():
                raise ValueError(f"Apple root CA 파일을 찾을 수 없습니다: {pem_path}")
            value = pem_path.read_text(encoding="utf-8").strip()
            if not value:
                raise ValueError(f"Apple root CA 파일이 비어 있습니다: {pem_path}")
            return value
        return None

    @staticmethod
    def _decode_b64url_to_json(value: str) -> dict:
        token = str(value or "")
        padded = token + "=" * ((4 - len(token) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Apple signedPayload 형식이 올바르지 않습니다.")
        return payload

    @staticmethod
    def _decode_b64url_to_bytes(value: str) -> bytes:
        token = str(value or "")
        padded = token + "=" * ((4 - len(token) % 4) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8"))

    @staticmethod
    def _verify_cert_signature(child_cert: x509.Certificate, issuer_cert: x509.Certificate) -> None:
        issuer_public_key = issuer_cert.public_key()
        signature_hash_algorithm = child_cert.signature_hash_algorithm
        if signature_hash_algorithm is None:
            raise ValueError("x5c 인증서 서명 알고리즘을 확인할 수 없습니다.")
        if isinstance(issuer_public_key, rsa.RSAPublicKey):
            issuer_public_key.verify(
                child_cert.signature,
                child_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                signature_hash_algorithm,
            )
            return
        if isinstance(issuer_public_key, ec.EllipticCurvePublicKey):
            issuer_public_key.verify(
                child_cert.signature,
                child_cert.tbs_certificate_bytes,
                ec.ECDSA(signature_hash_algorithm),
            )
            return
        raise ValueError("지원하지 않는 x5c 공개키 타입입니다.")

    def _parse_signed_payload_es256_x5c(
        self,
        token: str,
        *,
        root_ca_pem: str | None,
    ) -> tuple[dict, bool, str, bool]:
        parts = str(token or "").split(".")
        if len(parts) != 3:
            raise ValueError("Apple signedPayload JWS 형식이 올바르지 않습니다.")

        header = self._decode_b64url_to_json(parts[0])
        payload = self._decode_b64url_to_json(parts[1])
        algorithm = str(header.get("alg") or "").upper()
        if algorithm != "ES256":
            raise ValueError("Apple x5c 검증은 ES256 알고리즘만 지원합니다.")

        x5c_chain = header.get("x5c")
        if not isinstance(x5c_chain, list) or not x5c_chain:
            raise ValueError("Apple signedPayload x5c 체인이 없습니다.")

        certificates: list[x509.Certificate] = []
        now = self._utcnow_naive()
        for raw_cert in x5c_chain:
            if not isinstance(raw_cert, str) or not raw_cert.strip():
                raise ValueError("Apple x5c 인증서 형식이 올바르지 않습니다.")
            cert_der = base64.b64decode(raw_cert.encode("utf-8"))
            cert = x509.load_der_x509_certificate(cert_der)
            cert_not_before = cert.not_valid_before_utc.replace(tzinfo=None)
            cert_not_after = cert.not_valid_after_utc.replace(tzinfo=None)
            if now < cert_not_before or now > cert_not_after:
                raise ValueError("Apple x5c 인증서 유효기간 검증에 실패했습니다.")
            certificates.append(cert)

        for index in range(len(certificates) - 1):
            self._verify_cert_signature(certificates[index], certificates[index + 1])

        if root_ca_pem:
            root_cert = x509.load_pem_x509_certificate(root_ca_pem.encode("utf-8"))
            last_cert = certificates[-1]
            if root_cert.fingerprint(hashes.SHA256()) != last_cert.fingerprint(hashes.SHA256()):
                self._verify_cert_signature(last_cert, root_cert)

        leaf_key = certificates[0].public_key()
        if not isinstance(leaf_key, ec.EllipticCurvePublicKey):
            raise ValueError("Apple leaf 인증서 공개키가 ECDSA 타입이 아닙니다.")
        signed_message = f"{parts[0]}.{parts[1]}".encode("utf-8")
        signature = self._decode_b64url_to_bytes(parts[2])
        leaf_key.verify(signature, signed_message, ec.ECDSA(hashes.SHA256()))

        return payload, True, "provider", False

    def _parse_signed_payload_jws(self, token: str, secret: str | None) -> tuple[dict, bool, str, bool]:
        parts = str(token or "").split(".")
        if len(parts) != 3:
            raise ValueError("Apple signedPayload JWS 형식이 올바르지 않습니다.")

        header = self._decode_b64url_to_json(parts[0])
        payload = self._decode_b64url_to_json(parts[1])
        algorithm = str(header.get("alg") or "").upper()
        verification_mode = "simulation"
        verification_simulated = True
        signature_valid = True

        if secret:
            if algorithm != "HS256":
                raise ValueError("Apple signedPayload 검증은 현재 HS256 개발 모드만 지원합니다.")
            signed_message = f"{parts[0]}.{parts[1]}"
            expected = hmac.new(
                secret.encode("utf-8"),
                signed_message.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            token_signature = base64.urlsafe_b64decode(parts[2] + "=" * ((4 - len(parts[2]) % 4) % 4))
            signature_valid = hmac.compare_digest(expected, token_signature)
            verification_mode = "provider"
            verification_simulated = False
            if not signature_valid:
                raise ValueError("Apple signedPayload signature 검증에 실패했습니다.")

        return payload, signature_valid, verification_mode, verification_simulated

    def verify_purchase(
        self,
        *,
        purchase_token_or_receipt: str,
        transaction_id: str | None,
        external_product_id: str | None,
        external_price_id: str | None,
    ) -> AdapterVerificationResult:
        allow_simulation = (os.getenv("MARKETPLACE_BILLING_ALLOW_SIMULATED_VERIFY", "false") or "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not allow_simulation:
            raise BillingAdapterConfigurationError(
                "Apple receipt 검증은 아직 실연동되지 않았습니다. MARKETPLACE_BILLING_ALLOW_SIMULATED_VERIFY=true 에서만 시뮬레이션 검증이 허용됩니다."
            )

        now = self._utcnow_naive()
        receipt_hash = hashlib.sha256(purchase_token_or_receipt.encode("utf-8")).hexdigest()
        event_id = transaction_id or f"apple-sim-{receipt_hash[:24]}"
        return AdapterVerificationResult(
            provider=self.provider,
            event_type=SubscriptionEventType.PURCHASE_VERIFIED,
            event_time=now,
            period_start=now,
            period_end=default_period_end(now),
            original_transaction_id=event_id,
            latest_transaction_id=event_id,
            purchase_token_hash=receipt_hash,
            event_id=event_id,
            reason_code="apple_receipt_verified",
            verification_mode="simulation",
            verification_simulated=True,
            raw={
                "external_product_id": external_product_id,
                "external_price_id": external_price_id,
                "receipt_hash": receipt_hash,
            },
        )

    def parse_webhook(self, *, payload: dict) -> AdapterWebhookResult:
        signed_payload = payload.get("payload") or {}
        signed_payload_jws = str(
            signed_payload.get("signedPayload")
            or signed_payload.get("signed_payload")
            or payload.get("signedPayload")
            or payload.get("signed_payload")
            or ""
        ).strip()
        secret = str(os.getenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET") or "").strip() or None
        root_ca_pem = self._resolve_root_ca_pem()
        enable_x5c_verify = (os.getenv("MARKETPLACE_APPLE_WEBHOOK_ENABLE_X5C_VERIFY", "true") or "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        require_signed_payload = (os.getenv("MARKETPLACE_APPLE_WEBHOOK_REQUIRE_JWS", "false") or "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        jws_payload: dict = {}
        signature_valid = bool(payload.get("signature_valid", True))
        verification_mode = "simulation"
        verification_simulated = True
        if signed_payload_jws:
            if secret:
                jws_payload, signature_valid, verification_mode, verification_simulated = self._parse_signed_payload_jws(
                    signed_payload_jws,
                    secret,
                )
            elif enable_x5c_verify:
                jws_payload, signature_valid, verification_mode, verification_simulated = self._parse_signed_payload_es256_x5c(
                    signed_payload_jws,
                    root_ca_pem=root_ca_pem,
                )
            else:
                jws_payload = self._decode_b64url_to_json(signed_payload_jws.split(".")[1])
        elif require_signed_payload:
            raise ValueError("Apple webhook 은 signedPayload(JWS)가 필요합니다.")

        event_id = str(
            payload.get("event_id")
            or jws_payload.get("notificationUUID")
            or jws_payload.get("transactionId")
            or ""
        ).strip()
        if not event_id:
            raise ValueError("event_id 가 필요합니다.")

        inferred_apple_event = str(
            jws_payload.get("notificationType")
            or jws_payload.get("notification_type")
            or ""
        ).strip().lower()
        normalized_event_type = str(
            payload.get("event_type")
            or self.APPLE_NOTIFICATION_EVENT_MAP.get(inferred_apple_event)
            or ""
        ).strip().lower()
        event_type = self.WEBHOOK_EVENT_TYPE_MAP.get(normalized_event_type)
        if event_type is None:
            raise ValueError("지원하지 않는 webhook event_type 입니다.")

        signed_date_ms = jws_payload.get("signedDate")
        if signed_date_ms is not None:
            try:
                event_time = datetime.fromtimestamp(float(signed_date_ms) / 1000.0, timezone.utc).replace(tzinfo=None)
            except Exception:
                event_time = payload.get("event_time") or self._utcnow_naive()
        else:
            event_time = payload.get("event_time") or self._utcnow_naive()

        signed_payload = payload.get("payload") or {}
        if secret and not signed_payload_jws:
            signature = str(
                signed_payload.get("signature")
                or payload.get("signature")
                or ""
            ).strip()
            payload_for_signature = dict(signed_payload)
            payload_for_signature.pop("signature", None)
            message = json.dumps(payload_for_signature, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
            expected = hmac.new(
                secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            verification_mode = "provider"
            verification_simulated = False
            signature_valid = bool(signature) and hmac.compare_digest(expected, signature)
            if not signature_valid:
                raise ValueError("webhook signature 검증에 실패했습니다.")

        return AdapterWebhookResult(
            provider=self.provider,
            event_id=event_id,
            event_type=event_type,
            event_time=event_time,
            user_id=payload.get("user_id"),
            product_code=payload.get("product_code"),
            plan_code=payload.get("plan_code"),
            period_start=payload.get("period_start"),
            period_end=payload.get("period_end"),
            grace_until=payload.get("grace_until"),
            cancel_at_period_end=payload.get("cancel_at_period_end"),
            reason_code=payload.get("reason_code"),
            external_customer_id=payload.get("external_customer_id"),
            external_subscription_id=payload.get("external_subscription_id"),
            original_transaction_id=payload.get("original_transaction_id"),
            latest_transaction_id=payload.get("latest_transaction_id"),
            purchase_token_hash=payload.get("purchase_token_hash"),
            signature_valid=signature_valid,
            verification_mode=verification_mode,
            verification_simulated=verification_simulated,
            raw={"provider": self.provider, **payload},
        )