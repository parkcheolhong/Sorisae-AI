#!/usr/bin/env python3
"""Collect WorldLinco telemetry into a local runtime file.

Primary use:
- Fetch telemetry from admin API and save to `.runtime/admin_worldlinco_telemetry.json`
- If API is unavailable, initialize an empty schema-safe telemetry file
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_OUTPUT = Path('.runtime/admin_worldlinco_telemetry.json')
DEFAULT_ADMIN_ENDPOINT = '/api/admin/worldlinco/telemetry'


def _default_payload(note: str = '') -> Dict[str, Any]:
    return {
        'updated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'updated_by': 'collector',
        'note': note,
        'items': [],
        'summary': {
            'total_items': 0,
            'features': {},
        },
    }


def _fetch_from_api(api_base: str, endpoint: str, token: str, timeout_sec: int) -> Dict[str, Any]:
    base = api_base.rstrip('/')
    ep = endpoint if endpoint.startswith('/') else f'/{endpoint}'
    url = f'{base}{ep}'

    request = urllib.request.Request(url, method='GET')
    request.add_header('Accept', 'application/json')
    request.add_header('Authorization', f'Bearer {token}')

    with urllib.request.urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
        payload = json.loads(response.read().decode('utf-8'))

    if not isinstance(payload, dict):
        raise RuntimeError('Telemetry response is not a JSON object.')
    if not isinstance(payload.get('items'), list):
        payload['items'] = []
    if not isinstance(payload.get('summary'), dict):
        payload['summary'] = {'total_items': len(payload['items']), 'features': {}}
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Collect worldlinco telemetry payload to local runtime file.')
    parser.add_argument('--output-file', type=Path, default=DEFAULT_OUTPUT, help='Target telemetry JSON file path.')
    parser.add_argument('--api-base', type=str, default='', help='API base URL, e.g. http://127.0.0.1:8000')
    parser.add_argument('--endpoint', type=str, default=DEFAULT_ADMIN_ENDPOINT, help='Telemetry GET endpoint path.')
    parser.add_argument('--token', type=str, default='', help='Admin bearer token for API fetch.')
    parser.add_argument('--timeout-sec', type=int, default=12, help='HTTP timeout seconds.')
    parser.add_argument('--init-empty', action='store_true', help='Write empty telemetry file when API fetch is unavailable.')
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    payload: Optional[Dict[str, Any]] = None
    if args.api_base and args.token:
        try:
            payload = _fetch_from_api(args.api_base, args.endpoint, args.token, max(3, int(args.timeout_sec)))
            payload['updated_by'] = str(payload.get('updated_by') or 'collector:api')
            print(f"Fetched telemetry from API with {len(payload.get('items') or [])} items")
        except Exception as exc:  # noqa: BLE001
            print(f'API fetch failed: {exc}')
            if not args.init_empty:
                raise SystemExit(1)

    if payload is None:
        if not args.init_empty:
            raise SystemExit('No telemetry source available. Provide --api-base/--token or use --init-empty.')
        payload = _default_payload(note='initialized empty telemetry payload by collector')

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote telemetry file: {args.output_file}')
    print(f"Items: {len(payload.get('items') or [])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
