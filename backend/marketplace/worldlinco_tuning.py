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
    "version": 6,
    "updated_at": "2026-07-05T06:55:00Z",
    "updated_by": "locked-baseline-v6",
    "calibration_notes": "[v6 locked baseline] 단말 비교 실험 정합성 확보용 worldlinco 임계값 고정.",
    # NOTE: 이 fallback 기본값은 런타임 SSOT(knowledge/worldlinco_tuning_config.json)와
    # 정합 유지한다. 원격 fetch 실패(LTE 단절 등) 시에도 과거 14s/12s 과배칭으로 회귀하지
    # 않도록 calibrated 값과 동일하게 둔다.
    "voip": {
        "silero_silence_ms": 1000,
        "silero_speech_ms": 120,
        "silero_min_segment_ms": 3000,
        "silero_min_speech_span_ms": 1700,
        "silero_safety_cap_ms": 7000,
        "silero_post_flush_cooldown_ms": 1000,
        "remote_echo_guard_ms": 4800,
        "speaker_echo_guard_ms": 5800,
        "remote_listen_hold_ms": 2600,
        "post_playback_guard_ms": 550,
        "vad_silence_flush_ms": 1000,
        "vad_min_segment_ms": 3000,
        "vad_max_segment_ms": 7000,
        "speech_meter_min_db": -52,
        "file_speech_rms_db": -52,
        "meter_unavailable_fixed_flush_ms": 4000,
    },
    "face_conversation": {
        "silence_flush_ms": 1200,
        "min_segment_ms": 2200,
        "max_segment_ms": 11000,
        "file_speech_rms_db": -50,
        "meter_poll_every": 2,
        "restart_ms": 290,
        "playback_cap_ms": 45000,
        "playback_drain_ms": 1300,
        "tts_rate": 0.95,
    },
    # 서버 미디어 브리지(MCU) 통역 — 서버측 endpointer/볼륨/환각필터. media_bridge.py 가
    # 런타임(TTL 캐시)으로 읽어 통화 중에도 ~2초 내 반영된다(재시작·재빌드 불필요).
    # 값은 media_bridge.py 의 코드 기본값(_f env 기본)과 정합 유지.
    "voip_bridge": {
        "silence_gap_ms": 700,
        "min_speech_ms": 600,
        "max_speech_ms": 8000,
        "rms_gate": 580,
        "min_segment_rms_for_stt": 500,
        "asr_norm_floor_rms": 500,
        "drop_no_speech_prob": 0.82,
        "tts_guard_tail_ms": 1200,
        "live_echo_guard_ms": 700,
        "live_echo_forward_barge_in_rms": 1400,
        "live_echo_return_window_ms": 1200,
        "live_echo_return_barge_in_rms": 2400,
        "tts_target_rms": 0.28,
        "tts_target_peak": 0.99,
        "tts_max_gain": 16.0,
        "min_avg_logprob": -1.0,
        "max_no_speech_prob": 0.80,
    },
    # 소리새 AI 친구 모드(여행 컨시어지 대화) — STT 언어확률·위치정확도 임계.
    # voice_gateway._sorisae_cfg 가 런타임(TTL 캐시)으로 읽어 대화 중에도 ~2초 내 반영.
    "sorisae_ai": {
        # 감지 언어 확률이 이 미만이면 detected_language 를 무시하고 프로필 언어로 답한다(외국어 오답 방지).
        "friend_min_lang_prob": 0.65,
        # GPS 정확도(m)가 이보다 나쁘면 좌표를 '근처' 그라운딩에 신뢰하지 않는다(엉뚱한 동네 안내 방지).
        "geo_accuracy_max_m": 2500,
        "geo_accuracy_nearby_max_m": 600,
        "geo_accuracy_overview_max_m": 5000,
        "friend_timeout_sec": 20,
        "friend_reply_max_tokens": 400,
        "friend_realtime_max_tokens": 320,
        "tourism_guide_tier": 3,
        "tts_rate": 1.0,
    },
    # 일반 통역 전화(PSTN assist) — 일반전화통역 턴 전환/자막 커밋/호 연결 안정화.
    "pstn_assist": {
        "call_connect_timeout_ms": 12000,
        "turn_pause_ms": 1200,
        "subtitle_commit_delay_ms": 500,
        "stt_confidence_floor": 0.58,
        "max_caption_chars": 84,
    },
    # 채팅 — 번역 채팅 응답/스트림 체감속도/타이핑 지연/요약 턴 기준.
    "chat": {
        "message_latency_budget_ms": 1600,
        "stream_chunk_budget_ms": 350,
        "translation_cache_ttl_sec": 180,
        "typing_indicator_delay_ms": 280,
        "auto_summary_turn_threshold": 0,
    },
}


class WorldlincoVoipTuningUpdate(BaseModel):
    silero_silence_ms: Optional[int] = Field(None, ge=500, le=2500)
    silero_speech_ms: Optional[int] = Field(None, ge=80, le=400)
    silero_min_segment_ms: Optional[int] = Field(None, ge=1500, le=6000)
    silero_min_speech_span_ms: Optional[int] = Field(None, ge=800, le=5000)
    silero_safety_cap_ms: Optional[int] = Field(None, ge=7000, le=30000)
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
    playback_cap_ms: Optional[int] = Field(None, ge=3000, le=90_000)
    playback_drain_ms: Optional[int] = Field(None, ge=200, le=5000)
    tts_rate: Optional[float] = Field(None, ge=0.5, le=2.0)


