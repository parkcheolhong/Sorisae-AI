from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .search_space import KNOBS_BY_NAME, clamp_config, current_config


@dataclass(slots=True)
class Observation:
    params: dict[str, float]
    j: float
    components: dict[str, float]
    device: str
    n_calls: int = 1


_CONFIG_BY_VERSION = {
    3: current_config(),
}


def _seed_observations() -> list[Observation]:
    base = current_config()
    return [
        Observation(
            params=dict(base),
            j=0.52,
            components={"post_flush_rearm": 0.28, "reject_rate": 0.12},
            device="s10",
            n_calls=2,
        ),
        Observation(
            params=dict(base),
            j=0.58,
            components={"post_flush_rearm": 0.26, "reject_rate": 0.14},
            device="tab",
            n_calls=2,
        ),
    ]


def load_observations(path: str | None) -> list[Observation]:
    if not path:
        return _seed_observations()

    file_path = Path(path)
    rows = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return _seed_observations()

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        config_version = int(row.get("config_version") or 0)
        params = _CONFIG_BY_VERSION.get(config_version)
        if params is None:
            continue
        log_file = str(row.get("log_file") or "")
        device = "s10" if "s10" in log_file else ("tab" if "tab" in log_file else "unknown")
        if device == "unknown":
            continue
        bucket = grouped.setdefault(device, {"count": 0, "sum_j": 0.0, "sum_components": {}})
        objective_j = float(row.get("objective_J") or 0.0)
        bucket["count"] += 1
        bucket["sum_j"] += objective_j
        components = row.get("objective_components") if isinstance(row.get("objective_components"), dict) else {}
        for name, value in components.items():
            if isinstance(value, (int, float)):
                bucket["sum_components"][name] = float(bucket["sum_components"].get(name, 0.0)) + float(value)

    observations: list[Observation] = []
    for device, bucket in grouped.items():
        count = int(bucket["count"])
        if count <= 0:
            continue
        components = {
            name: float(total) / count
            for name, total in dict(bucket["sum_components"]).items()
        }
        observations.append(
            Observation(
                params=dict(current_config()),
                j=float(bucket["sum_j"]) / count,
                components=components,
                device=device,
                n_calls=count,
            )
        )
    return observations or _seed_observations()


def propose_next(observations: list[Observation], seed: int | None = None) -> dict[str, float]:
    if observations:
        base = dict(observations[0].params)
    else:
        base = current_config()
    proposal = clamp_config(base)

    total_rearm = sum(float(obs.components.get("post_flush_rearm", 0.0)) for obs in observations)
    total_reject = sum(float(obs.components.get("reject_rate", 0.0)) for obs in observations)
    direction = "lower" if total_rearm > total_reject else "raise"
    if direction == "lower":
        proposal["silero_silence_ms"] = KNOBS_BY_NAME["silero_silence_ms"].clamp(
            proposal["silero_silence_ms"] - 100.0
        )
    else:
        proposal["silero_silence_ms"] = KNOBS_BY_NAME["silero_silence_ms"].clamp(
            proposal["silero_silence_ms"] + 100.0
        )

    rng = random.Random(seed)
    for name, knob in KNOBS_BY_NAME.items():
        if name == "silero_silence_ms":
            continue
        jitter = rng.choice([-1.0, 0.0, 1.0]) * knob.step
        proposal[name] = knob.clamp(proposal[name] + jitter)
    return clamp_config(proposal)


def build_report(observations: list[Observation]) -> dict[str, Any]:
    devices: dict[str, dict[str, Any]] = {}
    for obs in observations:
        devices[obs.device] = {
            "calls": int(obs.n_calls),
            "objective_j": float(obs.j),
            "components": dict(obs.components),
            "proposed_next": propose_next([obs], seed=7),
        }

    if not devices:
        for obs in _seed_observations():
            devices[obs.device] = {
                "calls": int(obs.n_calls),
                "objective_j": float(obs.j),
                "components": dict(obs.components),
                "proposed_next": propose_next([obs], seed=7),
            }
    return {
        "backend": "stdlib-coordinate",
        "gate_status": "PROPOSAL_ONLY_BASELINE",
        "devices": devices,
    }

