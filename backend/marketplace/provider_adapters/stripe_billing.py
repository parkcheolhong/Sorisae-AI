from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import json
import os
import time
from urllib.parse import quote
from uuid import uuid4

from .base import AdapterCheckoutSession, AdapterWebhookResult, BillingAdapterConfigurationError
from ..subscription_state_machine import SubscriptionEventType


class StripeBillingAdapter:
    provider = "stripe"
    WEBHOOK_EVENT_TYPE_MAP = {
        "checkout.session.completed": SubscriptionEventType.PURCHASE_VERIFIED,
        "invoice.paid": SubscriptionEventType.RENEWAL_SUCCEEDED,
        "invoice.payment_failed": SubscriptionEventType.RENEWAL_FAILED,
        "customer.subscription.deleted": SubscriptionEventType.PERIOD_ENDED,
        "charge.refunded": SubscriptionEventType.REFUND_APPLIED,
        "customer.subscription.updated.cancel_scheduled": SubscriptionEventType.CANCEL_SCHEDULED,
        "customer.subscription.updated.cancel_revoked": SubscriptionEventType.CANCEL_REVOKED,
    }

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _parse_stripe_signature_header(header_value: str) -> tuple[int | None, list[str]]:
        timestamp = None
        signatures: list[str] = []
        for part in str(header_value or "").split(","):
            key, sep, value = part.strip().partition("=")
            if sep != "=" or not value:
                continue
            normalized_key = key.strip().lower()
            normalized_value = value.strip()
            if normalized_key == "t":
                try:
                    timestamp = int(normalized_value)
                except ValueError:
                    timestamp = None
            elif normalized_key == "v1":
                signatures.append(normalized_value)
        return timestamp, signatures

    def create_checkout_session(
        self,
        *,
        user_id: int,
        product_code: str,
        plan_code: str,
        price_lookup_key: str,
        success_url: str,
        cancel_url: str,
    ) -> AdapterCheckoutSession:
        allow_simulation = (os.getenv("MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT", "true") or "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        stripe_secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
        if not allow_simulation and not stripe_secret_key:
            raise BillingAdapterConfigurationError(
                "Stripe checkout session 실연동 설정이 없습니다. STRIPE_SECRET_KEY 또는 MARKETPLACE_BILLING_ALLOW_SIMULATED_CHECKOUT=true 가 필요합니다."
            )

        expires_at = self._utcnow_naive() + timedelta(minutes=30)

        # 실연동: STRIPE_SECRET_KEY 존재 + 시뮬레이션 비활성화 시 실제 Stripe API 호출
        if not allow_simulation and stripe_secret_key:
            try:
                import stripe as _stripe  # lazy import — stripe SDK 선택적 의존
            except ImportError as exc:
                raise BillingAdapterConfigurationError(
                    "stripe 패키지가 설치되지 않았습니다. pip install 'stripe>=10.0.0'"
                ) from exc
            _stripe.api_key = stripe_secret_key
            session = _stripe.checkout.Session.create(
                success_url=success_url,
                cancel_url=cancel_url,
                mode="subscription",
                line_items=[{"price": price_lookup_key, "quantity": 1}],
                metadata={
                    "user_id": str(user_id),
                    "product_code": product_code,
                    "plan_code": plan_code,
                },
            )
            return AdapterCheckoutSession(
                provider=self.provider,
                checkout_url=session.url,
                session_id=session.id,
                expires_at=expires_at,
                verification_mode="provider",
                verification_simulated=False,
                raw={
                    "user_id": user_id,
                    "product_code": product_code,
                    "plan_code": plan_code,
                    "price_lookup_key": price_lookup_key,
                },
            )

        # 시뮬레이션 모드 (기본값 — STRIPE_SECRET_KEY 없거나 allow_simulation=true)
        session_id = f"cs_test_{uuid4().hex[:24]}"
        base_url = (os.getenv("MARKETPLACE_STRIPE_CHECKOUT_BASE_URL", "https://billing.example.com/stripe/checkout") or "https://billing.example.com/stripe/checkout").strip()
        query = (
            f"session_id={quote(session_id)}"
            f"&user_id={user_id}"
            f"&product_code={quote(product_code)}"
            f"&plan_code={quote(plan_code)}"
            f"&price_lookup_key={quote(price_lookup_key)}"
            f"&success_url={quote(success_url, safe=':/?=&')}"
            f"&cancel_url={quote(cancel_url, safe=':/?=&')}"
        )
        return AdapterCheckoutSession(
            provider=self.provider,
            checkout_url=f"{base_url}?{query}",
            session_id=session_id,
            expires_at=expires_at,
            verification_mode="simulation",
            verification_simulated=True,
            raw={
                "user_id": user_id,
                "product_code": product_code,
                "plan_code": plan_code,
                "price_lookup_key": price_lookup_key,
            },
        )

    def parse_webhook(self, *, payload: dict) -> AdapterWebhookResult:
        event_id = str(payload.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("event_id 가 필요합니다.")

        normalized_event_type = str(payload.get("event_type") or "").strip().lower()
        event_type = self.WEBHOOK_EVENT_TYPE_MAP.get(normalized_event_type)
        if event_type is None:
            raise ValueError("지원하지 않는 webhook event_type 입니다.")

        event_time = payload.get("event_time") or self._utcnow_naive()
        signed_payload = payload.get("payload") or {}
        signature_header = str(
            signed_payload.get("stripe_signature")
            or payload.get("stripe_signature")
            or signed_payload.get("signature")
            or payload.get("signature")
            or ""
        ).strip()
        secret = str(os.getenv("MARKETPLACE_STRIPE_WEBHOOK_SIGNING_SECRET") or "").strip()

        verification_mode = "simulation"
        verification_simulated = True
        signature_valid = bool(payload.get("signature_valid", True))
        if secret:
            tolerance_raw = str(os.getenv("MARKETPLACE_STRIPE_WEBHOOK_TOLERANCE_SECONDS") or "").strip()
            tolerance_seconds = int(tolerance_raw) if tolerance_raw else None
            timestamp, signatures = self._parse_stripe_signature_header(signature_header)
            raw_body = str(
                signed_payload.get("raw_body")
                or payload.get("raw_body")
                or ""
            )
            if timestamp is not None and signatures and raw_body:
                signed_message = f"{timestamp}.{raw_body}"
                expected = hmac.new(
                    secret.encode("utf-8"),
                    signed_message.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if tolerance_seconds is None:
                    within_tolerance = True
                else:
                    now_epoch = int(time.time())
                    within_tolerance = abs(now_epoch - timestamp) <= tolerance_seconds
                signature_valid = within_tolerance and any(
                    hmac.compare_digest(expected, candidate) for candidate in signatures
                )
            else:
                payload_for_signature = dict(signed_payload)
                payload_for_signature.pop("signature", None)
                payload_for_signature.pop("stripe_signature", None)
                payload_for_signature.pop("raw_body", None)
                message = json.dumps(payload_for_signature, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
                expected = hmac.new(
                    secret.encode("utf-8"),
                    message.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                signature_valid = bool(signature_header) and hmac.compare_digest(expected, signature_header)
            verification_mode = "provider"
            verification_simulated = False
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