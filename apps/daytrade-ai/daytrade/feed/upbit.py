"""Upbit 실시간 피드(M1) — L2 오더북(orderbook_units) + 체결 → MarketTick.

Upbit 공개 WebSocket(wss://api.upbit.com/websocket/v1)은 인증 없이 구독 가능하며,
orderbook 메시지의 `orderbook_units` 는 레벨별 ask/bid 를 best-first 로 함께 제공한다.

정규화는 순수 함수, 라이브 전송은 지연 임포트(`websockets`) + 스레드 브리지로 분리(테스트는 주입).
"""
from __future__ import annotations

from typing import Iterable, Iterator

from ..types import MarketTick, OrderBookLevel, now_ns


def upbit_stream_kind(message: dict) -> str:
    t = message.get("type", "")
    if t == "orderbook":
        return "depth"
    if t == "trade":
        return "trade"
    return "unknown"


def normalize_upbit_orderbook(
    data: dict,
    symbol: str,
    depth: int,
    last_price: float,
    last_qty: float,
    ts_ns: int | None = None,
) -> MarketTick:
    units = data.get("orderbook_units", [])[:depth]
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []
    for u in units:
        try:
            bids.append(OrderBookLevel(price=float(u["bid_price"]), qty=float(u["bid_size"])))
            asks.append(OrderBookLevel(price=float(u["ask_price"]), qty=float(u["ask_size"])))
        except (KeyError, TypeError, ValueError):
            continue

    price = last_price
    if price <= 0:
        bb = bids[0].price if bids else 0.0
        ba = asks[0].price if asks else 0.0
        price = (bb + ba) / 2.0 if bb > 0 and ba > 0 else (bb or ba)

    return MarketTick(
        ts_ns=ts_ns if ts_ns is not None else now_ns(),
        symbol=symbol,
        bids=tuple(bids),
        asks=tuple(asks),
        last_price=price,
        last_qty=last_qty,
    )


def parse_upbit_trade(data: dict) -> tuple[float, float]:
    try:
        return float(data.get("trade_price", 0.0)), float(data.get("trade_volume", 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0


class UpbitFeed:
    """Upbit L2 오더북 + 체결 피드.

    Args:
        symbol: Upbit 마켓 코드(예: "KRW-BTC").
        depth: 사용할 오더북 레벨 수(Upbit 은 최대 15).
        message_source: 원시 메시지 이터러블(테스트/리플레이). None 이면 라이브 WS.
    """

    BASE_URL = "wss://api.upbit.com/websocket/v1"

    def __init__(
        self,
        symbol: str = "KRW-BTC",
        depth: int = 10,
        message_source: Iterable[dict] | None = None,
        max_ticks: int | None = None,
    ) -> None:
        self.symbol = symbol
        self.depth = depth
        self.message_source = message_source
        self.max_ticks = max_ticks
        self._last_price = 0.0
        self._last_qty = 0.0

    def _normalize(self, message: dict) -> MarketTick | None:
        kind = upbit_stream_kind(message)
        if kind == "trade":
            price, qty = parse_upbit_trade(message)
            if price > 0:
                self._last_price = price
                self._last_qty = qty
            return None
        if kind == "depth":
            return normalize_upbit_orderbook(
                message, self.symbol, self.depth, self._last_price, self._last_qty
            )
        return None

    def ticks(self) -> Iterator[MarketTick]:
        source = self.message_source if self.message_source is not None else self._live_messages()
        count = 0
        for message in source:
            tick = self._normalize(message)
            if tick is None:
                continue
            yield tick
            count += 1
            if self.max_ticks is not None and count >= self.max_ticks:
                break

    def _live_messages(self) -> Iterator[dict]:
        import asyncio
        import json
        import queue
        import threading
        import uuid

        sub = [
            {"ticket": str(uuid.uuid4())},
            {"type": "orderbook", "codes": [self.symbol]},
            {"type": "trade", "codes": [self.symbol]},
            {"format": "DEFAULT"},
        ]
        q: "queue.Queue[dict | None]" = queue.Queue(maxsize=10_000)

        async def _consume() -> None:
            import websockets

            async with websockets.connect(self.BASE_URL, ping_interval=20, max_queue=None) as ws:
                await ws.send(json.dumps(sub))
                async for raw in ws:
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode("utf-8")
                    try:
                        q.put(json.loads(raw))
                    except json.JSONDecodeError:
                        continue

        def _runner() -> None:
            try:
                asyncio.run(_consume())
            except Exception:  # noqa: BLE001
                pass
            finally:
                q.put(None)

        threading.Thread(target=_runner, name="upbit-ws", daemon=True).start()
        while True:
            item = q.get()
            if item is None:
                break
            yield item
