from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Knob:
    name: str
    low: float
    high: float
    step: float
    current: float

    def clamp(self, value: float) -> float:
        bounded = min(self.high, max(self.low, float(value)))
        snapped = self.low + round((bounded - self.low) / self.step) * self.step
        bounded_snapped = min(self.high, max(self.low, snapped))
        return float(round(bounded_snapped, 6))


KNOBS = [
    Knob("silero_silence_ms", low=600.0, high=1400.0, step=50.0, current=900.0),
    Knob("silero_safety_cap_ms", low=8000.0, high=13000.0, step=100.0, current=12000.0),
    Knob("vad_max_segment_ms", low=6000.0, high=13000.0, step=100.0, current=12000.0),
    Knob("meter_unavailable_fixed_flush_ms", low=1200.0, high=5000.0, step=50.0, current=2800.0),
]

KNOBS_BY_NAME = {knob.name: knob for knob in KNOBS}


def current_config() -> dict[str, float]:
    return {knob.name: knob.current for knob in KNOBS}


def clamp_config(partial: Mapping[str, float]) -> dict[str, float]:
    resolved = current_config()
    for name, value in partial.items():
        knob = KNOBS_BY_NAME.get(name)
        if knob is None:
            continue
        resolved[name] = knob.clamp(float(value))
    return resolved

