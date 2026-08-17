"""Marketplace subscription billing models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from .database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SubscriptionProduct(Base):
    __tablename__ = "subscription_products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    product_family = Column(String(100), nullable=False, default="marketplace")
    billing_type = Column(String(30), nullable=False, default="subscription")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("subscription_products.id"), nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    billing_period = Column(String(20), nullable=False, default="monthly")
    device_limit = Column(Integer, nullable=False, default=2)
    grace_days = Column(Integer, nullable=False, default=3)
    trial_days = Column(Integer, nullable=False, default=0)
    entitlement_version = Column(String(20), nullable=False, default="v1")
    feature_flags_json = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class SubscriptionEntitlement(Base):
    __tablename__ = "subscription_entitlements"
    __table_args__ = (
        UniqueConstraint("plan_id", "entitlement_key", name="uq_subscription_entitlement_plan_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    entitlement_key = Column(String(150), nullable=False, index=True)
    entitlement_value = Column(String(150))
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class SubscriptionPrice(Base):
    __tablename__ = "subscription_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("subscription_products.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    billing_period = Column(String(20), nullable=False, default="monthly")
    channel = Column(String(30), nullable=False, index=True)
    provider = Column(String(30), nullable=False, index=True)
    country_code = Column(String(2), index=True)
    currency = Column(String(10), nullable=False)
    amount_minor = Column(Integer, nullable=False)
    external_price_code = Column(String(150), index=True)
    tax_mode = Column(String(20), nullable=False, default="provider_managed")
    is_active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class ProviderSkuMapping(Base):
    __tablename__ = "provider_sku_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_product_id",
            "external_price_id",
            name="uq_provider_sku_mapping_provider_external_ids",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    price_id = Column(Integer, ForeignKey("subscription_prices.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=False, index=True)
    external_product_id = Column(String(150), nullable=False, index=True)
    external_price_id = Column(String(150), nullable=False, default="")
    external_offer_id = Column(String(150))
    environment = Column(String(20), nullable=False, default="production")
    raw_metadata_json = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class SubscriptionProductProject(Base):
    __tablename__ = "subscription_product_projects"
    __table_args__ = (
        UniqueConstraint(
            "subscription_product_id",
            "project_id",
            name="uq_subscription_product_project_mapping",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    subscription_product_id = Column(
        Integer,
        ForeignKey("subscription_products.id"),
        nullable=False,
        index=True,
    )
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("subscription_products.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    price_id = Column(Integer, ForeignKey("subscription_prices.id"), index=True)
    status = Column(String(30), nullable=False, index=True)
    source = Column(String(30), nullable=False, index=True)
    external_customer_id = Column(String(150), index=True)
    external_subscription_id = Column(String(150), index=True)
    original_transaction_id = Column(String(255), index=True)
    latest_transaction_id = Column(String(255), index=True)
    purchase_token_hash = Column(String(255), index=True)
    period_start = Column(DateTime)
    period_end = Column(DateTime, index=True)
    grace_until = Column(DateTime, index=True)
    trial_until = Column(DateTime, index=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    canceled_at = Column(DateTime)
    refunded_at = Column(DateTime)
    suspended_at = Column(DateTime)
    last_verified_at = Column(DateTime)
    last_event_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_payment_events_provider_event_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(30), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    payload_json = Column(Text, nullable=False)
    signature_valid = Column(Boolean)
    idempotency_key = Column(String(255), index=True)
    event_created_at = Column(DateTime, index=True)
    received_at = Column(DateTime, default=_utcnow_naive, nullable=False)
    processed_at = Column(DateTime)
    processing_status = Column(String(30), nullable=False, default="received", index=True)
    processing_error = Column(Text)


class SubscriptionStateTransition(Base):
    __tablename__ = "subscription_state_transitions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False, index=True)
    from_status = Column(String(30), index=True)
    to_status = Column(String(30), nullable=False, index=True)
    reason_code = Column(String(50), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("payment_events.id"), index=True)
    actor_type = Column(String(30), nullable=False, default="system")
    actor_id = Column(String(100))
    note = Column(Text)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class WebhookDeliveryAttempt(Base):
    __tablename__ = "webhook_delivery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(30), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)
    delivery_key = Column(String(255), index=True)
    http_status = Column(Integer)
    attempt_number = Column(Integer, nullable=False, default=1)
    result = Column(String(30), nullable=False, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)


class DeviceSession(Base):
    __tablename__ = "device_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_device_sessions_user_device"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), index=True)
    device_id = Column(String(255), nullable=False, index=True)
    device_type = Column(String(30), nullable=False, index=True)
    platform = Column(String(30), nullable=False, index=True)
    app_version = Column(String(50))
    os_version = Column(String(50))
    last_ip = Column(String(100))
    last_seen_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)
    revoked_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False)
