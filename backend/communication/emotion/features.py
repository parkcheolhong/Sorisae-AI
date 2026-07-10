"""언어 무관 음향 특징 추출 — 순수 파이썬(stdlib only, GPU/numpy 불필요).

PCM 샘플 시퀀스에서 RMS·ZCR·프레임 에너지 분산을 산출한다. 베이스라인 SER 입력용.
입력은 [-1,1] 정규화 float 또는 16-bit int 샘플 모두 허용(자동 정규화).
"""

from __future__ import annotations

import math
from typing import Sequence

from .models import AcousticFeatures


def _normalize(samples: Sequence[float]) -> list[float]:
    if not samples:
        return []
    peak = max(abs(float(s)) for s in samples)
    if peak <= 1.0:
        return [float(s) for s in samples]
    # 16-bit(또는 그 이상) 정수로 추정 → [-1,1] 정규화.
    scale = 32768.0 if peak <= 32768.0 else peak
    return [float(s) / scale for s in samples]


def extract_features(samples: Sequence[float], *, sample_rate: int = 16000,
                     frame_ms: int = 25) -> AcousticFeatures:
    """샘플 시퀀스 → AcousticFeatures.

    Args:
        samples: PCM 샘플(정수 또는 [-1,1] float).
        sample_rate: 샘플레이트(Hz).
        frame_ms: 에너지 분산 산정용 프레임 길이(ms).
    """

    xs = _normalize(samples)
    n = len(xs)
    if n == 0:
        return AcousticFeatures(rms=0.0, zcr=0.0, energy_var=0.0, n_samples=0)

    # RMS 에너지.
    rms = math.sqrt(sum(x * x for x in xs) / n)

    # 영교차율.
    crossings = 0
    for i in range(1, n):
        if (xs[i - 1] >= 0.0) != (xs[i] >= 0.0):
            crossings += 1
    zcr = crossings / max(1, n - 1)

    # 프레임별 RMS의 분산(운율 역동성 proxy) → 0..1 클램프.
    frame_len = max(1, int(sample_rate * frame_ms / 1000))
    frame_rms: list[float] = []
    for start in range(0, n, frame_len):
        frame = xs[start:start + frame_len]
        if not frame:
            continue
        fr = math.sqrt(sum(x * x for x in frame) / len(frame))
        frame_rms.append(fr)
    if len(frame_rms) >= 2:
        mean_fr = sum(frame_rms) / len(frame_rms)
        var = sum((fr - mean_fr) ** 2 for fr in frame_rms) / len(frame_rms)
        # 분산은 작은 값 → 가시화 위해 스케일·클램프.
        energy_var = min(1.0, var * 8.0)
    else:
        energy_var = 0.0

    return AcousticFeatures(
        rms=min(1.0, rms),
        zcr=min(1.0, zcr),
        energy_var=energy_var,
        n_samples=n,
    )
