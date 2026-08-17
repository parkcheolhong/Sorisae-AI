from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.marketplace import crud, models


@dataclass
class QueryStats:
    total: int = 0
    select: int = 0
    insert: int = 0
    update: int = 0
    delete: int = 0


@dataclass
class MeasureResult:
    label: str
    iterations: int
    elapsed_ms: list[float]
    queries_total: list[int]
    queries_select: list[int]
    queries_insert: list[int]
    ops_per_sec: float


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * q))
    idx = max(0, min(idx, len(ordered) - 1))
    return float(ordered[idx])


def _new_query_stats() -> QueryStats:
    return QueryStats()


def _attach_query_counter(engine: Engine, stats: QueryStats) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(_conn, _cursor, statement, _params, _context, _executemany):
        text = str(statement or "").strip().lower()
        stats.total += 1
        if text.startswith("select"):
            stats.select += 1
        elif text.startswith("insert"):
            stats.insert += 1
        elif text.startswith("update"):
            stats.update += 1
        elif text.startswith("delete"):
            stats.delete += 1


def _legacy_resolve_tags(db: Session, names: list[str]) -> list[models.Tag]:
    resolved: list[models.Tag] = []
    for raw_name in names:
        name = str(raw_name or "").strip()
        if not name:
            continue
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if tag is None:
            tag = models.Tag(name=name)
            db.add(tag)
            db.flush()
        resolved.append(tag)
    return resolved


def _batch_resolve_tags(db: Session, names: list[str]) -> list[models.Tag]:
    return crud._resolve_tags_batch(db, names)


def _seed_base_data(db: Session) -> None:
    category = models.Category(name="bench", description="bench")
    user = models.User(email="bench@example.com", username="bench", hashed_password="x")
    db.add(category)
    db.add(user)
    db.flush()

    for i in range(20):
        db.add(models.Tag(name=f"existing_{i}"))
    db.commit()


def _build_tag_names(iteration: int, existing_count: int, new_count: int) -> list[str]:
    names: list[str] = []
    for i in range(existing_count):
        names.append(f"existing_{i % 20}")
    for i in range(new_count):
        names.append(f"missing_{iteration}_{i}")
    return names


def _measure(
    label: str,
    session_factory: sessionmaker,
    resolver: Callable[[Session, list[str]], list[models.Tag]],
    query_stats: QueryStats,
    iterations: int,
    existing_count: int,
    new_count: int,
) -> MeasureResult:
    elapsed_ms: list[float] = []
    queries_total: list[int] = []
    queries_select: list[int] = []
    queries_insert: list[int] = []

    started_all = time.perf_counter()

    for i in range(iterations):
        db = session_factory()
        try:
            names = _build_tag_names(i, existing_count, new_count)
            before_total = query_stats.total
            before_select = query_stats.select
            before_insert = query_stats.insert

            started = time.perf_counter()
            _ = resolver(db, names)
            db.flush()
            elapsed_ms.append((time.perf_counter() - started) * 1000.0)

            after_total = query_stats.total
            after_select = query_stats.select
            after_insert = query_stats.insert

            queries_total.append(int(after_total - before_total))
            queries_select.append(int(after_select - before_select))
            queries_insert.append(int(after_insert - before_insert))

            db.rollback()
        finally:
            db.close()

    total_sec = max(1e-9, time.perf_counter() - started_all)
    return MeasureResult(
        label=label,
        iterations=iterations,
        elapsed_ms=elapsed_ms,
        queries_total=queries_total,
        queries_select=queries_select,
        queries_insert=queries_insert,
        ops_per_sec=iterations / total_sec,
    )


def _render_result(result: MeasureResult) -> None:
    print(f"\n=== {result.label} ===")
    print(f"iterations           : {result.iterations}")
    print(f"avg/p95 latency(ms)  : {statistics.fmean(result.elapsed_ms):.2f} / {_percentile(result.elapsed_ms, 0.95):.2f}")
    print(f"avg queries total    : {statistics.fmean(result.queries_total):.2f}")
    print(f"avg queries select   : {statistics.fmean(result.queries_select):.2f}")
    print(f"avg queries insert   : {statistics.fmean(result.queries_insert):.2f}")
    print(f"throughput(ops/sec)  : {result.ops_per_sec:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure DB query optimization for tag resolution (legacy vs batch)")
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--existing-count", type=int, default=20)
    parser.add_argument("--new-count", type=int, default=10)
    parser.add_argument("--target-query-reduction", type=float, default=60.0)
    parser.add_argument("--target-throughput-gain", type=float, default=20.0)
    args = parser.parse_args()

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    models.Base.metadata.create_all(bind=engine)

    query_stats = _new_query_stats()
    _attach_query_counter(engine, query_stats)

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    seed_db = SessionLocal()
    try:
        _seed_base_data(seed_db)
    finally:
        seed_db.close()

    legacy = _measure(
        label="LEGACY (N+1 per-tag query)",
        session_factory=SessionLocal,
        resolver=_legacy_resolve_tags,
        query_stats=query_stats,
        iterations=max(1, args.iterations),
        existing_count=max(1, args.existing_count),
        new_count=max(0, args.new_count),
    )

    batch = _measure(
        label="BATCH (current _resolve_tags_batch)",
        session_factory=SessionLocal,
        resolver=_batch_resolve_tags,
        query_stats=query_stats,
        iterations=max(1, args.iterations),
        existing_count=max(1, args.existing_count),
        new_count=max(0, args.new_count),
    )

    engine.dispose()

    _render_result(legacy)
    _render_result(batch)

    legacy_q = statistics.fmean(legacy.queries_total)
    batch_q = statistics.fmean(batch.queries_total)
    query_reduction_pct = ((legacy_q - batch_q) / legacy_q * 100.0) if legacy_q > 0 else 0.0

    legacy_t = legacy.ops_per_sec
    batch_t = batch.ops_per_sec
    throughput_gain_pct = ((batch_t - legacy_t) / legacy_t * 100.0) if legacy_t > 0 else 0.0

    print("\n=== DELTA ===")
    print(f"query reduction      : {query_reduction_pct:.2f}%")
    print(f"throughput gain      : {throughput_gain_pct:.2f}%")

    print("\n=== TARGET CHECK ===")
    print(
        f"query_reduction >= {args.target_query_reduction:.1f}% : "
        f"{'PASS' if query_reduction_pct >= args.target_query_reduction else 'FAIL'} ({query_reduction_pct:.2f}%)"
    )
    print(
        f"throughput_gain >= {args.target_throughput_gain:.1f}% : "
        f"{'PASS' if throughput_gain_pct >= args.target_throughput_gain else 'FAIL'} ({throughput_gain_pct:.2f}%)"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
