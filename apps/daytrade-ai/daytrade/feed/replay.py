"""CSV 리플레이 피드 — 저장된 틱 데이터를 그대로 재생(백테스트/회귀).

기대 CSV 헤더(최소): ts_ns,symbol,last_price,last_qty,bid_px_0,bid_qty_0,...,ask_px_0,ask_qty_0,...
오더북 레벨 수는 헤더의 bid_px_* / ask_px_* 개수로 자동 추론한다.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ..types import MarketTick, OrderBookLevel


class CsvReplayFeed:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def ticks(self) -> Iterator[MarketTick]:
        with self.path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            bid_idxs = sorted(
                int(f.split("_")[-1]) for f in fields if f.startswith("bid_px_")
            )
            ask_idxs = sorted(
                int(f.split("_")[-1]) for f in fields if f.startswith("ask_px_")
            )
            for row in reader:
                bids = tuple(
                    OrderBookLevel(
                        price=float(row[f"bid_px_{i}"]),
                        qty=float(row[f"bid_qty_{i}"]),
                    )
                    for i in bid_idxs
                    if row.get(f"bid_px_{i}") not in (None, "")
                )
                asks = tuple(
                    OrderBookLevel(
                        price=float(row[f"ask_px_{i}"]),
                        qty=float(row[f"ask_qty_{i}"]),
                    )
                    for i in ask_idxs
                    if row.get(f"ask_px_{i}") not in (None, "")
                )
                yield MarketTick(
                    ts_ns=int(row["ts_ns"]),
                    symbol=row.get("symbol", "UNKNOWN"),
                    bids=bids,
                    asks=asks,
                    last_price=float(row["last_price"]),
                    last_qty=float(row.get("last_qty", 0.0) or 0.0),
                )
