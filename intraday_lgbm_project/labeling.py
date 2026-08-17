"""
labeling.py — 미래 수익률 기반 라벨 생성
binary  : forward_bars 봉 후 수익률 >= profit_threshold → 1, 아니면 0
ternary : >= profit_threshold → 2 (수익), <= -loss_threshold → 0 (손실), 나머지 → 1 (중립)
"""

import numpy as np
import pandas as pd

from config import CFG, LabelConfig
from utils import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────
# 미래 수익률 계산
# ─────────────────────────────────────────
def compute_forward_return(
    df: pd.DataFrame,
    forward_bars: int = None,
) -> pd.Series:
    """
    forward_bars 봉 후의 close 기준 수익률 (소수점).
    현재 봉 close 를 진입가로 가정.
    """
    n = forward_bars or CFG.label.forward_bars
    fwd_ret = df["close"].shift(-n) / df["close"] - 1
    return fwd_ret.rename("forward_ret")


# ─────────────────────────────────────────
# Binary 라벨
# ─────────────────────────────────────────
def label_binary(
    df: pd.DataFrame,
    cfg: LabelConfig = None,
) -> pd.Series:
    """
    forward_ret >= profit_threshold → 1 (매수 수익)
    그 외 → 0
    마지막 forward_bars 행은 NaN → 제거 대상
    """
    cfg = cfg or CFG.label
    fwd_ret = compute_forward_return(df, cfg.forward_bars)
    label = (fwd_ret >= cfg.profit_threshold).astype(int)
    label[fwd_ret.isna()] = np.nan
    return label.rename(cfg.target_col)


# ─────────────────────────────────────────
# Ternary 라벨
# ─────────────────────────────────────────
def label_ternary(
    df: pd.DataFrame,
    cfg: LabelConfig = None,
) -> pd.Series:
    """
    2 : 수익 (forward_ret >= profit_threshold)
    0 : 손실 (forward_ret <= -loss_threshold)
    1 : 중립
    NaN : 미래 봉 부족
    """
    cfg = cfg or CFG.label
    fwd_ret = compute_forward_return(df, cfg.forward_bars)
    label = pd.Series(1, index=df.index, name=cfg.target_col, dtype=float)
    label[fwd_ret >= cfg.profit_threshold] = 2
    label[fwd_ret <= -cfg.loss_threshold] = 0
    label[fwd_ret.isna()] = np.nan
    return label


# ─────────────────────────────────────────
# 라벨 통계 출력
# ─────────────────────────────────────────
def label_stats(label: pd.Series) -> dict:
    clean = label.dropna()
    counts = clean.value_counts().sort_index()
    total = len(clean)
    stats = {
        "total_labeled": total,
        "label_counts": counts.to_dict(),
    }
    for v, cnt in counts.items():
        stats[f"label_{int(v)}_ratio"] = cnt / total if total > 0 else 0.0
    return stats


# ─────────────────────────────────────────
# 통합 라벨 생성 + df 에 붙이기
# ─────────────────────────────────────────
def attach_labels(
    df: pd.DataFrame,
    cfg: LabelConfig = None,
    drop_na: bool = True,
) -> pd.DataFrame:
    """
    df 에 forward_ret, label 컬럼을 추가하고
    NaN 라벨 행을 제거(drop_na=True) 후 반환합니다.
    """
    cfg = cfg or CFG.label
    out = df.copy()

    # 미래 수익률 컬럼 추가
    out["forward_ret"] = compute_forward_return(out, cfg.forward_bars)

    # 라벨 생성
    if cfg.label_mode == "binary":
        out[cfg.target_col] = label_binary(out, cfg)
    elif cfg.label_mode == "ternary":
        out[cfg.target_col] = label_ternary(out, cfg)
    else:
        raise ValueError(f"지원하지 않는 label_mode: {cfg.label_mode}")

    if drop_na:
        before = len(out)
        out = out.dropna(subset=[cfg.target_col])
        out[cfg.target_col] = out[cfg.target_col].astype(int)
        logger.info(f"라벨 NaN 제거: {before} → {len(out)}행")

    stats = label_stats(out[cfg.target_col])
    logger.info(
        f"라벨 생성 완료 ({cfg.label_mode}) — "
        + ", ".join(f"label_{k}={v}" for k, v in stats["label_counts"].items())
        + f" (총 {stats['total_labeled']}행)"
    )
    return out
