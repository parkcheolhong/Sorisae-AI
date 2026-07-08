"""WorldLinco mobile tuning config — VoIP relay + face conversation VAD/TTS timing."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


WORLDLINGCO_TUNING_PATH = _project_root() / "knowledge" / "worldlinco_tuning_config.json"


WORLDLINGCO_TUNING_DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "updated_at": None,
    "updated_by": "defaults",
    "calibration_notes": "",
    # NOTE: 이 fallback 기본값은 런타임 SSOT(knowledge/worldlinco_tuning_config.json)와
    # 정합 유지한다. 원격 fetch 실패(LTE 단절 등) 시에도 14s/12s 과배칭으로 회귀하지
    # 않도록 calibrated safety_cap/max_segment/fixed_flush 를 동일하게 둔다.
    "voip": {
        "silero_silence_ms": 1400,
        "silero_speech_ms": 120,
        "silero_min_segment_ms": 2400,
        "silero_min_speech_span_ms": 1700,
        "silero_safety_cap_ms": 12000,
        "silero_post_flush_cooldown_ms": 1000,
        "remote_echo_guard_ms": 4800,
        "speaker_echo_guard_ms": 5800,
        "remote_listen_hold_ms": 2600,
        "post_playback_guard_ms": 550,
        "vad_silence_flush_ms": 1500,
        "vad_min_segment_ms": 2200,
        "vad_max_segment_ms": 12000,
        "speech_meter_min_db": -52,
        "file_speech_rms_db": -52,
        "meter_unavailable_fixed_flush_ms": 4000,
    },
    "face_conversation": {
        "silence_flush_ms": 1600,
        "min_segment_ms": 2200,
        "max_segment_ms": 12000,
        "file_speech_rms_db": -50,
        "meter_poll_every": 2,
        "restart_ms": 250,
        "playback_cap_ms": 10000,
    },
}


class WorldlincoVoipTuningUpdate(BaseModel):
    silero_silence_ms: Optional[int] = Field(None, ge=500, le=2500)
    silero_speech_ms: Optional[int] = Field(None, ge=80, le=400)
    silero_min_segment_ms: Optional[int] = Field(None, ge=1500, le=6000)
    silero_min_speech_span_ms: Optional[int] = Field(None, ge=800, le=5000)
    silero_safety_cap_ms: Optional[int] = Field(None, ge=8000, le=30000)
    silero_post_flush_cooldown_ms: Optional[int] = Field(None, ge=200, le=3000)
    remote_echo_guard_ms: Optional[int] = Field(None, ge=1500, le=10000)
    speaker_echo_guard_ms: Optional[int] = Field(None, ge=2000, le=12000)
    remote_listen_hold_ms: Optional[int] = Field(None, ge=1000, le=8000)
    post_playback_guard_ms: Optional[int] = Field(None, ge=200, le=2000)
    vad_silence_flush_ms: Optional[int] = Field(None, ge=600, le=3500)
    vad_min_segment_ms: Optional[int] = Field(None, ge=1200, le=5000)
    vad_max_segment_ms: Optional[int] = Field(None, ge=6000, le=25000)
    speech_meter_min_db: Optional[int] = Field(None, ge=-70, le=-35)
    file_speech_rms_db: Optional[int] = Field(None, ge=-70, le=-35)
    meter_unavailable_fixed_flush_ms: Optional[int] = Field(None, ge=3000, le=12000)


class WorldlincoFaceTuningUpdate(BaseModel):
    silence_flush_ms: Optional[int] = Field(None, ge=600, le=3500)
    min_segment_ms: Optional[int] = Field(None, ge=1200, le=5000)
    max_segment_ms: Optional[int] = Field(None, ge=6000, le=25000)
    file_speech_rms_db: Optional[int] = Field(None, ge=-70, le=-35)
    meter_poll_every: Optional[int] = Field(None, ge=1, le=10)
    restart_ms: Optional[int] = Field(None, ge=100, le=1500)
    playback_cap_ms: Optional[int] = Field(None, ge=3000, le=20000)


class WorldlincoTuningUpdate(BaseModel):
    calibration_notes: Optional[str] = None
    voip: Optional[WorldlincoVoipTuningUpdate] = None
    face_conversation: Optional[WorldlincoFaceTuningUpdate] = None


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def load_worldlinco_tuning() -> Dict[str, Any]:
    defaults = deepcopy(WORLDLINGCO_TUNING_DEFAULTS)
    path = WORLDLINGCO_TUNING_PATH
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return defaults
        return _deep_merge_dict(defaults, raw)
    except (OSError, json.JSONDecodeError):
        return defaults


def save_worldlinco_tuning(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = WORLDLINGCO_TUNING_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def apply_worldlinco_tuning_update(update: WorldlincoTuningUpdate, updated_by: str = "admin") -> Dict[str, Any]:
    current = load_worldlinco_tuning()
    patch = update.model_dump(exclude_none=True)
    merged = _deep_merge_dict(current, patch)
    merged["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    merged["updated_by"] = updated_by
    return save_worldlinco_tuning(merged)


def worldlinco_tuning_public_payload() -> Dict[str, Any]:
    data = load_worldlinco_tuning()
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at"),
        "voip": data.get("voip", {}),
        "face_conversation": data.get("face_conversation", {}),
    }
