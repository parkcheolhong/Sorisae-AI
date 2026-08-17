"""
features.py — 피처 엔지니어링
OHLCV + signal_mask 가 포함된 DataFrame을 받아
모델 학습에 쓸 피처 컬럼 목록과 DataFrame 을 반환합니다.
"""

from typing import List, Tuple

import numpy as np
import pandas as pd

from config import CFG, FeatureConfig
from utils import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────
# 지표 계산 (features 전용 — 외부 의존 없음)
# ─────────────────────────────────────────
def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _bollinger_pct_b(close: pd.Series, period: int, std_mult: float) -> pd.Series:
    """%B: 현재 가격이 밴드 내 어느 위치에 있는지 (0~1, 0.5=중심)"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return pct_b


def _bollinger_width(close: pd.Series, period: int, std_mult: float) -> pd.Series:
    """밴드 폭 / 중심가격 (변동성 지표)"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    width = (2 * std_mult * std) / mid.replace(0, np.nan)
    return width


def _macd_hist(close: pd.Series, fast=12, slow=26, signal=9) -> pd.Series:
    macd = _ema(close, fast) - _ema(close, slow)
    sig = _ema(macd, signal)
    return macd - sig


def _stochastic_k(df: pd.DataFrame, period: int = 14) -> pd.Series:
    low_min = df["low"].rolling(period).min()
    high_max = df["high"].rolling(period).max()
    denom = (high_max - low_min).replace(0, np.nan)
    return (df["close"] - low_min) / denom * 100


def _williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    denom = (high_max - low_min).replace(0, np.nan)
    return (high_max - df["close"]) / denom * -100


def _cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mean_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - mean_tp) / (0.015 * mad.replace(0, np.nan))


# ─────────────────────────────────────────
# 피처 그룹별 생성 함수
# ─────────────────────────────────────────
def _add_return_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    for p in cfg.return_periods:
        df[f"ret_{p}"] = df["close"].pct_change(p)
        df[f"log_ret_{p}"] = np.log(df["close"] / df["close"].shift(p))
    return df


def _add_volatility_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    for w in cfg.volatility_windows:
        # 실현 변동성 (log return std)
        log_ret = np.log(df["close"] / df["close"].shift(1))
        df[f"vol_real_{w}"] = log_ret.rolling(w).std()
        # ATR 기반 정규화 변동성
        atr = _atr(df, w)
        df[f"atr_norm_{w}"] = atr / df["close"].replace(0, np.nan)
    return df


def _add_volume_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    for w in cfg.volume_ma_windows:
        vol_ma = df["volume"].rolling(w).mean()
        df[f"vol_ratio_{w}"] = df["volume"] / vol_ma.replace(0, np.nan)
    df["vol_log"] = np.log1p(df["volume"])
    # OBV (On-Balance Volume) 변화율
    obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
    df["obv_ret_5"] = obv.pct_change(5)
    return df


def _add_momentum_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    for w in cfg.momentum_windows:
        df[f"mom_{w}"] = df["close"] / df["close"].shift(w) - 1
    # ROC (Rate of Change)
    df["roc_10"] = df["close"].pct_change(10)
    return df


def _add_rsi_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    for p in cfg.rsi_periods:
        df[f"rsi_{p}"] = _rsi(df["close"], p)
        # RSI 변화량
        df[f"rsi_{p}_delta"] = df[f"rsi_{p}"].diff(1)
    return df


def _add_macd_features(df: pd.DataFrame) -> pd.DataFrame:
    hist = _macd_hist(df["close"])
    df["macd_hist"] = hist
    df["macd_hist_delta"] = hist.diff(1)
    df["macd_hist_sign"] = np.sign(hist)
    return df


def _add_bollinger_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    # 기본 20봉 설정
    df["bb_pct_b"] = _bollinger_pct_b(df["close"], 20, 2.0)
    df["bb_width"] = _bollinger_width(df["close"], 20, 2.0)
    return df


def _add_oscillator_features(df: pd.DataFrame) -> pd.DataFrame:
    df["stoch_k"] = _stochastic_k(df, 14)
    df["stoch_k_delta"] = df["stoch_k"].diff(1)
    df["williams_r"] = _williams_r(df, 14)
    df["cci_20"] = _cci(df, 20)
    return df


def _add_price_structure_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    # 캔들 바디 크기
    df["candle_body"] = (df["close"] - df["open"]) / df["open"].replace(0, np.nan)
    df["candle_upper_shadow"] = (df["high"] - df[["close", "open"]].max(axis=1)) / df["close"].replace(0, np.nan)
    df["candle_lower_shadow"] = (df[["close", "open"]].min(axis=1) - df["low"]) / df["close"].replace(0, np.nan)
    df["candle_range"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
    # 갭
    df["gap"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1).replace(0, np.nan)
    # EMA 위치
    for span in [9, 21, 50]:
        ema = _ema(df["close"], span)
        df[f"close_vs_ema{span}"] = (df["close"] - ema) / ema.replace(0, np.nan)
    return df


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    df["hour"] = idx.hour
    df["minute"] = idx.minute
    df["dayofweek"] = idx.dayofweek
    # 장 초반/중반/후반 인코딩 (9~10시=0, 10~14시=1, 14~16시=2)
    df["session"] = pd.cut(
        idx.hour + idx.minute / 60,
        bins=[0, 10, 14, 24],
        labels=[0, 1, 2],
        right=False,
    ).astype(float)
    return df


# ─────────────────────────────────────────
# 메인 피처 생성 함수
# ─────────────────────────────────────────
def build_features(
    df: pd.DataFrame,
    cfg: FeatureConfig = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    피처를 계산하고 (DataFrame, 피처_컬럼_목록) 을 반환합니다.
    입력 df에는 signal_mask 컬럼이 있어야 합니다.
    NaN 처리는 cfg.nan_handling 설정에 따릅니다.
    """
    cfg = cfg or CFG.feature
    out = df.copy()

    out = _add_return_features(out, cfg)
    out = _add_volatility_features(out, cfg)
    out = _add_volume_features(out, cfg)
    out = _add_momentum_features(out, cfg)
    out = _add_rsi_features(out, cfg)
    out = _add_macd_features(out)
    out = _add_bollinger_features(out, cfg)
    out = _add_oscillator_features(out)
    out = _add_price_structure_features(out, cfg)
    if cfg.use_time_features:
        _add_time_features(out)

    # 피처 컬럼: OHLCV, signal_mask, label 제외한 나머지
    exclude = {"open", "high", "low", "close", "volume", "signal_mask",
               "label", "forward_ret"}
    # 신호 컬럼도 제외 (sig_ 접두어)
    feature_cols = [
        c for c in out.columns
        if c not in exclude and not c.startswith("sig_")
    ]

    # NaN 처리
    if cfg.nan_handling == "drop":
        before = len(out)
        out = out.dropna(subset=feature_cols)
        logger.info(f"NaN 제거: {before} → {len(out)}행")
    elif cfg.nan_handling == "fill_zero":
        out[feature_cols] = out[feature_cols].fillna(0)
    elif cfg.nan_handling == "fill_ffill":
        out[feature_cols] = out[feature_cols].fillna(method="ffill").fillna(0)

    # inf 처리
    out[feature_cols] = out[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0)

    logger.info(f"피처 생성 완료: {len(feature_cols)}개 피처, {len(out)}행")
    return out, feature_cols
