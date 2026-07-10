"""장애 주입 피드/실행기 — 결정론적 chaos 로 회복 동작 검증.

- `FaultInjectingFeed`  : 끊김(ConnectionError)·드롭·손상·지연을 틱 인덱스 기준으로 주입.
- `FlakyFeedFactory`    : 초기 N개 세션은 조기 끊김, 이후 정상 — 재연결→회복 시나리오 재현.
- `FlakyExecutor`       : 주문 제출 인덱스 기준 거부(rejected)·예외·부분체결 주입.
"""
from __future__ import annotations

from typing import Callable, Iterable, Iterator

from ..execution.base import OrderExecutor
from ..feed.base import MarketFeed
from ..types import Fill, MarketTick, Order


class FaultInjectingFeed(MarketFeed):
    """내부 피드를 감싸 결정론적 장애를 주입하는 데코레이터 피드.

    Args:
        inner: 원본 피드(또는 틱 이터러블).
        disconnect_after: N개 틱을 흘린 뒤 ConnectionError 발생(피드 드롭 모사). None=없음.
        drop_indices: 건너뛸(유실) 틱 인덱스 집합(패킷 로스 모사).
        corrupt_indices: 호가창을 비워 내보낼 틱 인덱스(손상 데이터 모사).
        latency_indices: `sleep` 훅을 호출할 틱 인덱스(지연 스파이크 모사).
        sleep: latency_indices 에서 호출할 지연 함수(기본 no-op; 테스트는 주입).
    """

    def __init__(self, inner, *, disconnect_after: int | None = None,
                 drop_indices: Iterable[int] | None = None,
                 corrupt_indices: Iterable[int] | None = None,
                 latency_indices: Iterable[int] | None = None,
                 sleep: Callable[[float], None] | None = None,
                 latency_sec: float = 0.05) -> None:
        self.inner = inner
        self.disconnect_after = disconnect_after
        self.drop_indices = set(drop_indices or ())
        self.corrupt_indices = set(corrupt_indices or ())
        self.latency_indices = set(latency_indices or ())
        self.sleep = sleep or (lambda _s: None)
        self.latency_sec = latency_sec
        self.emitted = 0

    def _inner_iter(self) -> Iterator[MarketTick]:
        if hasattr(self.inner, "ticks"):
            return iter(self.inner.ticks())
        return iter(self.inner)

    def ticks(self) -> Iterator[MarketTick]:
        seen = 0
        for tick in self._inner_iter():
            if self.disconnect_after is not None and self.emitted >= self.disconnect_after:
                raise ConnectionError(f"injected disconnect after {self.emitted} ticks")
            idx = seen
            seen += 1
            if idx in self.drop_indices:
                continue
            if idx in self.latency_indices:
                self.sleep(self.latency_sec)
            if idx in self.corrupt_indices:
                tick = MarketTick(ts_ns=tick.ts_ns, symbol=tick.symbol, bids=(), asks=(),
                                  last_price=tick.last_price, last_qty=tick.last_qty)
            self.emitted += 1
            yield tick
        # 스트림 끝에서도 disconnect_after 도달 시 끊김 보장(짧은 입력 대비).
        if self.disconnect_after is not None and self.emitted >= self.disconnect_after:
            raise ConnectionError(f"injected disconnect after {self.emitted} ticks")


class FlakyFeedFactory:
    """초기 `fail_sessions` 개 세션은 조기 끊김, 이후 정상 피드를 반환하는 팩토리.

    `LiveRunner(feed_factory=...)` 에 그대로 주입하면 '끊김→백오프 재연결→회복' 전 과정을
    네트워크 없이 결정론적으로 검증할 수 있다.
    """

    def __init__(self, base_factory: Callable[[], MarketFeed], *,
                 fail_sessions: int = 1, disconnect_after: int = 3) -> None:
        self.base_factory = base_factory
        self.fail_sessions = fail_sessions
        self.disconnect_after = disconnect_after
        self.session = 0

    def __call__(self) -> MarketFeed:
        s = self.session
        self.session += 1
        base = self.base_factory()
        if s < self.fail_sessions:
            return FaultInjectingFeed(base, disconnect_after=self.disconnect_after)
        return base


class FlakyExecutor(OrderExecutor):
    """내부 실행기를 감싸 주문 제출 인덱스 기준 장애를 주입.

    Args:
        inner: 원본 실행기.
        raise_indices: ConnectionError 를 던질 제출 인덱스(브로커 단절 모사).
        reject_indices: status='rejected' 빈 체결을 반환할 인덱스(주문 거부 모사).
        partial_indices: 수량을 `partial_ratio` 배만 체결할 인덱스(부분체결 모사).
    """

    def __init__(self, inner: OrderExecutor, *, raise_indices: Iterable[int] | None = None,
                 reject_indices: Iterable[int] | None = None,
                 partial_indices: Iterable[int] | None = None,
                 partial_ratio: float = 0.5) -> None:
        self.inner = inner
        self.raise_indices = set(raise_indices or ())
        self.reject_indices = set(reject_indices or ())
        self.partial_indices = set(partial_indices or ())
        self.partial_ratio = partial_ratio
        self.submits = 0

    @property
    def is_live(self) -> bool:
        return self.inner.is_live

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        idx = self.submits
        self.submits += 1
        if idx in self.raise_indices:
            raise ConnectionError(f"injected broker error on submit #{idx}")
        if idx in self.reject_indices:
            return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns,
                        status="rejected")
        if idx in self.partial_indices:
            partial = Order(symbol=order.symbol, side=order.side,
                            qty=order.qty * self.partial_ratio, order_type=order.order_type,
                            limit_price=order.limit_price, ts_ns=order.ts_ns,
                            client_order_id=order.client_order_id)
            fill = self.inner.submit(partial, tick)
            return Fill(order=order, filled_qty=fill.filled_qty, avg_price=fill.avg_price,
                        ts_ns=fill.ts_ns, slippage=fill.slippage, fee=fill.fee, status="partial")
        return self.inner.submit(order, tick)
