"""골든 테스트 — market.fbs(직렬화 SSOT) ↔ types.py/FEATURE_NAMES(의미 SSOT) 일치 검증."""
import re
from pathlib import Path

from daytrade.features.engine import FEATURE_NAMES

FBS = Path(__file__).resolve().parents[1] / "schemas" / "market.fbs"


def _table_fields(name: str) -> list[str]:
    text = FBS.read_text(encoding="utf-8")
    m = re.search(rf"table\s+{name}\s*\{{(.*?)\}}", text, re.DOTALL)
    assert m, f"table {name} not found in market.fbs"
    body = m.group(1)
    fields = []
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        fm = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if fm:
            fields.append(fm.group(1))
    return fields


def test_fbs_file_exists():
    assert FBS.exists()


def test_market_tick_fields():
    fields = _table_fields("MarketTick")
    assert fields == ["ts_ns", "symbol", "bids", "asks", "last_price", "last_qty"]


def test_feature_vector_order_matches_feature_names():
    fields = _table_fields("FeatureVector")
    # 앞의 ts_ns, symbol 메타 이후가 FEATURE_NAMES 와 정확히 동일 순서여야 한다.
    assert fields[:2] == ["ts_ns", "symbol"]
    assert tuple(fields[2:]) == FEATURE_NAMES


def test_fill_has_fee_field():
    # 비용 모델(M1-a)로 추가된 fee 가 스키마에도 존재해야 한다.
    assert "fee" in _table_fields("Fill")
