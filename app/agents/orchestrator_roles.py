# FILE-ID: FILE-APP-AGENTS-ORCHESTRATOR-ROLES-PY
# SECTION-ID: SECTION-APP-AGENTS-ORCHESTRATOR-ROLES-PY-MAIN
# FEATURE-ID: FEATURE-APP-AGENTS-ORCHESTRATOR-ROLES-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-AGENTS-ORCHESTRATOR-ROLES-PY-001

from __future__ import annotations

def build_orchestrator_role_matrix() -> list[dict]:
    return [
        {'role': 'planner', 'responsibility': '요구 해석 및 단계 계획', 'status': 'ready'},
        {'role': 'coder', 'responsibility': '서비스/라우트/설정 생성', 'status': 'ready'},
        {'role': 'reviewer', 'responsibility': '계약/구조 점검', 'status': 'ready'},
        {'role': 'security', 'responsibility': '보안 설정/헤더 점검', 'status': 'ready'},
        {'role': 'qa', 'responsibility': '헬스체크/pytest 검증', 'status': 'ready'},
        {'role': 'ops', 'responsibility': '운영 readiness 및 상태 어댑터 점검', 'status': 'ready'},
    ]
