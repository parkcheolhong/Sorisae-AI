import numpy as np
import pandas as pd


def safe_div(a, b):
    return np.where(np.abs(b) > 1e-12, a / b, np.nan)


def ensure_datetime(df: pd.DataFrame, col: str = 'datetime') -> pd.DataFrame:
    out = df.copy()
    out[col] = pd.to_datetime(out[col])
    return out


def load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


def max_drawdown(equity_curve: pd.Series) -> float:
    roll_max = equity_curve.cummax()
    dd = equity_curve / roll_max - 1.0
    return float(dd.min())
