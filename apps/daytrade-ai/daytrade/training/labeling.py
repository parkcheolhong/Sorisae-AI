"""라벨링 — forward-return 기반 방향 라벨(설계서 §7 백테스트/§3 시그널 정합).

시점 t 의 피처로 t+horizon 의 가격 변화를 예측한다:
    ret_t = (price[t+h] - price[t]) / price[t]
    y_buy  = 1 if ret_t >  up_bps   else 0
    y_sell = 1 if ret_t < -down_bps else 0   (bps = 0.01%)

두 라벨은 독립 이진값으로, 런타임 추론(`InferenceModel.predict → (prob_buy, prob_sell)`)
과 정확히 같은 의미 구조를 갖는다. up/down 둘 다 아니면 FLAT(둘 다 0).

look-ahead 차단: 미래(t+h)가 존재하는 t 만 라벨링한다 → 유효 표본 수 = len(prices) - horizon.
"""
from __future__ import annotations

import numpy as np


def make_labels(
    prices: "np.ndarray",
    horizon: int,
    up_bps: float = 5.0,
    down_bps: float = 5.0,
) -> tuple["np.ndarray", "np.ndarray", int]:
    """forward-return 라벨 생성.

    Args:
        prices: 시점별 기준가(mid 또는 last), shape (T,).
        horizon: 예측 지평(틱 수). t 와 t+horizon 비교.
        up_bps/down_bps: 상승/하락 라벨 임계값(bps). 5bps = 0.05%.

    Returns:
        (y_buy, y_sell, n) — 각 라벨 shape (n,), n = T - horizon (음수면 0).
    """
    prices = np.asarray(prices, dtype=np.float64)
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    n = len(prices) - horizon
    if n <= 0:
        empty = np.zeros((0,), dtype=np.float32)
        return empty, empty.copy(), 0

    cur = prices[:n]
    fut = prices[horizon : horizon + n]
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = np.where(cur != 0.0, (fut - cur) / cur, 0.0)

    up = up_bps / 10_000.0
    down = down_bps / 10_000.0
    y_buy = (ret > up).astype(np.float32)
    y_sell = (ret < -down).astype(np.float32)
    return y_buy, y_sell, n
