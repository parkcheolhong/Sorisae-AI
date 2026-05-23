"""
utils.py — 공통 유틸리티 (데이터 로드, 로깅, 저장/불러오기)
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from config import CFG, DataConfig


# ─────────────────────────────────────────
# 로거 설정
# ─────────────────────────────────────────
def get_logger(name: str = "intraday_lgbm") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = getattr(logging, CFG.log_level, logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


logger = get_logger()


# ─────────────────────────────────────────
# 산출물 디렉토리 생성
# ─────────────────────────────────────────
def ensure_artifacts_dir() -> Path:
    p = Path(CFG.artifacts_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────
def load_ohlcv(cfg: Optional[DataConfig] = None) -> pd.DataFrame:
    """
    OHLCV 데이터를 반환합니다.
    cfg.csv_path 가 있으면 CSV 우선, 없으면 yfinance 다운로드.
    반환 컬럼: open, high, low, close, volume (소문자)
    인덱스: DatetimeIndex (UTC aware 제거)
    """
    cfg = cfg or CFG.data
    if cfg.csv_path and Path(cfg.csv_path).exists():
        logger.info(f"CSV 로드: {cfg.csv_path}")
        df = pd.read_csv(cfg.csv_path, index_col=0, parse_dates=True)
    else:
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance 미설치. `pip install yfinance` 실행 후 재시도하세요.")
        logger.info(f"yfinance 다운로드: {cfg.ticker} {cfg.interval} {cfg.start_date}~{cfg.end_date}")
        df = yf.download(
            cfg.ticker,
            start=cfg.start_date,
            end=cfg.end_date,
            interval=cfg.interval,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise ValueError(f"데이터 없음: {cfg.ticker} ({cfg.interval})")

    # 컬럼 정규화
    df.columns = [c.lower().split()[-1] for c in df.columns]
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")

    # 타임존 정보 제거 (연산 일관성)
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df = df[list(required)].sort_index()
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["close"])
    logger.info(f"데이터 로드 완료: {len(df)}행, {df.index[0]} ~ {df.index[-1]}")
    return df


# ─────────────────────────────────────────
# 학습 / 검증 / 테스트 분할 (시계열 순서 유지)
# ─────────────────────────────────────────
def time_split(
    df: pd.DataFrame,
    train_ratio: float = None,
    val_ratio: float = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_ratio = train_ratio or CFG.data.train_ratio
    val_ratio = val_ratio or CFG.data.val_ratio
    n = len(df)
    t1 = int(n * train_ratio)
    t2 = int(n * (train_ratio + val_ratio))
    train = df.iloc[:t1].copy()
    val = df.iloc[t1:t2].copy()
    test = df.iloc[t2:].copy()
    logger.info(
        f"분할 — train:{len(train)} val:{len(val)} test:{len(test)}"
    )
    return train, val, test


# ─────────────────────────────────────────
# 수익률 계산 헬퍼
# ─────────────────────────────────────────
def log_return(series: pd.Series, periods: int = 1) -> pd.Series:
    return np.log(series / series.shift(periods))


def pct_return(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods)


# ─────────────────────────────────────────
# 모델 저장 / 불러오기
# ─────────────────────────────────────────
def save_model(model, path: str = None) -> None:
    path = path or CFG.model.model_save_path
    ensure_artifacts_dir()
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"모델 저장: {path}")


def load_model(path: str = None):
    path = path or CFG.model.model_save_path
    if not Path(path).exists():
        raise FileNotFoundError(f"모델 파일 없음: {path}")
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info(f"모델 불러오기: {path}")
    return model


# ─────────────────────────────────────────
# DataFrame 저장 헬퍼
# ─────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: str, **kwargs) -> None:
    ensure_artifacts_dir()
    df.to_csv(path, **kwargs)
    logger.info(f"CSV 저장: {path} ({len(df)}행)")


# ─────────────────────────────────────────
# 성능 지표 요약 출력
# ─────────────────────────────────────────
def print_metrics(metrics: dict, title: str = "결과") -> None:
    bar = "─" * 40
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k:<28}: {v:.4f}")
        else:
            print(f"  {k:<28}: {v}")
    print(bar)


# ─────────────────────────────────────────
# 재현성 시드 고정
# ─────────────────────────────────────────
def set_seed(seed: int = None) -> None:
    seed = seed or CFG.random_seed
    np.random.seed(seed)
    try:
        import random
        random.seed(seed)
    except Exception:
        pass
