from __future__ import annotations

import base64
from datetime import datetime, timezone
import hmac
import hashlib
import json
import os

from jose import jwt
import requests

from .base import AdapterVerificationResult, AdapterWebhookResult, BillingAdapterConfigurationError, default_period_end
from ..subscription_state_machine import SubscriptionEventType


class GoogleBillingAdapter:
    provider = "google"
    _jwks_cache: dict[str, object] | None = None
    WEBHOOK_EVENT_TYPE_MAP = {
        "purchase_verified": SubscriptionEventType.PURCHASE_VERIFIED,
        "renewal_succeeded": SubscriptionEventType.RENEWAL_SUCCEEDED,
        "renewal_failed": SubscriptionEventType.RENEWAL_FAILED,
        "grace_expired": SubscriptionEventType.GRACE_EXPIRED,
        "cancel_scheduled": SubscriptionEventType.CANCEL_SCHEDULED,
        "cancel_revoked": SubscriptionEventType.CANCEL_REVOKED,
        "period_ended": SubscriptionEventType.PERIOD_ENDED,
        "refund_applied": SubscriptionEventType.REFUND_APPLIED,
        "subscription_suspended": SubscriptionEventType.SUBSCRIPTION_SUSPENDED,
        "subscription_restored": SubscriptionEventType.SUBSCRIPTION_RESTORED,
    }

    GOOGLE_NOTIFICATION_EVENT_MAP = {
        "subscription_purchased": "purchase_verified",
        "subscription_renewed": "renewal_succeeded",
        "subscription_in_grace_period": "grace_expired",
        "subscription_on_hold": "renewal_failed",
        "subscription_canceled": "cancel_scheduled",
        "subscription_recovered": "subscription_restored",
        "subscription_revoked": "refund_applied",
        "subscription_expired": "period_ended",
    }

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _is_production_env() -> bool:
        app_env = str(os.getenv("APP_ENV") or "dev").strip().lower()
        return app_env in {"prod", "production", "stage", "staging"}

    @staticmethod
    def _resolve_expected_issuers() -> list[str]:
        configured = str(os.getenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER") or "").strip()
        if configured:
            return [token.strip() for token in configured.split(",") if token.strip()]
        return ["https://accounts.google.com", "accounts.google.com"]

    @staticmethod
    def _decode_pubsub_data(data: str) -> dict:
        token = str(data or "")
        padded = token + "=" * ((4 - len(token) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Google RTDN data 형식이 올바르지 않습니다.")
        return payload

    @classmethod
    def _fetch_google_jwks(cls, url: str) -> dict:
        if cls._jwks_cache and cls._jwks_cache.get("url") == url:
            cached_payload = cls._jwks_cache.get("payload")
            if isinstance(cached_payload, dict):
                return dict(cached_payload)
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Google JWKS 응답 형식이 올바르지 않습니다.")
        cls._jwks_cache = {"url": url, "payload": payload}
        return payload

    def _verify_oidc_token(self, token: str) -> tuple[dict, bool, str, bool]:
        if not token:
            raise ValueError("Google OIDC 토큰이 비어 있습니다.")

        header = jwt.get_unverified_header(token)
        kid = str(header.get("kid") or "")
        if not kid:
            raise ValueError("Google OIDC kid 가 없습니다.")

        jwks_url = str(os.getenv("MARKETPLACE_GOOGLE_OIDC_JWKS_URL") or "https://www.googleapis.com/oauth2/v3/certs").strip()
        jwks = self._fetch_google_jwks(jwks_url)
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise ValueError("Google JWKS keys 형식이 올바르지 않습니다.")
        key = next((row for row in keys if isinstance(row, dict) and str(row.get("kid") or "") == kid), None)
        if key is None:
            raise ValueError("Google JWKS 에서 kid 를 찾을 수 없습니다.")

        expected_audience = str(os.getenv("MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE") or "").strip()
        expected_service_account = str(os.getenv("MARKETPLACE_GOOGLE_PUBSUB_SERVICE_ACCOUNT") or "").strip().lower()
        issuer_candidates = self._resolve_expected_issuers()

        if self._is_production_env() and not expected_audience:
            raise BillingAdapterConfigurationError(
                "운영 환경에서는 MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE 값을 필수로 설정해야 합니다."
            )
        if self._is_production_env() and not str(os.getenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER") or "").strip():
            raise BillingAdapterConfigurationError(
                "운영 환경에서는 MARKETPLACE_GOOGLE_PUBSUB_ISSUER 값을 필수로 설정해야 합니다."
            )

        decode_kwargs = {
            "key": key,
            "algorithms": ["RS256"],
            "options": {"verify_aud": bool(expected_audience)},
        }
        if expected_audience:
            decode_kwargs["audience"] = expected_audience

        last_error: Exception | None = None
        claims: dict | None = None
        for issuer in issuer_candidates:
            try:
                parsed = jwt.decode(token, issuer=issuer, **decode_kwargs)
                if isinstance(parsed, dict):
                    claims = parsed
                    break
            except Exception as exc:
                last_error = exc
                continue
        if claims is None:
            if last_error:
                raise ValueError(f"Google OIDC 검증에 실패했습니다: {last_error}") from last_error
            raise ValueError("Google OIDC 검증에 실패했습니다.")

        if expected_service_account:
            token_email = str(claims.get("email") or "").strip().lower()
            if token_email != expected_service_account:
                raise ValueError("Google OIDC service account 검증에 실패했습니다.")

        return claims, True, "provider", False

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
                "Google purchase token 검증은 아직 실연동되지 않았습니다. MARKETPLACE_BILLING_ALLOW_SIMULATED_VERIFY=true 에서만 시뮬레이션 검증이 허용됩니다."
            )

        now = self._utcnow_naive()
        token_hash = hashlib.sha256(purchase_token_or_receipt.encode("utf-8")).hexdigest()
        event_id = transaction_id or f"google-sim-{token_hash[:24]}"
        return AdapterVerificationResult(
            provider=self.provider,
            event_type=SubscriptionEventType.PURCHASE_VERIFIED,
            event_time=now,
            period_start=now,
            period_end=default_period_end(now),
            original_transaction_id=event_id,
            latest_transaction_id=event_id,
            purchase_token_hash=token_hash,
            event_id=event_id,
            reason_code="google_purchase_verified",
            verification_mode="simulation",
            verification_simulated=True,
            raw={
                "external_product_id": external_product_id,
                "external_price_id": external_price_id,
                "token_hash": token_hash,
            },
        )

    def parse_webhook(self, *, payload: dict) -> AdapterWebhookResult:
        signed_payload = payload.get("payload") or {}
        pubsub_message = signed_payload.get("message") if isinstance(signed_payload, dict) else None
        decoded_message_payload: dict = {}
        if isinstance(pubsub_message, dict) and pubsub_message.get("data"):
            decoded_message_payload = self._decode_pubsub_data(str(pubsub_message.get("data") or ""))

        event_id = str(
            payload.get("event_id")
            or (pubsub_message.get("messageId") if isinstance(pubsub_message, dict) else None)
            or ""
        ).strip()
        if not event_id:
            raise ValueError("event_id 가 필요합니다.")

        inferred_google_event = str(
            decoded_message_payload.get("eventType")
            or decoded_message_payload.get("notificationType")
            or ""
        ).strip().lower()
        normalized_event_type = str(
            payload.get("event_type")
            or self.GOOGLE_NOTIFICATION_EVENT_MAP.get(inferred_google_event)
            or ""
        ).strip().lower()
        event_type = self.WEBHOOK_EVENT_TYPE_MAP.get(normalized_event_type)
        if event_type is None:
            raise ValueError("지원하지 않는 webhook event_type 입니다.")

        event_time = payload.get("event_time") or self._utcnow_naive()
        signature = str(
            signed_payload.get("x_goog_signature")
            or signed_payload.get("x-goog-signature")
            or signed_payload.get("signature")
            or payload.get("signature")
            or ""
        ).strip()
        secret = str(os.getenv("MARKETPLACE_GOOGLE_WEBHOOK_SIGNING_SECRET") or "").strip()
        oidc_token = str(
            signed_payload.get("oidc_token")
            or payload.get("oidc_token")
            or signed_payload.get("authorization")
            or payload.get("authorization")
            or ""
        ).strip()
        if oidc_token.lower().startswith("bearer "):
            oidc_token = oidc_token[7:].strip()
        enable_oidc_verify = (os.getenv("MARKETPLACE_GOOGLE_WEBHOOK_ENABLE_OIDC_VERIFY", "true") or "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        verification_mode = "simulation"
        verification_simulated = True
        signature_valid = bool(payload.get("signature_valid", True))
        if enable_oidc_verify and oidc_token:
            _, signature_valid, verification_mode, verification_simulated = self._verify_oidc_token(oidc_token)
        elif secret:
            payload_for_signature = dict(signed_payload)
            payload_for_signature.pop("signature", None)
            payload_for_signature.pop("x-goog-signature", None)
            payload_for_signature.pop("x_goog_signature", None)
            raw_body = str(
                signed_payload.get("raw_body")
                or payload.get("raw_body")
                or ""
            )
            message = raw_body or json.dumps(payload_for_signature, ensure_ascii=True, separators=(",", ":"), default=str)
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
            raw={"provider": self.provider, **payload, "decoded_message_payload": decoded_message_payload},
        )