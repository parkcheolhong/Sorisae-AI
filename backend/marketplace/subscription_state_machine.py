"""Pure subscription state transition rules for marketplace billing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SubscriptionStatus(StrEnum):
    NONE = "none"
    TRIALING = "trialing"
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    SUSPENDED = "suspended"


class SubscriptionEventType(StrEnum):
    PURCHASE_VERIFIED = "purchase_verified"
    RENEWAL_SUCCEEDED = "renewal_succeeded"
    RENEWAL_FAILED = "renewal_failed"
    GRACE_EXPIRED = "grace_expired"
    CANCEL_SCHEDULED = "cancel_scheduled"
    CANCEL_REVOKED = "cancel_revoked"
    PERIOD_ENDED = "period_ended"
    REFUND_APPLIED = "refund_applied"
    SUBSCRIPTION_SUSPENDED = "subscription_suspended"
    SUBSCRIPTION_RESTORED = "subscription_restored"
    TRIAL_STARTED = "trial_started"


@dataclass(slots=True)
class SubscriptionSnapshot:
    status: SubscriptionStatus = SubscriptionStatus.NONE
    cancel_at_period_end: bool = False
    last_event_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    grace_until: datetime | None = None
    trial_until: datetime | None = None
    canceled_at: datetime | None = None
    refunded_at: datetime | None = None
    suspended_at: datetime | None = None


@dataclass(slots=True)
class NormalizedSubscriptionEvent:
    event_type: SubscriptionEventType
    event_time: datetime
    period_start: datetime | None = None
    period_end: datetime | None = None
    grace_until: datetime | None = None
    trial_until: datetime | None = None
    cancel_at_period_end: bool | None = None
    reason_code: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TransitionResult:
    from_status: SubscriptionStatus
    to_status: SubscriptionStatus
    applied: bool
    ignored: bool = False
    reason_code: str = ""
    updated_fields: dict[str, Any] = field(default_factory=dict)


TERMINAL_STATUSES = {
    SubscriptionStatus.REFUNDED,
    SubscriptionStatus.SUSPENDED,
}


def should_ignore_event(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> bool:
    if snapshot.last_event_at is None:
        return False
    return event.event_time < snapshot.last_event_at


def apply_subscription_event(
    snapshot: SubscriptionSnapshot,
    event: NormalizedSubscriptionEvent,
) -> TransitionResult:
    from_status = snapshot.status
    if should_ignore_event(snapshot, event):
        return TransitionResult(
            from_status=from_status,
            to_status=from_status,
            applied=False,
            ignored=True,
            reason_code="ignored_out_of_order",
        )

    if from_status in TERMINAL_STATUSES and event.event_type not in {
        SubscriptionEventType.SUBSCRIPTION_RESTORED,
    }:
        return TransitionResult(
            from_status=from_status,
            to_status=from_status,
            applied=False,
            ignored=True,
            reason_code="ignored_terminal_state",
        )

    handler = EVENT_HANDLERS.get(event.event_type)
    if handler is None:
        return TransitionResult(
            from_status=from_status,
            to_status=from_status,
            applied=False,
            ignored=True,
            reason_code="ignored_unknown_event",
        )

    result = handler(snapshot, event)
    if result.applied:
        result.updated_fields.setdefault("last_event_at", event.event_time)
    return result


def _activate(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent, reason_code: str) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.ACTIVE,
        applied=True,
        reason_code=reason_code,
        updated_fields={
            "period_start": event.period_start,
            "period_end": event.period_end,
            "grace_until": None,
            "trial_until": None,
            "cancel_at_period_end": bool(event.cancel_at_period_end) if event.cancel_at_period_end is not None else False,
            "canceled_at": None,
        },
    )


def _handle_trial_started(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.TRIALING,
        applied=True,
        reason_code=event.reason_code or "trial_started",
        updated_fields={
            "trial_until": event.trial_until,
            "period_start": event.period_start,
            "period_end": event.period_end,
            "cancel_at_period_end": False,
        },
    )


def _handle_purchase_verified(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return _activate(snapshot, event, event.reason_code or "purchase_verified")


def _handle_renewal_succeeded(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return _activate(snapshot, event, event.reason_code or "renewal_succeeded")


def _handle_renewal_failed(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.GRACE_PERIOD,
        applied=True,
        reason_code=event.reason_code or "renewal_failed",
        updated_fields={
            "grace_until": event.grace_until,
        },
    )


def _handle_grace_expired(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.PAST_DUE,
        applied=True,
        reason_code=event.reason_code or "grace_expired",
        updated_fields={
            "grace_until": None,
        },
    )


def _handle_cancel_scheduled(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=snapshot.status,
        applied=True,
        reason_code=event.reason_code or "cancel_scheduled",
        updated_fields={
            "cancel_at_period_end": True,
            "canceled_at": event.event_time,
        },
    )


def _handle_cancel_revoked(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    target_status = snapshot.status
    if snapshot.status == SubscriptionStatus.CANCELED and snapshot.period_end and snapshot.period_end >= event.event_time:
        target_status = SubscriptionStatus.ACTIVE
    return TransitionResult(
        from_status=snapshot.status,
        to_status=target_status,
        applied=True,
        reason_code=event.reason_code or "cancel_revoked",
        updated_fields={
            "cancel_at_period_end": False,
            "canceled_at": None,
        },
    )


def _handle_period_ended(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    if snapshot.cancel_at_period_end or snapshot.status in {SubscriptionStatus.PAST_DUE, SubscriptionStatus.TRIALING}:
        return TransitionResult(
            from_status=snapshot.status,
            to_status=SubscriptionStatus.CANCELED,
            applied=True,
            reason_code=event.reason_code or "period_ended",
            updated_fields={
                "period_end": event.period_end or snapshot.period_end,
                "cancel_at_period_end": False,
            },
        )
    return TransitionResult(
        from_status=snapshot.status,
        to_status=snapshot.status,
        applied=False,
        ignored=True,
        reason_code="ignored_period_end_without_cancel",
    )


def _handle_refund_applied(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.REFUNDED,
        applied=True,
        reason_code=event.reason_code or "refund_applied",
        updated_fields={
            "refunded_at": event.event_time,
            "grace_until": None,
            "cancel_at_period_end": False,
        },
    )


def _handle_subscription_suspended(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.SUSPENDED,
        applied=True,
        reason_code=event.reason_code or "subscription_suspended",
        updated_fields={
            "suspended_at": event.event_time,
        },
    )


def _handle_subscription_restored(snapshot: SubscriptionSnapshot, event: NormalizedSubscriptionEvent) -> TransitionResult:
    return TransitionResult(
        from_status=snapshot.status,
        to_status=SubscriptionStatus.ACTIVE,
        applied=True,
        reason_code=event.reason_code or "subscription_restored",
        updated_fields={
            "suspended_at": None,
            "refunded_at": None,
            "period_start": event.period_start or snapshot.period_start,
            "period_end": event.period_end or snapshot.period_end,
        },
    )


EVENT_HANDLERS = {
    SubscriptionEventType.TRIAL_STARTED: _handle_trial_started,
    SubscriptionEventType.PURCHASE_VERIFIED: _handle_purchase_verified,
    SubscriptionEventType.RENEWAL_SUCCEEDED: _handle_renewal_succeeded,
    SubscriptionEventType.RENEWAL_FAILED: _handle_renewal_failed,
    SubscriptionEventType.GRACE_EXPIRED: _handle_grace_expired,
    SubscriptionEventType.CANCEL_SCHEDULED: _handle_cancel_scheduled,
    SubscriptionEventType.CANCEL_REVOKED: _handle_cancel_revoked,
    SubscriptionEventType.PERIOD_ENDED: _handle_period_ended,
    SubscriptionEventType.REFUND_APPLIED: _handle_refund_applied,
    SubscriptionEventType.SUBSCRIPTION_SUSPENDED: _handle_subscription_suspended,
    SubscriptionEventType.SUBSCRIPTION_RESTORED: _handle_subscription_restored,
}
