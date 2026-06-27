"""전화 브리지(T1) 도메인 모델 (순수 dataclass)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


def _now() -> float:
    return time.time()


class LegRole(str, Enum):
    """브리지 레그 역할."""

    CALLER = "caller"   # 착신을 건 쪽(원격 전화)
    CALLEE = "callee"   # 받는 쪽


@dataclass
class CallLeg:
    """브리지 한쪽 레그(SIP 다이얼로그 1개에 대응)."""

    leg_id: str
    role: LegRole
    language: str                      # 이 레그 화자의 언어
    peer_language: str                 # 상대 레그 언어(이 레그로 주입할 통역 언어)
    created_at: float = field(default_factory=_now)


@dataclass
class AudioFrame:
    """RTP 페이로드 1프레임 모사(PCM16 mono)."""

    leg_id: str
    samples: list[int]                 # PCM16 int 샘플
    seq: int = 0
    is_speech: bool = True             # VAD voiced 여부(무음 누적 종단용)
    ts: float = field(default_factory=_now)


@dataclass
class BridgeStats:
    """브리지 1콜 통계(PoC 평가용)."""

    frames_in: dict[str, int] = field(default_factory=dict)
    segments_bridged: dict[str, int] = field(default_factory=dict)
    frames_injected: dict[str, int] = field(default_factory=dict)
    rejects: int = 0
    pipeline_ms: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        med = None
        if self.pipeline_ms:
            s = sorted(self.pipeline_ms)
            med = s[len(s) // 2]
        return {
            "frames_in": dict(self.frames_in),
            "segments_bridged": dict(self.segments_bridged),
            "frames_injected": dict(self.frames_injected),
            "rejects": self.rejects,
            "pipeline_ms_median": med,
            "pipeline_ms_count": len(self.pipeline_ms),
        }
