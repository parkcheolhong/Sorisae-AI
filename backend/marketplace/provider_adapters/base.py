from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..subscription_state_machine import SubscriptionEventType


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BillingAdapterConfigurationError(RuntimeError):
    pass


@dataclass(slots=True)
class AdapterVerificationResult:
    provider: str
    event_type: SubscriptionEventType
    event_time: datetime
    period_start: datetime | None = None
    period_end: datetime | None = None
    grace_until: datetime | None = None
    cancel_at_period_end: bool = False
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    original_transaction_id: str | None = None
    latest_transaction_id: str | None = None
    purchase_token_hash: str | None = None
    event_id: str | None = None
    reason_code: str | None = None
    verification_mode: str = "simulation"
    verification_simulated: bool = True
    signature_valid: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AdapterCheckoutSession:
    provider: str
    checkout_url: str
    session_id: str
    expires_at: datetime
    verification_mode: str = "simulation"
    verification_simulated: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def expires_in(self) -> int:
        remaining = int((self.expires_at - _utcnow_naive()).total_seconds())
        return max(0, remaining)


@dataclass(slots=True)
class AdapterWebhookResult:
    provider: str
    event_id: str
    event_type: SubscriptionEventType
    event_time: datetime
    user_id: int | None = None
    product_code: str | None = None
    plan_code: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    grace_until: datetime | None = None
    cancel_at_period_end: bool | None = None
    reason_code: str | None = None
    external_customer_id: str | None = None
    external_subscription_id: str | None = None
    original_transaction_id: str | None = None
    latest_transaction_id: str | None = None
    purchase_token_hash: str | None = None
    signature_valid: bool = True
    verification_mode: str = "simulation"
    verification_simulated: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


def default_period_end(now: datetime, *, days: int = 30) -> datetime:
    return now + timedelta(days=days)