"""Marketplace subscription service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import subscription_models
from .provider_adapters import BillingAdapterConfigurationError, billing_adapter_registry
from .subscription_state_machine import (
    NormalizedSubscriptionEvent,
    SubscriptionEventType,
    SubscriptionSnapshot,
    SubscriptionStatus,
    apply_subscription_event,
)


DEFAULT_SUBSCRIPTION_CATALOG = [
    {
        "product_code": "stock-ai-suite",
        "product_name": "Stock AI Suite",
        "product_description": "주식 AI 분석/리포트 기능군 월정액",
        "product_family": "stock-ai",
        "plan_code": "stock-ai-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 39000,
        "external_price_code": "price_stock_ai_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.stock_ai.use"],
    },
    {
        "product_code": "ai-powerpoint-suite",
        "product_name": "AI PowerPoint Suite",
        "product_description": "프레젠테이션 생성/편집 기능군 월정액",
        "product_family": "powerpoint",
        "plan_code": "ai-powerpoint-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 29000,
        "external_price_code": "price_ai_powerpoint_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_powerpoint.use"],
    },
    {
        "product_code": "ai-sheet-suite",
        "product_name": "AI Sheet Suite",
        "product_description": "스프레드시트 자동화 기능군 월정액",
        "product_family": "spreadsheet",
        "plan_code": "ai-sheet-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 24000,
        "external_price_code": "price_ai_sheet_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_sheet.use"],
    },
    {
        "product_code": "ai-image-suite",
        "product_name": "AI Image Suite",
        "product_description": "이미지 생성/보정 기능군 월정액",
        "product_family": "image",
        "plan_code": "ai-image-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 19000,
        "external_price_code": "price_ai_image_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_image.use"],
    },
    {
        "product_code": "ai-video-suite",
        "product_name": "AI Video Suite",
        "product_description": "영상 생성/편집 기능군 월정액",
        "product_family": "video",
        "plan_code": "ai-video-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 49000,
        "external_price_code": "price_ai_video_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_video.use"],
    },
    {
        "product_code": "ai-document-suite",
        "product_name": "AI Document Suite",
        "product_description": "문서 작성/검수 기능군 월정액",
        "product_family": "document",
        "plan_code": "ai-document-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 17000,
        "external_price_code": "price_ai_document_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_document.use"],
    },
    {
        "product_code": "ai-music-suite",
        "product_name": "AI Music Suite",
        "product_description": "음원 생성/편집 기능군 월정액",
        "product_family": "music",
        "plan_code": "ai-music-monthly",
        "plan_name": "Monthly",
        "provider": "stripe",
        "currency": "KRW",
        "amount_minor": 22000,
        "external_price_code": "price_ai_music_monthly",
        "device_limit": 2,
        "entitlements": ["marketplace.app_family.ai_music.use"],
    },
]


class SubscriptionService:
    WEBHOOK_MAX_ATTEMPTS = 3
    WEBHOOK_BACKOFF_SECONDS = [30, 120, 300]

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _resolve_product_and_plan(self, db: Session, product_code: str, plan_code: str):
        product = (
            db.query(subscription_models.SubscriptionProduct)
            .filter(
                subscription_models.SubscriptionProduct.code == product_code,
                subscription_models.SubscriptionProduct.is_active.is_(True),
            )
            .first()
        )
        if not product:
            raise HTTPException(status_code=404, detail="구독 상품을 찾을 수 없습니다.")

        plan = (
            db.query(subscription_models.SubscriptionPlan)
            .filter(
                subscription_models.SubscriptionPlan.product_id == product.id,
                subscription_models.SubscriptionPlan.code == plan_code,
                subscription_models.SubscriptionPlan.is_active.is_(True),
            )
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="구독 플랜을 찾을 수 없습니다.")
        return product, plan

    def _ensure_default_subscription_catalog(self, db: Session) -> None:
        for item in DEFAULT_SUBSCRIPTION_CATALOG:
            product_code = str(item["product_code"])
            plan_code = str(item["plan_code"])
            provider = str(item["provider"])

            product = (
                db.query(subscription_models.SubscriptionProduct)
                .filter(subscription_models.SubscriptionProduct.code == product_code)
                .first()
            )
            if product is None:
                product = subscription_models.SubscriptionProduct(
                    code=product_code,
                    name=str(item["product_name"]),
                    description=str(item.get("product_description") or ""),
                    product_family=str(item.get("product_family") or "general"),
                    is_active=True,
                )
                db.add(product)
                db.flush()
            else:
                product.name = str(item["product_name"])
                product.description = str(item.get("product_description") or product.description or "")
                product.product_family = str(item.get("product_family") or product.product_family or "general")
                product.is_active = True

            plan = (
                db.query(subscription_models.SubscriptionPlan)
                .filter(subscription_models.SubscriptionPlan.code == plan_code)
                .first()
            )
            if plan is None:
                plan = subscription_models.SubscriptionPlan(
                    product_id=int(product.id),
                    code=plan_code,
                    name=str(item["plan_name"]),
                    billing_period="monthly",
                    device_limit=int(item.get("device_limit") or 1),
                    is_active=True,
                )
                db.add(plan)
                db.flush()
            else:
                plan.product_id = int(product.id)
                plan.name = str(item["plan_name"])
                plan.billing_period = "monthly"
                plan.device_limit = int(item.get("device_limit") or plan.device_limit or 1)
                plan.is_active = True

            existing_keys = {
                str(row.entitlement_key): row
                for row in db.query(subscription_models.SubscriptionEntitlement)
                .filter(subscription_models.SubscriptionEntitlement.plan_id == int(plan.id))
                .all()
            }
            for entitlement_key in [str(key) for key in item.get("entitlements") or []]:
                if entitlement_key in existing_keys:
                    continue
                db.add(
                    subscription_models.SubscriptionEntitlement(
                        plan_id=int(plan.id),
                        entitlement_key=entitlement_key,
                        entitlement_value="true",
                    )
                )

            price = (
                db.query(subscription_models.SubscriptionPrice)
                .filter(
                    subscription_models.SubscriptionPrice.product_id == int(product.id),
                    subscription_models.SubscriptionPrice.plan_id == int(plan.id),
                    subscription_models.SubscriptionPrice.provider == provider,
                    subscription_models.SubscriptionPrice.channel == "web",
                    subscription_models.SubscriptionPrice.billing_period == "monthly",
                )
                .order_by(subscription_models.SubscriptionPrice.id.desc())
                .first()
            )
            if price is None:
                db.add(
                    subscription_models.SubscriptionPrice(
                        product_id=int(product.id),
                        plan_id=int(plan.id),
                        channel="web",
                        provider=provider,
                        currency=str(item["currency"]),
                        amount_minor=int(item["amount_minor"]),
                        billing_period="monthly",
                        external_price_code=str(item.get("external_price_code") or ""),
                        is_active=True,
                    )
                )
            else:
                price.currency = str(item["currency"])
                price.amount_minor = int(item["amount_minor"])
                price.external_price_code = str(item.get("external_price_code") or price.external_price_code or "")
                price.is_active = True

    @staticmethod
    def _guess_default_product_code_for_project(*, title: str, description: str, category_name: str) -> str | None:
        bag = " ".join([title, description, category_name]).lower()
        rules: list[tuple[str, tuple[str, ...]]] = [
            ("stock-ai-suite", ("stock", "주식", "trading", "invest")),
            ("ai-powerpoint-suite", ("powerpoint", "ppt", "presentation", "프레젠테이션")),
            ("ai-sheet-suite", ("sheet", "excel", "spreadsheet", "스프레드시트")),
            ("ai-image-suite", ("image", "photo", "사진", "이미지", "design")),
            ("ai-video-suite", ("video", "movie", "ad", "영상", "동영상", "광고")),
            ("ai-document-suite", ("document", "docs", "pdf", "문서", "report")),
            ("ai-music-suite", ("music", "song", "audio", "음악", "음원")),
        ]
        for product_code, keywords in rules:
            if any(keyword in bag for keyword in keywords):
                return product_code
        return None

    def _ensure_default_project_subscription_links(self, db: Session) -> None:
        from . import models

        products = db.query(subscription_models.SubscriptionProduct).all()
        if not products:
            return
        product_by_code = {str(product.code): product for product in products}

        existing_project_ids = {
            int(row.project_id)
            for row in db.query(subscription_models.SubscriptionProductProject).all()
        }

        projects = (
            db.query(models.Project)
            .filter(models.Project.is_active.is_(True))
            .all()
        )
        for project in projects:
            if int(project.id) in existing_project_ids:
                continue
            category_name = str(getattr(getattr(project, "category", None), "name", "") or "")
            guessed_code = self._guess_default_product_code_for_project(
                title=str(getattr(project, "title", "") or ""),
                description=str(getattr(project, "description", "") or ""),
                category_name=category_name,
            )
            if not guessed_code:
                continue
            target_product = product_by_code.get(guessed_code)
            if target_product is None:
                continue
            db.add(
                subscription_models.SubscriptionProductProject(
                    subscription_product_id=int(target_product.id),
                    project_id=int(project.id),
                )
            )

    def ensure_runtime_bootstrap(self, db: Session) -> None:
        self._ensure_default_subscription_catalog(db)
        self._ensure_default_project_subscription_links(db)
        db.commit()

    def list_subscription_catalog(self, db: Session, user_id: int) -> list[dict[str, Any]]:
        self._ensure_default_subscription_catalog(db)
        db.commit()

        products = (
            db.query(subscription_models.SubscriptionProduct)
            .filter(subscription_models.SubscriptionProduct.is_active.is_(True))
            .order_by(subscription_models.SubscriptionProduct.id.asc())
            .all()
        )
        catalog: list[dict[str, Any]] = []
        for product in products:
            subscription = (
                db.query(subscription_models.UserSubscription)
                .filter(
                    subscription_models.UserSubscription.user_id == user_id,
                    subscription_models.UserSubscription.product_id == product.id,
                )
                .order_by(subscription_models.UserSubscription.updated_at.desc(), subscription_models.UserSubscription.id.desc())
                .first()
            )
            active_plan = None
            entitlement_set: list[str] = []
            if subscription is not None:
                entitlement_set = self._load_entitlements(db, int(subscription.plan_id))

            plan = (
                db.query(subscription_models.SubscriptionPlan)
                .filter(
                    subscription_models.SubscriptionPlan.product_id == product.id,
                    subscription_models.SubscriptionPlan.is_active.is_(True),
                    subscription_models.SubscriptionPlan.billing_period == "monthly",
                )
                .order_by(subscription_models.SubscriptionPlan.id.asc())
                .first()
            )
            if plan is not None:
                price = (
                    db.query(subscription_models.SubscriptionPrice)
                    .filter(
                        subscription_models.SubscriptionPrice.product_id == product.id,
                        subscription_models.SubscriptionPrice.plan_id == plan.id,
                        subscription_models.SubscriptionPrice.channel == "web",
                        subscription_models.SubscriptionPrice.provider == "stripe",
                        subscription_models.SubscriptionPrice.is_active.is_(True),
                    )
                    .order_by(subscription_models.SubscriptionPrice.id.desc())
                    .first()
                )
                if price is not None:
                    active_plan = {
                        "plan_code": str(plan.code),
                        "plan_name": str(plan.name),
                        "billing_period": str(plan.billing_period),
                        "provider": str(price.provider),
                        "currency": str(price.currency),
                        "amount_minor": int(price.amount_minor),
                    }

            catalog.append(
                {
                    "product_code": str(product.code),
                    "product_name": str(product.name),
                    "product_description": product.description,
                    "product_family": str(product.product_family or "general"),
                    "subscription_status": str(getattr(subscription, "status", SubscriptionStatus.NONE.value)),
                    "cancel_at_period_end": bool(getattr(subscription, "cancel_at_period_end", False)),
                    "period_end": getattr(subscription, "period_end", None),
                    "active_plan": active_plan,
                    "entitlement_set": entitlement_set,
                }
            )

        return catalog

    def list_project_subscription_links(
        self,
        db: Session,
        project_ids: list[int] | None = None,
    ) -> dict[int, dict[str, Any]]:
        query = db.query(subscription_models.SubscriptionProductProject)
        if project_ids:
            query = query.filter(subscription_models.SubscriptionProductProject.project_id.in_(project_ids))
        mappings = query.all()
        if not mappings:
            return {}

        product_ids = [int(mapping.subscription_product_id) for mapping in mappings]
        products = (
            db.query(subscription_models.SubscriptionProduct)
            .filter(subscription_models.SubscriptionProduct.id.in_(product_ids))
            .all()
        )
        product_by_id = {int(product.id): product for product in products}

        product_payload_by_id: dict[int, dict[str, Any]] = {}
        for product_id in product_ids:
            if product_id in product_payload_by_id:
                continue
            product = product_by_id.get(product_id)
            if product is None:
                continue

            plan = (
                db.query(subscription_models.SubscriptionPlan)
                .filter(
                    subscription_models.SubscriptionPlan.product_id == product_id,
                    subscription_models.SubscriptionPlan.is_active.is_(True),
                    subscription_models.SubscriptionPlan.billing_period == "monthly",
                )
                .order_by(subscription_models.SubscriptionPlan.id.asc())
                .first()
            )
            price = None
            if plan is not None:
                price = (
                    db.query(subscription_models.SubscriptionPrice)
                    .filter(
                        subscription_models.SubscriptionPrice.product_id == product_id,
                        subscription_models.SubscriptionPrice.plan_id == int(plan.id),
                        subscription_models.SubscriptionPrice.channel == "web",
                        subscription_models.SubscriptionPrice.is_active.is_(True),
                    )
                    .order_by(subscription_models.SubscriptionPrice.id.desc())
                    .first()
                )

            product_payload_by_id[product_id] = {
                "product_code": str(product.code),
                "product_name": str(product.name),
                "product_description": product.description,
                "plan_code": str(getattr(plan, "code", "") or "") or None,
                "plan_name": str(getattr(plan, "name", "") or "") or None,
                "currency": str(getattr(price, "currency", "") or "") or None,
                "amount_minor": int(getattr(price, "amount_minor", 0) or 0) if price is not None else None,
                "provider": str(getattr(price, "provider", "") or "") or None,
            }

        linked: dict[int, dict[str, Any]] = {}
        for mapping in mappings:
            payload = product_payload_by_id.get(int(mapping.subscription_product_id))
            if payload is None:
                continue
            linked[int(mapping.project_id)] = payload
        return linked

    def upsert_project_subscription_link(
        self,
        db: Session,
        *,
        project_id: int,
        product_code: str,
    ) -> dict[str, Any]:
        from . import models

        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project is None:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

        product = (
            db.query(subscription_models.SubscriptionProduct)
            .filter(subscription_models.SubscriptionProduct.code == product_code)
            .first()
        )
        if product is None:
            raise HTTPException(status_code=404, detail="구독 상품을 찾을 수 없습니다.")

        link = (
            db.query(subscription_models.SubscriptionProductProject)
            .filter(subscription_models.SubscriptionProductProject.project_id == project_id)
            .first()
        )
        if link is None:
            link = subscription_models.SubscriptionProductProject(
                project_id=project_id,
                subscription_product_id=int(product.id),
            )
            db.add(link)
        else:
            link.subscription_product_id = int(product.id)
        db.commit()

        return {
            "project_id": project_id,
            "product_code": str(product.code),
            "linked": True,
        }

    def _load_entitlements(self, db: Session, plan_id: int) -> list[str]:
        rows = (
            db.query(subscription_models.SubscriptionEntitlement)
            .filter(subscription_models.SubscriptionEntitlement.plan_id == plan_id)
            .order_by(subscription_models.SubscriptionEntitlement.entitlement_key.asc())
            .all()
        )
        return [str(row.entitlement_key) for row in rows]

    def _active_device_count(self, db: Session, user_id: int, subscription_id: int | None) -> int:
        query = db.query(subscription_models.DeviceSession).filter(
            subscription_models.DeviceSession.user_id == user_id,
            subscription_models.DeviceSession.revoked_at.is_(None),
        )
        if subscription_id is not None:
            query = query.filter(subscription_models.DeviceSession.subscription_id == subscription_id)
        return int(query.count())

    def _resolve_price(
        self,
        db: Session,
        *,
        product_id: int,
        plan_id: int,
        provider: str,
        external_product_id: str | None = None,
        external_price_id: str | None = None,
    ):
        price = (
            db.query(subscription_models.SubscriptionPrice)
            .filter(
                subscription_models.SubscriptionPrice.product_id == product_id,
                subscription_models.SubscriptionPrice.plan_id == plan_id,
                subscription_models.SubscriptionPrice.provider == provider,
                subscription_models.SubscriptionPrice.is_active.is_(True),
            )
            .order_by(subscription_models.SubscriptionPrice.id.desc())
            .first()
        )

        if external_product_id:
            mapping_query = db.query(subscription_models.ProviderSkuMapping).filter(
                subscription_models.ProviderSkuMapping.provider == provider,
                subscription_models.ProviderSkuMapping.external_product_id == external_product_id,
            )
            if external_price_id is not None:
                mapping_query = mapping_query.filter(
                    subscription_models.ProviderSkuMapping.external_price_id == external_price_id
                )
            mapping = mapping_query.first()
            if mapping is None:
                raise HTTPException(status_code=404, detail="provider SKU 매핑을 찾을 수 없습니다.")
            if price is None or int(mapping.price_id) != int(price.id):
                price = (
                    db.query(subscription_models.SubscriptionPrice)
                    .filter(subscription_models.SubscriptionPrice.id == mapping.price_id)
                    .first()
                )

        if price is None:
            raise HTTPException(status_code=404, detail="활성 구독 가격을 찾을 수 없습니다.")
        return price

    def _get_or_create_subscription(
        self,
        db: Session,
        *,
        user_id: int,
        product_id: int,
        plan_id: int,
        price_id: int,
        provider: str,
    ):
        subscription = (
            db.query(subscription_models.UserSubscription)
            .filter(
                subscription_models.UserSubscription.user_id == user_id,
                subscription_models.UserSubscription.product_id == product_id,
            )
            .order_by(subscription_models.UserSubscription.updated_at.desc())
            .first()
        )
        if subscription is None:
            subscription = subscription_models.UserSubscription(
                user_id=user_id,
                product_id=product_id,
                plan_id=plan_id,
                price_id=price_id,
                status=SubscriptionStatus.NONE.value,
                source=provider,
            )
            db.add(subscription)
            db.flush()
        return subscription

    def _serialize_subscription(self, db: Session, user_id: int, subscription: subscription_models.UserSubscription | None) -> dict[str, Any]:
        if subscription is None:
            return {
                "user_id": user_id,
                "subscription_status": SubscriptionStatus.NONE.value,
                "product_code": None,
                "plan_code": None,
                "entitlement_set": [],
                "period_end": None,
                "cancel_at_period_end": False,
                "device_limit": 0,
                "active_device_count": 0,
                "source": None,
            }

        product = db.query(subscription_models.SubscriptionProduct).filter(subscription_models.SubscriptionProduct.id == subscription.product_id).first()
        plan = db.query(subscription_models.SubscriptionPlan).filter(subscription_models.SubscriptionPlan.id == subscription.plan_id).first()
        entitlement_set = self._load_entitlements(db, subscription.plan_id)
        return {
            "user_id": user_id,
            "subscription_status": str(subscription.status),
            "product_code": getattr(product, "code", None),
            "plan_code": getattr(plan, "code", None),
            "entitlement_set": entitlement_set,
            "period_end": subscription.period_end,
            "cancel_at_period_end": bool(subscription.cancel_at_period_end),
            "device_limit": int(getattr(plan, "device_limit", 0) or 0),
            "active_device_count": self._active_device_count(db, user_id, subscription.id),
            "source": subscription.source,
        }

    def _find_user_subscription(
        self,
        db: Session,
        *,
        user_id: int,
        product_code: str | None = None,
    ):
        query = db.query(subscription_models.UserSubscription).filter(
            subscription_models.UserSubscription.user_id == user_id,
        )
        if product_code:
            product = (
                db.query(subscription_models.SubscriptionProduct)
                .filter(subscription_models.SubscriptionProduct.code == product_code)
                .first()
            )
            if product is None:
                raise HTTPException(status_code=404, detail="구독 상품을 찾을 수 없습니다.")
            query = query.filter(subscription_models.UserSubscription.product_id == product.id)

        subscription = (
            query.order_by(
                subscription_models.UserSubscription.updated_at.desc(),
                subscription_models.UserSubscription.id.desc(),
            )
            .first()
        )
        if subscription is None:
            raise HTTPException(status_code=404, detail="활성 구독을 찾을 수 없습니다.")
        return subscription

    def _build_snapshot(self, subscription: subscription_models.UserSubscription) -> SubscriptionSnapshot:
        return SubscriptionSnapshot(
            status=SubscriptionStatus(str(subscription.status)),
            cancel_at_period_end=bool(subscription.cancel_at_period_end),
            last_event_at=subscription.last_event_at,
            period_start=subscription.period_start,
            period_end=subscription.period_end,
            grace_until=subscription.grace_until,
            trial_until=subscription.trial_until,
            canceled_at=subscription.canceled_at,
            refunded_at=subscription.refunded_at,
            suspended_at=subscription.suspended_at,
        )

    def _apply_transition_to_subscription(
        self,
        db: Session,
        *,
        subscription: subscription_models.UserSubscription,
        user_id: int,
        provider: str,
        event_id: str,
        event: NormalizedSubscriptionEvent,
        actor_type: str,
        actor_id: str,
        payload_json: str,
        signature_valid: bool | None = None,
        external_customer_id: str | None = None,
        external_subscription_id: str | None = None,
        original_transaction_id: str | None = None,
        latest_transaction_id: str | None = None,
        purchase_token_hash: str | None = None,
    ):
        duplicate = (
            db.query(subscription_models.PaymentEvent)
            .filter(
                subscription_models.PaymentEvent.provider == provider,
                subscription_models.PaymentEvent.event_id == event_id,
            )
            .first()
        )
        if duplicate:
            return {
                "transition": None,
                "payment_event": duplicate,
                "duplicate": True,
                "ignored": True,
                "reason_code": "duplicate_event",
            }

        snapshot = self._build_snapshot(subscription)
        transition = apply_subscription_event(snapshot, event)
        if not transition.applied and not transition.ignored:
            raise HTTPException(status_code=409, detail="구독 상태 전이에 실패했습니다.")

        subscription.status = transition.to_status.value
        subscription.source = provider
        subscription.external_customer_id = external_customer_id or subscription.external_customer_id
        subscription.external_subscription_id = external_subscription_id or subscription.external_subscription_id
        subscription.original_transaction_id = original_transaction_id or subscription.original_transaction_id
        subscription.latest_transaction_id = latest_transaction_id or subscription.latest_transaction_id
        subscription.purchase_token_hash = purchase_token_hash or subscription.purchase_token_hash
        for field_name, field_value in transition.updated_fields.items():
            setattr(subscription, field_name, field_value)

        payment_event = subscription_models.PaymentEvent(
            provider=provider,
            event_id=event_id,
            event_type=event.event_type.value,
            subscription_id=subscription.id,
            user_id=user_id,
            payload_json=payload_json,
            signature_valid=signature_valid,
            idempotency_key=event_id,
            event_created_at=event.event_time,
            processed_at=self._utcnow_naive(),
            processing_status="applied" if transition.applied else "ignored",
        )
        db.add(payment_event)
        db.flush()

        if transition.applied:
            db.add(
                subscription_models.SubscriptionStateTransition(
                    subscription_id=subscription.id,
                    from_status=transition.from_status.value,
                    to_status=transition.to_status.value,
                    reason_code=transition.reason_code,
                    event_id=payment_event.id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                )
            )

        return {
            "transition": transition,
            "payment_event": payment_event,
            "duplicate": False,
            "ignored": transition.ignored,
            "reason_code": transition.reason_code,
        }

    def _resolve_webhook_subscription(
        self,
        db: Session,
        *,
        provider: str,
        user_id: int | None,
        product_code: str | None,
        plan_code: str | None,
        external_subscription_id: str | None,
        original_transaction_id: str | None,
    ):
        subscription = None
        if external_subscription_id:
            subscription = (
                db.query(subscription_models.UserSubscription)
                .filter(
                    subscription_models.UserSubscription.source == provider,
                    subscription_models.UserSubscription.external_subscription_id == external_subscription_id,
                )
                .order_by(subscription_models.UserSubscription.updated_at.desc())
                .first()
            )
        if subscription is None and original_transaction_id:
            subscription = (
                db.query(subscription_models.UserSubscription)
                .filter(
                    subscription_models.UserSubscription.source == provider,
                    subscription_models.UserSubscription.original_transaction_id == original_transaction_id,
                )
                .order_by(subscription_models.UserSubscription.updated_at.desc())
                .first()
            )
        if subscription is None and user_id is not None:
            query = db.query(subscription_models.UserSubscription).filter(
                subscription_models.UserSubscription.user_id == user_id,
            )
            if product_code:
                product = (
                    db.query(subscription_models.SubscriptionProduct)
                    .filter(subscription_models.SubscriptionProduct.code == product_code)
                    .first()
                )
                if product is not None:
                    query = query.filter(subscription_models.UserSubscription.product_id == product.id)
            subscription = query.order_by(subscription_models.UserSubscription.updated_at.desc()).first()

        if subscription is None and user_id is not None and product_code and plan_code:
            product, plan = self._resolve_product_and_plan(db, product_code, plan_code)
            price = self._resolve_price(
                db,
                product_id=int(product.id),
                plan_id=int(plan.id),
                provider=provider,
            )
            subscription = self._get_or_create_subscription(
                db,
                user_id=user_id,
                product_id=int(product.id),
                plan_id=int(plan.id),
                price_id=int(price.id),
                provider=provider,
            )

        if subscription is None:
            raise HTTPException(status_code=404, detail="webhook 대상 구독을 찾을 수 없습니다.")
        return subscription

    def _create_webhook_delivery_attempt(self, db: Session, *, provider: str, event_id: str):
        latest = (
            db.query(subscription_models.WebhookDeliveryAttempt)
            .filter(
                subscription_models.WebhookDeliveryAttempt.provider == provider,
                subscription_models.WebhookDeliveryAttempt.event_id == event_id,
            )
            .order_by(subscription_models.WebhookDeliveryAttempt.attempt_number.desc())
            .first()
        )
        attempt_number = int(getattr(latest, "attempt_number", 0) or 0) + 1
        delivery_attempt = subscription_models.WebhookDeliveryAttempt(
            provider=provider,
            event_id=event_id,
            delivery_key=event_id,
            attempt_number=attempt_number,
            result="received",
        )
        db.add(delivery_attempt)
        db.flush()
        return delivery_attempt

    def _mark_webhook_failure(
        self,
        *,
        delivery_attempt,
        status_code: int,
        error_message: str,
    ) -> None:
        attempt_number = int(getattr(delivery_attempt, "attempt_number", 1) or 1)
        if attempt_number >= self.WEBHOOK_MAX_ATTEMPTS:
            delivery_attempt.result = "dead_letter"
            delivery_attempt.error_message = f"{error_message} | dead_letter=true"
        else:
            backoff_seconds = self.WEBHOOK_BACKOFF_SECONDS[min(attempt_number - 1, len(self.WEBHOOK_BACKOFF_SECONDS) - 1)]
            delivery_attempt.result = "retry_scheduled"
            delivery_attempt.error_message = f"{error_message} | retry_in_seconds={backoff_seconds}"
        delivery_attempt.http_status = status_code

    def get_user_subscription_status(self, db: Session, user_id: int, product_code: str | None = None) -> dict[str, Any]:
        self._ensure_default_subscription_catalog(db)
        db.commit()
        query = db.query(subscription_models.UserSubscription).filter(
            subscription_models.UserSubscription.user_id == user_id,
        )
        if product_code:
            product = (
                db.query(subscription_models.SubscriptionProduct)
                .filter(subscription_models.SubscriptionProduct.code == product_code)
                .first()
            )
            if not product:
                return self._serialize_subscription(db, user_id, None)
            query = query.filter(subscription_models.UserSubscription.product_id == product.id)

        subscription = (
            query.order_by(
                subscription_models.UserSubscription.updated_at.desc(),
                subscription_models.UserSubscription.id.desc(),
            )
            .first()
        )
        return self._serialize_subscription(db, user_id, subscription)

    def create_checkout_session(
        self,
        db: Session,
        *,
        user_id: int,
        provider: str,
        product_code: str,
        plan_code: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        self._ensure_default_subscription_catalog(db)
        db.commit()
        product, plan = self._resolve_product_and_plan(db, product_code, plan_code)
        price = self._resolve_price(
            db,
            product_id=int(product.id),
            plan_id=int(plan.id),
            provider=provider,
        )
        try:
            session = billing_adapter_registry.checkout_adapter_for_provider(provider).create_checkout_session(
                user_id=user_id,
                product_code=product_code,
                plan_code=plan_code,
                price_lookup_key=str(getattr(price, "external_price_code", None) or getattr(price, "id")),
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except BillingAdapterConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "provider": session.provider,
            "checkout_url": session.checkout_url,
            "session_id": session.session_id,
            "expires_in": session.expires_in,
            "verification_mode": session.verification_mode,
            "verification_simulated": session.verification_simulated,
        }

    def verify_mobile_subscription(
        self,
        db: Session,
        *,
        user_id: int,
        platform: str,
        product_code: str,
        plan_code: str,
        purchase_token_or_receipt: str,
        transaction_id: str | None,
        external_product_id: str | None,
        external_price_id: str | None,
    ) -> dict[str, Any]:
        try:
            adapter = billing_adapter_registry.mobile_adapter_for_platform(platform)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        provider = adapter.provider
        product, plan = self._resolve_product_and_plan(db, product_code, plan_code)
        price = self._resolve_price(
            db,
            product_id=int(product.id),
            plan_id=int(plan.id),
            provider=provider,
            external_product_id=external_product_id,
            external_price_id=external_price_id,
        )
        subscription = self._get_or_create_subscription(
            db,
            user_id=user_id,
            product_id=int(product.id),
            plan_id=int(plan.id),
            price_id=int(price.id),
            provider=provider,
        )

        try:
            verification = adapter.verify_purchase(
                purchase_token_or_receipt=purchase_token_or_receipt,
                transaction_id=transaction_id,
                external_product_id=external_product_id,
                external_price_id=external_price_id,
            )
        except BillingAdapterConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        event_id = verification.event_id or transaction_id or f"{provider}-event-{user_id}-{price.id}"
        duplicate = (
            db.query(subscription_models.PaymentEvent)
            .filter(
                subscription_models.PaymentEvent.provider == provider,
                subscription_models.PaymentEvent.event_id == event_id,
            )
            .first()
        )
        if duplicate:
            payload = self._serialize_subscription(db, user_id, subscription)
            payload.update(
                {
                    "verified": True,
                    "source_original_id": subscription.original_transaction_id,
                    "verification_mode": verification.verification_mode,
                    "verification_simulated": verification.verification_simulated,
                }
            )
            return payload

        now = self._utcnow_naive()
        event = NormalizedSubscriptionEvent(
            event_type=verification.event_type,
            event_time=verification.event_time,
            period_start=verification.period_start,
            period_end=verification.period_end,
            grace_until=verification.grace_until,
            cancel_at_period_end=verification.cancel_at_period_end,
            reason_code=verification.reason_code,
            raw={
                "platform": platform,
                **verification.raw,
            },
        )
        snapshot = SubscriptionSnapshot(
            status=SubscriptionStatus(str(subscription.status)),
            cancel_at_period_end=bool(subscription.cancel_at_period_end),
            last_event_at=subscription.last_event_at,
            period_start=subscription.period_start,
            period_end=subscription.period_end,
            grace_until=subscription.grace_until,
            trial_until=subscription.trial_until,
            canceled_at=subscription.canceled_at,
            refunded_at=subscription.refunded_at,
            suspended_at=subscription.suspended_at,
        )
        transition = apply_subscription_event(snapshot, event)
        if not transition.applied and not transition.ignored:
            raise HTTPException(status_code=409, detail="구독 상태 전이에 실패했습니다.")

        subscription.status = transition.to_status.value
        subscription.plan_id = plan.id
        subscription.price_id = price.id
        subscription.source = provider
        subscription.external_customer_id = verification.external_customer_id or subscription.external_customer_id
        subscription.external_subscription_id = verification.external_subscription_id or subscription.external_subscription_id
        subscription.latest_transaction_id = verification.latest_transaction_id or transaction_id or event_id
        subscription.original_transaction_id = (
            subscription.original_transaction_id
            or verification.original_transaction_id
            or transaction_id
            or event_id
        )
        subscription.purchase_token_hash = verification.purchase_token_hash or subscription.purchase_token_hash
        subscription.last_verified_at = now
        for field_name, field_value in transition.updated_fields.items():
            setattr(subscription, field_name, field_value)

        payment_event = subscription_models.PaymentEvent(
            provider=provider,
            event_id=event_id,
            event_type=event.event_type.value,
            subscription_id=subscription.id,
            user_id=user_id,
            payload_json=json.dumps(event.raw, ensure_ascii=True, default=str),
            signature_valid=verification.signature_valid,
            idempotency_key=event_id,
            event_created_at=event.event_time,
            processed_at=now,
            processing_status="applied",
        )
        db.add(payment_event)
        db.flush()

        transition_row = subscription_models.SubscriptionStateTransition(
            subscription_id=subscription.id,
            from_status=transition.from_status.value,
            to_status=transition.to_status.value,
            reason_code=transition.reason_code,
            event_id=payment_event.id,
            actor_type="system",
            actor_id=f"mobile-verify:{provider}",
        )
        db.add(transition_row)
        db.commit()
        db.refresh(subscription)

        payload = self._serialize_subscription(db, user_id, subscription)
        payload.update(
            {
                "verified": True,
                "source_original_id": subscription.original_transaction_id,
                "verification_mode": verification.verification_mode,
                "verification_simulated": verification.verification_simulated,
            }
        )
        return payload

    def cancel_subscription(self, db: Session, *, user_id: int, product_code: str | None = None) -> dict[str, Any]:
        subscription = self._find_user_subscription(db, user_id=user_id, product_code=product_code)
        now = self._utcnow_naive()
        event = NormalizedSubscriptionEvent(
            event_type=SubscriptionEventType.CANCEL_SCHEDULED,
            event_time=now,
            cancel_at_period_end=True,
            reason_code="user_cancel_requested",
            raw={"product_code": product_code, "action": "cancel"},
        )
        result = self._apply_transition_to_subscription(
            db,
            subscription=subscription,
            user_id=user_id,
            provider=str(subscription.source),
            event_id=f"manual-cancel:{subscription.id}:{int(now.timestamp())}",
            event=event,
            actor_type="user",
            actor_id=str(user_id),
            payload_json=json.dumps(event.raw, ensure_ascii=True, default=str),
        )
        db.commit()
        db.refresh(subscription)
        payload = self._serialize_subscription(db, user_id, subscription)
        payload.update(
            {
                "applied": not result["duplicate"],
                "ignored": bool(result["ignored"]),
                "reason_code": str(result["reason_code"]),
            }
        )
        return payload

    def resume_subscription(self, db: Session, *, user_id: int, product_code: str | None = None) -> dict[str, Any]:
        subscription = self._find_user_subscription(db, user_id=user_id, product_code=product_code)
        now = self._utcnow_naive()
        event = NormalizedSubscriptionEvent(
            event_type=SubscriptionEventType.CANCEL_REVOKED,
            event_time=now,
            cancel_at_period_end=False,
            reason_code="user_resume_requested",
            raw={"product_code": product_code, "action": "resume"},
        )
        result = self._apply_transition_to_subscription(
            db,
            subscription=subscription,
            user_id=user_id,
            provider=str(subscription.source),
            event_id=f"manual-resume:{subscription.id}:{int(now.timestamp())}",
            event=event,
            actor_type="user",
            actor_id=str(user_id),
            payload_json=json.dumps(event.raw, ensure_ascii=True, default=str),
        )
        db.commit()
        db.refresh(subscription)
        payload = self._serialize_subscription(db, user_id, subscription)
        payload.update(
            {
                "applied": not result["duplicate"],
                "ignored": bool(result["ignored"]),
                "reason_code": str(result["reason_code"]),
            }
        )
        return payload

    def register_device(
        self,
        db: Session,
        *,
        user_id: int,
        product_code: str | None,
        device_id: str,
        device_type: str,
        platform: str,
        app_version: str | None,
        os_version: str | None,
        last_ip: str | None,
    ) -> dict[str, Any]:
        subscription = self._find_user_subscription(db, user_id=user_id, product_code=product_code)
        if str(subscription.status) not in {
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
            SubscriptionStatus.GRACE_PERIOD.value,
        }:
            raise HTTPException(status_code=409, detail="현재 상태에서는 기기 등록이 불가능합니다.")

        plan = (
            db.query(subscription_models.SubscriptionPlan)
            .filter(subscription_models.SubscriptionPlan.id == subscription.plan_id)
            .first()
        )
        device_limit = int(getattr(plan, "device_limit", 0) or 0)
        existing = (
            db.query(subscription_models.DeviceSession)
            .filter(
                subscription_models.DeviceSession.user_id == user_id,
                subscription_models.DeviceSession.device_id == device_id,
            )
            .first()
        )

        active_count = self._active_device_count(db, user_id, subscription.id)
        if existing is None and device_limit > 0 and active_count >= device_limit:
            raise HTTPException(status_code=409, detail="기기 제한을 초과했습니다.")

        now = self._utcnow_naive()
        if existing is None:
            existing = subscription_models.DeviceSession(
                user_id=user_id,
                subscription_id=subscription.id,
                device_id=device_id,
                device_type=device_type,
                platform=platform,
                app_version=app_version,
                os_version=os_version,
                last_ip=last_ip,
                last_seen_at=now,
            )
            db.add(existing)
        else:
            existing.subscription_id = subscription.id
            existing.device_type = device_type
            existing.platform = platform
            existing.app_version = app_version
            existing.os_version = os_version
            existing.last_ip = last_ip
            existing.last_seen_at = now
            existing.revoked_at = None

        db.commit()
        db.refresh(subscription)
        payload = self._serialize_subscription(db, user_id, subscription)
        payload.update(
            {
                "registered": True,
                "device_id": device_id,
                "device_revoked": False,
            }
        )
        return payload

    def check_mobile_license(
        self,
        db: Session,
        *,
        user_id: int,
        product_code: str,
        device_id: str,
    ) -> dict[str, Any]:
        status_payload = self.get_user_subscription_status(db, user_id=user_id, product_code=product_code)
        status = str(status_payload.get("subscription_status") or SubscriptionStatus.NONE.value)
        allowed_statuses = {
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
            SubscriptionStatus.GRACE_PERIOD.value,
        }
        if status not in allowed_statuses:
            status_payload.update(
                {
                    "allowed": False,
                    "reason_code": "inactive_subscription",
                    "device_registered": False,
                }
            )
            return status_payload

        subscription = self._find_user_subscription(db, user_id=user_id, product_code=product_code)
        device = (
            db.query(subscription_models.DeviceSession)
            .filter(
                subscription_models.DeviceSession.user_id == user_id,
                subscription_models.DeviceSession.subscription_id == int(subscription.id),
                subscription_models.DeviceSession.device_id == device_id,
                subscription_models.DeviceSession.revoked_at.is_(None),
            )
            .first()
        )
        if device is not None:
            device.last_seen_at = self._utcnow_naive()
            db.commit()
            status_payload.update(
                {
                    "allowed": True,
                    "reason_code": "ok",
                    "device_registered": True,
                }
            )
            return status_payload

        active_count = int(status_payload.get("active_device_count") or 0)
        device_limit = int(status_payload.get("device_limit") or 0)
        if device_limit > 0 and active_count >= device_limit:
            status_payload.update(
                {
                    "allowed": False,
                    "reason_code": "device_limit_exceeded",
                    "device_registered": False,
                }
            )
            return status_payload

        status_payload.update(
            {
                "allowed": True,
                "reason_code": "device_registration_required",
                "device_registered": False,
            }
        )
        return status_payload

    def revoke_device(self, db: Session, *, user_id: int, product_code: str | None, device_id: str) -> dict[str, Any]:
        subscription = self._find_user_subscription(db, user_id=user_id, product_code=product_code)
        device = (
            db.query(subscription_models.DeviceSession)
            .filter(
                subscription_models.DeviceSession.user_id == user_id,
                subscription_models.DeviceSession.device_id == device_id,
            )
            .first()
        )
        if device is None:
            raise HTTPException(status_code=404, detail="기기 세션을 찾을 수 없습니다.")

        device.revoked_at = self._utcnow_naive()
        db.commit()
        db.refresh(subscription)
        payload = self._serialize_subscription(db, user_id, subscription)
        payload.update(
            {
                "revoked": True,
                "device_id": device_id,
            }
        )
        return payload

    def process_webhook(
        self,
        db: Session,
        *,
        provider: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_provider = str(provider or "").strip().lower()
        raw_event_id = str(payload.get("event_id") or "").strip() or "unknown"
        delivery_attempt = self._create_webhook_delivery_attempt(
            db,
            provider=normalized_provider,
            event_id=raw_event_id,
        )

        try:
            adapter = billing_adapter_registry.webhook_adapter_for_provider(normalized_provider)
            normalized_webhook = adapter.parse_webhook(payload=payload)
        except ValueError as exc:
            status_code = 401 if "signature" in str(exc).lower() else 400
            self._mark_webhook_failure(
                delivery_attempt=delivery_attempt,
                status_code=status_code,
                error_message=str(exc),
            )
            db.commit()
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except BillingAdapterConfigurationError as exc:
            self._mark_webhook_failure(
                delivery_attempt=delivery_attempt,
                status_code=503,
                error_message=str(exc),
            )
            db.commit()
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        event_id = normalized_webhook.event_id
        delivery_attempt.event_id = event_id
        delivery_attempt.delivery_key = event_id

        duplicate = (
            db.query(subscription_models.PaymentEvent)
            .filter(
                subscription_models.PaymentEvent.provider == normalized_provider,
                subscription_models.PaymentEvent.event_id == event_id,
            )
            .first()
        )
        if duplicate:
            delivery_attempt.http_status = 200
            delivery_attempt.result = "duplicate"
            db.commit()
            return {
                "provider": normalized_provider,
                "event_id": event_id,
                "processed": False,
                "ignored": True,
                "reason_code": "duplicate_event",
                "subscription_status": None,
                "delivery_attempt_id": int(delivery_attempt.id),
            }

        subscription = self._resolve_webhook_subscription(
            db,
            provider=normalized_provider,
            user_id=normalized_webhook.user_id,
            product_code=normalized_webhook.product_code,
            plan_code=normalized_webhook.plan_code,
            external_subscription_id=normalized_webhook.external_subscription_id,
            original_transaction_id=normalized_webhook.original_transaction_id,
        )
        event = NormalizedSubscriptionEvent(
            event_type=normalized_webhook.event_type,
            event_time=normalized_webhook.event_time,
            period_start=normalized_webhook.period_start,
            period_end=normalized_webhook.period_end,
            grace_until=normalized_webhook.grace_until,
            cancel_at_period_end=normalized_webhook.cancel_at_period_end,
            reason_code=normalized_webhook.reason_code,
            raw=normalized_webhook.raw,
        )
        result = self._apply_transition_to_subscription(
            db,
            subscription=subscription,
            user_id=int(subscription.user_id),
            provider=normalized_provider,
            event_id=event_id,
            event=event,
            actor_type="system",
            actor_id=f"webhook:{normalized_provider}",
            payload_json=json.dumps(normalized_webhook.raw, ensure_ascii=True, default=str),
            signature_valid=normalized_webhook.signature_valid,
            external_customer_id=normalized_webhook.external_customer_id,
            external_subscription_id=normalized_webhook.external_subscription_id,
            original_transaction_id=normalized_webhook.original_transaction_id,
            latest_transaction_id=normalized_webhook.latest_transaction_id,
            purchase_token_hash=normalized_webhook.purchase_token_hash,
        )
        delivery_attempt.http_status = 200
        delivery_attempt.result = "applied" if not result["ignored"] else "ignored"
        db.commit()
        db.refresh(subscription)
        return {
            "provider": normalized_provider,
            "event_id": event_id,
            "processed": not result["ignored"],
            "ignored": bool(result["ignored"]),
            "reason_code": str(result["reason_code"]),
            "subscription_status": str(subscription.status),
            "delivery_attempt_id": int(delivery_attempt.id),
        }


subscription_service = SubscriptionService()