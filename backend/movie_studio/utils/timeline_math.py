from __future__ import annotations


def seconds_to_frames(seconds: float, fps: int) -> int:
    return max(1, int(round(float(seconds) * max(1, int(fps)))))
