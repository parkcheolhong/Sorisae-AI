"""
signals.py — 후보 신호 생성
각 신호 함수는 pd.Series(bool) 을 반환합니다.
True = 해당 봉에서 롱 진입 후보.
generate_signals() 로 모든 신호를 합쳐 signal_mask(bool) 컬럼을 붙여줍니다.
"""

import numpy as np
import pandas as pd

from config import CFG, SignalConfig
from utils import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────
# 내부 지표 헬퍼 (신호 전용 경량 버전)
# ─────────────────────────────────────────
def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _macd(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger(close: pd.Series, period: int, std_mult: float):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


# ─────────────────────────────────────────
# 개별 신호 함수
# ─────────────────────────────────────────
def signal_rsi_oversold(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """RSI 과매도 반등: 이전 봉 RSI < oversold 이고 현재 봉 RSI > oversold 로 반등"""
    cfg = cfg or CFG.signal
    rsi = _rsi(df["close"], cfg.rsi_period)
    prev_oversold = rsi.shift(1) < cfg.rsi_oversold
    current_cross = rsi > cfg.rsi_oversold
    return (prev_oversold & current_cross).rename("sig_rsi_oversold")


def signal_macd_crossover(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """MACD 골든크로스: MACD 라인이 Signal 라인을 위로 돌파"""
    cfg = cfg or CFG.signal
    macd_line, signal_line, _ = _macd(
        df["close"], cfg.macd_fast, cfg.macd_slow, cfg.macd_signal
    )
    cross_up = (macd_line.shift(1) < signal_line.shift(1)) & (macd_line > signal_line)
    return cross_up.rename("sig_macd_cross")


def signal_bb_breakout_lower(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """볼린저 밴드 하단 돌파 후 복귀: 이전 봉 low < lower band, 현재 봉 close > lower band"""
    cfg = cfg or CFG.signal
    _, _, lower = _bollinger(df["close"], cfg.bb_period, cfg.bb_std)
    prev_below = df["low"].shift(1) < lower.shift(1)
    current_above = df["close"] > lower
    return (prev_below & current_above).rename("sig_bb_breakout")


def signal_ema_crossover(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """단기 EMA가 장기 EMA를 상향 돌파"""
    cfg = cfg or CFG.signal
    ema_s = _ema(df["close"], cfg.ema_short)
    ema_l = _ema(df["close"], cfg.ema_long)
    cross_up = (ema_s.shift(1) < ema_l.shift(1)) & (ema_s > ema_l)
    return cross_up.rename("sig_ema_cross")


def signal_volume_spike(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """거래량 급증 + 양봉: 거래량이 20일 평균의 N배 이상이고 종가 > 시가"""
    cfg = cfg or CFG.signal
    vol_ma = df["volume"].rolling(20).mean()
    vol_spike = df["volume"] > (vol_ma * cfg.volume_spike_mult)
    bullish = df["close"] > df["open"]
    return (vol_spike & bullish).rename("sig_vol_spike")


def signal_inside_bar_breakout(df: pd.DataFrame) -> pd.Series:
    """인사이드 바 돌파: 직전 봉의 고/저 범위 내에 갇혔다가 현재 봉이 직전 고가를 돌파"""
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    inside = (df["high"].shift(1) < prev_high.shift(1)) & (
        df["low"].shift(1) > prev_low.shift(1)
    )
    breakout = df["close"] > prev_high
    return (inside.shift(1) & breakout).rename("sig_inside_bar")


def signal_pullback_to_ema(df: pd.DataFrame, cfg: SignalConfig = None) -> pd.Series:
    """
    풀백 매수: 상승 추세(현재 close > EMA21)이고,
    직전 봉 low가 EMA9에 닿거나 하회했다가 현재 봉에서 EMA9 위로 복귀
    """
    cfg = cfg or CFG.signal
    ema_s = _ema(df["close"], cfg.ema_short)
    ema_l = _ema(df["close"], cfg.ema_long)
    trend_up = df["close"] > ema_l
    touched = df["low"].shift(1) <= ema_s.shift(1)
    recovered = df["close"] > ema_s
    return (trend_up & touched & recovered).rename("sig_pullback_ema")


# ─────────────────────────────────────────
# 신호 통합
# ─────────────────────────────────────────
SIGNAL_FUNCTIONS = [
    signal_rsi_oversold,
    signal_macd_crossover,
    signal_bb_breakout_lower,
    signal_ema_crossover,
    signal_volume_spike,
    signal_inside_bar_breakout,
    signal_pullback_to_ema,
]


def generate_signals(
    df: pd.DataFrame,
    cfg: SignalConfig = None,
    mode: str = "any",
) -> pd.DataFrame:
    """
    모든 신호를 계산해 df에 컬럼으로 추가하고
    signal_mask (bool) 컬럼을 반환합니다.

    mode:
        "any"  — 하나 이상의 신호가 True이면 후보
        "all"  — 모든 신호가 True이어야 후보 (조건 매우 엄격)
        "vote_N" — N개 이상 True (예: "vote_2")
    """
    cfg = cfg or CFG.signal
    out = df.copy()

    sig_cols = []
    for fn in SIGNAL_FUNCTIONS:
        try:
            sig = fn(df, cfg) if fn.__code__.co_varcount >= 2 else fn(df)
            out[sig.name] = sig.fillna(False).astype(bool)
            sig_cols.append(sig.name)
        except Exception as e:
            logger.warning(f"신호 생성 실패 ({fn.__name__}): {e}")

    if mode == "any":
        mask = out[sig_cols].any(axis=1)
    elif mode == "all":
        mask = out[sig_cols].all(axis=1)
    elif mode.startswith("vote_"):
        n = int(mode.split("_")[1])
        mask = out[sig_cols].sum(axis=1) >= n
    else:
        raise ValueError(f"알 수 없는 mode: {mode}")

    out["signal_mask"] = mask.astype(bool)

    total = int(mask.sum())
    logger.info(
        f"신호 생성 완료 — mode={mode}, 후보 신호 수: {total}/{len(df)} "
        f"({total/len(df)*100:.1f}%)"
    )
    return out
