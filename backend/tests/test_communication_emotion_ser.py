"""감정 SER(E0) 언어 무관 베이스라인 단위테스트.

핵심: 핫패스 무접촉(텔레메트리 전용), flag off no-op, 휴리스틱 단조성·중립 폴백,
integration throw 금지.
"""

import math

import pytest  # pyright: ignore[reportMissingImports]

from backend.communication.emotion.config import EmotionSerConfig
from backend.communication.emotion.features import extract_features
from backend.communication.emotion.estimator import AcousticHeuristicSER
from backend.communication.emotion.models import AcousticFeatures, EmotionLabel
from backend.communication.emotion import integration as ser_integration


def _tone(freq_hz: float, amp: float, n: int, sample_rate: int = 16000) -> list[float]:
    return [amp * math.sin(2 * math.pi * freq_hz * i / sample_rate) for i in range(n)]


def _cfg(**kw) -> EmotionSerConfig:
    base = dict(enabled=True, confidence_threshold=0.35, min_samples=1600)
    base.update(kw)
    return EmotionSerConfig(**base)


def test_extract_features_basic():
    sig = _tone(220.0, 0.5, 16000)
    f = extract_features(sig, sample_rate=16000)
    assert f.n_samples == 16000
    assert 0.0 < f.rms <= 1.0
    assert 0.0 < f.zcr <= 1.0
    # 16-bit 정수 입력도 정규화되어야 함.
    f_int = extract_features([16000, -16000] * 2000, sample_rate=16000)
    assert f_int.rms <= 1.0


def test_silence_is_low_arousal_neutral():
    est = AcousticHeuristicSER(config=_cfg())
    silence = extract_features([0.0] * 16000, sample_rate=16000)
    out = est.estimate(silence)
    assert out.arousal < 0.3
    assert out.label == EmotionLabel.NEUTRAL  # 저신뢰 → 중립 폴백


def test_loud_signal_higher_arousal_than_quiet():
    est = AcousticHeuristicSER(config=_cfg())
    quiet = est.estimate(extract_features(_tone(220, 0.05, 16000)))
    loud = est.estimate(extract_features(_tone(220, 0.9, 16000)))
    assert loud.arousal > quiet.arousal


def test_too_short_is_zero_confidence_neutral():
    est = AcousticHeuristicSER(config=_cfg(min_samples=1600))
    short = extract_features(_tone(220, 0.9, 200))  # < min_samples
    out = est.estimate(short)
    assert out.confidence == 0.0
    assert out.label == EmotionLabel.NEUTRAL


def test_confidence_threshold_forces_neutral():
    # 임계를 1.0으로 올리면 어떤 추정도 중립 폴백.
    est = AcousticHeuristicSER(config=_cfg(confidence_threshold=1.0))
    out = est.estimate(extract_features(_tone(440, 0.9, 16000)))
    assert out.label == EmotionLabel.NEUTRAL


def test_estimate_to_dict_shape():
    est = AcousticHeuristicSER(config=_cfg())
    out = est.estimate(extract_features(_tone(300, 0.7, 16000)))
    d = out.to_dict()
    assert set(d) >= {"label", "arousal", "valence", "confidence", "source"}
    assert 0.0 <= d["arousal"] <= 1.0 and 0.0 <= d["valence"] <= 1.0


def test_integration_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_EMOTION_SER", raising=False)
    ser_integration.reset_for_test()
    assert ser_integration.estimate_from_samples(_tone(220, 0.9, 16000)) is None
    assert ser_integration.estimate_as_telemetry(_tone(220, 0.9, 16000)) is None
    ser_integration.reset_for_test()


def test_integration_runs_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_SER", "true")
    ser_integration.reset_for_test()
    try:
        est = ser_integration.estimate_from_samples(_tone(300, 0.8, 16000))
        assert est is not None
        tel = ser_integration.estimate_as_telemetry(_tone(300, 0.8, 16000))
        assert tel is not None and "label" in tel
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_SER", raising=False)
        ser_integration.reset_for_test()


def test_integration_never_throws_on_bad_input(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_SER", "true")
    ser_integration.reset_for_test()
    try:
        assert ser_integration.estimate_from_samples([]) is None
        assert ser_integration.estimate_from_samples(None) is None  # type: ignore[arg-type]
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_SER", raising=False)
        ser_integration.reset_for_test()
