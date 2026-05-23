"""
marketplace_storage_service.py
────────────────────────────────────────────────────────────────────────────
마켓플레이스 파일 저장소 유틸리티.
MinIO 업로드/로컬 폴백, 고객 실행 경로 계산, 텍스트 검증 로직을 제공한다.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException

from . import models
from .minio_service import minio_service


def _slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣_-]", "-", (value or "project").strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "project"


def _has_mojibake(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = str(value)
    if re.search(r"\?{3,}", text):
        return True
    if "�" in text:
        return True
    if re.search(r"[\u0080-\u009F]", text):
        return True
    if re.search(r"(?:Ã.|Â.|ì.|ë.|ê.|í.){2,}", text):
        return True
    return False


def _validate_text_fields(fields: List[Tuple[str, Optional[str]]]):
    broken = [name for name, value in fields if _has_mojibake(value)]
    if broken:
        raise HTTPException(
            status_code=400,
            detail=f"문자 인코딩이 깨진 텍스트가 감지되었습니다: {', '.join(broken)}",
        )


def _resolve_marketplace_upload_root() -> Path:
    configured_root = (os.getenv("MARKETPLACE_UPLOAD_ROOT", "") or "").strip()
    if configured_root:
        if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", configured_root):
            mounted_upload_root = Path("/app/uploads")
            if mounted_upload_root.exists():
                return mounted_upload_root.resolve()
        return Path(configured_root).expanduser().resolve()
    workspace_root = Path(__file__).resolve().parents[2]
    return (workspace_root / "uploads").resolve()


def _resolve_marketplace_temp_root() -> Path:
    temp_root = (_resolve_marketplace_upload_root() / "tmp").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def _resolve_customer_orchestrator_run_root(user_id: int) -> Path:
    run_root = (
        _resolve_marketplace_upload_root()
        / "projects"
        / f"customer_{user_id}"
        / "runs"
    ).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    return run_root


def _allocate_customer_orchestrator_output_dir(
    run_root: Path,
    project_name: Optional[str],
) -> Path:
    slug = _slugify_text(project_name or "project")
    candidate = (run_root / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}").resolve()
    if not str(candidate).startswith(str(run_root)):
        raise HTTPException(status_code=500, detail="출력 경로 계산 실패")
    suffix = 1
    while candidate.exists():
        candidate = (run_root / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{suffix:02d}").resolve()
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _validate_customer_generated_output_dir(
    output_dir: Path,
    current_user_id: int,
) -> Path:
    base_allowed = _resolve_customer_orchestrator_run_root(current_user_id)
    resolved_output = output_dir.resolve()

    if not str(resolved_output).startswith(str(base_allowed)):
        raise HTTPException(
            status_code=403,
            detail="허용되지 않은 출력 경로입니다.",
        )
    if resolved_output == base_allowed:
        raise HTTPException(
            status_code=400,
            detail="실행 루트 전체가 아닌 개별 결과 폴더를 선택해야 합니다.",
        )
    if resolved_output.parent != base_allowed:
        raise HTTPException(
            status_code=400,
            detail="개별 실행 결과 폴더만 게시할 수 있습니다.",
        )
    if str(resolved_output.name).startswith("_archive"):
        raise HTTPException(
            status_code=400,
            detail="보관 폴더는 게시 대상으로 사용할 수 없습니다.",
        )
    return resolved_output


def _ensure_customer_publish_deploy_handoff(
    output_dir: Path,
    request: "CustomerPublishRequest",  # noqa: F821  forward ref
    current_user_id: int,
) -> None:
    handoff_path = (output_dir / "deploy_handoff.json").resolve()
    if handoff_path.parent != output_dir.resolve():
        raise HTTPException(status_code=500, detail="배포 인계 파일 경로 계산 실패")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": current_user_id,
        "output_dir": str(output_dir),
        "publish": {
            "title": request.title.strip(),
            "description": request.description.strip(),
            "price": float(request.price),
            "category_id": request.category_id,
            "image_url": request.image_url,
            "demo_url": request.demo_url,
            "github_url": request.github_url,
            "tags": [tag.strip() for tag in (request.tags or []) if str(tag).strip()],
        },
    }
    handoff_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_file_from_storage(file_key: str) -> Optional[bytes]:
    if not file_key:
        return None

    if file_key.startswith("local:"):
        rel = file_key[len("local:"):].lstrip("/").replace("\\", "/")
        local_base = (_resolve_marketplace_upload_root() / "marketplace_local").resolve()
        local_path = (local_base / rel).resolve()
        if not str(local_path).startswith(str(local_base)):
            return None
        if not local_path.exists() or not local_path.is_file():
            return None
        return local_path.read_bytes()

    return minio_service.download_file(file_key)


def _store_bytes_with_fallback(file_bytes: bytes, object_key: str, content_type: str) -> str:
    uploaded = minio_service.upload_file(file_bytes, object_key, content_type)
    if uploaded:
        return object_key

    local_base = (_resolve_marketplace_upload_root() / "marketplace_local").resolve()
    local_target = (local_base / object_key).resolve()
    if not str(local_target).startswith(str(local_base)):
        raise HTTPException(status_code=500, detail="로컬 저장 경로 계산 실패")
    local_target.parent.mkdir(parents=True, exist_ok=True)
    local_target.write_bytes(file_bytes)
    return f"local:{object_key}"
