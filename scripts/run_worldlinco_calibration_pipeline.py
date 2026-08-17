#!/usr/bin/env python3
"""Run worldlinco telemetry calibration pipeline end-to-end.

Pipeline:
1) collect telemetry payload
2) calibrate recommendation JSON
3) optionally apply recommendation to tuning config
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List

from collect_worldlinco_telemetry import _default_payload, _fetch_from_api
from calibrate_worldlinco_tuning_from_telemetry import _compute_recommendation, _load_items
from apply_worldlinco_tuning_recommendation import _deep_merge
from datetime import datetime, timezone


DEFAULT_TOKEN_FILE = Path('.runtime/secrets/admin_bearer_token.txt')


FEATURE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    'sorisae': {
        'display_name': '소리새',
        'metrics': [
            ('sorisae_ai', ['friend_lang_prob', 'lang_prob', 'detected_lang_prob']),
            ('sorisae_ai', ['geo_accuracy_m', 'gps_accuracy_m']),
        ],
    },
    'face': {
        'display_name': '대면',
        'metrics': [
            ('face_conversation', ['roundtrip_ms', 'latency_ms', 'response_roundtrip_ms']),
            ('face_conversation', ['playback_ms', 'tts_playback_ms']),
            ('face_conversation', ['overlap_detected', 'echo_overlap']),
        ],
    },
    'voip': {
        'display_name': 'VoIP',
        'metrics': [
            ('voip', ['echo_blocked', 'echo_rejected', 'echo_guard_blocked']),
            ('voip', ['fairness_barge_in', 'barge_in']),
            ('voip', ['no_speech_prob', 'stt_no_speech_prob']),
            ('voip', ['segment_rms', 'input_rms', 'bridge_input_rms']),
        ],
    },
    'pstn': {
        'display_name': 'PSTN',
        'metrics': [
            ('pstn_assist', ['stt_confidence', 'confidence']),
            ('pstn_assist', ['caption_len', 'subtitle_chars']),
        ],
    },
    'chat': {
        'display_name': '채팅',
        'metrics': [
            ('chat', ['message_latency_ms', 'reply_latency_ms']),
            ('chat', ['stream_chunk_ms', 'chunk_interval_ms']),
        ],
    },
}

TEST_ACTIONS: Dict[str, Dict[str, Any]] = {
    'sorisae_ai.friend_lang_prob': {
        'test': '소리새 짧은+일반 발화 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'sorisae_ai.geo_accuracy_m': {
        'test': '소리새 위치 기반 질의 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'face_conversation.roundtrip_ms': {
        'test': '대면 통역 일반 왕복 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'face_conversation.playback_ms': {
        'test': '대면 통역 TTS 포함 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'face_conversation.overlap_detected': {
        'test': '대면 오버랩 유도 1턴(재생 직후 발화)',
        'gain_per_run': 1,
        'priority_boost': 1,
    },
    'voip.echo_blocked': {
        'test': 'VoIP 통화 에코 억제 검증 1턴',
        'gain_per_run': 1,
        'priority_boost': 1,
    },
    'voip.fairness_barge_in': {
        'test': 'VoIP barge-in 유도 1턴',
        'gain_per_run': 1,
        'priority_boost': 1,
    },
    'voip.no_speech_prob': {
        'test': 'VoIP 무음 구간 1회 삽입',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'voip.segment_rms': {
        'test': 'VoIP 정상 발화 구간 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'pstn_assist.stt_confidence': {
        'test': 'PSTN 보조통역 자막 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'pstn_assist.caption_len': {
        'test': 'PSTN 장문 자막 1턴',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'chat.message_latency_ms': {
        'test': '채팅 일반 질의 1회',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
    'chat.stream_chunk_ms': {
        'test': '채팅 장문/스트림 응답 1회',
        'gain_per_run': 1,
        'priority_boost': 0,
    },
}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _load_json(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise RuntimeError(f'JSON object expected: {path}')
    return raw


def _count_metric_samples(items: List[Dict[str, Any]], feature: str, aliases: List[str]) -> int:
    alias_set = {alias.strip() for alias in aliases if alias.strip()}
    count = 0
    for item in items:
        if str(item.get('feature', '')).strip() != feature:
            continue
        if str(item.get('metric', '')).strip() not in alias_set:
            continue
        value = item.get('value')
        if isinstance(value, (int, float)):
            count += 1
            continue
        try:
            float(value)
            count += 1
        except (TypeError, ValueError):
            continue
    return count


def _build_sample_coverage_report(items: List[Dict[str, Any]], min_samples: int) -> Dict[str, Any]:
    feature_reports: List[Dict[str, Any]] = []
    all_satisfied = True

    for _, requirement in FEATURE_REQUIREMENTS.items():
        display_name = str(requirement['display_name'])
        metric_defs = requirement['metrics']
        metric_reports: List[Dict[str, Any]] = []
        min_metric_count = 10**9

        for metric_feature, aliases in metric_defs:
            count = _count_metric_samples(items, metric_feature, aliases)
            min_metric_count = min(min_metric_count, count)
            shortage = max(0, min_samples - count)
            metric_reports.append({
                'feature': metric_feature,
                'aliases': aliases,
                'primary_metric': aliases[0] if aliases else 'metric',
                'count': count,
                'shortage': shortage,
                'satisfied': shortage == 0,
            })

        if min_metric_count == 10**9:
            min_metric_count = 0
        feature_shortage = max(0, min_samples - min_metric_count)
        satisfied = feature_shortage == 0
        if not satisfied:
            all_satisfied = False

        feature_reports.append({
            'name': display_name,
            'min_metric_count': min_metric_count,
            'required_min_samples': min_samples,
            'shortage': feature_shortage,
            'satisfied': satisfied,
            'metrics': metric_reports,
        })

    overall_shortage = sum(report['shortage'] for report in feature_reports)
    return {
        'required_min_samples': min_samples,
        'all_features_satisfied': all_satisfied,
        'overall_shortage': overall_shortage,
        'features': feature_reports,
    }


def _build_test_priority_plan(coverage_report: Dict[str, Any]) -> Dict[str, Any]:
    feature_plans: List[Dict[str, Any]] = []
    for feature in coverage_report.get('features', []):
        if feature.get('satisfied'):
            continue
        tasks: List[Dict[str, Any]] = []
        total_runs = 0
        for metric in feature.get('metrics', []):
            if metric.get('satisfied'):
                continue
            metric_key = f"{metric.get('feature')}.{metric.get('primary_metric')}"
            action = TEST_ACTIONS.get(metric_key, {
                'test': f"{metric_key} 샘플 수집",
                'gain_per_run': 1,
                'priority_boost': 0,
            })
            gain_per_run = max(1, int(action.get('gain_per_run', 1)))
            shortage = int(metric.get('shortage') or 0)
            recommended_runs = int(math.ceil(shortage / gain_per_run))
            total_runs += recommended_runs
            tasks.append({
                'metric': metric_key,
                'test': action.get('test'),
                'shortage': shortage,
                'gain_per_run': gain_per_run,
                'recommended_runs': recommended_runs,
                'priority_score': shortage + int(action.get('priority_boost', 0)),
            })
        tasks.sort(key=lambda item: (item['priority_score'], item['shortage']), reverse=True)
        feature_plans.append({
            'feature_name': feature.get('name'),
            'feature_shortage': int(feature.get('shortage') or 0),
            'recommended_total_runs': total_runs,
            'tasks': tasks,
        })

    feature_plans.sort(key=lambda item: (item['feature_shortage'], item['recommended_total_runs']), reverse=True)
    return {
        'has_shortage': len(feature_plans) > 0,
        'ordered_features': feature_plans,
    }


def _print_sample_coverage_report(report: Dict[str, Any]) -> None:
    print('[SAMPLE_CHECK] min-samples:', report['required_min_samples'])
    print('[SAMPLE_CHECK] all_features_satisfied:', report['all_features_satisfied'])

    for feature in report['features']:
        status = 'OK' if feature['satisfied'] else 'LOW'
        print(
            f"[SAMPLE_CHECK] {feature['name']}: {status} "
            f"(min_metric_count={feature['min_metric_count']}, shortage={feature['shortage']})"
        )
        if feature['satisfied']:
            continue
        for metric in feature['metrics']:
            if metric['satisfied']:
                continue
            primary_metric = metric['aliases'][0] if metric['aliases'] else 'metric'
            print(
                f"  - need +{metric['shortage']} samples for {metric['feature']}.{primary_metric} "
                f"(current={metric['count']})"
            )

    if not report['all_features_satisfied']:
        print('[SAMPLE_CHECK] ACTION: collect additional real-device samples for LOW features and rerun.')


def _print_test_priority_plan(plan: Dict[str, Any]) -> None:
    if not plan.get('has_shortage'):
        print('[TEST_PLAN] 모든 기능 샘플이 min-samples 이상입니다. 추가 우선순위 테스트가 필요하지 않습니다.')
        return
    print('[TEST_PLAN] 부족 샘플 기준 기능별 테스트 우선순위:')
    for index, feature in enumerate(plan.get('ordered_features', []), start=1):
        print(
            f"[TEST_PLAN] {index}. {feature.get('feature_name')} "
            f"(shortage={feature.get('feature_shortage')}, recommended_total_runs={feature.get('recommended_total_runs')})"
        )
        for task in feature.get('tasks', []):
            print(
                f"  - {task.get('test')} | metric={task.get('metric')} | "
                f"need +{task.get('shortage')} => run x{task.get('recommended_runs')}"
            )


def _emit_test_priority_csv(plan: Dict[str, Any], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w', encoding='utf-8-sig', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow([
            'priority_rank',
            'feature_name',
            'feature_shortage',
            'feature_recommended_total_runs',
            'metric',
            'test',
            'metric_shortage',
            'gain_per_run',
            'recommended_runs',
            'priority_score',
            'check',
            'evidence',
            'notes',
        ])

        if not plan.get('has_shortage'):
            writer.writerow([
                1,
                'all-features',
                0,
                0,
                '',
                'No additional run needed',
                0,
                1,
                0,
                0,
                '[x]',
                '',
                'All features already satisfy min-samples',
            ])
            return

        for index, feature in enumerate(plan.get('ordered_features', []), start=1):
            tasks = feature.get('tasks', [])
            if not tasks:
                writer.writerow([
                    index,
                    feature.get('feature_name'),
                    feature.get('feature_shortage'),
                    feature.get('recommended_total_runs'),
                    '',
                    'No actionable task',
                    0,
                    1,
                    0,
                    0,
                    '[ ]',
                    '',
                    '',
                ])
                continue
            for task in tasks:
                writer.writerow([
                    index,
                    feature.get('feature_name'),
                    feature.get('feature_shortage'),
                    feature.get('recommended_total_runs'),
                    task.get('metric'),
                    task.get('test'),
                    task.get('shortage'),
                    task.get('gain_per_run'),
                    task.get('recommended_runs'),
                    task.get('priority_score'),
                    '[ ]',
                    '',
                    '',
                ])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run worldlinco calibration pipeline (collect -> calibrate -> apply).')
    parser.add_argument('--api-base', type=str, default='')
    parser.add_argument('--token', type=str, default='')
    parser.add_argument('--token-file', type=Path, default=DEFAULT_TOKEN_FILE, help='Bearer token file path (fallback).')
    parser.add_argument('--endpoint', type=str, default='/api/admin/worldlinco/telemetry')
    parser.add_argument('--timeout-sec', type=int, default=12)
    parser.add_argument('--telemetry-file', type=Path, default=Path('.runtime/admin_worldlinco_telemetry.json'))
    parser.add_argument('--recommendation-file', type=Path, default=Path('.runtime/worldlinco_tuning_recommendation.json'))
    parser.add_argument('--tuning-file', type=Path, default=Path('knowledge/worldlinco_tuning_config.json'))
    parser.add_argument('--min-samples', type=int, default=20)
    parser.add_argument('--updated-by', type=str, default='auto-calibrator')
    parser.add_argument('--backup-dir', type=Path, default=Path('.runtime/backups'))
    parser.add_argument('--skip-apply', action='store_true')
    parser.add_argument('--init-empty', action='store_true')
    parser.add_argument('--emit-priority-csv', action='store_true', help='Emit test_priority_plan as CSV checklist.')
    parser.add_argument('--priority-csv-file', type=Path, default=Path('.runtime/worldlinco_test_priority_plan.csv'))
    parser.add_argument('--stdout', action='store_true')
    return parser


def _resolve_token(args: argparse.Namespace) -> str:
    direct = str(args.token or '').strip()
    if direct:
        return direct

    env_token = str(os.getenv('ADMIN_BEARER_TOKEN', '')).strip()
    if env_token:
        return env_token

    token_file = args.token_file
    if token_file and Path(token_file).is_file():
        try:
            file_token = Path(token_file).read_text(encoding='utf-8').strip()
            if file_token:
                return file_token
        except OSError:
            pass

    return ''


def _collect(args: argparse.Namespace) -> Dict[str, Any]:
    resolved_token = _resolve_token(args)
    if args.api_base and resolved_token:
        payload = _fetch_from_api(args.api_base, args.endpoint, resolved_token, max(3, int(args.timeout_sec)))
        payload['updated_by'] = str(payload.get('updated_by') or 'collector:api')
        _write_json(args.telemetry_file, payload)
        return payload

    if args.init_empty:
        payload = _default_payload(note='initialized by run_worldlinco_calibration_pipeline')
        _write_json(args.telemetry_file, payload)
        return payload

    if args.telemetry_file.is_file():
        return _load_json(args.telemetry_file)

    raise RuntimeError('No telemetry source available. Provide API token, existing telemetry file, or --init-empty.')


def _apply(args: argparse.Namespace, recommendation: Dict[str, Any]) -> None:
    patch = recommendation.get('recommended_patch')
    if not isinstance(patch, dict) or not patch:
        raise RuntimeError('recommended_patch missing in recommendation.')

    if not args.tuning_file.is_file():
        raise RuntimeError(f'Tuning file not found: {args.tuning_file}')

    current = _load_json(args.tuning_file)
    merged = _deep_merge(current, patch)
    merged['updated_at'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    merged['updated_by'] = args.updated_by

    meta = recommendation.get('meta') if isinstance(recommendation.get('meta'), dict) else {}
    note = str(patch.get('calibration_notes') or '').strip()
    if note:
        merged['calibration_notes'] = (
            f"{note} | confidence={meta.get('confidence', 'unknown')} | telemetry_items={meta.get('telemetry_item_count', 0)}"
        )

    args.backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = args.backup_dir / f"{args.tuning_file.stem}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak.json"
    _write_json(backup_file, current)
    _write_json(args.tuning_file, merged)

    print(f'Backup written: {backup_file}')
    print(f'Tuning updated: {args.tuning_file}')


def main() -> int:
    args = _build_parser().parse_args()

    collected = _collect(args)
    items = _load_items(args.telemetry_file)
    recommendation = _compute_recommendation(items, min_samples=max(1, int(args.min_samples)))
    coverage_report = _build_sample_coverage_report(items, min_samples=max(1, int(args.min_samples)))
    test_priority_plan = _build_test_priority_plan(coverage_report)
    recommendation['sample_coverage'] = coverage_report
    recommendation['test_priority_plan'] = test_priority_plan
    _write_json(args.recommendation_file, recommendation)

    print(f"Telemetry file: {args.telemetry_file} (items={len(collected.get('items') or [])})")
    print(f"Recommendation file: {args.recommendation_file}")
    print(f"Confidence: {recommendation.get('meta', {}).get('confidence')}")
    _print_sample_coverage_report(coverage_report)
    _print_test_priority_plan(test_priority_plan)

    if args.emit_priority_csv:
        _emit_test_priority_csv(test_priority_plan, args.priority_csv_file)
        print(f"[TEST_PLAN] CSV emitted: {args.priority_csv_file}")

    if args.stdout:
        print(json.dumps(recommendation, ensure_ascii=False, indent=2))

    if args.skip_apply:
        print('Apply skipped (--skip-apply).')
        return 0

    _apply(args, recommendation)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
