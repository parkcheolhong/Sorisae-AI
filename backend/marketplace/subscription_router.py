from typing import Any, Optional

from fastapi import APIRouter, Body, Depends


def build_subscription_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/v1/subscription/catalog", response_model=list[contract.schemas.SubscriptionCatalogItem])
    def get_subscription_catalog(
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        return contract.subscription_service.list_subscription_catalog(
            db,
            user_id=int(current_user.id),
        )

    @router.get("/v1/me/subscription", response_model=contract.schemas.SubscriptionStatusResponse)
    def get_my_subscription_status(
        product_code: Optional[str] = None,
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        return contract.subscription_service.get_user_subscription_status(
            db,
            user_id=int(current_user.id),
            product_code=product_code,
        )

    @router.post("/v1/billing/checkout/sessions", response_model=contract.schemas.CheckoutSessionResponse)
    def create_subscription_checkout_session(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.CheckoutSessionCreateRequest.model_validate(payload)
        return contract.subscription_service.create_checkout_session(
            db,
            user_id=int(current_user.id),
            provider=parsed.provider,
            product_code=parsed.product_code,
            plan_code=parsed.plan_code,
            success_url=parsed.success_url,
            cancel_url=parsed.cancel_url,
        )

    @router.post("/v1/billing/mobile/verify", response_model=contract.schemas.MobileSubscriptionVerifyResponse)
    def verify_mobile_subscription(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.MobileSubscriptionVerifyRequest.model_validate(payload)
        return contract.subscription_service.verify_mobile_subscription(
            db,
            user_id=int(current_user.id),
            platform=parsed.platform,
            product_code=parsed.product_code,
            plan_code=parsed.plan_code,
            purchase_token_or_receipt=parsed.purchase_token_or_receipt,
            transaction_id=parsed.transaction_id,
            external_product_id=parsed.external_product_id,
            external_price_id=parsed.external_price_id,
        )

    @router.post("/v1/mobile/license/check", response_model=contract.schemas.MobileLicenseCheckResponse)
    def check_mobile_license(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.MobileLicenseCheckRequest.model_validate(payload)
        return contract.subscription_service.check_mobile_license(
            db,
            user_id=int(current_user.id),
            product_code=parsed.product_code,
            device_id=parsed.device_id,
        )

    @router.post("/v1/subscription/project-links", response_model=contract.schemas.SubscriptionProjectLinkResponse)
    def upsert_subscription_project_link(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        if not bool(getattr(current_user, "is_admin", False) or getattr(current_user, "is_staff", False)):
            raise contract.HTTPException(status_code=403, detail="권한이 없습니다.")
        parsed = contract.schemas.SubscriptionProjectLinkRequest.model_validate(payload)
        return contract.subscription_service.upsert_project_subscription_link(
            db,
            project_id=parsed.project_id,
            product_code=parsed.product_code,
        )

    @router.post("/v1/me/subscription/cancel", response_model=contract.schemas.SubscriptionActionResponse)
    def cancel_subscription(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.SubscriptionActionRequest.model_validate(payload)
        return contract.subscription_service.cancel_subscription(
            db,
            user_id=int(current_user.id),
            product_code=parsed.product_code,
        )

    @router.post("/v1/me/subscription/resume", response_model=contract.schemas.SubscriptionActionResponse)
    def resume_subscription(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.SubscriptionActionRequest.model_validate(payload)
        return contract.subscription_service.resume_subscription(
            db,
            user_id=int(current_user.id),
            product_code=parsed.product_code,
        )

    @router.post("/v1/me/devices/register", response_model=contract.schemas.DeviceRegisterResponse)
    def register_subscription_device(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.DeviceRegisterRequest.model_validate(payload)
        return contract.subscription_service.register_device(
            db,
            user_id=int(current_user.id),
            product_code=parsed.product_code,
            device_id=parsed.device_id,
            device_type=parsed.device_type,
            platform=parsed.platform,
            app_version=parsed.app_version,
            os_version=parsed.os_version,
            last_ip=parsed.last_ip,
        )

    @router.post("/v1/me/devices/revoke", response_model=contract.schemas.DeviceRevokeResponse)
    def revoke_subscription_device(
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        parsed = contract.schemas.DeviceRevokeRequest.model_validate(payload)
        return contract.subscription_service.revoke_device(
            db,
            user_id=int(current_user.id),
            product_code=parsed.product_code,
            device_id=parsed.device_id,
        )

    @router.post("/v1/billing/webhooks/{provider}", response_model=contract.schemas.SubscriptionWebhookResponse)
    def process_subscription_webhook(
        provider: str,
        payload: dict[str, Any] = Body(...),
        db=Depends(contract.get_db),
    ):
        parsed = contract.schemas.SubscriptionWebhookRequest.model_validate(payload)
        return contract.subscription_service.process_webhook(
            db,
            provider=provider,
            payload=parsed.model_dump(),
        )

    return router
