"""백테스트 리포트 고도화 — equity curve 기반 리스크/성과 분석 + JSON·HTML export.

기본 `RunMetrics`(요약)에 더해, 순자산 곡선에서 위험조정 지표(Sortino·Calmar)·낙폭 지속·수익팩터·
VaR/CVaR·승률(틱 기준)을 산출하고, 의존성 없는 인라인 SVG 스파크라인 HTML 리포트를 만든다.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np  # pyright: ignore[reportMissingImports]

from ..monitoring.metrics import RunMetrics


@dataclass(slots=True)
class BacktestAnalytics:
    n_points: int
    start_equity: float
    end_equity: float
    total_return_pct: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown_pct: float
    max_drawdown_duration: int   # 최장 수중(underwater) 구간 길이(틱)
    positive_ratio: float        # 틱 수익률 > 0 비율(승률 프록시)
    profit_factor: float         # 이익 합 / |손실 합|
    avg_gain_pct: float
    avg_loss_pct: float
    var_5_pct: float             # 5% VaR(틱 수익률 하위 5분위)
    cvar_5_pct: float            # 5% CVaR(조건부 기대손실)
    best_tick_pct: float
    worst_tick_pct: float

    def as_dict(self) -> dict:
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def analyze_equity_curve(equity: list[float] | np.ndarray, start_equity: float | None = None) -> BacktestAnalytics:
    arr = np.asarray(equity, dtype=float)
    if arr.size == 0:
        arr = np.asarray([start_equity if start_equity is not None else 0.0])
    start = float(start_equity if start_equity is not None else arr[0])
    end = float(arr[-1])
    total_return = ((end - start) / start * 100.0) if start else 0.0

    rets = np.diff(arr) / arr[:-1] if arr.size >= 2 else np.zeros(0)
    rets = rets[np.isfinite(rets)]

    sharpe = _ratio(rets, np.std(rets, ddof=1) if rets.size >= 2 else 0.0)
    downside = rets[rets < 0]
    dstd = float(np.std(downside, ddof=1)) if downside.size >= 2 else 0.0
    sortino = _ratio(rets, dstd)

    mdd, mdd_dur = _drawdown(arr)
    calmar = (total_return / (mdd * 100.0)) if mdd > 0 else 0.0

    gains = rets[rets > 0]
    losses = rets[rets < 0]
    profit_factor = float(gains.sum() / abs(losses.sum())) if losses.size and losses.sum() != 0 else 0.0
    var5 = float(np.percentile(rets, 5)) if rets.size else 0.0
    cvar5 = float(rets[rets <= var5].mean()) if rets.size and np.any(rets <= var5) else 0.0

    return BacktestAnalytics(
        n_points=int(arr.size),
        start_equity=start,
        end_equity=end,
        total_return_pct=total_return,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown_pct=mdd * 100.0,
        max_drawdown_duration=mdd_dur,
        positive_ratio=float(np.mean(rets > 0)) if rets.size else 0.0,
        profit_factor=profit_factor,
        avg_gain_pct=float(gains.mean() * 100.0) if gains.size else 0.0,
        avg_loss_pct=float(losses.mean() * 100.0) if losses.size else 0.0,
        var_5_pct=var5 * 100.0,
        cvar_5_pct=cvar5 * 100.0,
        best_tick_pct=float(rets.max() * 100.0) if rets.size else 0.0,
        worst_tick_pct=float(rets.min() * 100.0) if rets.size else 0.0,
    )


def analyze_run(metrics: RunMetrics) -> BacktestAnalytics:
    return analyze_equity_curve(metrics.equity_curve, metrics.start_equity)


def _ratio(rets: np.ndarray, denom: float) -> float:
    if rets.size < 2 or denom <= 0:
        return 0.0
    return float(np.mean(rets) / denom * np.sqrt(rets.size))


def _drawdown(equity: np.ndarray) -> tuple[float, int]:
    """(최대낙폭 비율, 최장 수중 구간 길이)."""
    if equity.size == 0:
        return 0.0, 0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(abs(np.min(dd)))
    # 수중(현재값 < 직전 peak) 구간의 최장 연속 길이.
    underwater = equity < peak
    longest = cur = 0
    for u in underwater:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return max_dd, int(longest)


def report_to_json(metrics: RunMetrics, path: str | Path) -> dict:
    """요약(RunMetrics) + 고급 분석을 JSON 으로 저장하고 dict 반환."""
    payload = {"summary": metrics.as_dict(), "analytics": analyze_run(metrics).as_dict()}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _sparkline_svg(equity: list[float], width: int = 720, height: int = 160) -> str:
    arr = np.asarray(equity, dtype=float)
    if arr.size < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    lo, hi = float(arr.min()), float(arr.max())
    rng = hi - lo or 1.0
    n = arr.size
    pts = []
    for i, v in enumerate(arr):
        x = i / (n - 1) * (width - 8) + 4
        y = height - 4 - (v - lo) / rng * (height - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    color = "#16a34a" if arr[-1] >= arr[0] else "#dc2626"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="{" ".join(pts)}"/></svg>')


def report_to_html(metrics: RunMetrics, path: str | Path, *, title: str = "daytrade-ai backtest") -> str:
    """equity 스파크라인 + 요약/분석 표가 담긴 단일 HTML 리포트(의존성 0)."""
    a = analyze_run(metrics)
    spark = _sparkline_svg(metrics.equity_curve)

    def _rows(d: dict) -> str:
        return "".join(f"<tr><td>{k}</td><td style='text-align:right'>{v}</td></tr>" for k, v in d.items())

    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{title}</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#111;background:#fafafa}}
h1{{font-size:18px}} h2{{font-size:14px;margin-top:20px;color:#374151}}
table{{border-collapse:collapse;font-size:13px;min-width:340px}}
td{{padding:4px 12px;border-bottom:1px solid #eee}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px}}
.wrap{{display:flex;gap:24px;flex-wrap:wrap}}
</style></head><body>
<h1>{title}</h1>
<div class="card"><h2>순자산 곡선 (equity curve)</h2>{spark}</div>
<div class="wrap">
<div class="card"><h2>요약</h2><table>{_rows(metrics.as_dict())}</table></div>
<div class="card"><h2>리스크/성과 분석</h2><table>{_rows(a.as_dict())}</table></div>
</div></body></html>"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return html
