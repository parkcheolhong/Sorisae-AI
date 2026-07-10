"""MarketFeed 인터페이스 — 시장 데이터 소스 추상화."""
from __future__ import annotations

import abc
from typing import Iterator

from ..types import MarketTick


class MarketFeed(abc.ABC):
    """시장 데이터 피드. ``ticks()`` 로 MarketTick 스트림을 동기 이터레이터로 제공한다.

    실거래소/브로커 웹소켓 연동 시 이 클래스를 상속해 ``ticks()`` 를 구현하면
    파이프라인 나머지(Feature→Detection→...)는 변경 없이 동작한다.
    """

    @abc.abstractmethod
    def ticks(self) -> Iterator[MarketTick]:
        """MarketTick 스트림(이터레이터). 유한(백테스트) 또는 무한(라이브)일 수 있다."""
        raise NotImplementedError
