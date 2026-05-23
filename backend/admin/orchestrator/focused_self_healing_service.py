from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

SOURCE_FILE_SUFFIXES = {
    '.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yml', '.yaml', '.md', '.sh', '.css', '.scss', '.html'
}

AUTO_APPLY_ALLOWED_CATEGORIES = {
    'cors_header',
    'proxy_route',
    'import_path',
    'schema_contract',
    'null_guard',
    'health_score',
    'self_run_record',
    'diagnostic_ui',
    'log_trace_link',
}

APPROVAL_REQUIRED_CATEGORIES = {
    'db_schema',
    'payment_flow',
    'authorization_policy',
    'approval_gate',
    'bulk_source_apply',
    'feature_extension',
    'external_contract',
    'deployment_policy',
}


@dataclass(frozen=True)
class FocusedSelfHealingDecision:
    operation_id: str
    requested_path: str
    focused_path: str
    target_source_path: str
    target_kind: str
    category: str
    auto_apply_allowed: bool
    approval_required: bool
    rationale: str
    suggested_action: str


@dataclass(frozen=True)
class TowerCraneOption:
    option_id: str
    title: str
    scope: str
    pros: List[str]
    cons: List[str]
    impact_paths: List[str]
    validation_plan: List[str]
    risk_level: str


def _normalize_suffix_target(path: Path) -> str:
    if path.suffix.lower() in SOURCE_FILE_SUFFIXES:
        return 'file'
    return 'directory'


def _classify_healing_category(focused_path: str, reason: str) -> str:
    normalized_reason = str(reason or '').lower()
    normalized_path = str(focused_path or '').lower()
    if 'cors' in normalized_reason or 'access-control' in normalized_reason:
        return 'cors_header'
    if 'proxy' in normalized_reason or 'route' in normalized_reason:
        return 'proxy_route'
    if 'import' in normalized_reason or 'modulenotfound' in normalized_reason:
        return 'import_path'
    if any(token in normalized_reason for token in ('payment', 'purchase', 'settlement', 'billing')):
        return 'payment_flow'
    if any(token in normalized_reason for token in ('external contract', 'commercial terms', 'provider contract')):
        return 'external_contract'
    if any(token in normalized_reason for token in ('db schema', 'migration', 'database schema')):
        return 'db_schema'
    if any(token in normalized_reason for token in ('authorization', 'permission', 'role policy', 'admin policy')):
        return 'authorization_policy'
    if 'schema' in normalized_reason or 'contract' in normalized_reason:
        return 'schema_contract'
    if 'null' in normalized_reason or 'none' in normalized_reason or 'optional' in normalized_reason:
        return 'null_guard'
    if 'health' in normalized_reason and 'score' in normalized_reason:
        return 'health_score'
    if 'approval' in normalized_reason or 'gate' in normalized_reason:
        return 'approval_gate'
    if any(token in normalized_path for token in ('payment', 'purchase', 'settlement', 'billing')):
        return 'payment_flow'
    if any(token in normalized_path for token in ('auth', 'permission', 'role', 'admin')) and 'ui' not in normalized_reason:
        return 'authorization_policy'
    return 'feature_extension' if 'feature' in normalized_reason or 'extension' in normalized_reason else 'diagnostic_ui'


