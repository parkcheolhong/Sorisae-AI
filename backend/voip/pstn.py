"""P3-B: PSTN(전화망) 다이얼아웃 공급자 어댑터.

통신사 연동/미디어 브리지는 외부 서비스에 의존하므로 공급자(provider) 어댑터로 추상화한다.
환경변수 `VOIP_PSTN_PROVIDER` 로 선택:
  - dialer_fallback (기본): 앱 다이얼러로 폴백(현행 P1 동작).
  - simulated: 통신사 없이 발신 흐름 시뮬레이션(테스트/스테이징).
  - twilio: Twilio Programmable Voice REST로 발신(자격 필요, 미구성 시 폴백). 미디어 브리지/통역
    삽입은 별도(P3-B 후속) — 본 어댑터는 발신 생성까지 담당.

반환 dict 키: call_route, phone_dialer_required, fallback_dial_url, status, resolved_mode,
provider_call_id?, user_message?, error_code?
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _dialer_fallback(callee_phone: str, reason: str = "") -> Dict[str, Any]:
    return {
        "call_route": "pstn_fallback",
        "phone_dialer_required": True,
        "fallback_dial_url": f"tel:{callee_phone}",
        "status": "dialer_required",
        "resolved_mode": "pstn_fallback",
        "user_message": "앱 통화 대상이 아니어서 전화 다이얼러로 연결합니다." + (f" ({reason})" if reason else ""),
    }


class DialerFallbackProvider:
    name = "dialer_fallback"

    async def dial(self, *, callee_phone: str, call_id: str = "", caller_label: str = "") -> Dict[str, Any]:
        return _dialer_fallback(callee_phone)


class SimulatedPstnProvider:
    name = "simulated"

    async def dial(self, *, callee_phone: str, call_id: str = "", caller_label: str = "") -> Dict[str, Any]:
        return {
            "call_route": "pstn",
            "phone_dialer_required": False,
            "status": "dialing",
            "resolved_mode": "pstn",
            "provider_call_id": "sim_" + uuid.uuid4().hex[:12],
            "user_message": "전화망으로 발신을 시작합니다(시뮬레이션).",
        }


class TwilioPstnProvider:
    name = "twilio"

    def _configured(self) -> bool:
        return all((
            (os.getenv("TWILIO_ACCOUNT_SID", "") or "").strip(),
            (os.getenv("TWILIO_AUTH_TOKEN", "") or "").strip(),
            (os.getenv("TWILIO_FROM_NUMBER", "") or "").strip(),
            (os.getenv("VOIP_PSTN_TWIML_URL", "") or "").strip(),
        ))

    async def dial(self, *, callee_phone: str, call_id: str = "", caller_label: str = "") -> Dict[str, Any]:
        if not self._configured():
            return _dialer_fallback(callee_phone, reason="twilio_not_configured")
        try:
            import asyncio

            from twilio.rest import Client  # 선택 의존성

            def _create() -> str:
                client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
                call = client.calls.create(
                    to=callee_phone,
                    from_=os.environ["TWILIO_FROM_NUMBER"],
                    url=os.environ["VOIP_PSTN_TWIML_URL"],
                )
                return call.sid

            sid = await asyncio.to_thread(_create)
            return {
                "call_route": "pstn",
                "phone_dialer_required": False,
                "status": "dialing",
                "resolved_mode": "pstn",
                "provider_call_id": sid,
                "user_message": "전화망으로 발신을 시작합니다.",
            }
        except Exception as exc:  # noqa: BLE001 — 발신 실패 시 다이얼러 폴백.
            logger.warning("[VoIP] Twilio PSTN dial 실패(폴백): %s", exc)
            return _dialer_fallback(callee_phone, reason="twilio_error")


_PROVIDERS = {
    "dialer_fallback": DialerFallbackProvider,
    "simulated": SimulatedPstnProvider,
    "twilio": TwilioPstnProvider,
}


def get_pstn_provider():
    name = (os.getenv("VOIP_PSTN_PROVIDER", "dialer_fallback") or "dialer_fallback").strip().lower()
    return _PROVIDERS.get(name, DialerFallbackProvider)()
