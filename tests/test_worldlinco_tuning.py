import json

import pytest  # pyright: ignore[reportMissingImports]

from backend.marketplace import worldlinco_tuning as wt
from backend.marketplace.worldlinco_tuning import (
    WORLDLINGCO_TUNING_DEFAULTS,
    WorldlincoTuningUpdate,
    apply_worldlinco_tuning_update,
    load_worldlinco_tuning,
    worldlinco_tuning_public_payload,
)


@pytest.fixture
def isolated_tuning_path(tmp_path, monkeypatch):
    # 운영 설정(knowledge/worldlinco_tuning_config.json)을 오염시키지 않도록
    # 쓰기 경로를 임시 파일로 격리한다. (이전에는 update 테스트가 라이브 설정을 덮어썼다.)
    fake_path = tmp_path / "worldlinco_tuning_config.json"
    fake_path.write_text(
        json.dumps({"version": 1, "voip": {}, "face_conversation": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(wt, "WORLDLINGCO_TUNING_PATH", fake_path)
    return fake_path


def test_worldlinco_tuning_defaults_load():
    # 가변 캘리브레이션 파일(knowledge/worldlinco_tuning_config.json)에 결합하지 않는다.
    # 모든 voip 키가 채워지고 calibrated cap 들이 과배칭 회귀 한계 내에 있는지만 검증한다.
    payload = load_worldlinco_tuning()
    for key in WORLDLINGCO_TUNING_DEFAULTS["voip"]:
        assert key in payload["voip"], f"missing voip tuning key: {key}"
    assert payload["face_conversation"]["file_speech_rms_db"] == -50
    # 과배칭 안전 한계: safety_cap/max_segment 는 calibrated 상한(<=13000) 이하로 유지한다.
    # (V.2 장문장 수용: 7000->12000 상향, 검증기 ge=8000/6000 범위 내)
    assert payload["voip"]["silero_safety_cap_ms"] <= 13000
    assert payload["voip"]["vad_max_segment_ms"] <= 13000


def test_worldlinco_tuning_fallback_defaults_no_overbatching():
    # 원격 fetch 실패 시 사용하는 코드 fallback 기본값이 과배칭(14s/12s)으로
    # 회귀하지 않도록 calibrated cap 과 정합 유지되는지 확인한다.
    voip = WORLDLINGCO_TUNING_DEFAULTS["voip"]
    assert voip["silero_safety_cap_ms"] <= 13000
    assert voip["vad_max_segment_ms"] <= 13000
    assert voip["meter_unavailable_fixed_flush_ms"] <= 5000


def test_worldlinco_tuning_public_payload_strips_admin_fields():
    public = worldlinco_tuning_public_payload()
    assert "calibration_notes" not in public
    assert "voip" in public
    assert public["voip"]["remote_echo_guard_ms"] == 4800


def test_worldlinco_tuning_update_merge(isolated_tuning_path):
    updated = apply_worldlinco_tuning_update(
        WorldlincoTuningUpdate(voip={"silero_silence_ms": 1200}),
        updated_by="test",
    )
    assert updated["voip"]["silero_silence_ms"] == 1200
    assert updated["updated_by"] == "test"
    # 격리 확인: 운영 설정 파일이 아니라 임시 파일에만 기록되어야 한다.
    persisted = json.loads(isolated_tuning_path.read_text(encoding="utf-8"))
    assert persisted["voip"]["silero_silence_ms"] == 1200
