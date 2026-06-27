"""감정 E3 — 표현형 TTS 지연 예산 서킷브레이커 단위테스트.

핵심: 기본 허용, 표본 부족 시 미발동, P95 예산 초과 시 차단(폴백), 히스테리시스 회복,
비표현형 지연은 브레이커에 미반영, throw 금지.
"""

from backend.communication.emotion import budget


def _feed(values_ms, *, expressive=True):
    for ms in values_ms:
        budget.observe_tts_latency(ms / 1000.0, expressive=expressive)


def test_default_allowed():
    budget.reset_for_test()
    assert budget.expressive_allowed() is True
    assert budget.p95_ms() is None


def test_not_tripped_below_min_samples(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS", "2000")
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES", "5")
    budget.reset_for_test()
    try:
        # 2개만(임계 5 미만) — 매우 느려도 미발동.
        _feed([9000, 9000])
        assert budget.expressive_allowed() is True
    finally:
        budget.reset_for_test()


def test_trips_when_p95_exceeds_budget(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS", "2000")
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES", "5")
    budget.reset_for_test()
    try:
        _feed([3000] * 8)  # 모두 3s > 2s 예산
        assert budget.expressive_allowed() is False
        assert budget.p95_ms() is not None and budget.p95_ms() > 2000
    finally:
        budget.reset_for_test()


def test_recovers_with_hysteresis(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS", "2000")
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES", "5")
    budget.reset_for_test()
    try:
        _feed([3000] * 8)
        assert budget.expressive_allowed() is False
        # 빠른 합성으로 윈도우 채움 → P95 가 예산의 80%(1600ms) 이하로 회복 → 복귀.
        _feed([500] * 30)
        assert budget.expressive_allowed() is True
    finally:
        budget.reset_for_test()


def test_nonexpressive_latency_does_not_trip(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS", "2000")
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_MIN_SAMPLES", "5")
    budget.reset_for_test()
    try:
        _feed([9000] * 10, expressive=False)  # 비표현형은 브레이커 미반영
        assert budget.expressive_allowed() is True
        assert budget.p95_ms() is None
    finally:
        budget.reset_for_test()


def test_observe_never_throws():
    budget.reset_for_test()
    budget.observe_tts_latency(None, expressive=True)
    budget.observe_tts_latency(-1.0, expressive=True)
    budget.observe_tts_latency(0.5, expressive=False)
    assert budget.expressive_allowed() is True
