"""Alpaca 실시간 피드(M1) — 미국주식 IEX(무료) 호가/체결 → MarketTick.

무료 IEX 피드는 **L1(top-of-book) 호가**만 제공하므로 depth=1 틱을 만든다(OBI 의미 제한적).
실시간 사용에는 API 키/시크릿과 인증 핸드셰이크가 필요하다(라이브 경로). 정규화는 순수 함수로 테스트.

메시지(배열의 각 원소) 종류는 "T" 필드로 구분: "q"(quote), "t"(trade), 그 외 제어 메시지.
"""
from __future__ import annotations

import os
from typing import Iterable, Iterator

from ..types import MarketTick, OrderBookLevel, now_ns


def alpaca_msg_kind(data: dict) -> str:
    t = data.get("T", "")
    if t == "q":
        return "quote"
    if t == "t":
        return "trade"
    return "unknown"


def normalize_alpaca_quote(
    data: dict,
    last_price: float,
    last_qty: float,
    ts_ns: int | None = None,
) -> MarketTick:
    symbol = data.get("S", "UNKNOWN")
    try:
        bid_px = float(data.get("bp", 0.0))
        bid_sz = float(data.get("bs", 0.0))
        ask_px = float(data.get("ap", 0.0))
        ask_sz = float(data.get("as", 0.0))
    except (TypeError, ValueError):
        bid_px = bid_sz = ask_px = ask_sz = 0.0

    bids = (OrderBookLevel(bid_px, bid_sz),) if bid_px > 0 else ()
    asks = (OrderBookLevel(ask_px, ask_sz),) if ask_px > 0 else ()

    price = last_price
    if price <= 0:
        price = (bid_px + ask_px) / 2.0 if bid_px > 0 and ask_px > 0 else (bid_px or ask_px)

    return MarketTick(
        ts_ns=ts_ns if ts_ns is not None else now_ns(),
        symbol=symbol,
        bids=bids,
        asks=asks,
        last_price=price,
        last_qty=last_qty,
    )


def parse_alpaca_trade(data: dict) -> tuple[float, float]:
    try:
        return float(data.get("p", 0.0)), float(data.get("s", 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0


class AlpacaFeed:
    """Alpaca IEX L1 피드. 라이브는 API 키 필요(env ALPACA_API_KEY/ALPACA_SECRET_KEY).

    Args:
        symbol: 종목(예: "AAPL").
        message_source: 원시 메시지(각 원소가 dict) 이터러블. None 이면 라이브 WS.
        api_key/secret_key: 라이브 인증(없으면 env 사용).
    """

    BASE_URL = "wss://stream.data.alpaca.markets/v2/iex"

    def __init__(
        self,
        symbol: str = "AAPL",
        message_source: Iterable[dict] | None = None,
        api_key: str | None = None,
        secret_key: str | None = None,
        max_ticks: int | None = None,
    ) -> None:
        self.symbol = symbol
        self.message_source = message_source
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")
        self.max_ticks = max_ticks
        self._last_price = 0.0
        self._last_qty = 0.0

    def _normalize(self, data: dict) -> MarketTick | None:
        kind = alpaca_msg_kind(data)
        if kind == "trade":
            price, qty = parse_alpaca_trade(data)
            if price > 0:
                self._last_price = price
                self._last_qty = qty
            return None
        if kind == "quote":
            return normalize_alpaca_quote(data, self._last_price, self._last_qty)
        return None

    def ticks(self) -> Iterator[MarketTick]:
        source = self.message_source if self.message_source is not None else self._live_messages()
        count = 0
        for data in source:
            tick = self._normalize(data)
            if tick is None:
                continue
            yield tick
            count += 1
            if self.max_ticks is not None and count >= self.max_ticks:
                break

    def _live_messages(self) -> Iterator[dict]:  # NOSONAR
        if not self.api_key or not self.secret_key:
            raise RuntimeError(
                "Alpaca 라이브 피드에는 ALPACA_API_KEY/ALPACA_SECRET_KEY 가 필요합니다."
            )
        import asyncio
        import json
        import queue
        import threading

        q: "queue.Queue[dict | None]" = queue.Queue(maxsize=10_000)

        async def _consume() -> None:
            import websockets

            async with websockets.connect(self.BASE_URL, ping_interval=20, max_queue=None) as ws:
                await ws.send(json.dumps({"action": "auth", "key": self.api_key, "secret": self.secret_key}))
                await ws.send(json.dumps({"action": "subscribe", "quotes": [self.symbol], "trades": [self.symbol]}))
                async for raw in ws:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    # Alpaca 는 메시지를 배열로 보냄.
                    for item in payload if isinstance(payload, list) else [payload]:
                        q.put(item)

        def _runner() -> None:
            try:
                asyncio.run(_consume())
            except Exception:  # noqa: BLE001
                pass
            finally:
                q.put(None)

        threading.Thread(target=_runner, name="alpaca-ws", daemon=True).start()
        while True:
            item = q.get()
            if item is None:
                break
            yield item
