"""Binance 실시간 피드(M1) — L2 오더북(top-10) + 체결 → MarketTick 정규화.

설계 메모:
    - Binance `<sym>@depth10@100ms` 부분 오더북 스트림은 **상위 10레벨**을 100ms마다 그대로 전송하므로
      diff 재구성 없이 곧바로 `MarketTick`(depth=10)으로 매핑된다.
    - `<sym>@aggTrade` 로 최근 체결가/체결량을 갱신한다.
    - 정규화 로직은 **순수 함수**(network 무관) → 단위 테스트로 회귀 차단.
    - 라이브 전송(WebSocket)은 지연 임포트(`websockets`)로 분리하고, 테스트/리플레이는
      `message_source`(원시 메시지 이터러블)를 주입해 네트워크 없이 검증한다.

ts_ns 는 현재 단조시계(now_ns)를 사용한다. 하드웨어 타임스탬프(PTP, ±100ns)는 M3/M9에서 도입.
"""
from __future__ import annotations

from typing import Iterable, Iterator

from ..types import MarketTick, OrderBookLevel, now_ns


# ── 순수 정규화 함수 ─────────────────────────────────────────────

def parse_levels(raw_levels: list, depth: int) -> tuple[OrderBookLevel, ...]:
    """[["price","qty"], ...] → OrderBookLevel 튜플(상위 depth개)."""
    out: list[OrderBookLevel] = []
    for entry in raw_levels[:depth]:
        try:
            price = float(entry[0])
            qty = float(entry[1])
        except (TypeError, ValueError, IndexError):
            continue
        out.append(OrderBookLevel(price=price, qty=qty))
    return tuple(out)


def normalize_depth(
    data: dict,
    symbol: str,
    depth: int,
    last_price: float,
    last_qty: float,
    ts_ns: int | None = None,
) -> MarketTick:
    """depth10 부분 오더북 메시지 → MarketTick.

    last_price 가 0이면(체결 미수신) best bid/ask 중앙값으로 보정한다.
    """
    bids = parse_levels(data.get("bids", []), depth)
    asks = parse_levels(data.get("asks", []), depth)

    price = last_price
    if price <= 0:
        bb = bids[0].price if bids else 0.0
        ba = asks[0].price if asks else 0.0
        if bb > 0 and ba > 0:
            price = (bb + ba) / 2.0
        else:
            price = bb or ba

    return MarketTick(
        ts_ns=ts_ns if ts_ns is not None else now_ns(),
        symbol=symbol,
        bids=bids,
        asks=asks,
        last_price=price,
        last_qty=last_qty,
    )


def parse_agg_trade(data: dict) -> tuple[float, float]:
    """aggTrade 메시지 → (price, qty). 파싱 실패 시 (0,0)."""
    try:
        return float(data.get("p", 0.0)), float(data.get("q", 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0


def stream_kind(message: dict) -> str:
    """combined/raw 메시지에서 종류 판별: 'depth' | 'trade' | 'unknown'."""
    stream = message.get("stream", "")
    data = message.get("data", message)
    if "depth" in stream:
        return "depth"
    if "aggTrade" in stream or data.get("e") == "aggTrade":
        return "trade"
    if "bids" in data and "asks" in data:
        return "depth"
    return "unknown"


# ── 피드 ────────────────────────────────────────────────────────

class BinanceFeed:
    """Binance L2(top-10) + 체결 피드.

    Args:
        symbol: 표시용 심볼(예: "BTCUSDT").
        depth: 오더북 레벨 수(기본 10 — depth10 스트림과 일치).
        message_source: 원시 메시지 이터러블(테스트/리플레이용). None 이면 라이브 WS 연결.
        ws_symbol: 스트림 구독용 소문자 심볼(예: "btcusdt"). None 이면 symbol.lower().
        emit_on: 'depth'(기본) — depth 메시지 수신 시마다 틱 emit.
    """

    BASE_URL = "wss://stream.binance.com:9443/stream"

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        depth: int = 10,
        message_source: Iterable[dict] | None = None,
        ws_symbol: str | None = None,
        max_ticks: int | None = None,
    ) -> None:
        self.symbol = symbol
        self.depth = depth
        self.message_source = message_source
        self.ws_symbol = (ws_symbol or symbol).lower()
        self.max_ticks = max_ticks
        self._last_price = 0.0
        self._last_qty = 0.0

    def _normalize(self, message: dict) -> MarketTick | None:
        kind = stream_kind(message)
        data = message.get("data", message)
        if kind == "trade":
            price, qty = parse_agg_trade(data)
            if price > 0:
                self._last_price = price
                self._last_qty = qty
            return None
        if kind == "depth":
            return normalize_depth(
                data,
                symbol=self.symbol,
                depth=self.depth,
                last_price=self._last_price,
                last_qty=self._last_qty,
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

    # ── 라이브 WebSocket(지연 임포트, 네트워크 필요) ──
    def _live_messages(self) -> Iterator[dict]:
        """websockets 로 combined 스트림을 구독해 원시 메시지를 yield(블로킹 브리지)."""
        import asyncio
        import json
        import queue
        import threading

        streams = f"{self.ws_symbol}@depth{self.depth}@100ms/{self.ws_symbol}@aggTrade"
        url = f"{self.BASE_URL}?streams={streams}"
        q: "queue.Queue[dict | None]" = queue.Queue(maxsize=10_000)

        async def _consume() -> None:
            import websockets  # 지연 임포트(미설치 환경 보호)

            async with websockets.connect(url, ping_interval=20, max_queue=None) as ws:
                async for raw in ws:
                    try:
                        q.put(json.loads(raw))
                    except json.JSONDecodeError:
                        continue

        def _runner() -> None:
            try:
                asyncio.run(_consume())
            except Exception:  # noqa: BLE001 — 연결 종료/오류 시 센티넬로 정상 종료
                pass
            finally:
                q.put(None)

        thread = threading.Thread(target=_runner, name="binance-ws", daemon=True)
        thread.start()
        while True:
            item = q.get()
            if item is None:
                break
            yield item
