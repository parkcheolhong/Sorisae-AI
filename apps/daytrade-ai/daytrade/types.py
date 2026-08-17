"""핵심 도메인 타입 — 파이프라인 전 구간에서 공유되는 불변(immutable) 데이터 구조.

표준 라이브러리 ``dataclass`` 만 사용해 의존성 없이 빠르고 명확하게 정의한다.
설계서의 ``struct MarketTick`` 에 대응하되, Python 에서 안전하게 다루도록 정규화했다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


def now_ns() -> int:
    """단조(monotonic) 나노초 타임스탬프. 레이턴시 측정용(벽시계 보정 영향 없음)."""
    import time

    return time.monotonic_ns()


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    """오더북 한 레벨(가격·수량)."""

    price: float
    qty: float


@dataclass(frozen=True, slots=True)
class MarketTick:
    """시장 데이터 1틱(스냅샷). 오더북 상위 N레벨 + 최근 체결 정보를 담는다.

    Attributes:
        ts_ns: 이벤트(또는 수신) 단조 나노초 타임스탬프.
        symbol: 종목 코드.
        bids: 매수 호가 레벨(가격 내림차순; index 0 = best bid).
        asks: 매도 호가 레벨(가격 오름차순; index 0 = best ask).
        last_price: 최근 체결가.
        last_qty: 최근 체결 수량(이번 틱 구간 체결량).
    """

    ts_ns: int
    symbol: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    last_price: float
    last_qty: float = 0.0

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> float | None:
        bb, ba = self.best_bid, self.best_ask
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    @property
    def spread(self) -> float | None:
        bb, ba = self.best_bid, self.best_ask
        if bb is None or ba is None:
            return None
        return ba - bb


class SignalSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"  # 관망(no-op)


@dataclass(frozen=True, slots=True)
class Signal:
    """탐지 엔진 또는 AI 추론이 생성한 매매 시그널."""

    side: SignalSide
    confidence: float  # [0,1]
    ts_ns: int
    symbol: str
    reason: str = ""
    features: dict[str, float] = field(default_factory=dict)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    IOC = "ioc"  # immediate-or-cancel


@dataclass(frozen=True, slots=True)
class Order:
    """주문 요청."""

    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    ts_ns: int = 0
    client_order_id: str = ""


@dataclass(frozen=True, slots=True)
class Fill:
    """체결 결과(부분/전량). slippage 는 의도가/체결가 차이, fee 는 수수료+세금 총액."""

    order: Order
    filled_qty: float
    avg_price: float
    ts_ns: int
    slippage: float = 0.0
    fee: float = 0.0
    status: str = "filled"  # filled | partial | rejected


@dataclass(slots=True)
class Position:
    """종목별 포지션 상태(가변)."""

    symbol: str
    qty: float = 0.0
    avg_entry: float = 0.0
    realized_pnl: float = 0.0

    def market_value(self, price: float) -> float:
        return self.qty * price

    def unrealized_pnl(self, price: float) -> float:
        if self.qty == 0:
            return 0.0
        return (price - self.avg_entry) * self.qty


def total_qty(levels: Sequence[OrderBookLevel]) -> float:
    return float(sum(level.qty for level in levels))
