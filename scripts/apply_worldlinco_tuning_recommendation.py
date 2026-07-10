#!/usr/bin/env python3
"""Apply a worldlinco tuning recommendation patch to worldlinco_tuning_config.json.

The script deep-merges `recommended_patch` from a recommendation JSON and writes
an updated tuning config with backup support.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


DEFAULT_RECOMMENDATION_FILE = Path('.runtime/worldlinco_tuning_recommendation.json')
DEFAULT_TUNING_FILE = Path('knowledge/worldlinco_tuning_config.json')


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_json(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise RuntimeError(f'JSON object expected: {path}')
    return raw


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Apply worldlinco tuning recommendation patch.')
    parser.add_argument('--recommendation-file', type=Path, default=DEFAULT_RECOMMENDATION_FILE)
    parser.add_argument('--tuning-file', type=Path, default=DEFAULT_TUNING_FILE)
    parser.add_argument('--updated-by', type=str, default='auto-calibrator')
    parser.add_argument('--backup-dir', type=Path, default=Path('.runtime/backups'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--stdout', action='store_true')
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if not args.recommendation_file.is_file():
        raise SystemExit(f'Recommendation file not found: {args.recommendation_file}')
    if not args.tuning_file.is_file():
        raise SystemExit(f'Tuning file not found: {args.tuning_file}')

    recommendation = _load_json(args.recommendation_file)
    patch = recommendation.get('recommended_patch')
    if not isinstance(patch, dict) or not patch:
        raise SystemExit('recommended_patch is missing or empty.')

    current = _load_json(args.tuning_file)
    merged = _deep_merge(current, patch)
    merged['updated_at'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    merged['updated_by'] = args.updated_by

    recommendation_meta = recommendation.get('meta') if isinstance(recommendation.get('meta'), dict) else {}
    calibration_note_prefix = str(patch.get('calibration_notes') or '').strip()
    if calibration_note_prefix:
        confidence = str(recommendation_meta.get('confidence') or 'unknown')
        sample_count = int(recommendation_meta.get('telemetry_item_count') or 0)
        merged['calibration_notes'] = f"{calibration_note_prefix} | confidence={confidence} | telemetry_items={sample_count}"

    if args.stdout:
        print(json.dumps(merged, ensure_ascii=False, indent=2))

    if args.dry_run:
        print('Dry-run: no file write performed.')
        return 0

    args.backup_dir.mkdir(parents=True, exist_ok=True)
    backup_name = f"{args.tuning_file.stem}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak.json"
    backup_path = args.backup_dir / backup_name
    backup_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')

    args.tuning_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Backup written: {backup_path}')
    print(f'Tuning updated: {args.tuning_file}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
