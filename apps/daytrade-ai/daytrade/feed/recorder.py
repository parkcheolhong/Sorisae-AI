"""틱 레코더 — 임의의 MarketFeed 를 감싸 CSV(`CsvReplayFeed` 포맷)로 저장.

라이브 → 기록 → 리플레이 → 백테스트 루프를 닫는다(M1).
CSV 헤더: ts_ns,symbol,last_price,last_qty,bid_px_0,bid_qty_0,...,ask_px_{d-1},ask_qty_{d-1},ask_px_0,...

`RecordingFeed` 는 데코레이터로, 내부 피드 틱을 그대로 흘려보내며(yield) 동시에 파일에 적재한다.
실시간 운용 중에도 무손실 기록이 가능하고, 저장된 CSV 는 그대로 `CsvReplayFeed` 로 재생된다.
"""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from ..types import MarketTick


def _resolve_safe_output_path(path: str | Path) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise ValueError("출력 경로가 비어 있습니다.")
    if "\x00" in raw:
        raise ValueError("출력 경로에 허용되지 않는 문자가 포함되어 있습니다.")
    input_path = Path(raw).expanduser()
    if not input_path.is_absolute() and any(part == ".." for part in input_path.parts):
        raise ValueError("상위 경로(..)는 출력 경로로 허용되지 않습니다.")
    candidate = input_path.resolve() if input_path.is_absolute() else (Path.cwd() / input_path).resolve()
    allowed_roots = [Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve()]
    if not any(candidate == root or root in candidate.parents for root in allowed_roots):
        raise ValueError("출력 경로는 현재 작업 디렉터리 또는 시스템 임시 디렉터리 내부여야 합니다.")
    return candidate


def build_header(depth: int) -> list[str]:
    cols = ["ts_ns", "symbol", "last_price", "last_qty"]
    for i in range(depth):
        cols.extend([f"bid_px_{i}", f"bid_qty_{i}"])
    for i in range(depth):
        cols.extend([f"ask_px_{i}", f"ask_qty_{i}"])
    return cols


def tick_to_row(tick: MarketTick, depth: int) -> dict[str, object]:
    row: dict[str, object] = {
        "ts_ns": tick.ts_ns,
        "symbol": tick.symbol,
        "last_price": tick.last_price,
        "last_qty": tick.last_qty,
    }
    for i in range(depth):
        if i < len(tick.bids):
            row[f"bid_px_{i}"] = tick.bids[i].price
            row[f"bid_qty_{i}"] = tick.bids[i].qty
        else:
            row[f"bid_px_{i}"] = ""
            row[f"bid_qty_{i}"] = ""
    for i in range(depth):
        if i < len(tick.asks):
            row[f"ask_px_{i}"] = tick.asks[i].price
            row[f"ask_qty_{i}"] = tick.asks[i].qty
        else:
            row[f"ask_px_{i}"] = ""
            row[f"ask_qty_{i}"] = ""
    return row


def write_ticks_csv(path: str | Path, ticks: Iterable[MarketTick], depth: int = 10) -> int:
    """틱 이터러블을 CSV 로 저장하고 기록한 틱 수를 반환한다."""
    path = _resolve_safe_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = build_header(depth)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for tick in ticks:
            writer.writerow(tick_to_row(tick, depth))
            count += 1
    return count


class RecordingFeed:
    """내부 피드를 감싸 통과(pass-through)시키며 CSV 로 동시에 기록하는 데코레이터 피드."""

    def __init__(self, inner, path: str | Path, depth: int = 10) -> None:
        self.inner = inner
        self.path = _resolve_safe_output_path(path)
        self.depth = depth
        self.recorded = 0

    def ticks(self) -> Iterator[MarketTick]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        header = build_header(self.depth)
        with self.path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=header)
            writer.writeheader()
            for tick in self.inner.ticks():
                writer.writerow(tick_to_row(tick, self.depth))
                self.recorded += 1
                fh.flush()
                yield tick
