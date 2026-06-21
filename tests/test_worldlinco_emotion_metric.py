"""WorldLinco E2 — 감정 보존도 목적함수 항 단위테스트.

핵심: AV 손실 정규화, EMOTION_PROBE 파싱→집계, J에 emotion_loss 반영,
텔레메트리 없으면 0 기여(기존 J 하위호환).
"""

from datetime import datetime, timedelta

import pytest  # pyright: ignore[reportMissingImports]

from eval.worldlinco.parse_logs import ProbeEvent
from eval.worldlinco.objective import (
    emotion_av_loss,
    compute_call_metrics,
    scalar_objective,
)


def _ev(name: str, t: float, **fields) -> ProbeEvent:
    base = datetime(2026, 6, 21, 0, 0, 0)
    return ProbeEvent(
        ts=base + timedelta(seconds=t),
        event=name,
        raw_event="VOIP_" + name,
        fields={"event": "VOIP_" + name, **fields},
    )


def test_av_loss_bounds():
    assert emotion_av_loss(0.5, 0.5, 0.5, 0.5) == 0.0          # 완전 보존
    assert emotion_av_loss(0.0, 0.0, 1.0, 1.0) == pytest.approx(1.0)  # 정반대
    mid = emotion_av_loss(0.2, 0.2, 0.5, 0.6)
    assert 0.0 < mid < 1.0


def test_emotion_probe_parsed_and_aggregated():
    events = [
        _ev("EMOTION_PROBE", 0.0, src_arousal=0.8, src_valence=0.2,
            out_arousal=0.8, out_valence=0.2),   # loss 0
        _ev("EMOTION_PROBE", 1.0, src_arousal=0.8, src_valence=0.2,
            out_arousal=0.5, out_valence=0.5),   # some loss
        _ev("VOICE_RELAY_SEGMENT_FLUSH", 2.0),
    ]
    m = compute_call_metrics(events, "s10-test.log", 157)
    assert m.emotion_pairs == 2
    assert m.emotion_loss_mean is not None and m.emotion_loss_mean > 0.0
    assert m.emotion_preservation_median is not None
    # 보존도 = 1 - 손실.
    assert 0.0 <= m.emotion_preservation_median <= 1.0


def test_emotion_loss_contributes_to_J():
    events_hi_loss = [
        _ev("EMOTION_PROBE", 0.0, src_arousal=0.0, src_valence=0.0,
            out_arousal=1.0, out_valence=1.0),   # loss ~1.0
        _ev("VOICE_RELAY_SEGMENT_FLUSH", 1.0),
    ]
    m = compute_call_metrics(events_hi_loss, "s10-test.log", 157)
    j, contrib = scalar_objective(m)
    assert contrib["emotion_loss"] > 0.0
    # 가중치 0.15 × min(loss/1.0, 2) ≈ 0.15.
    assert contrib["emotion_loss"] == pytest.approx(0.15, abs=0.02)


def test_no_emotion_telemetry_is_zero_contribution():
    # EMOTION_PROBE 없는 기존 로그 → emotion_loss 기여 0 (하위호환).
    events = [
        _ev("VOICE_TRANSLATE_REQUEST", 0.0),
        _ev("VOICE_RELAY_SENT", 0.3),
        _ev("VOICE_RELAY_SEGMENT_FLUSH", 1.0),
        _ev("VOICE_RELAY_SILERO_STARTED", 2.0),
    ]
    m = compute_call_metrics(events, "s10-test.log", 157)
    assert m.emotion_pairs == 0
    assert m.emotion_loss_mean is None
    _, contrib = scalar_objective(m)
    assert contrib["emotion_loss"] == 0.0


def test_malformed_emotion_probe_ignored():
    events = [
        _ev("EMOTION_PROBE", 0.0, src_arousal="x", src_valence=0.2,
            out_arousal=0.8, out_valence=0.2),   # 잘못된 값 → 무시
        _ev("EMOTION_PROBE", 1.0, src_arousal=0.5),  # 필드 부족 → 무시
    ]
    m = compute_call_metrics(events, "s10-test.log", 157)
    assert m.emotion_pairs == 0
