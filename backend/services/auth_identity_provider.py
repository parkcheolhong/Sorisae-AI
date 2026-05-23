from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Any, Dict, Mapping
from urllib.parse import urlencode
import os

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    _HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)

from backend.secret_store import read_secret_env


@dataclass
class IdentityVerificationStartResult:
    session_token: str
    provider: str
    redirect_url: str
    expires_at: datetime
    verification_code: str
    request_payload: Dict[str, Any]
    callback_url: str


@dataclass
class IdentityVerificationCompleteResult:
    verified: bool
    provider: str
    ci: str
    di: str
    phone: str
    name: str
    birth: str
    provider_result_payload: Dict[str, Any]


@dataclass
class IdentityCompletePayloadContract:
    provider: str
    required_fields: list[str]
    optional_fields: list[str]
    callback_fields: list[str]


class IdentityProviderConfigurationError(RuntimeError):
    pass


class CarrierIdentityProviderBase:
    provider_name = "mock-carrier"
    provider_endpoint_env = ""
    client_id_env = ""
    client_secret_env = ""
    callback_env = "IDENTITY_PROVIDER_CALLBACK_URL"
    complete_required_fields = ["provider", "verified", "ci", "di", "phone", "name", "birth"]
    complete_optional_fields = ["carrier", "gender", "nationality", "result_code", "result_message"]
    complete_callback_fields = ["provider", "verified", "ci", "di", "phone", "name", "birth"]
    _placeholder_tokens = ("example", "dummy", "changeme", "replace", "sample", "placeholder", "test-secret")

    def _resolve_env_value(self, key: str) -> str:
        return str(read_secret_env(key, "") or "").strip()

    def _resolve_callback_url(self) -> str:
        configured = self._resolve_env_value(self.callback_env)
        if configured:
            return configured
        return f"https://metanova1004.com/api/auth/identity/providers/{self.provider_name}/callback"

    def _resolve_provider_endpoint(self) -> str:
        configured = self._resolve_env_value(self.provider_endpoint_env)
        if configured:
            return configured
        return f"https://{self.provider_name}.example.com/identity/start"

    def _resolve_client_id(self) -> str:
        return self._resolve_env_value(self.client_id_env) or f"{self.provider_name}-client-id"

    def _resolve_client_secret(self) -> str:
        return self._resolve_env_value(self.client_secret_env) or f"{self.provider_name}-client-secret"

    def _is_placeholder_value(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        if not normalized:
            return False
        return any(token in normalized for token in self._placeholder_tokens)

    def _resolve_live_configuration(self) -> Dict[str, str]:
        return {
            "endpoint": self._resolve_env_value(self.provider_endpoint_env) if self.provider_endpoint_env else "",
            "client_id": self._resolve_env_value(self.client_id_env) if self.client_id_env else "",
            "client_secret": self._resolve_env_value(self.client_secret_env) if self.client_secret_env else "",
            "callback_url": self._resolve_env_value(self.callback_env) if self.callback_env else "",
        }

    def _configuration_error_message(self) -> str:
        provider_label = self.provider_name.upper()
        return (
            f"{provider_label} 실서비스 설정이 placeholder/example 값입니다. "
            f"운영 endpoint/client id/client secret을 실제 계약 값으로 교체한 뒤 다시 시도하세요."
        )

    def _validate_live_configuration(self) -> None:
        values = self._resolve_live_configuration()
        required = [values.get("endpoint", ""), values.get("client_id", ""), values.get("client_secret", "")]
        if not all(required):
            return
        if any(self._is_placeholder_value(value) for value in required):
            raise IdentityProviderConfigurationError(self._configuration_error_message())

    def build_mapping_status(self, configured_values: Dict[str, str] | None = None) -> Dict[str, Any]:
        configured_values = configured_values or {}
        def configured(key: str) -> str:
            value = str(configured_values.get(key) or "").strip()
            return value or self._resolve_env_value(key)

        endpoint = configured(self.provider_endpoint_env) if self.provider_endpoint_env else self._resolve_provider_endpoint()
        client_id = configured(self.client_id_env) if self.client_id_env else self._resolve_client_id()
        client_secret = configured(self.client_secret_env) if self.client_secret_env else self._resolve_client_secret()
        callback_url = configured(self.callback_env) or self._resolve_callback_url()
        endpoint_configured = bool(endpoint) and not self._is_placeholder_value(endpoint) if self.provider_endpoint_env else False
        client_id_configured = bool(client_id) and not self._is_placeholder_value(client_id) if self.client_id_env else False
        client_secret_configured = bool(client_secret) and not self._is_placeholder_value(client_secret) if self.client_secret_env else False
        callback_configured = bool(callback_url)
        return {
            "provider": self.provider_name,
            "endpoint": endpoint,
            "callback_url": callback_url,
            "endpoint_configured": endpoint_configured,
            "client_id_configured": client_id_configured,
            "client_secret_configured": client_secret_configured,
            "callback_configured": callback_configured,
            "request_mapping_ready": endpoint_configured and client_id_configured and client_secret_configured,
            "complete_mapping_ready": callback_configured,
            "placeholder_detected": any(self._is_placeholder_value(value) for value in [endpoint, client_id, client_secret] if value),
            "complete_payload_fields": ["ci", "di", "phone", "name", "birth"],
            "request_payload_fields": ["client_id", "client_secret", "callback_url", "session_token", "scope", "purpose", "user_hint"],
        }

    def build_complete_payload_contract(self) -> IdentityCompletePayloadContract:
        return IdentityCompletePayloadContract(
            provider=self.provider_name,
            required_fields=list(self.complete_required_fields),
            optional_fields=list(self.complete_optional_fields),
            callback_fields=list(self.complete_callback_fields),
        )

    def _build_request_payload(self, scope: str, purpose: str, user_hint: str, session_token: str) -> Dict[str, Any]:
        return {
            "client_id": self._resolve_client_id(),
            "client_secret": self._resolve_client_secret(),
            "callback_url": self._resolve_callback_url(),
            "session_token": session_token,
            "scope": scope,
            "purpose": purpose,
            "user_hint": user_hint,
        }

    def _build_redirect_url(self, payload: Mapping[str, Any]) -> str:
        return f"{self._resolve_provider_endpoint()}?{urlencode({k: v for k, v in payload.items() if v is not None})}"

    def _is_live_configured(self) -> bool:
        """실서비스 API 키가 모두 설정되어 있는지 확인"""
        if not self.provider_endpoint_env or not self.client_id_env or not self.client_secret_env:
            return False
        try:
            self._validate_live_configuration()
        except IdentityProviderConfigurationError:
            return False
        return bool(
            self._resolve_env_value(self.provider_endpoint_env)
            and self._resolve_env_value(self.client_id_env)
            and self._resolve_env_value(self.client_secret_env)
        )

    def _call_provider_api(self, url: str, payload: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
        """통신사 API HTTP 호출 (httpx 사용)"""
        if not _HTTPX_AVAILABLE or httpx is None:
            raise RuntimeError("httpx 미설치 — pip install httpx")
        with httpx.Client(timeout=timeout, verify=True) as client:
            response = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()

    def start_verification(self, scope: str, purpose: str, user_hint: str) -> IdentityVerificationStartResult:
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        session_token = f"identity_{token_urlsafe(24)}"
        request_payload = self._build_request_payload(scope, purpose, user_hint, session_token)
        redirect_url = self._build_redirect_url(request_payload)

        configured_live_values = self._resolve_live_configuration()
        if any(configured_live_values.get(key) for key in ("endpoint", "client_id", "client_secret")):
            self._validate_live_configuration()

        # 실서비스 모드: 통신사 API 호출
        if self._is_live_configured():
            try:
                api_result = self._call_provider_api(
                    self._resolve_provider_endpoint(), request_payload,
                )
                verification_code = str(api_result.get("verification_code") or api_result.get("tx_id") or token_urlsafe(6))
                redirect_url = str(api_result.get("redirect_url") or redirect_url)
                request_payload["tx_id"] = api_result.get("tx_id")
                logger.info("[%s] 실서비스 본인인증 시작 — session=%s", self.provider_name, session_token)
            except Exception as exc:
                logger.error("[%s] 통신사 API 호출 실패: %s — Mock 폴백", self.provider_name, exc)
                verification_code = "000000"
        else:
            # Mock 모드
            verification_code = "000000"

        return IdentityVerificationStartResult(
            session_token=session_token,
            provider=self.provider_name,
            redirect_url=redirect_url,
            expires_at=expires_at,
            verification_code=verification_code,
            request_payload=request_payload,
            callback_url=self._resolve_callback_url(),
        )

    def complete_verification(self, payload: Dict[str, Any]) -> IdentityVerificationCompleteResult:
        configured_live_values = self._resolve_live_configuration()
        if any(configured_live_values.get(key) for key in ("endpoint", "client_id", "client_secret")):
            self._validate_live_configuration()

        # 실서비스 모드: 통신사 콜백 검증
        if self._is_live_configured():
            try:
                verify_url = self._resolve_provider_endpoint().rstrip("/").rsplit("/", 1)[0] + "/complete"
                api_result = self._call_provider_api(verify_url, {
                    "client_id": self._resolve_client_id(),
                    "client_secret": self._resolve_client_secret(),
                    "session_token": payload.get("session_token"),
                    "verification_code": payload.get("verification_code"),
                })
                verified = bool(api_result.get("verified", False))
                logger.info("[%s] 실서비스 본인인증 완료 — verified=%s", self.provider_name, verified)
                return IdentityVerificationCompleteResult(
                    verified=verified,
                    provider=self.provider_name,
                    ci=str(api_result.get("ci") or ""),
                    di=str(api_result.get("di") or ""),
                    phone=str(api_result.get("phone") or ""),
                    name=str(api_result.get("name") or ""),
                    birth=str(api_result.get("birth") or ""),
                    provider_result_payload=api_result,
                )
            except Exception as exc:
                logger.error("[%s] 통신사 검증 API 실패: %s", self.provider_name, exc)
                raise RuntimeError(f"본인인증 검증 실패: {exc}") from exc

        # Mock 모드 폴백
        phone = str(payload.get("phone") or "01000000000")
        name = str(payload.get("name") or "관리자")
        birth = str(payload.get("birth") or "19900101")
        ci = str(payload.get("ci") or f"{self.provider_name}-ci-{token_urlsafe(8)}")
        di = str(payload.get("di") or f"{self.provider_name}-di-{token_urlsafe(8)}")
        return IdentityVerificationCompleteResult(
            verified=True,
            provider=self.provider_name,
            ci=ci, di=di, phone=phone, name=name, birth=birth,
            provider_result_payload={"provider": self.provider_name, "verified": True, "mode": "mock"},
        )


class MockCarrierIdentityProvider(CarrierIdentityProviderBase):
    provider_name = "mock-carrier"

    def _resolve_provider_endpoint(self) -> str:
        return "https://mock-carrier.local/identity/start"


class PassIdentityProvider(CarrierIdentityProviderBase):
    provider_name = "pass"
    provider_endpoint_env = "PASS_IDENTITY_ENDPOINT"
    client_id_env = "PASS_CLIENT_ID"
    client_secret_env = "PASS_CLIENT_SECRET"
    callback_env = "PASS_CALLBACK_URL"
    complete_optional_fields = ["carrier", "gender", "nationality", "tx_id", "result_code", "result_message"]


class KmcIdentityProvider(CarrierIdentityProviderBase):
    provider_name = "kmc"
    provider_endpoint_env = "KMC_IDENTITY_ENDPOINT"
    client_id_env = "KMC_CLIENT_ID"
    client_secret_env = "KMC_CLIENT_SECRET"
    callback_env = "KMC_CALLBACK_URL"
    complete_optional_fields = ["carrier", "gender", "nationality", "transaction_id", "result_code", "result_message"]


class KcbIdentityProvider(CarrierIdentityProviderBase):
    provider_name = "kcb"
    provider_endpoint_env = "KCB_IDENTITY_ENDPOINT"
    client_id_env = "KCB_CLIENT_ID"
    client_secret_env = "KCB_CLIENT_SECRET"
    callback_env = "KCB_CALLBACK_URL"
    complete_optional_fields = ["carrier", "gender", "nationality", "cert_no", "result_code", "result_message"]


def resolve_identity_provider(provider_name: str | None = None) -> CarrierIdentityProviderBase:
    configured_provider = provider_name if provider_name is not None else read_secret_env("IDENTITY_PROVIDER", "mock-carrier")
    normalized = str(configured_provider or "").strip().lower()
    if normalized == "pass":
        return PassIdentityProvider()
    if normalized == "kmc":
        return KmcIdentityProvider()
    if normalized == "kcb":
        return KcbIdentityProvider()
    return MockCarrierIdentityProvider()