def build_focused_self_healing_decision(
    *,
    operation_id: str,
    requested_path: str,
    resolved_path: Path,
    reason: str,
) -> FocusedSelfHealingDecision:
    focused_path = str(resolved_path)
    target_source_path = focused_path
    target_kind = 'directory'
    if resolved_path.exists() and resolved_path.is_file():
        target_kind = 'file'
        target_source_path = str(resolved_path)
    elif _normalize_suffix_target(resolved_path) == 'file':
        target_kind = 'file'
        target_source_path = str(resolved_path)

    category = _classify_healing_category(focused_path, reason)
    auto_apply_allowed = category in AUTO_APPLY_ALLOWED_CATEGORIES
    approval_required = category in APPROVAL_REQUIRED_CATEGORIES or not auto_apply_allowed
    rationale = (
        '무승인 자동반영 허용 범위로 분류되어 focused self-healing 대상입니다.'
        if auto_apply_allowed and not approval_required
        else '승인/검증 분기가 필요한 범위로 분류되어 원인 설명과 승인 패킷이 필요합니다.'
    )
    suggested_action = (
        f'집중 경로 {focused_path} 기준으로 관련 파일만 분석하고 {target_source_path} 범위에서 self-healing 을 재실행합니다.'
    )
    return FocusedSelfHealingDecision(
        operation_id=operation_id,
        requested_path=requested_path,
        focused_path=focused_path,
        target_source_path=target_source_path,
        target_kind=target_kind,
        category=category,
        auto_apply_allowed=auto_apply_allowed,
        approval_required=approval_required,
        rationale=rationale,
        suggested_action=suggested_action,
    )


def build_tower_crane_options(
    *,
    proposal_id: str,
    title: str,
    summary: str,
    focused_path: str,
) -> List[Dict[str, Any]]:
    path_list = [focused_path] if focused_path else []
    options = [
        TowerCraneOption(
            option_id=f'{proposal_id}-A',
            title=f'{title} 최소 변경형',
            scope='국소 수정과 기존 계약 유지',
            pros=['반영 속도가 빠릅니다.', '기존 흐름 영향이 가장 작습니다.', '무승인 자동반영 후보가 되기 쉽습니다.'],
            cons=['확장성은 제한됩니다.', '근본 구조 개선은 부족할 수 있습니다.'],
            impact_paths=path_list,
            validation_plan=['정적 검사', '문제 재현 API 재호출', '회귀 경로 1회 확인'],
            risk_level='low',
        ),
        TowerCraneOption(
            option_id=f'{proposal_id}-B',
            title=f'{title} 균형형',
            scope='원인 파일과 연관 계약 파일을 함께 정리',
            pros=['재발 방지력이 높습니다.', '원인과 계약을 같이 정리합니다.', '중간 수준의 리스크로 구조 개선이 가능합니다.'],
            cons=['수정 파일 수가 늘어날 수 있습니다.', '추가 검증 비용이 있습니다.'],
            impact_paths=path_list,
            validation_plan=['정적 검사', '핵심 API/화면 검증', '운영 경로 재검증'],
            risk_level='medium',
        ),
        TowerCraneOption(
            option_id=f'{proposal_id}-C',
            title=f'{title} 확장형',
            scope='기능 확장과 운영 제어 패널까지 같이 보강',
            pros=['운영 생산성이 큽니다.', '신규 제어 기능을 함께 붙일 수 있습니다.', '장기적 확장에 유리합니다.'],
            cons=['승인이 필요할 가능성이 큽니다.', '구현/검증 범위가 넓습니다.'],
            impact_paths=path_list,
            validation_plan=['정적 검사', '핵심 API/화면 검증', '운영 실도메인 검증', '롤백 계획 확인'],
            risk_level='high',
        ),
    ]
    return [
        {
            'option_id': option.option_id,
            'title': option.title,
            'scope': option.scope,
            'pros': option.pros,
            'cons': option.cons,
            'impact_paths': option.impact_paths,
            'validation_plan': option.validation_plan,
            'risk_level': option.risk_level,
            'summary': summary,
        }
        for option in options
    ]


def assert_focused_self_healing_contract() -> None:
    sample = build_focused_self_healing_decision(
        operation_id='heal-001',
        requested_path='frontend/frontend/app/admin/page.tsx',
        resolved_path=Path('frontend/frontend/app/admin/page.tsx'),
        reason='health score contract mismatch',
    )
    if sample.target_kind != 'file' or not sample.target_source_path:
        raise HTTPException(status_code=500, detail='focused self-healing contract 누락')
