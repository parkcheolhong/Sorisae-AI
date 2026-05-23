"""
backtest.py — 필터 전/후 백테스트 엔진
- before_filter: signal_mask == True 인 모든 신호를 진입
- after_filter : signal_mask == True AND model pred == 1 인 신호만 진입
수수료, 슬리피지, 손절/이익실현, 포지션 크기 지원
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import CFG, BacktestConfig
from utils import get_logger, print_metrics, save_csv

logger = get_logger(__name__)


# ─────────────────────────────────────────
# 단일 백테스트 실행
# ─────────────────────────────────────────
@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    entry_price: float
    exit_price: float
    pnl_pct: float       # 수수료 차감 후 손익률
    pnl_abs: float       # 절대 손익
    exit_reason: str     # "forward_close" | "stop_loss" | "take_profit"
    capital_at_entry: float


def run_backtest(
    df: pd.DataFrame,
    signal_col: str,
    cfg: BacktestConfig = None,
) -> Tuple[List[Trade], pd.Series]:
    """
    df: 인덱스=DatetimeIndex, signal_col=진입 신호(bool), OHLCV 포함
    반환: (trades_list, equity_curve)

    단순화 가정:
      - 진입: 신호 봉의 close (다음 봉 open 슬리피지 생략)
      - 청산: forward_bars 봉 후 close (또는 손절/이익실현)
    """
    cfg = cfg or CFG.backtest
    forward_bars = CFG.label.forward_bars
    capital = cfg.initial_capital
    comm = cfg.commission
    size_pct = cfg.position_size_pct
    sl = cfg.stop_loss_pct
    tp = cfg.take_profit_pct

    prices = df["close"].values
    signals = df[signal_col].values.astype(bool)
    n = len(df)
    idx = df.index

    trades: List[Trade] = []
    equity = np.full(n, np.nan)
    equity[0] = capital
    active_exits: dict = {}   # {exit_bar_idx: (entry_bar_idx, entry_price, cap_at_entry)}

    for i in range(n):
        # 종료 처리 (이번 봉에 청산 예정인 포지션)
        if i in active_exits:
            for (entry_i, entry_price, cap_at_entry) in active_exits.pop(i):
                exit_price = prices[i]
                gross_ret = (exit_price - entry_price) / entry_price
                net_ret = gross_ret - 2 * comm   # 진입/청산 수수료
                pnl_abs = cap_at_entry * size_pct * net_ret
                capital += pnl_abs
                trades.append(Trade(
                    entry_time=idx[entry_i],
                    exit_time=idx[i],
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl_pct=net_ret,
                    pnl_abs=pnl_abs,
                    exit_reason="forward_close",
                    capital_at_entry=cap_at_entry,
                ))

        equity[i] = capital

        # 진입 신호 처리
        if not signals[i]:
            continue
        if len(active_exits) >= cfg.max_positions:
            continue

        entry_price = prices[i]
        cap_at_entry = capital
        exit_bar = i + forward_bars

        # 손절/이익실현 intrabar 시뮬레이션 (미래 봉 순차 검사)
        actual_exit_bar = exit_bar
        actual_exit_price = prices[min(exit_bar, n - 1)]
        exit_reason = "forward_close"

        if (sl is not None or tp is not None) and exit_bar < n:
            for j in range(i + 1, min(exit_bar + 1, n)):
                high_j = df["high"].iloc[j]
                low_j = df["low"].iloc[j]
                gross_ret_high = (high_j - entry_price) / entry_price
                gross_ret_low = (low_j - entry_price) / entry_price

                if tp is not None and gross_ret_high >= tp:
                    actual_exit_bar = j
                    actual_exit_price = entry_price * (1 + tp)
                    exit_reason = "take_profit"
                    break
                if sl is not None and gross_ret_low <= -sl:
                    actual_exit_bar = j
                    actual_exit_price = entry_price * (1 - sl)
                    exit_reason = "stop_loss"
                    break

        if actual_exit_bar >= n:
            actual_exit_bar = n - 1
            actual_exit_price = prices[n - 1]

        # 즉시 청산(같은 봉)이면 records 에 직접 추가
        if actual_exit_bar == i:
            net_ret = -2 * comm  # 진입/청산만으로 비용 발생
            pnl_abs = cap_at_entry * size_pct * net_ret
            capital += pnl_abs
            trades.append(Trade(
                entry_time=idx[i],
                exit_time=idx[i],
                entry_price=entry_price,
                exit_price=actual_exit_price,
                pnl_pct=net_ret,
                pnl_abs=pnl_abs,
                exit_reason=exit_reason,
                capital_at_entry=cap_at_entry,
            ))
        else:
            active_exits.setdefault(actual_exit_bar, []).append(
                (i, entry_price, cap_at_entry)
            )

    equity_series = pd.Series(equity, index=idx, name="equity").ffill()
    return trades, equity_series


# ─────────────────────────────────────────
# 성능 지표 계산
# ─────────────────────────────────────────
def compute_backtest_metrics(
    trades: List[Trade],
    equity: pd.Series,
    label: str = "",
) -> Dict[str, float]:
    if not trades:
        logger.warning(f"[{label}] 거래 없음.")
        return {}

    pnl_pcts = np.array([t.pnl_pct for t in trades])
    pnl_abs = np.array([t.pnl_abs for t in trades])

    # 기본 지표
    n = len(trades)
    wins = (pnl_pcts > 0).sum()
    losses = (pnl_pcts <= 0).sum()
    win_rate = wins / n if n > 0 else 0.0
    avg_win = pnl_pcts[pnl_pcts > 0].mean() if wins > 0 else 0.0
    avg_loss = pnl_pcts[pnl_pcts <= 0].mean() if losses > 0 else 0.0

    # Profit Factor
    gross_profit = pnl_abs[pnl_abs > 0].sum()
    gross_loss = abs(pnl_abs[pnl_abs <= 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # 총 수익률
    total_return = (equity.iloc[-1] - equity.iloc[0]) / equity.iloc[0]

    # Max Drawdown
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    max_dd = drawdown.min()

    # Sharpe (일별 수익률 기반)
    daily_ret = equity.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0.0

    # Calmar
    calmar = total_return / abs(max_dd) if max_dd != 0 else np.inf

    # 청산 사유별 집계
    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    metrics = {
        "label": label,
        "n_trades": n,
        "win_rate": win_rate,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "calmar": calmar,
        "final_capital": equity.iloc[-1],
        **{f"exit_{k}": v for k, v in exit_reasons.items()},
    }
    print_metrics(metrics, title=f"백테스트 결과 [{label}]")
    return metrics


# ─────────────────────────────────────────
# 필터 전/후 비교 백테스트
# ─────────────────────────────────────────
def compare_before_after_filter(
    test_df: pd.DataFrame,
    cfg: BacktestConfig = None,
) -> Dict[str, dict]:
    """
    test_df 에는 다음 컬럼이 필요합니다:
      - signal_mask (bool): 원래 신호 후보
      - pred (int 0/1): 모델 필터 결과
      - open, high, low, close, volume

    반환: {"before": metrics_dict, "after": metrics_dict}
    """
    cfg = cfg or CFG.backtest

    if "signal_mask" not in test_df.columns:
        raise ValueError("test_df에 signal_mask 컬럼이 없습니다.")
    if "pred" not in test_df.columns:
        raise ValueError("test_df에 pred 컬럼이 없습니다. train.run_training() 결과를 사용하세요.")

    # before: signal_mask 그대로
    before_trades, before_equity = run_backtest(test_df, "signal_mask", cfg)
    before_metrics = compute_backtest_metrics(before_trades, before_equity, label="필터 전(모든 신호)")

    # after: signal_mask AND pred==1
    test_df = test_df.copy()
    test_df["filtered_signal"] = (
        test_df["signal_mask"].astype(bool) & (test_df["pred"] == 1)
    )
    after_trades, after_equity = run_backtest(test_df, "filtered_signal", cfg)
    after_metrics = compute_backtest_metrics(after_trades, after_equity, label="필터 후(모델 선택)")

    # 비교 요약
    _print_comparison(before_metrics, after_metrics)

    # 결과 저장
    trades_df = _trades_to_df(before_trades, "before") 
    trades_df = pd.concat([trades_df, _trades_to_df(after_trades, "after")])
    save_csv(trades_df, cfg.result_path, index=False)

    eq_df = pd.DataFrame({"before": before_equity, "after": after_equity})
    save_csv(eq_df, "artifacts/equity_curve.csv")

    return {
        "before": before_metrics,
        "after": after_metrics,
        "before_equity": before_equity,
        "after_equity": after_equity,
    }


def _trades_to_df(trades: List[Trade], tag: str) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = [
        {
            "tag": tag,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl_pct": t.pnl_pct,
            "pnl_abs": t.pnl_abs,
            "exit_reason": t.exit_reason,
        }
        for t in trades
    ]
    return pd.DataFrame(rows)


def _print_comparison(before: dict, after: dict) -> None:
    keys = ["n_trades", "win_rate", "profit_factor", "total_return", "max_drawdown", "sharpe"]
    bar = "═" * 58
    print(f"\n{bar}")
    print(f"  {'지표':<22}  {'필터 전':>12}  {'필터 후':>12}")
    print(f"  {'─'*22}  {'─'*12}  {'─'*12}")
    for k in keys:
        bv = before.get(k, "-")
        av = after.get(k, "-")
        bv_s = f"{bv:.4f}" if isinstance(bv, float) else str(bv)
        av_s = f"{av:.4f}" if isinstance(av, float) else str(av)
        print(f"  {k:<22}  {bv_s:>12}  {av_s:>12}")
    print(bar)


# ─────────────────────────────────────────
# 수익 곡선 플롯 (matplotlib 선택적)
# ─────────────────────────────────────────
def plot_equity_curves(
    before_equity: pd.Series,
    after_equity: pd.Series,
    save_path: str = "artifacts/equity_curve.png",
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib 미설치 — 그래프 생략.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    before_norm = before_equity / before_equity.iloc[0]
    after_norm = after_equity / after_equity.iloc[0]
    ax.plot(before_norm.index, before_norm.values, label="필터 전 (모든 신호)", alpha=0.7, linewidth=1.2)
    ax.plot(after_norm.index, after_norm.values, label="필터 후 (모델 선택)", linewidth=1.5)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_title("수익 곡선 비교 (정규화)", fontsize=13)
    ax.set_ylabel("누적 수익률 (배)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    logger.info(f"수익 곡선 저장: {save_path}")
