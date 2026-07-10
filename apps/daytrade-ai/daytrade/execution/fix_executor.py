"""FixExecutor — FIX 4.4 주문 실행 어댑터(설계서 §6 Order Router).

`OrderExecutor` 를 구현하며, 주문을 NewOrderSingle(35=D)로 직렬화해 **FIX venue(전송 계층)** 로
보내고 ExecutionReport(35=8)를 파싱해 `Fill` 로 반환한다. 전송 계층은 주입식(injectable)이라:
  - `SimulatedFixVenue` : 실제 와이어 포맷을 왕복(encode→decode→매칭→encode)하는 모의 거래소.
                          페이퍼 트레이딩/테스트용. `is_live=False`.
  - 실거래 venue        : QuickFIX/N 세션 등으로 구현(이 저장소 미포함). `is_live=True`.

안전: `is_live` 는 주입된 venue 가 live 일 때만 True. 파이프라인의 이중 안전 게이트와 함께,
실거래는 LIVE 모드 + 환경변수 토큰이 모두 충족돼야만 활성화된다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from ..types import Fill, MarketTick, Order, OrderSide, OrderType
from . import fix
from .base import OrderExecutor
from .paper import PaperExecutor


def _fix_time() -> str:
    """FIX SendingTime(52) 포맷: YYYYMMDD-HH:MM:SS.sss (UTC)."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


class FixVenue(Protocol):
    """FIX 전송 계층 프로토콜 — NewOrderSingle 문자열을 받아 ExecutionReport 문자열을 반환."""

    is_live: bool

    def send(self, new_order_single: str, tick: MarketTick) -> str: ...


class SimulatedFixVenue:
    """모의 FIX 거래소 — 와이어 포맷을 실제로 왕복하며 페이퍼 체결을 보고.

    수신한 NewOrderSingle 을 디코드 → 내부 `PaperExecutor` 로 체결 계산 → ExecutionReport 인코드.
    체결 모델은 PaperExecutor 와 동일(슬리피지/부분체결/수수료). 테스트·페이퍼에 사용.
    """

    is_live = False

    def __init__(self, config=None, seed: int | None = 7, *, sender: str = "VENUE", target: str = "CLIENT") -> None:
        self._paper = PaperExecutor(config, seed=seed)
        self._sender = sender
        self._target = target
        self._seq = 0
        self._exec_id = 0

    def send(self, new_order_single: str, tick: MarketTick) -> str:
        if not fix.verify_checksum(new_order_single):
            raise ValueError("FIX 체크섬 불일치 — 손상된 NewOrderSingle")
        tags = fix.decode(new_order_single)
        side = fix.FIX_SIDE_INV[tags[54]]
        ot = OrderType.IOC if tags.get(59) == fix.TIF_IOC else (
            OrderType.LIMIT if tags.get(40) == "2" else OrderType.MARKET
        )
        order = Order(
            symbol=tags[55],
            side=side,
            qty=float(tags[38]),
            order_type=ot,
            limit_price=float(tags[44]) if 44 in tags else None,
            ts_ns=tick.ts_ns,
            client_order_id=tags.get(11, ""),
        )
        fill = self._paper.submit(order, tick)
        self._seq += 1
        self._exec_id += 1
        status = {"filled": "2", "partial": "1", "rejected": "8"}.get(fill.status, "8")
        leaves = max(0.0, order.qty - fill.filled_qty)
        return fix.build_execution_report(
            sender=self._sender, target=self._target, seq_num=self._seq,
            sending_time=_fix_time(), cl_ord_id=order.client_order_id or f"COID-{self._seq}",
            order_id=f"ORD-{self._exec_id}", exec_id=f"EXEC-{self._exec_id}",
            symbol=order.symbol, side=order.side, ord_status=status,
            last_qty=fill.filled_qty, last_px=fill.avg_price,
            cum_qty=fill.filled_qty, leaves_qty=leaves, avg_px=fill.avg_price,
        )


class FixExecutor(OrderExecutor):
    """FIX venue 를 통해 주문을 실행하는 `OrderExecutor`.

    Args:
        venue: FIX 전송 계층(SimulatedFixVenue 또는 실거래 세션).
        sender/target: CompID(49/56).
    """

    def __init__(self, venue: FixVenue, *, sender: str = "CLIENT", target: str = "VENUE") -> None:
        self.venue = venue
        self.sender = sender
        self.target = target
        self._seq = 0

    @property
    def is_live(self) -> bool:
        return bool(getattr(self.venue, "is_live", False))

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        self._seq += 1
        nos = fix.build_new_order_single(
            order, sender=self.sender, target=self.target,
            seq_num=self._seq, sending_time=_fix_time(),
            cl_ord_id=order.client_order_id or None,
        )
        report = self.venue.send(nos, tick)
        if not fix.verify_checksum(report):
            return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")
        fill = fix.parse_execution_report(report, order)
        # 슬리피지 보정: 의도가(mid) 대비 체결가 차이(매수/매도 방향 반영).
        if fill.status != "rejected" and fill.avg_price > 0 and tick.mid_price:
            intended = tick.mid_price
            if order.side == OrderSide.BUY:
                slip = (fill.avg_price - intended) / intended
            else:
                slip = (intended - fill.avg_price) / intended
            fill = Fill(order=fill.order, filled_qty=fill.filled_qty, avg_price=fill.avg_price,
                        ts_ns=fill.ts_ns, slippage=slip, fee=fill.fee, status=fill.status)
        return fill
