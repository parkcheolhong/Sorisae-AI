from daytrade.feed.alpaca import (
    AlpacaFeed,
    alpaca_msg_kind,
    normalize_alpaca_quote,
    parse_alpaca_trade,
)

import pytest
from daytrade.feed.upbit import (
    UpbitFeed,
    normalize_upbit_orderbook,
    parse_upbit_trade,
    upbit_stream_kind,
)


# ── Upbit ──

def upbit_orderbook():
    return {
        "type": "orderbook",
        "code": "KRW-BTC",
        "orderbook_units": [
            {"ask_price": 100.1, "bid_price": 100.0, "ask_size": 4, "bid_size": 5},
            {"ask_price": 100.2, "bid_price": 99.9, "ask_size": 6, "bid_size": 3},
        ],
    }


def upbit_trade(price=100.05, vol=0.5):
    return {"type": "trade", "code": "KRW-BTC", "trade_price": price, "trade_volume": vol}


def test_upbit_stream_kind():
    assert upbit_stream_kind(upbit_orderbook()) == "depth"
    assert upbit_stream_kind(upbit_trade()) == "trade"
    assert upbit_stream_kind({"type": "ticker"}) == "unknown"


def test_upbit_orderbook_normalization():
    t = normalize_upbit_orderbook(upbit_orderbook(), "KRW-BTC", 10, 0.0, 0.0)
    assert t.best_bid == pytest.approx(100.0)
    assert t.best_ask == pytest.approx(100.1)
    assert len(t.bids) == 2 and len(t.asks) == 2
    assert abs(t.last_price - 100.05) < 1e-9  # mid when no trade


def test_upbit_parse_trade():
    assert parse_upbit_trade(upbit_trade(101.0, 2.0)) == (101.0, 2.0)


def test_upbit_feed_applies_trade_then_depth():
    msgs = [upbit_trade(100.07, 1.0), upbit_orderbook()]
    ticks = list(UpbitFeed(symbol="KRW-BTC", message_source=msgs).ticks())
    assert len(ticks) == 1
    assert ticks[0].last_price == pytest.approx(100.07)
    assert ticks[0].symbol == "KRW-BTC"


# ── Alpaca ──

def alpaca_quote():
    return {"T": "q", "S": "AAPL", "bp": 100.0, "bs": 3, "ap": 100.1, "as": 4}


def alpaca_trade(p=100.05, s=50):
    return {"T": "t", "S": "AAPL", "p": p, "s": s}


def test_alpaca_msg_kind():
    assert alpaca_msg_kind(alpaca_quote()) == "quote"
    assert alpaca_msg_kind(alpaca_trade()) == "trade"
    assert alpaca_msg_kind({"T": "success"}) == "unknown"


def test_alpaca_quote_normalization_l1():
    t = normalize_alpaca_quote(alpaca_quote(), 0.0, 0.0)
    assert t.symbol == "AAPL"
    assert len(t.bids) == 1 and len(t.asks) == 1
    assert t.best_bid == 100.0 and t.best_ask == 100.1
    assert abs(t.last_price - 100.05) < 1e-9


def test_alpaca_parse_trade():
    assert parse_alpaca_trade(alpaca_trade(101.0, 10)) == (101.0, 10.0)


def test_alpaca_feed_trade_then_quote():
    msgs = [alpaca_trade(100.07, 10), alpaca_quote()]
    ticks = list(AlpacaFeed(symbol="AAPL", message_source=msgs).ticks())
    assert len(ticks) == 1
    assert ticks[0].last_price == pytest.approx(100.07)
    assert ticks[0].last_qty == pytest.approx(10.0)


def test_alpaca_live_requires_keys():
    import pytest

    feed = AlpacaFeed(symbol="AAPL", api_key="", secret_key="")
    with pytest.raises(RuntimeError):
        list(feed.ticks())
