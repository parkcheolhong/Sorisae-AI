from __future__ import annotations

from .apple_billing import AppleBillingAdapter
from .google_billing import GoogleBillingAdapter
from .stripe_billing import StripeBillingAdapter


class BillingAdapterRegistry:
    def __init__(self) -> None:
        self.apple = AppleBillingAdapter()
        self.google = GoogleBillingAdapter()
        self.stripe = StripeBillingAdapter()

    def mobile_adapter_for_platform(self, platform: str):
        normalized = str(platform or "").strip().lower()
        if normalized == "ios":
            return self.apple
        if normalized == "android":
            return self.google
        raise ValueError("지원하지 않는 모바일 플랫폼입니다.")

    def checkout_adapter_for_provider(self, provider: str):
        normalized = str(provider or "").strip().lower()
        if normalized != "stripe":
            raise ValueError("현재 지원하는 checkout provider 는 stripe 뿐입니다.")
        return self.stripe

    def webhook_adapter_for_provider(self, provider: str):
        normalized = str(provider or "").strip().lower()
        if normalized == "apple":
            return self.apple
        if normalized == "google":
            return self.google
        if normalized == "stripe":
            return self.stripe
        raise ValueError("지원하지 않는 webhook provider 입니다.")


billing_adapter_registry = BillingAdapterRegistry()