"""관광 데이터 품질 검증 — Great Expectations 호환 표현식(expectation) 하니스.

설계 의도(법·윤리·품질 체크리스트: 품질 검증)
- 풀 Great Expectations 스택은 무겁고 Qdrant(벡터DB) 소스에 바로 안 맞으므로, **GE 와 동일한
  expectation 명명·결과 스키마**를 따르는 경량 하니스를 제공한다. 후일 데이터 규모가 커지면
  동일 expectation 을 GE `ExpectationSuite` 로 1:1 이식할 수 있다(이름/kwargs 동일).
- 결과 포맷은 GE `ExpectationSuiteValidationResult` 를 축약: 각 expectation 마다
  {expectation_type, kwargs, success, result:{element_count, unexpected_count, unexpected_percent}}.
- `mostly`(GE 개념): 성공 비율이 임계 이상이면 통과. null/범위는 1.0, 카테고리 화이트리스트는 0.95 기본.

데이터 소스: Qdrant `tourism_places` 컬렉션을 scroll 로 적재(임베딩 불필요 → 가벼움).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services.tourism_kb.service import _KNOWN_CATEGORIES, get_tourism_store

logger = logging.getLogger(__name__)


def load_points_from_qdrant(limit: Optional[int] = None, *, batch: int = 512) -> List[Dict[str, Any]]:
    """tourism_places payload 전수(또는 limit) 적재. 미가동 시 빈 리스트."""
    store = get_tourism_store()
    if not getattr(store, "client", None):
        return []
    out: List[Dict[str, Any]] = []
    offset = None
    try:
        while True:
            points, offset = store.client.scroll(
                collection_name=store.collection,
                limit=batch,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                out.append(dict(p.payload or {}))
            if offset is None or (limit is not None and len(out) >= limit):
                break
    except Exception as exc:
        logger.warning("[tourism_kb.quality] scroll 실패: %s", exc)
    return out[:limit] if limit is not None else out


def _result(expectation_type: str, kwargs: dict, element_count: int, unexpected: int, mostly: float) -> Dict[str, Any]:
    pct = (unexpected / element_count * 100.0) if element_count else 0.0
    success_fraction = (1.0 - unexpected / element_count) if element_count else 1.0
    return {
        "expectation_type": expectation_type,
        "kwargs": kwargs,
        "success": success_fraction >= mostly,
        "result": {
            "element_count": element_count,
            "unexpected_count": unexpected,
            "unexpected_percent": round(pct, 3),
            "success_fraction": round(success_fraction, 4),
            "mostly": mostly,
        },
    }


def _expect_not_null(rows: List[Dict[str, Any]], column: str, mostly: float = 1.0) -> Dict[str, Any]:
    unexpected = sum(1 for r in rows if r.get(column) in (None, ""))
    return _result("expect_column_values_to_not_be_null", {"column": column}, len(rows), unexpected, mostly)


def _expect_between(rows: List[Dict[str, Any]], column: str, lo: float, hi: float, mostly: float = 1.0) -> Dict[str, Any]:
    unexpected = 0
    for r in rows:
        v = r.get(column)
        if v is None:
            unexpected += 1
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            unexpected += 1
            continue
        if not (lo <= fv <= hi):
            unexpected += 1
    return _result(
        "expect_column_values_to_be_between",
        {"column": column, "min_value": lo, "max_value": hi}, len(rows), unexpected, mostly,
    )


def _expect_in_set(rows: List[Dict[str, Any]], column: str, value_set: set, mostly: float = 0.95) -> Dict[str, Any]:
    # null 은 검사 대상에서 제외(GE 기본 동작과 동일).
    checked = [r for r in rows if r.get(column) not in (None, "")]
    unexpected = sum(1 for r in checked if r.get(column) not in value_set)
    return _result(
        "expect_column_values_to_be_in_set",
        {"column": column, "value_set_size": len(value_set)}, len(checked), unexpected, mostly,
    )


def _expect_compound_unique(rows: List[Dict[str, Any]], columns: Tuple[str, ...], mostly: float = 1.0) -> Dict[str, Any]:
    seen: set = set()
    unexpected = 0
    for r in rows:
        key = tuple(str(r.get(c) or "") for c in columns)
        if key in seen:
            unexpected += 1
        else:
            seen.add(key)
    return _result(
        "expect_compound_columns_to_be_unique",
        {"column_list": list(columns)}, len(rows), unexpected, mostly,
    )


def _expect_row_count_min(rows: List[Dict[str, Any]], min_value: int) -> Dict[str, Any]:
    n = len(rows)
    return {
        "expectation_type": "expect_table_row_count_to_be_between",
        "kwargs": {"min_value": min_value},
        "success": n >= min_value,
        "result": {"observed_value": n, "min_value": min_value},
    }


def run_expectation_suite(rows: List[Dict[str, Any]], *, min_rows: int = 100) -> Dict[str, Any]:
    """GE 호환 expectation suite 실행 → 축약 ValidationResult."""
    started = time.time()
    results: List[Dict[str, Any]] = [
        _expect_row_count_min(rows, min_rows),
        _expect_not_null(rows, "name"),
        _expect_not_null(rows, "lat"),
        _expect_not_null(rows, "lon"),
        _expect_not_null(rows, "source"),
        _expect_not_null(rows, "license"),
        _expect_between(rows, "lat", -90.0, 90.0),
        _expect_between(rows, "lon", -180.0, 180.0),
        _expect_in_set(rows, "category", set(_KNOWN_CATEGORIES), mostly=0.95),
        _expect_compound_unique(rows, ("source", "source_id")),
    ]
    success_count = sum(1 for r in results if r["success"])
    return {
        "success": success_count == len(results),
        "evaluated_expectations": len(results),
        "successful_expectations": success_count,
        "unsuccessful_expectations": len(results) - success_count,
        "element_count": len(rows),
        "run_time_sec": round(time.time() - started, 3),
        "results": results,
    }
