"""인메모리 피드 — 이미 보유한 MarketTick 시퀀스를 그대로 재생.

워크포워드/단위테스트에서 동일 틱 집합을 여러 번 슬라이스해 재생할 때 쓴다.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Sequence

from ..types import MarketTick
from .base import MarketFeed


class ListFeed(MarketFeed):
    """리스트(또는 임의 시퀀스)의 MarketTick 을 순서대로 yield 하는 피드."""

    def __init__(self, ticks: Sequence[MarketTick] | Iterable[MarketTick]) -> None:
        self._ticks = list(ticks)

    def __len__(self) -> int:
        return len(self._ticks)

    def ticks(self) -> Iterator[MarketTick]:
        yield from self._ticks
