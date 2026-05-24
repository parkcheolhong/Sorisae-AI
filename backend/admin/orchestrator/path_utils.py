from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import re
import tempfile
from fastapi import HTTPException


def admin_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_shared_admin_runtime_root() -> Optional[Path]:
    configured_upload_root = os.getenv("MARKETPLACE_UPLOAD_ROOT", "").strip()
    shared_upload_root: Optional[Path] = None

    if configured_upload_root:
        if os.name == "nt" and configured_upload_root.startswith("/"):
            workspace_upload_root = (admin_workspace_root() / "uploads").resolve()
            if workspace_upload_root.exists():
                shared_upload_root = workspace_upload_root
        elif os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", configured_upload_root):
            mounted_upload_root = Path("/app/uploads")
            if mounted_upload_root.exists():
                shared_upload_root = mounted_upload_root.resolve()

        if shared_upload_root is None:
            shared_upload_root = Path(configured_upload_root).expanduser().resolve()
    else:
        workspace_upload_root = (admin_workspace_root() / "uploads").resolve()
        if workspace_upload_root.exists():
            shared_upload_root = workspace_upload_root

    if shared_upload_root is None:
        return None
    return (shared_upload_root / "tmp" / "codeai_admin_runtime").resolve()


def admin_runtime_root() -> Path:
    configured_root = os.getenv("ADMIN_RUNTIME_ROOT", "").strip()
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if os.name != "nt":
        container_local_tmp = Path("/tmp")
        if container_local_tmp.exists():
            return (container_local_tmp / "codeai_admin_runtime").resolve()
    shared_runtime_root = resolve_shared_admin_runtime_root()
    if shared_runtime_root is not None:
        return shared_runtime_root
    return (Path(tempfile.gettempdir()) / "codeai_admin_runtime").resolve()


def admin_allowed_roots() -> List[Path]:
    return [
        admin_workspace_root(),
        admin_runtime_root(),
    ]


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_marketplace_upload_root_path() -> Path:
    configured_upload_root = str(os.getenv("MARKETPLACE_UPLOAD_ROOT", "") or "").strip()
    if configured_upload_root:
        return Path(configured_upload_root).expanduser().resolve()
    return (admin_workspace_root() / "uploads").resolve()


def require_allowed_root_path(path_value: Path, *, detail: str) -> Path:
    candidate = path_value
    if any(is_relative_to(candidate, allowed_root) for allowed_root in admin_allowed_roots()):
        return candidate
    raise HTTPException(status_code=400, detail=detail)


def resolve_safe_child_path(root: Path, relative_path: str, *, detail: str) -> Path:
    normalized = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail=detail)
    relative = Path(normalized)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise HTTPException(status_code=400, detail=detail)
    return require_allowed_root_path((root.resolve() / relative), detail=detail)
