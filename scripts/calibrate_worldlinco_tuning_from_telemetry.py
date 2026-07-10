#!/usr/bin/env python3
"""Derive stable WorldLinco tuning recommendations from real-device telemetry.

Reads `.runtime/admin_worldlinco_telemetry.json` (default), computes robust metric ranges,
and emits a recommendation JSON patch that can be reviewed before applying.

This script is intentionally conservative: it does not mutate runtime tuning by itself.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_TELEMETRY_PATH = Path('.runtime/admin_worldlinco_telemetry.json')
DEFAULT_OUTPUT_PATH = Path('.runtime/worldlinco_tuning_recommendation.json')

METRIC_ALIASES: Dict[str, List[str]] = {
    'face.roundtrip_ms': ['roundtrip_ms', 'latency_ms', 'response_roundtrip_ms'],
    'face.playback_ms': ['playback_ms', 'tts_playback_ms'],
    'face.overlap_detected': ['overlap_detected', 'echo_overlap'],
    'voip.echo_blocked': ['echo_blocked', 'echo_rejected', 'echo_guard_blocked'],
    'voip.fairness_barge_in': ['fairness_barge_in', 'barge_in'],
    'voip.no_speech_prob': ['no_speech_prob', 'stt_no_speech_prob'],
    'voip.segment_rms': ['segment_rms', 'input_rms', 'bridge_input_rms'],
    'sorisae.friend_lang_prob': ['friend_lang_prob', 'lang_prob', 'detected_lang_prob'],
    'sorisae.geo_accuracy_m': ['geo_accuracy_m', 'gps_accuracy_m'],
    'pstn.stt_confidence': ['stt_confidence', 'confidence'],
    'pstn.caption_len': ['caption_len', 'subtitle_chars'],
    'chat.message_latency_ms': ['message_latency_ms', 'reply_latency_ms'],
    'chat.stream_chunk_ms': ['stream_chunk_ms', 'chunk_interval_ms'],
}


@dataclass
class MetricStats:
    count: int
    min_value: float
    max_value: float
    avg: float
    p10: float
    p50: float
    p90: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return float('nan')
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * _clamp(p, 0.0, 1.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    frac = rank - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def _collect_metric_values(items: Iterable[Dict[str, Any]], feature: str, metric: str) -> List[float]:
    values: List[float] = []
    for item in items:
        if str(item.get('feature', '')).strip() != feature:
            continue
        if str(item.get('metric', '')).strip() != metric:
            continue
        raw = item.get('value')
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(num):
            continue
        values.append(num)
    return values


def _collect_metric_values_by_aliases(items: Iterable[Dict[str, Any]], feature: str, aliases: List[str]) -> List[float]:
    values: List[float] = []
    alias_set = {alias.strip() for alias in aliases if alias.strip()}
    for item in items:
        if str(item.get('feature', '')).strip() != feature:
            continue
        if str(item.get('metric', '')).strip() not in alias_set:
            continue
        raw = item.get('value')
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(num):
            continue
        values.append(num)
    return values


def _calc_stats(values: List[float]) -> Optional[MetricStats]:
    if not values:
        return None
    return MetricStats(
        count=len(values),
        min_value=min(values),
        max_value=max(values),
        avg=mean(values),
        p10=_percentile(values, 0.10),
        p50=_percentile(values, 0.50),
        p90=_percentile(values, 0.90),
    )


def _stats_dict(stats: Optional[MetricStats]) -> Optional[Dict[str, Any]]:
    if not stats:
        return None
    return {
        'count': stats.count,
        'min': round(stats.min_value, 3),
        'max': round(stats.max_value, 3),
        'mean': round(stats.avg, 3),
        'p10': round(stats.p10, 3),
        'p50': round(stats.p50, 3),
        'p90': round(stats.p90, 3),
    }


def _compute_recommendation(items: List[Dict[str, Any]], min_samples: int) -> Dict[str, Any]:
    face_roundtrip = _calc_stats(_collect_metric_values_by_aliases(items, 'face_conversation', METRIC_ALIASES['face.roundtrip_ms']))
    face_playback = _calc_stats(_collect_metric_values_by_aliases(items, 'face_conversation', METRIC_ALIASES['face.playback_ms']))
    face_overlap = _calc_stats(_collect_metric_values_by_aliases(items, 'face_conversation', METRIC_ALIASES['face.overlap_detected']))

    voip_echo = _calc_stats(_collect_metric_values_by_aliases(items, 'voip', METRIC_ALIASES['voip.echo_blocked']))
    voip_fairness = _calc_stats(_collect_metric_values_by_aliases(items, 'voip', METRIC_ALIASES['voip.fairness_barge_in']))
    voip_no_speech_prob = _calc_stats(_collect_metric_values_by_aliases(items, 'voip', METRIC_ALIASES['voip.no_speech_prob']))
    voip_segment_rms = _calc_stats(_collect_metric_values_by_aliases(items, 'voip', METRIC_ALIASES['voip.segment_rms']))

    sorisae_friend_lang_prob = _calc_stats(_collect_metric_values_by_aliases(items, 'sorisae_ai', METRIC_ALIASES['sorisae.friend_lang_prob']))
    sorisae_geo_accuracy_m = _calc_stats(_collect_metric_values_by_aliases(items, 'sorisae_ai', METRIC_ALIASES['sorisae.geo_accuracy_m']))

    pstn_stt_confidence = _calc_stats(_collect_metric_values_by_aliases(items, 'pstn_assist', METRIC_ALIASES['pstn.stt_confidence']))
    pstn_caption_len = _calc_stats(_collect_metric_values_by_aliases(items, 'pstn_assist', METRIC_ALIASES['pstn.caption_len']))

    chat_message_latency = _calc_stats(_collect_metric_values_by_aliases(items, 'chat', METRIC_ALIASES['chat.message_latency_ms']))
    chat_stream_chunk = _calc_stats(_collect_metric_values_by_aliases(items, 'chat', METRIC_ALIASES['chat.stream_chunk_ms']))

    face_turns = face_roundtrip.count if face_roundtrip else 0
    voip_turns = max((voip_echo.count if voip_echo else 0), (voip_fairness.count if voip_fairness else 0))

    face_overlap_rate = 0.0
    if face_overlap and face_overlap.count > 0:
        face_overlap_rate = face_overlap.avg

    voip_echo_rate = 0.0
    if voip_echo and voip_echo.count > 0:
        voip_echo_rate = voip_echo.avg

    voip_fairness_rate = 0.0
    if voip_fairness and voip_fairness.count > 0:
        voip_fairness_rate = voip_fairness.avg

    # Conservative synthesis using robust quantiles from real-device data.
    face_restart_ms = 240
    if face_roundtrip and face_roundtrip.count >= min_samples:
        candidate = 160 + ((face_roundtrip.p90 - 2200.0) * 0.06) + (face_overlap_rate * 260.0)
        face_restart_ms = int(round(_clamp(candidate, 120.0, 1200.0)))

    face_playback_cap_ms = 50000
    if face_playback and face_playback.count >= min_samples:
        # p90 playback plus a safety margin; upper-bounded to avoid unbounded stalls.
        candidate = max(6000.0, (face_playback.p90 * 1.35) + 1200.0)
        face_playback_cap_ms = int(round(_clamp(candidate, 6000.0, 90000.0)))

    voip_remote_listen_hold_ms = 2600
    voip_post_playback_guard_ms = 550
    voip_fairness_barge_in_ms = 7000
    if voip_turns >= min_samples:
        voip_remote_listen_hold_ms = int(round(_clamp(
            2600.0 + (voip_echo_rate * 800.0) - (voip_fairness_rate * 500.0),
            1200.0,
            4500.0,
        )))
        voip_post_playback_guard_ms = int(round(_clamp(
            550.0 + (voip_echo_rate * 220.0),
            250.0,
            1400.0,
        )))
        voip_fairness_barge_in_ms = int(round(_clamp(
            7000.0 - (voip_fairness_rate * 1400.0),
            2500.0,
            9000.0,
        )))

    confidence = 'low'
    if face_turns >= min_samples and voip_turns >= min_samples:
        confidence = 'high'
    elif face_turns >= min_samples or voip_turns >= min_samples:
        confidence = 'medium'

    warnings: List[str] = []
    if not items:
        warnings.append('telemetry items are empty; recommendations are baseline-safe defaults')
    if face_turns < min_samples:
        warnings.append('face sample count is below min_samples')
    if voip_turns < min_samples:
        warnings.append('voip sample count is below min_samples')

    voip_bridge_max_no_speech_prob = 0.80
    if voip_no_speech_prob and voip_no_speech_prob.count >= min_samples:
        voip_bridge_max_no_speech_prob = round(_clamp(voip_no_speech_prob.p90 + 0.03, 0.40, 0.95), 3)

    voip_bridge_min_segment_rms_for_stt = 500
    if voip_segment_rms and voip_segment_rms.count >= min_samples:
        voip_bridge_min_segment_rms_for_stt = int(round(_clamp(voip_segment_rms.p10 * 0.92, 180.0, 1200.0)))

    sorisae_friend_min_lang_prob = 0.65
    if sorisae_friend_lang_prob and sorisae_friend_lang_prob.count >= min_samples:
        sorisae_friend_min_lang_prob = round(_clamp(max(0.55, sorisae_friend_lang_prob.p10), 0.50, 0.90), 3)

    sorisae_geo_accuracy_max_m = 2500
    if sorisae_geo_accuracy_m and sorisae_geo_accuracy_m.count >= min_samples:
        sorisae_geo_accuracy_max_m = int(round(_clamp(sorisae_geo_accuracy_m.p90, 300.0, 10000.0)))

    pstn_stt_conf_floor = 0.58
    if pstn_stt_confidence and pstn_stt_confidence.count >= min_samples:
        pstn_stt_conf_floor = round(_clamp(pstn_stt_confidence.p10, 0.45, 0.90), 3)

    pstn_max_caption_chars = 84
    if pstn_caption_len and pstn_caption_len.count >= min_samples:
        pstn_max_caption_chars = int(round(_clamp(max(60.0, pstn_caption_len.p90), 40.0, 160.0)))

    chat_message_latency_budget_ms = 6000
    if chat_message_latency and chat_message_latency.count >= min_samples:
        chat_message_latency_budget_ms = int(round(_clamp(chat_message_latency.p90 * 1.08, 1200.0, 12000.0)))

    chat_stream_chunk_budget_ms = 180
    if chat_stream_chunk and chat_stream_chunk.count >= min_samples:
        chat_stream_chunk_budget_ms = int(round(_clamp(chat_stream_chunk.p90 * 1.05, 80.0, 1200.0)))

    return {
        'meta': {
            'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            'min_samples_required': min_samples,
            'telemetry_item_count': len(items),
            'face_turn_samples': face_turns,
            'voip_turn_samples': voip_turns,
            'confidence': confidence,
            'warnings': warnings,
        },
        'ranges': {
            'face_conversation.roundtrip_ms': _stats_dict(face_roundtrip),
            'face_conversation.playback_ms': _stats_dict(face_playback),
            'face_conversation.overlap_detected': _stats_dict(face_overlap),
            'voip.echo_blocked': _stats_dict(voip_echo),
            'voip.fairness_barge_in': _stats_dict(voip_fairness),
            'voip.no_speech_prob': _stats_dict(voip_no_speech_prob),
            'voip.segment_rms': _stats_dict(voip_segment_rms),
            'sorisae_ai.friend_lang_prob': _stats_dict(sorisae_friend_lang_prob),
            'sorisae_ai.geo_accuracy_m': _stats_dict(sorisae_geo_accuracy_m),
            'pstn_assist.stt_confidence': _stats_dict(pstn_stt_confidence),
            'pstn_assist.caption_len': _stats_dict(pstn_caption_len),
            'chat.message_latency_ms': _stats_dict(chat_message_latency),
            'chat.stream_chunk_ms': _stats_dict(chat_stream_chunk),
        },
        'recommended_patch': {
            'calibration_notes': '[auto-calibrator] real-device telemetry quantile calibration',
            'face_conversation': {
                'restart_ms': face_restart_ms,
                'playback_cap_ms': face_playback_cap_ms,
            },
            'voip': {
                'remote_listen_hold_ms': voip_remote_listen_hold_ms,
                'post_playback_guard_ms': voip_post_playback_guard_ms,
                'fairness_barge_in_ms': voip_fairness_barge_in_ms,
            },
            'voip_bridge': {
                'min_segment_rms_for_stt': voip_bridge_min_segment_rms_for_stt,
                'max_no_speech_prob': voip_bridge_max_no_speech_prob,
            },
            'sorisae_ai': {
                'friend_min_lang_prob': sorisae_friend_min_lang_prob,
                'geo_accuracy_max_m': sorisae_geo_accuracy_max_m,
            },
            'pstn_assist': {
                'stt_confidence_floor': pstn_stt_conf_floor,
                'max_caption_chars': pstn_max_caption_chars,
            },
            'chat': {
                'message_latency_budget_ms': chat_message_latency_budget_ms,
                'stream_chunk_budget_ms': chat_stream_chunk_budget_ms,
            },
        },
    }


def _load_items(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    items = payload.get('items') if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Calibrate WorldLinco tuning from real-device telemetry.')
    parser.add_argument('--telemetry-file', type=Path, default=DEFAULT_TELEMETRY_PATH, help='Path to telemetry JSON payload file.')
    parser.add_argument('--output-file', type=Path, default=DEFAULT_OUTPUT_PATH, help='Path to write recommendation JSON.')
    parser.add_argument('--min-samples', type=int, default=20, help='Minimum sample count required for high-confidence tuning.')
    parser.add_argument('--stdout', action='store_true', help='Print recommendation JSON to stdout.')
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    telemetry_path: Path = args.telemetry_file
    if not telemetry_path.is_file():
        raise SystemExit(f'Telemetry file not found: {telemetry_path}')

    items = _load_items(telemetry_path)
    recommendation = _compute_recommendation(items, min_samples=max(1, int(args.min_samples)))

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding='utf-8')

    if args.stdout:
        print(json.dumps(recommendation, ensure_ascii=False, indent=2))
    else:
        print(f'Wrote recommendation: {args.output_file}')
        print(f"Confidence: {recommendation['meta']['confidence']}")
        print(f"Face samples: {recommendation['meta']['face_turn_samples']}, VoIP samples: {recommendation['meta']['voip_turn_samples']}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
