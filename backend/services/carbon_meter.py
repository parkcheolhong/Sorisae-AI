"""추론 전력/탄소 측정기(경량, best-effort, fail-open).

법·윤리·품질 체크리스트 '탄소·환경' 항목.
- CodeCarbon 대신 의존성 없는 경량 측정기(컨테이너/권한 제약에서도 동작).
- GPU 전력: `nvidia-smi --query-gpu=power.draw` 샘플(가용 시). 미가용이면 폴백 추정(env) 또는 0.
- 에너지(Wh) = 평균전력(W) × 시간(h), 탄소(gCO2) = 에너지(kWh) × 그리드 배출계수(gCO2/kWh).
- 측정 실패는 절대 추론을 막지 않음(예외 삼킴). 집계는 프로세스 메모리(롤링) 보관.

환경변수:
- GRID_CARBON_INTENSITY_G_PER_KWH (기본 415.0 — 한국 전력망 근사)
- INFERENCE_FALLBACK_POWER_W       (GPU 미측정 시 추정 전력, 기본 0.0 = 미상)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _grid_intensity() -> float:
    try:
        return float(os.getenv("GRID_CARBON_INTENSITY_G_PER_KWH", "415"))
    except Exception:
        return 415.0


def _fallback_power_w() -> float:
    try:
        return float(os.getenv("INFERENCE_FALLBACK_POWER_W", "0"))
    except Exception:
        return 0.0


class CarbonMeter:
    _instance: Optional["CarbonMeter"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._stats_lock = threading.Lock()
        self._nvsmi: Optional[str] = shutil.which("nvidia-smi")
        self._gpu_checked = False
        self._gpu_ok = False
        self.reset()

    @classmethod
    def shared(cls) -> "CarbonMeter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def reset(self):
        with self._stats_lock:
            self._totals = {"calls": 0, "duration_s": 0.0, "energy_wh": 0.0, "carbon_g": 0.0}
            self._by_label: Dict[str, Dict[str, float]] = {}
            self._last_power_w: Optional[float] = None

    # ── GPU 전력 샘플 ────────────────────────────────────────────────────
    def _sample_gpu_power_w(self) -> Optional[float]:
        if not self._nvsmi:
            return None
        try:
            out = subprocess.run(
                [self._nvsmi, "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2.0,
            )
            if out.returncode != 0:
                return None
            total = 0.0
            found = False
            for line in out.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    total += float(line)
                    found = True
                except ValueError:
                    continue
            return total if found else None
        except Exception:
            return None

    @property
    def gpu_available(self) -> bool:
        if not self._gpu_checked:
            self._gpu_ok = self._sample_gpu_power_w() is not None
            self._gpu_checked = True
        return self._gpu_ok

    # ── 측정 컨텍스트 ────────────────────────────────────────────────────
    @contextmanager
    def measure(self, label: str = "inference"):
        """`with meter.measure("voice_answer"):` — 블록 실행시간·전력으로 에너지/탄소 적립.

        async 블록을 감싸도 안전(소요시간은 벽시계 기준). 예외는 재발생시키되 측정은 fail-open.
        """
        start = time.monotonic()
        p_start = None
        try:
            p_start = self._sample_gpu_power_w()
        except Exception:
            p_start = None
        try:
            yield
        finally:
            try:
                duration_s = max(0.0, time.monotonic() - start)
                p_end = self._sample_gpu_power_w()
                samples = [p for p in (p_start, p_end) if p is not None]
                if samples:
                    power_w = sum(samples) / len(samples)
                    source = "nvidia-smi"
                else:
                    power_w = _fallback_power_w()
                    source = "fallback" if power_w > 0 else "none"
                energy_wh = power_w * (duration_s / 3600.0)
                carbon_g = (energy_wh / 1000.0) * _grid_intensity()
                self._record(label, duration_s, energy_wh, carbon_g, power_w, source)
            except Exception as exc:
                logger.debug("[carbon_meter] 측정 적립 실패(무시): %s", exc)

    def _record(self, label, duration_s, energy_wh, carbon_g, power_w, source):
        with self._stats_lock:
            self._totals["calls"] += 1
            self._totals["duration_s"] += duration_s
            self._totals["energy_wh"] += energy_wh
            self._totals["carbon_g"] += carbon_g
            self._last_power_w = power_w
            row = self._by_label.setdefault(label, {"calls": 0, "duration_s": 0.0, "energy_wh": 0.0, "carbon_g": 0.0})
            row["calls"] += 1
            row["duration_s"] += duration_s
            row["energy_wh"] += energy_wh
            row["carbon_g"] += carbon_g
            row["power_source"] = source  # type: ignore[assignment]

    # ── 집계 조회 ────────────────────────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            t = dict(self._totals)
            calls = t["calls"] or 1
            return {
                "gpu_available": self.gpu_available,
                "grid_intensity_g_per_kwh": _grid_intensity(),
                "fallback_power_w": _fallback_power_w(),
                "last_power_w": round(self._last_power_w, 1) if self._last_power_w is not None else None,
                "totals": {
                    "calls": t["calls"],
                    "duration_s": round(t["duration_s"], 3),
                    "energy_wh": round(t["energy_wh"], 4),
                    "carbon_g": round(t["carbon_g"], 4),
                    "avg_carbon_g_per_call": round(t["carbon_g"] / calls, 4),
                    "avg_energy_wh_per_call": round(t["energy_wh"] / calls, 4),
                },
                "by_label": {
                    k: {
                        "calls": v["calls"],
                        "duration_s": round(v["duration_s"], 3),
                        "energy_wh": round(v["energy_wh"], 4),
                        "carbon_g": round(v["carbon_g"], 4),
                        "power_source": v.get("power_source"),
                    }
                    for k, v in self._by_label.items()
                },
            }


def get_carbon_meter() -> CarbonMeter:
    return CarbonMeter.shared()
