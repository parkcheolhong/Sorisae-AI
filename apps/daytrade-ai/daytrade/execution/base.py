"""OrderExecutor 인터페이스 — 실행기 추상화(어댑터 지점).

실거래 브로커(FIX/REST/WebSocket) 연동 시 이 인터페이스를 구현해 끼운다.
이 저장소에는 **실주문을 내는 구현체를 포함하지 않는다**(법·규제·계정 책임 분리).
"""
from __future__ import annotations

import abc

from ..types import Fill, MarketTick, Order


class OrderExecutor(abc.ABC):
    """주문 실행기. ``submit`` 은 주문을 받아 체결(Fill)을 반환한다."""

    @abc.abstractmethod
    def submit(self, order: Order, tick: MarketTick) -> Fill:
        raise NotImplementedError

    @property
    def is_live(self) -> bool:
        """실거래 여부. paper/backtest 는 False."""
        return False