class WorldlincoVoipBridgeTuningUpdate(BaseModel):
    # 대화 템포(지연).
    silence_gap_ms: Optional[int] = Field(None, ge=300, le=1500)
    min_speech_ms: Optional[int] = Field(None, ge=200, le=1500)
    max_speech_ms: Optional[int] = Field(None, ge=2000, le=15000)
    rms_gate: Optional[int] = Field(None, ge=100, le=900)
    tts_guard_tail_ms: Optional[int] = Field(None, ge=100, le=2000)
    # 볼륨(번역 음성 라우드니스).
    tts_target_rms: Optional[float] = Field(None, ge=0.08, le=0.70)
    tts_target_peak: Optional[float] = Field(None, ge=0.50, le=1.0)
    tts_max_gain: Optional[float] = Field(None, ge=1.0, le=48.0)
    # 환각 필터.
    min_avg_logprob: Optional[float] = Field(None, ge=-3.0, le=-0.2)
    max_no_speech_prob: Optional[float] = Field(None, ge=0.40, le=0.99)


class WorldlincoSorisaeAiTuningUpdate(BaseModel):
    # 친구 모드 STT 언어확률 임계(B-2) — 낮을수록 감지 언어를 더 신뢰(오감지 위험↑).
    friend_min_lang_prob: Optional[float] = Field(None, ge=0.0, le=1.0)
    # GPS 정확도 신뢰 상한(m, G-3) — 이보다 거친 좌표는 '근처' 그라운딩에서 제외.
    geo_accuracy_max_m: Optional[int] = Field(None, ge=200, le=50000)
    geo_accuracy_nearby_max_m: Optional[int] = Field(None, ge=200, le=10000)
    geo_accuracy_overview_max_m: Optional[int] = Field(None, ge=500, le=50000)
    friend_timeout_sec: Optional[int] = Field(None, ge=5, le=60)
    friend_reply_max_tokens: Optional[int] = Field(None, ge=100, le=1000)
    friend_realtime_max_tokens: Optional[int] = Field(None, ge=50, le=500)
    tourism_guide_tier: Optional[int] = Field(None, ge=1, le=5)
    tts_rate: Optional[float] = Field(None, ge=0.5, le=2.0)


class WorldlincoPstnAssistTuningUpdate(BaseModel):
    call_connect_timeout_ms: Optional[int] = Field(None, ge=3000, le=30000)
    turn_pause_ms: Optional[int] = Field(None, ge=300, le=5000)
    subtitle_commit_delay_ms: Optional[int] = Field(None, ge=50, le=3000)
    stt_confidence_floor: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_caption_chars: Optional[int] = Field(None, ge=20, le=240)


class WorldlincoChatTuningUpdate(BaseModel):
    message_latency_budget_ms: Optional[int] = Field(None, ge=200, le=10000)
    stream_chunk_budget_ms: Optional[int] = Field(None, ge=50, le=3000)
    translation_cache_ttl_sec: Optional[int] = Field(None, ge=0, le=86400)
    typing_indicator_delay_ms: Optional[int] = Field(None, ge=0, le=3000)
    auto_summary_turn_threshold: Optional[int] = Field(None, ge=0, le=200)


class WorldlincoTuningUpdate(BaseModel):
    calibration_notes: Optional[str] = None
    voip: Optional[WorldlincoVoipTuningUpdate] = None
    face_conversation: Optional[WorldlincoFaceTuningUpdate] = None
    voip_bridge: Optional[WorldlincoVoipBridgeTuningUpdate] = None
    sorisae_ai: Optional[WorldlincoSorisaeAiTuningUpdate] = None
    pstn_assist: Optional[WorldlincoPstnAssistTuningUpdate] = None
    chat: Optional[WorldlincoChatTuningUpdate] = None


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
        "voip_bridge": data.get("voip_bridge", {}),
        "sorisae_ai": data.get("sorisae_ai", {}),
        "pstn_assist": data.get("pstn_assist", {}),
        "chat": data.get("chat", {}),
    }


def worldlinco_tuning_admin_payload() -> Dict[str, Any]:
    data = load_worldlinco_tuning()
    payload = dict(data)
    raw_fixed_baseline = data.get("fixed_baseline")
    fixed_baseline_payload: Dict[str, Any] = raw_fixed_baseline if isinstance(raw_fixed_baseline, dict) else {}
    sorisae_fixed_baseline = fixed_baseline_payload.get("sorisae_ai")
    payload["fixed_baseline"] = {
        "sorisae_ai": deepcopy(
            (sorisae_fixed_baseline if isinstance(sorisae_fixed_baseline, dict) else None)
            or WORLDLINGCO_TUNING_DEFAULTS.get("sorisae_ai")
            or {}
        ),
    }
    return payload
