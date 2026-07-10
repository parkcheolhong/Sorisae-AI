"""감정 E3 — 표현형 TTS 지연 예산 모니터링 + 폴백 서킷브레이커.

설계([`EMOTION_EXPRESSIVE_DESIGN.md`](../../../docs/worldlinco-v2/EMOTION_EXPRESSIVE_DESIGN.md)) §4
체감 균형 · §6 지연 예산(**P95<2s, 위반 시 비표현형 폴백**).

- **Prometheus** `voice_tts_synth_seconds{expressive}` 히스토그램 → Grafana 에서 P95 모니터.
- **인프로세스 롤링 p95**(표현형 합성 지연)로 예산 초과 시 표현형을 **자동 차단**(서킷브레이커),
  회복되면 자동 복귀(히스테리시스로 채터링 방지). 음색/품질이 아닌 **지연**만 본다.
- **hot path 보호**: 모든 함수는 예외 흡수(절대 throw 금지). `prometheus_client` 부재 시 메트릭 no-op,
  서킷브레이커(순수 파이썬)는 계속 동작.
"""

from __future__ import annotations

import logging
import os
import threading
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

try:  # 의존성 가드.
    from prometheus_client import Histogram

    _PROM = True
except Exception:  # pragma: no cover - 방어적
    _PROM = False

if _PROM:
    TTS_SYNTH = Histogram(
        "voice_tts_synth_seconds",
        "Voice-translate TTS synthesis latency (E3 expressive budget monitor)",
        ["expressive"],
        buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0),
    )
else:  # pragma: no cover
    TTS_SYNTH = None

_DEFAULT_BUDGET_MS = 2000.0
_DEFAULT_MIN_SAMPLES = 5
_WINDOW = 30

_lock = threading.Lock()
_recent_expressive_ms: deque[float] = deque(maxlen=_WINDOW)
_tripped = False


def _budget_ms() -> float:
    raw = os.getenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS", "")
    try:
        v = float(raw) if raw.strip() else _DEFAULT_BUDGET_MS
        return v if v > 0 else _DEFAULT_BUDGET_MS
    except (TypeError, ValueError):
        return _DEFAULT_BUDGET_MS


def _min_samples() -> int:
    raw = os.getenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES", "")
    try:
        v = int(float(raw)) if raw.strip() else _DEFAULT_MIN_SAMPLES
        return max(1, v)
    except (TypeError, ValueError):
        return _DEFAULT_MIN_SAMPLES


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def _reevaluate_locked() -> None:
    global _tripped
    if len(_recent_expressive_ms) < _min_samples():
        return
    p95 = _percentile(sorted(_recent_expressive_ms), 0.95)
    budget = _budget_ms()
    if p95 > budget:
        _tripped = True
    elif p95 <= budget * 0.8:  # 히스테리시스: 예산의 80% 이하로 회복돼야 복귀.
        _tripped = False


def observe_tts_latency(seconds: Optional[float], *, expressive: bool) -> None:
    """TTS 합성 지연을 메트릭에 기록하고(표현형/비표현형 라벨), 표현형이면 서킷브레이커 갱신."""

    try:
        if _PROM and seconds is not None and seconds >= 0:
            TTS_SYNTH.labels(expressive=("1" if expressive else "0")).observe(float(seconds))
    except Exception:  # pragma: no cover
        logger.debug("[expressive-budget] observe metric skipped", exc_info=True)

    if not expressive or seconds is None:
        return
    try:
        with _lock:
            _recent_expressive_ms.append(float(seconds) * 1000.0)
            _reevaluate_locked()
    except Exception:  # pragma: no cover
        logger.debug("[expressive-budget] breaker update skipped", exc_info=True)


def expressive_allowed() -> bool:
    """표현형 TTS 허용 여부. 롤링 P95 가 예산 초과면 False(폴백). 기본 True."""

    try:
        with _lock:
            return not _tripped
    except Exception:  # pragma: no cover
        return True


def p95_ms() -> Optional[float]:
    try:
        with _lock:
            if not _recent_expressive_ms:
                return None
            return round(_percentile(sorted(_recent_expressive_ms), 0.95), 1)
    except Exception:  # pragma: no cover
        return None


def reset_for_test() -> None:
    global _tripped
    with _lock:
        _recent_expressive_ms.clear()
        _tripped = False
