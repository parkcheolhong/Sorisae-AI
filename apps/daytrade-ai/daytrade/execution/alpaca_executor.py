"""Alpaca 주문 어댑터(설계서 §6 — IBKR Paper/Alpaca). **계정·네트워크 필요(서버)**.

Alpaca Trading API v2(REST)로 주문을 전송한다. 메시지(payload) 구성·응답 파싱은 의존성 없이
테스트 가능하며, 실제 전송은 `requests`(guarded import)로 수행한다. 기본 엔드포인트는 **paper**
(모의계좌, 실자본 없음). 실계좌(live)는 `is_live_account=True` + 라이브 base_url 로 명시 전환.

IBKR 연동은 FIX 경로(`FixExecutor` + `config/fix.cfg`)를 사용한다(IBKR 은 FIX/네이티브 API 제공).
"""
from __future__ import annotations

from ..types import Fill, MarketTick, Order, OrderSide, OrderType
from .base import OrderExecutor

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"

_TIF = {OrderType.MARKET: "day", OrderType.LIMIT: "day", OrderType.IOC: "ioc"}
_TYPE = {OrderType.MARKET: "market", OrderType.LIMIT: "limit", OrderType.IOC: "market"}


def build_alpaca_order(order: Order) -> dict:
    """`Order` → Alpaca POST /v2/orders JSON payload(테스트 가능, 네트워크 불요)."""
    payload = {
        "symbol": order.symbol,
        "qty": _num(order.qty),
        "side": "buy" if order.side == OrderSide.BUY else "sell",
        "type": _TYPE[order.order_type],
        "time_in_force": _TIF[order.order_type],
    }
    if order.client_order_id:
        payload["client_order_id"] = order.client_order_id
    if order.order_type == OrderType.LIMIT and order.limit_price is not None:
        payload["limit_price"] = _num(order.limit_price)
    return payload


def parse_alpaca_fill(resp: dict, order: Order, *, ts_ns: int) -> Fill:
    """Alpaca 주문/체결 응답(JSON) → `Fill`."""
    status_map = {"filled": "filled", "partially_filled": "partial",
                  "rejected": "rejected", "canceled": "rejected", "expired": "rejected"}
    status = status_map.get(str(resp.get("status", "")), "rejected")
    filled_qty = float(resp.get("filled_qty") or 0.0)
    avg_price = float(resp.get("filled_avg_price") or 0.0)
    if status == "rejected" or filled_qty <= 0:
        return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=ts_ns, status="rejected")
    return Fill(order=order, filled_qty=filled_qty, avg_price=round(avg_price, 6),
                ts_ns=ts_ns, status=status)


class AlpacaExecutor(OrderExecutor):
    """Alpaca REST 주문 실행기. paper 기본. 실전송에는 `requests` 필요."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        base_url: str = PAPER_BASE_URL,
        is_live_account: bool = False,
        timeout: float = 5.0,
        session=None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self._is_live = bool(is_live_account)
        self.timeout = timeout
        self._session = session  # 테스트 시 가짜 세션 주입 가능

    @property
    def is_live(self) -> bool:
        return self._is_live

    def _client(self):
        if self._session is not None:
            return self._session
        try:
            import requests  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as exc:  # pragma: no cover - 서버 의존
            raise ModuleNotFoundError(
                "Alpaca 전송에는 'requests' 가 필요합니다: pip install requests (서버/계정 환경)."
            ) from exc
        self._session = requests.Session()
        return self._session

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        payload = build_alpaca_order(order)
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }
        resp = self._client().post(
            f"{self.base_url}/v2/orders", json=payload, headers=headers, timeout=self.timeout
        )
        data = resp.json()
        return parse_alpaca_fill(data, order, ts_ns=tick.ts_ns)


def _num(x: float) -> str:
    f = float(x)
    return str(int(f)) if f == int(f) else repr(round(f, 8))
