"""고정폭 바이너리 틱 스토어 — 의존성 없는 고속 타임시리즈 저장/질의.

파일 포맷(little-endian, 자연 정렬 없음 → 완전 팩):
  헤더: magic(4s "DTS1") · version(B) · depth(H) · symbol(16s, utf-8 truncate/pad)
  레코드(고정폭, ts_ns 오름차순 가정):
    ts_ns(q) · last_price(d) · last_qty(d) · n_bid(B) · n_ask(B)
    · depth×(bid_px d, bid_qty d) · depth×(ask_px d, ask_qty d)
  (실제 호가 레벨 수는 n_bid/n_ask 로 복원; 빈 슬롯은 0 으로 패딩)

고정폭이므로 레코드 i 의 오프셋 = header_size + i*record_size → 임의 접근.
타임스탬프 정렬을 전제로 `read_range` 는 lower-bound 이진 탐색 후 순차 스캔(O(log n + k)).
CSV(`CsvReplayFeed` 포맷) 텍스트 파싱과 달리 struct 언팩만 하므로 적재가 빠르고 용량도 작다.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Iterable, Iterator

from ..feed.base import MarketFeed
from ..types import MarketTick, OrderBookLevel

_MAGIC = b"DTS1"
_VERSION = 1
_HEADER = struct.Struct("<4sBH16s")  # magic, version, depth, symbol


def _record_struct(depth: int) -> struct.Struct:
    return struct.Struct("<qddBB" + "dd" * (2 * depth))


def _encode_symbol(symbol: str) -> bytes:
    return symbol.encode("utf-8")[:16].ljust(16, b"\x00")


def _decode_symbol(raw: bytes) -> str:
    return raw.rstrip(b"\x00").decode("utf-8", errors="replace")


class TickStoreWriter:
    """틱을 고정폭 바이너리로 적재. 스토어 1개 = 종목 1개(첫 틱/인자로 심볼 고정).

    사용: ``with TickStoreWriter(path, depth=10) as w: w.extend(ticks)``
    """

    def __init__(self, path: str | Path, *, depth: int = 10, symbol: str | None = None,
                 append: bool = False) -> None:
        self.path = Path(path)
        self.depth = depth
        self.symbol = symbol
        self.count = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 이어쓰기(append): 기존 헤더의 depth/symbol 을 채택해 같은 파일에 계속 적재(캡처 재시작 안전).
        if append and self.path.exists() and self.path.stat().st_size >= _HEADER.size:
            existing = TickStore(self.path)
            self.depth = existing.depth
            self.symbol = existing.symbol
            self.count = len(existing)
            self._rec = _record_struct(self.depth)
            self._fh = self.path.open("r+b")
            self._fh.seek(0, 2)  # 끝으로 이동.
            self._header_written = True
            return
        self._rec = _record_struct(depth)
        self._fh = self.path.open("wb")
        self._header_written = symbol is not None
        if self._header_written:
            self._write_header()

    def _write_header(self) -> None:
        self._fh.seek(0)
        self._fh.write(_HEADER.pack(_MAGIC, _VERSION, self.depth, _encode_symbol(self.symbol or "")))

    def append(self, tick: MarketTick) -> None:
        if not self._header_written:
            self.symbol = tick.symbol
            self._write_header()
            self._header_written = True
        d = self.depth
        bids = tick.bids[:d]
        asks = tick.asks[:d]
        flat: list[float] = []
        for i in range(d):
            if i < len(bids):
                flat.extend((bids[i].price, bids[i].qty))
            else:
                flat.extend((0.0, 0.0))
        for i in range(d):
            if i < len(asks):
                flat.extend((asks[i].price, asks[i].qty))
            else:
                flat.extend((0.0, 0.0))
        self._fh.write(self._rec.pack(
            int(tick.ts_ns), float(tick.last_price), float(tick.last_qty),
            len(bids), len(asks), *flat))
        self.count += 1

    def extend(self, ticks: Iterable[MarketTick]) -> int:
        for t in ticks:
            self.append(t)
        return self.count

    def close(self) -> None:
        if not self._fh.closed:
            if not self._header_written:  # 빈 스토어도 유효 헤더 보장.
                self.symbol = self.symbol or ""
                self._write_header()
                self._header_written = True
            self._fh.close()

    def __enter__(self) -> "TickStoreWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class TickStore:
    """고정폭 바이너리 틱 스토어 리더 — 전체/시간범위/인덱스 임의접근 질의."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        with self.path.open("rb") as fh:
            head = fh.read(_HEADER.size)
        if len(head) < _HEADER.size:
            raise ValueError(f"손상된 틱 스토어(헤더 부족): {self.path}")
        magic, version, depth, sym = _HEADER.unpack(head)
        if magic != _MAGIC:
            raise ValueError(f"틱 스토어 매직 불일치: {magic!r}")
        self.version = version
        self.depth = depth
        self.symbol = _decode_symbol(sym)
        self._rec = _record_struct(depth)
        size = self.path.stat().st_size
        self._count = max(0, (size - _HEADER.size) // self._rec.size)

    def __len__(self) -> int:
        return self._count

    def _unpack(self, buf: bytes) -> MarketTick:
        vals = self._rec.unpack(buf)
        ts_ns, last_price, last_qty, n_bid, n_ask = vals[:5]
        levels = vals[5:]
        d = self.depth
        bids = tuple(OrderBookLevel(levels[2 * i], levels[2 * i + 1]) for i in range(n_bid))
        ask0 = 2 * d
        asks = tuple(OrderBookLevel(levels[ask0 + 2 * i], levels[ask0 + 2 * i + 1])
                     for i in range(n_ask))
        return MarketTick(ts_ns=ts_ns, symbol=self.symbol, bids=bids, asks=asks,
                          last_price=last_price, last_qty=last_qty)

    def _read_at(self, fh, index: int) -> MarketTick:
        fh.seek(_HEADER.size + index * self._rec.size)
        return self._unpack(fh.read(self._rec.size))

    def _ts_at(self, fh, index: int) -> int:
        fh.seek(_HEADER.size + index * self._rec.size)
        return struct.unpack("<q", fh.read(8))[0]

    def time_bounds(self) -> tuple[int, int] | None:
        if self._count == 0:
            return None
        with self.path.open("rb") as fh:
            return self._ts_at(fh, 0), self._ts_at(fh, self._count - 1)

    def get(self, index: int) -> MarketTick:
        if index < 0:
            index += self._count
        if not 0 <= index < self._count:
            raise IndexError(index)
        with self.path.open("rb") as fh:
            return self._read_at(fh, index)

    def _lower_bound(self, fh, ts: int) -> int:
        """ts_ns >= ts 인 첫 레코드 인덱스(이진 탐색). 정렬 전제."""
        lo, hi = 0, self._count
        while lo < hi:
            mid = (lo + hi) // 2
            if self._ts_at(fh, mid) < ts:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def read_all(self) -> Iterator[MarketTick]:
        with self.path.open("rb") as fh:
            fh.seek(_HEADER.size)
            rs = self._rec.size
            while True:
                buf = fh.read(rs)
                if len(buf) < rs:
                    break
                yield self._unpack(buf)

    def read_range(self, start_ns: int | None = None,
                   end_ns: int | None = None) -> Iterator[MarketTick]:
        """[start_ns, end_ns] (양끝 포함) 구간 틱 스트림. start 는 이진 탐색으로 점프."""
        with self.path.open("rb") as fh:
            start_idx = 0 if start_ns is None else self._lower_bound(fh, start_ns)
            fh.seek(_HEADER.size + start_idx * self._rec.size)
            rs = self._rec.size
            while True:
                buf = fh.read(rs)
                if len(buf) < rs:
                    break
                tick = self._unpack(buf)
                if end_ns is not None and tick.ts_ns > end_ns:
                    break
                yield tick

    def to_feed(self, start_ns: int | None = None, end_ns: int | None = None) -> "TickStoreFeed":
        return TickStoreFeed(self.path, start_ns=start_ns, end_ns=end_ns)


class TickStoreFeed(MarketFeed):
    """`TickStore` 를 `MarketFeed` 로 노출 — 파이프라인/백테스트에 그대로 결선."""

    def __init__(self, path: str | Path, *, start_ns: int | None = None,
                 end_ns: int | None = None) -> None:
        self.store = TickStore(path)
        self.start_ns = start_ns
        self.end_ns = end_ns

    def ticks(self) -> Iterator[MarketTick]:
        if self.start_ns is None and self.end_ns is None:
            yield from self.store.read_all()
        else:
            yield from self.store.read_range(self.start_ns, self.end_ns)


def write_ticks_store(path: str | Path, ticks: Iterable[MarketTick], *,
                      depth: int = 10, symbol: str | None = None) -> int:
    """틱 이터러블을 바이너리 스토어로 저장하고 기록 수를 반환."""
    with TickStoreWriter(path, depth=depth, symbol=symbol) as w:
        return w.extend(ticks)


def csv_to_store(csv_path: str | Path, store_path: str | Path, *, depth: int = 10) -> int:
    """`CsvReplayFeed` 포맷 CSV → 바이너리 틱 스토어로 변환(적재 가속용)."""
    from ..feed.replay import CsvReplayFeed

    return write_ticks_store(store_path, CsvReplayFeed(csv_path).ticks(), depth=depth)
