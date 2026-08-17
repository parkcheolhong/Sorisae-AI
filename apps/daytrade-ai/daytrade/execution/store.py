"""TradeStore — 페이퍼 트레이딩 상태 영속(설계서 §6 "상태 DB 영속").

표준 라이브러리 `sqlite3` 만 사용(의존성 0). 실행(run)·체결(fill)·자본곡선(equity)을 기록해
세션 재시작/사후분석/재학습 데이터 추출에 쓴다. 체결 피드백 루프의 적재 지점이기도 하다.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..types import Fill

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    mode       TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    note       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS fills (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL,
    ts_ns         INTEGER NOT NULL,
    client_order_id TEXT,
    symbol        TEXT NOT NULL,
    side          TEXT NOT NULL,
    qty           REAL NOT NULL,
    price         REAL NOT NULL,
    slippage      REAL NOT NULL,
    fee           REAL NOT NULL,
    status        TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);
CREATE TABLE IF NOT EXISTS equity (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL,
    ts_ns   INTEGER NOT NULL,
    equity  REAL NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_fills_run ON fills(run_id);
CREATE INDEX IF NOT EXISTS idx_equity_run ON equity(run_id);
"""


@dataclass
class TradeStore:
    path: str = ":memory:"

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.run_id: int | None = None

    def start_run(self, *, mode: str, symbol: str, started_at: str, note: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO runs(started_at, mode, symbol, note) VALUES(?,?,?,?)",
            (started_at, mode, symbol, note),
        )
        self._conn.commit()
        self.run_id = int(cur.lastrowid)
        return self.run_id

    def record_fill(self, fill: Fill, *, run_id: int | None = None) -> None:
        rid = run_id if run_id is not None else self.run_id
        if rid is None:
            raise RuntimeError("start_run() 을 먼저 호출하세요.")
        o = fill.order
        self._conn.execute(
            "INSERT INTO fills(run_id, ts_ns, client_order_id, symbol, side, qty, price, slippage, fee, status)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (rid, fill.ts_ns, o.client_order_id, o.symbol, o.side.value,
             fill.filled_qty, fill.avg_price, fill.slippage, fill.fee, fill.status),
        )
        self._conn.commit()

    def record_equity(self, ts_ns: int, equity: float, *, run_id: int | None = None) -> None:
        rid = run_id if run_id is not None else self.run_id
        if rid is None:
            raise RuntimeError("start_run() 을 먼저 호출하세요.")
        self._conn.execute(
            "INSERT INTO equity(run_id, ts_ns, equity) VALUES(?,?,?)", (rid, ts_ns, equity)
        )
        self._conn.commit()

    def latest_run_id(self) -> int | None:
        row = self._conn.execute("SELECT run_id FROM runs ORDER BY run_id DESC LIMIT 1").fetchone()
        return int(row[0]) if row else None

    def equity_curve(self, run_id: int | None = None) -> list[float]:
        rid = run_id if run_id is not None else self.run_id
        rows = self._conn.execute(
            "SELECT equity FROM equity WHERE run_id=? ORDER BY id", (rid,)
        ).fetchall()
        return [float(r[0]) for r in rows]

    def fills_count(self, run_id: int | None = None) -> int:
        rid = run_id if run_id is not None else self.run_id
        row = self._conn.execute(
            "SELECT COUNT(*) FROM fills WHERE run_id=? AND status!='rejected'", (rid,)
        ).fetchone()
        return int(row[0]) if row else 0

    def summary(self, run_id: int | None = None) -> dict:
        rid = run_id if run_id is not None else self.run_id
        cur = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(qty),0), COALESCE(SUM(fee),0),"
            " COALESCE(AVG(slippage),0) FROM fills WHERE run_id=? AND status!='rejected'", (rid,)
        )
        n_fills, total_qty, total_fee, avg_slip = cur.fetchone()
        eq = self._conn.execute(
            "SELECT equity FROM equity WHERE run_id=? ORDER BY id", (rid,)
        ).fetchall()
        first_eq = eq[0][0] if eq else 0.0
        last_eq = eq[-1][0] if eq else 0.0
        return {
            "run_id": rid,
            "fills": int(n_fills),
            "total_qty": round(total_qty, 6),
            "total_fee": round(total_fee, 6),
            "avg_slippage": round(avg_slip, 8),
            "start_equity": round(first_eq, 2),
            "end_equity": round(last_eq, 2),
            "equity_points": len(eq),
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "TradeStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
