from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence

from .parse_logs import ProbeEvent


@dataclass(slots=True)
class CallMetrics:
    emotion_pairs: int = 0
    emotion_loss_mean: float | None = None
    emotion_preservation_median: float | None = None
    log_file: str = ""
    config_version: int = 0


def emotion_av_loss(
    src_arousal: float,
    src_valence: float,
    out_arousal: float,
    out_valence: float,
) -> float:
    da = float(out_arousal) - float(src_arousal)
    dv = float(out_valence) - float(src_valence)
    normalized = ((da * da + dv * dv) ** 0.5) / (2.0**0.5)
    return max(0.0, min(1.0, normalized))


def _safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compute_call_metrics(events: Sequence[ProbeEvent], log_file: str, config_version: int) -> CallMetrics:
    losses: list[float] = []
    for event in events:
        if str(event.event).strip().upper() != "EMOTION_PROBE":
            continue
        fields = event.fields if isinstance(event.fields, dict) else {}
        src_arousal = _safe_float(fields.get("src_arousal"))
        src_valence = _safe_float(fields.get("src_valence"))
        out_arousal = _safe_float(fields.get("out_arousal"))
        out_valence = _safe_float(fields.get("out_valence"))
        if None in (src_arousal, src_valence, out_arousal, out_valence):
            continue
        losses.append(
            emotion_av_loss(
                src_arousal=src_arousal,
                src_valence=src_valence,
                out_arousal=out_arousal,
                out_valence=out_valence,
            )
        )

    emotion_loss_mean = (sum(losses) / len(losses)) if losses else None
    emotion_preservation_median = (1.0 - median(losses)) if losses else None
    if emotion_preservation_median is not None:
        emotion_preservation_median = max(0.0, min(1.0, emotion_preservation_median))
    return CallMetrics(
        emotion_pairs=len(losses),
        emotion_loss_mean=emotion_loss_mean,
        emotion_preservation_median=emotion_preservation_median,
        log_file=log_file,
        config_version=int(config_version),
    )


def scalar_objective(metrics: CallMetrics) -> tuple[float, dict[str, float]]:
    emotion_loss_value = float(metrics.emotion_loss_mean or 0.0)
    emotion_contribution = 0.15 * min(emotion_loss_value / 1.0, 2.0)
    contributions = {
        "emotion_loss": round(emotion_contribution, 6),
    }
    return (round(sum(contributions.values()), 6), contributions)

