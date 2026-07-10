"""틱 스토어 레코더 — 라이브 피드를 일별 로테이션 바이너리 스토어로 무손실 적재.

`RollingTickStoreWriter` 는 **UTC 날짜 경계**마다 새 파일(`{prefix}_{symbol}_{YYYYMMDD}.dts`)로
전환하여 KDB+ 식 일별 파티셔닝을 따른다(이어쓰기 지원 → 캡처 재시작 안전). `StoreRecordingFeed` 는
내부 피드를 통과(pass-through)시키며 동시에 스토어에 적재하므로, 라이브 운용 중 무손실 기록이 가능하다.

증설 대기 기간 동안 이 레코더로 실데이터를 축적해두면, GPU 확보 직후 6개월+ walk-forward/INT8
검증에 바로 투입할 수 있다(설계서 §8 데이터 계층 준비).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from ..feed.base import MarketFeed
from ..types import MarketTick
from .tickstore import TickStoreWriter


class RollingTickStoreWriter:
    """UTC 일별로 `.dts` 파일을 전환하며 틱을 적재. 같은 날 재시작 시 이어쓰기."""

    def __init__(self, out_dir: str | Path, symbol: str, *, depth: int = 10,
                 prefix: str = "ticks", wall: Callable[[], float] = time.time) -> None:
        self.out_dir = Path(out_dir)
        self.symbol = symbol
        self.depth = depth
        self.prefix = prefix
        self._wall = wall
        self._date: str | None = None
        self._writer: TickStoreWriter | None = None
        self.files: list[Path] = []
        self.total = 0

    def _date_str(self) -> str:
        return datetime.fromtimestamp(self._wall(), tz=timezone.utc).strftime("%Y%m%d")

    def path_for(self, date_str: str) -> Path:
        return self.out_dir / f"{self.prefix}_{self.symbol}_{date_str}.dts"

    def _roll_if_needed(self) -> None:
        d = self._date_str()
        if d == self._date and self._writer is not None:
            return
        if self._writer is not None:
            self._writer.close()
        self._date = d
        path = self.path_for(d)
        self._writer = TickStoreWriter(path, depth=self.depth, symbol=self.symbol, append=True)
        if path not in self.files:
            self.files.append(path)

    def append(self, tick: MarketTick) -> None:
        self._roll_if_needed()
        assert self._writer is not None
        self._writer.append(tick)
        self.total += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None

    def __enter__(self) -> "RollingTickStoreWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class StoreRecordingFeed(MarketFeed):
    """내부 피드를 통과시키며 일별 틱 스토어로 동시에 기록하는 데코레이터 피드."""

    def __init__(self, inner, out_dir: str | Path, *, symbol: str | None = None,
                 depth: int = 10, prefix: str = "ticks",
                 wall: Callable[[], float] = time.time) -> None:
        self.inner = inner
        self.out_dir = Path(out_dir)
        self.symbol = symbol
        self.depth = depth
        self.prefix = prefix
        self._wall = wall
        self.recorded = 0
        self.writer: RollingTickStoreWriter | None = None

    def ticks(self) -> Iterator[MarketTick]:
        src = self.inner.ticks() if hasattr(self.inner, "ticks") else iter(self.inner)
        writer: RollingTickStoreWriter | None = None
        try:
            for tick in src:
                if writer is None:
                    writer = RollingTickStoreWriter(
                        self.out_dir, self.symbol or tick.symbol,
                        depth=self.depth, prefix=self.prefix, wall=self._wall)
                    self.writer = writer
                writer.append(tick)
                self.recorded += 1
                yield tick
        finally:
            if writer is not None:
                writer.close()
