# FILE-ID: FILE-AI-FEATURES-PY
# SECTION-ID: SECTION-AI-FEATURES-PY-MAIN
# FEATURE-ID: FEATURE-AI-FEATURES-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-FEATURES-PY-001

from collections import Counter
from typing import Any, Dict, List

DOMAIN_RECORD_KEY = 'jobs'
IS_TRADING_PROFILE = False

FEATURE_WINDOW_SIZE = 3

def normalize_domain_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(records, start=1):
        if not isinstance(item, dict):
            continue
        candidate = dict(item)
        candidate.setdefault('record_no', index)
        normalized.append(candidate)
    return normalized

def build_feature_windows(records: List[Dict[str, Any]], window_size: int = FEATURE_WINDOW_SIZE) -> List[Dict[str, Any]]:
    normalized = normalize_domain_records(records)
    if not normalized:
        return []
    windows: List[Dict[str, Any]] = []
    step = max(1, min(window_size, len(normalized)))
    for index in range(step, len(normalized) + 1):
        chunk = normalized[index - step:index]
        field_counter = Counter()
        for item in chunk:
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    field_counter[key] += float(value)
                elif isinstance(value, str) and value:
                    field_counter[key] += 1
                elif isinstance(value, list):
                    field_counter[key] += len(value)
        windows.append({
            'window_index': index - step + 1,
            'record_count': len(chunk),
            'field_scores': dict(field_counter),
        })
    return windows

def build_feature_set(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(raw_payload or {})
    records = normalize_domain_records(payload.get(DOMAIN_RECORD_KEY) or payload.get('records') or [])
    windows = build_feature_windows(records)
    return {
        'raw': payload,
        DOMAIN_RECORD_KEY: records,
        'feature_windows': windows,
        'feature_count': len(windows),
        'engine-core': bool(records),
        'feature-pipeline': bool(windows),
        'signal-ingestion': bool(records) if IS_TRADING_PROFILE else False,
        'risk-guard': any('risk_score' in item for item in records) if IS_TRADING_PROFILE else False,
    }
