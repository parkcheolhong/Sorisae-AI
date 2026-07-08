from daytrade.feed.binance import (
    BinanceFeed,
    normalize_depth,
    parse_agg_trade,
    parse_levels,
    stream_kind,
)

import pytest


def depth_msg(symbol="btcusdt"):
    return {
        "stream": f"{symbol}@depth10@100ms",
        "data": {
            "lastUpdateId": 1,
            "bids": [["100.0", "5"], ["99.9", "3"], ["99.8", "2"]],
            "asks": [["100.1", "4"], ["100.2", "6"], ["100.3", "1"]],
        },
    }


def trade_msg(symbol="btcusdt", price="100.05", qty="2.5"):
    return {
        "stream": f"{symbol}@aggTrade",
        "data": {"e": "aggTrade", "s": symbol.upper(), "p": price, "q": qty, "T": 123},
    }


def test_parse_levels_truncates_to_depth():
    levels = parse_levels([["1", "2"], ["3", "4"], ["5", "6"]], depth=2)
    assert len(levels) == 2
    assert levels[0].price == 1.0 and levels[0].qty == 2.0


def test_parse_levels_skips_malformed():
    levels = parse_levels([["1", "2"], ["bad"], ["3", "4"]], depth=10)
    assert len(levels) == 2


def test_parse_agg_trade():
    assert parse_agg_trade({"p": "100.5", "q": "3"}) == (100.5, 3.0)
    assert parse_agg_trade({"p": "x"}) == (0.0, 0.0)


def test_stream_kind():
    assert stream_kind(depth_msg()) == "depth"
    assert stream_kind(trade_msg()) == "trade"
    assert stream_kind({"data": {"foo": 1}}) == "unknown"


def test_normalize_depth_uses_mid_when_no_trade():
    tick = normalize_depth(depth_msg()["data"], "BTCUSDT", depth=10, last_price=0.0, last_qty=0.0)
    # mid of 100.0 / 100.1
    assert abs(tick.last_price - 100.05) < 1e-9
    assert tick.best_bid == 100.0
    assert tick.best_ask == 100.1


def test_normalize_depth_uses_last_trade_price():
    tick = normalize_depth(depth_msg()["data"], "BTCUSDT", depth=10, last_price=100.07, last_qty=2.5)
    assert tick.last_price == pytest.approx(100.07)
    assert tick.last_qty == pytest.approx(2.5)


def test_feed_emits_tick_per_depth_and_applies_trade_state():
    # trade 먼저 → 이후 depth 틱에 체결가 반영
    messages = [trade_msg(price="100.07", qty="2.5"), depth_msg(), depth_msg()]
    feed = BinanceFeed(symbol="BTCUSDT", message_source=messages)
    ticks = list(feed.ticks())
    assert len(ticks) == 2  # depth 메시지 2건만 틱 생성(trade 는 상태만 갱신)
    assert ticks[0].last_price == pytest.approx(100.07)
    assert ticks[0].last_qty == pytest.approx(2.5)
    assert ticks[0].symbol == "BTCUSDT"


def test_feed_max_ticks():
    messages = [depth_msg()] * 10
    feed = BinanceFeed(symbol="BTCUSDT", message_source=messages, max_ticks=3)
    assert len(list(feed.ticks())) == 3
