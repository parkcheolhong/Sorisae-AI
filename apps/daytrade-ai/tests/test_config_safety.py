from daytrade.config import (
    LIVE_ENV_KEY,
    LIVE_ENV_TOKEN,
    TradingConfig,
    TradingMode,
    resolve_safety_gate,
)


def test_paper_is_default_safe():
    gate = resolve_safety_gate(TradingConfig(), env={})
    assert gate.effective_mode == TradingMode.PAPER
    assert not gate.live_allowed


def test_live_downgraded_without_token():
    cfg = TradingConfig(mode=TradingMode.LIVE)
    gate = resolve_safety_gate(cfg, env={})
    assert gate.effective_mode == TradingMode.PAPER
    assert gate.downgraded
    assert not gate.live_allowed


def test_live_downgraded_with_wrong_token():
    cfg = TradingConfig(mode=TradingMode.LIVE)
    gate = resolve_safety_gate(cfg, env={LIVE_ENV_KEY: "nope"})
    assert gate.effective_mode == TradingMode.PAPER


def test_live_allowed_with_exact_token():
    cfg = TradingConfig(mode=TradingMode.LIVE)
    gate = resolve_safety_gate(cfg, env={LIVE_ENV_KEY: LIVE_ENV_TOKEN})
    assert gate.effective_mode == TradingMode.LIVE
    assert gate.live_allowed
