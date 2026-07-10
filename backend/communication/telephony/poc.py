"""전화 브리지 1콜 PoC (시뮬레이션) — 실행 가능 데모.

통신사/SIP 없이 합성 오디오를 두 레그에 흘려, 서버측 브리지가 화자 교대를 통역해 상대
레그로 주입하는 콜 플로우를 검증한다. 실엔진은 `StubPipeline` 으로 대체.

사용::

    python -m backend.communication.telephony.poc
"""

from __future__ import annotations

import argparse
import json

from .config import TelephonyBridgeConfig
from .media_bridge import SimulatedMediaBridge
from .models import AudioFrame, CallLeg, LegRole
from .pipeline import StubPipeline


def _frames(leg_id: str, *, voiced_frames: int, frame_samples: int, start_seq: int = 0):
    """voiced 프레임 N개 + 종단용 무음 1프레임."""

    out = []
    seq = start_seq
    for _ in range(voiced_frames):
        out.append(AudioFrame(leg_id=leg_id, samples=[1000] * frame_samples, seq=seq, is_speech=True))
        seq += 1
    # 무음 종단(700ms 이상 누적되도록 큰 무음 1프레임).
    out.append(AudioFrame(leg_id=leg_id, samples=[0] * (frame_samples * 40), seq=seq, is_speech=False))
    return out


def run_one_call_poc(*, turns: int = 3) -> dict:
    cfg = TelephonyBridgeConfig(enabled=True, sample_rate=16000, frame_ms=20,
                                segment_silence_ms=700, segment_max_ms=7000)
    bridge = SimulatedMediaBridge(StubPipeline(), config=cfg)
    caller = CallLeg(leg_id="leg-caller", role=LegRole.CALLER, language="ko", peer_language="en")
    callee = CallLeg(leg_id="leg-callee", role=LegRole.CALLEE, language="en", peer_language="ko")
    bridge.add_leg(caller)
    bridge.add_leg(callee)

    frame_samples = int(cfg.sample_rate * cfg.frame_ms / 1000)  # 320 @20ms/16k
    transcript = {"caller_to_callee": [], "callee_to_caller": []}

    for turn in range(turns):
        # 화자 교대: caller(ko) → callee(en) 주입, 다음 turn은 반대.
        for frame in _frames("leg-caller", voiced_frames=10, frame_samples=frame_samples):
            bridge.push_frame(frame)
        injected_to_callee = bridge.drain_output("leg-callee")
        transcript["caller_to_callee"].append(len(injected_to_callee))

        for frame in _frames("leg-callee", voiced_frames=8, frame_samples=frame_samples):
            bridge.push_frame(frame)
        injected_to_caller = bridge.drain_output("leg-caller")
        transcript["callee_to_caller"].append(len(injected_to_caller))

    bridge.flush_all()
    report = {
        "turns": turns,
        "injection_counts": transcript,
        "stats": bridge.stats.to_dict(),
        "note": "SIMULATION ONLY — 실 SIP/통신사 트렁크 연결은 T0 사업 결정 후(T1 실통화).",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="전화 브리지 1콜 PoC (시뮬레이션)")
    ap.add_argument("--turns", type=int, default=3)
    args = ap.parse_args(argv)
    report = run_one_call_poc(turns=args.turns)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
