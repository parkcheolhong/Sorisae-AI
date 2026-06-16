"""단계별 코더 패치 범위 — 전체 템플릿(155+) 대신 diff/patch SSOT."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

# python_fastapi 프로필 — 단계당 최소 파일만 갱신
PYTHON_FASTAPI_STAGE_PATCH: Dict[str, List[str]] = {
    "STAGE-01": [
        "README.md",
        "requirements.txt",
        ".gitignore",
        "app/__init__.py",
        "app/main.py",
        "app/routes/__init__.py",
        "app/routes/health.py",
        "tests/__init__.py",
        "tests/test_health.py",
    ],
    "STAGE-02": [
        "app/core/__init__.py",
        "app/core/config.py",
        "app/services/__init__.py",
        "app/services/health_service.py",
        "tests/conftest.py",
    ],
    "STAGE-03": [
        "app/models/__init__.py",
        "app/models/health.py",
        "app/schemas/__init__.py",
        "app/schemas/health.py",
        "app/routes/health.py",
    ],
    "STAGE-04": [
        "app/core/engine.py",
        "app/services/runtime_service.py",
        "app/routes/health.py",
    ],
    "STAGE-045": [
        "app/routes/health.py",
        "app/services/health_service.py",
        "app/core/database.py",
        "app/external_adapters/status_client.py",
        "tests/test_health.py",
        "tests/test_external_services.py",
    ],
    "STAGE-05": [
        "app/core/identifiers.py",
        "app/services/id_service.py",
    ],
    "STAGE-06": [
        "app/core/database.py",
        "app/repositories/__init__.py",
        "app/repositories/health_repository.py",
    ],
    "STAGE-07": [
        "app/services/__init__.py",
        "app/services/health_service.py",
        "app/services/runtime_service.py",
    ],
    "STAGE-08": [
        "app/routes/__init__.py",
        "app/routes/health.py",
        "app/routes/ops.py",
    ],
    "STAGE-09": [
        "frontend/app/page.tsx",
        "frontend/app/layout.tsx",
    ],
    "STAGE-10": [
        "tests/test_health.py",
        "tests/test_runtime.py",
        "docs/deployment.md",
    ],
}

GENERIC_STAGE_PATCH: Dict[str, List[str]] = {
    "STAGE-01": ["README.md", "requirements.txt", "app/main.py", "tests/test_health.py"],
    "STAGE-02": ["app/core/config.py", "tests/conftest.py"],
    "STAGE-03": ["app/routes/health.py"],
    "STAGE-04": ["app/core/engine.py"],
    "STAGE-045": ["tests/test_health.py", "app/routes/health.py"],
    "STAGE-05": ["app/services/id_service.py"],
    "STAGE-06": ["app/core/database.py"],
    "STAGE-07": ["app/services/runtime_service.py"],
    "STAGE-08": ["app/routes/health.py"],
    "STAGE-09": ["frontend/app/page.tsx"],
    "STAGE-10": ["tests/test_runtime.py", "docs/deployment.md"],
}


def get_stage_patch_scope(stage_id: Optional[str], validation_profile: str) -> List[str]:
    """단계별 패치 범위 — 항상 전체 스코프 반환 (기존 파일 여부와 무관)."""
    if not stage_id:
        return []
    profile_map = (
        PYTHON_FASTAPI_STAGE_PATCH
        if validation_profile == "python_fastapi"
        else GENERIC_STAGE_PATCH
    )
    return list(profile_map.get(stage_id, []))


def resolve_stage_patch_files(
    *,
    stage_id: Optional[str],
    validation_profile: str,
    output_dir: Optional[str] = None,
) -> List[str]:
    """단계 패치 대상 파일 — 스코프 SSOT, 빈 목록이 되면 전체 템플릿 폭주 방지."""
    return get_stage_patch_scope(stage_id, validation_profile)


def build_stage_patch_task_suffix(stage_id: str, files: List[str]) -> str:
    if not files:
        return ""
    joined = ", ".join(files)
    return (
        f"\n\n[단계 패치 · {stage_id}]\n"
        f"수정 가능 파일은 {joined} 뿐입니다.\n"
        "기존 프로젝트는 유지하고 위 파일만 추가·수정하세요."
    )


def is_incremental_stage_patch(stage_id: Optional[str], output_dir: Optional[str]) -> bool:
    if not stage_id:
        return False
    if stage_id == "STAGE-01":
        if not output_dir:
            return False
        root = Path(output_dir)
        return root.exists() and any(root.rglob("*"))
    return True
