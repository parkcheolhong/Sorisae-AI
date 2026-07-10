"""Execution — 주문 실행 계층(설계서 §1/§6 Order Router / Execution Engine 대응).

- ``Portfolio``: 현금/포지션/실현손익 회계(account state).
- ``OrderExecutor``: 실행기 인터페이스(어댑터 지점).
- ``PaperExecutor``: 모의투자 체결기(기본·안전). 실주문 없음.
- ``OrderRouter``: 스마트 라우팅(멱등키·슬리피지가드·재견적·체결 콜백).
- ``FixExecutor``/``SimulatedFixVenue``: FIX 4.4 주문 실행 어댑터(M5).
- ``TradeStore``: sqlite 상태 영속(체결/자본곡선).
"""
from .portfolio import Portfolio
from .base import OrderExecutor
from .paper import PaperExecutor
from .router import OrderRouter, RouterStats
from .fix_executor import FixExecutor, SimulatedFixVenue
from .alpaca_executor import AlpacaExecutor, build_alpaca_order, parse_alpaca_fill
from .store import TradeStore

__all__ = [
    "Portfolio",
    "OrderExecutor",
    "PaperExecutor",
    "OrderRouter",
    "RouterStats",
    "FixExecutor",
    "SimulatedFixVenue",
    "AlpacaExecutor",
    "build_alpaca_order",
    "parse_alpaca_fill",
    "TradeStore",
]
