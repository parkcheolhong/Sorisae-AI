from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from fastapi import HTTPException

from .path_utils import admin_workspace_root, is_relative_to, require_allowed_root_path, resolve_marketplace_upload_root_path

ADMIN_TEXT_FILE_SUFFIXES = {
    ".txt", ".md", ".json", ".yml", ".yaml", ".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".scss", ".env", ".log", ".mmd",
}
ADMIN_TEXT_FILE_NAMES = {
    "dockerfile", "makefile", ".gitignore", ".gitattributes",
}
ADMIN_TEXT_MAX_BYTES = 200 * 1024
ADMIN_TEXT_LIST_LIMIT = 200
ADMIN_WORKSPACE_PATH_DENIED_DETAIL = "허용된 관리자 런타임/워크스페이스 내부 경로만 열 수 있습니다."


def resolve_marketplace_host_root_text(read_admin_env_values, admin_env_path) -> str:
    env_path = admin_env_path()
    env_values = read_admin_env_values(env_path) if env_path.exists() else {}
    configured = str(env_values.get("MARKETPLACE_HOST_ROOT", "") or "").strip()
    if configured:
        return configured.rstrip("\\/")
    return str((admin_workspace_root() / "uploads").resolve())


def resolve_admin_workspace_path(
    requested_path: Optional[str],
    *,
    read_admin_env_values,
    admin_env_path,
) -> Path:
    workspace_root = admin_workspace_root()
    marketplace_host_root = resolve_marketplace_host_root_text(read_admin_env_values, admin_env_path).replace('\\', '/').rstrip('/')
    marketplace_upload_root = resolve_marketplace_upload_root_path()
    if requested_path:
        raw = str(requested_path).strip()
        normalized = raw.replace('\\', '/')
        candidates: List[Path] = []
        workspace_root_posix = str(workspace_root).replace('\\', '/')
        raw_path = Path(raw).expanduser()
        if not (re.match(r'^[A-Za-z]:/', normalized) or normalized.startswith('/app/')):
            candidates.append(workspace_root / raw_path)
            candidates.append(raw_path)
        if marketplace_host_root and normalized.lower().startswith(marketplace_host_root.lower()):
            relative = normalized[len(marketplace_host_root):].lstrip('/')
            if relative:
                candidates.append(marketplace_upload_root / Path(relative))
        if normalized.lower().startswith(workspace_root_posix.lower()):
            relative = normalized[len(workspace_root_posix):].lstrip('/')
            candidates.append(workspace_root / Path(relative))
        elif normalized.lower().startswith('/app/'):
            candidates.append(workspace_root / Path(normalized[len('/app/'):]))
        elif re.match(r'^[A-Za-z]:/', normalized):
            drive_relative = normalized.split(':', 1)[1].lstrip('/')
            path_parts = [part for part in drive_relative.split('/') if part]
            lowered_parts = [part.lower() for part in path_parts]
            if 'codeai' in lowered_parts:
                codeai_index = lowered_parts.index('codeai')
                relative_parts = path_parts[codeai_index + 1:]
                if relative_parts:
                    candidates.append(workspace_root.joinpath(*relative_parts))
            candidates.append(workspace_root / Path(drive_relative))
        else:
            candidates.append(workspace_root / Path(normalized))

        candidate = None
        for next_candidate in candidates:
            try:
                resolved_candidate = require_allowed_root_path(
                    next_candidate,
                    detail=ADMIN_WORKSPACE_PATH_DENIED_DETAIL,
                )
                candidate = resolved_candidate
                break
            except HTTPException:
                continue
        if candidate is None:
            candidate = require_allowed_root_path(
                candidates[0],
                detail=ADMIN_WORKSPACE_PATH_DENIED_DETAIL,
            )
    else:
        candidate = workspace_root

    return require_allowed_root_path(
        candidate,
        detail=ADMIN_WORKSPACE_PATH_DENIED_DETAIL,
    )


def is_admin_text_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name.lower()
    suffix = path.suffix.lower()
    return (
        suffix in ADMIN_TEXT_FILE_SUFFIXES
        or name in ADMIN_TEXT_FILE_NAMES
        or name.startswith('.env')
    )


def decode_admin_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=400,
        detail="UTF-8 또는 CP949 텍스트 파일만 불러올 수 있습니다.",
    )


def read_admin_text_file(path: Path) -> str:
    size_bytes = path.stat().st_size
    if size_bytes > ADMIN_TEXT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                "전체 본문 불러오기는 200KB 이하 텍스트 파일만 허용합니다. "
                f"현재 파일 크기: {size_bytes} bytes"
            ),
        )
    return decode_admin_text_file(path)


def list_workspace_text_files(
    path: Optional[str],
    *,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    current_dir = resolve_admin_workspace_path(
        path,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    if not current_dir.exists():
        raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")
    if not current_dir.is_dir():
        raise HTTPException(status_code=400, detail="디렉터리만 탐색할 수 있습니다.")

    workspace_root = admin_workspace_root()
    entries = []
    children = sorted(
        current_dir.iterdir(),
        key=lambda child: (0 if child.is_dir() else 1, child.name.lower()),
    )
    for child in children:
        if child.is_dir() or is_admin_text_file(child):
            stat = child.stat()
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "kind": "dir" if child.is_dir() else "file",
                    "size_bytes": None if child.is_dir() else stat.st_size,
                    "modified_at": stat.st_mtime,
                }
            )
        if len(entries) >= ADMIN_TEXT_LIST_LIMIT:
            break

    parent_path = None
    if current_dir != workspace_root and is_relative_to(current_dir.parent, workspace_root):
        parent_path = str(current_dir.parent)

    return {
        "root_path": str(workspace_root),
        "current_path": str(current_dir),
        "parent_path": parent_path,
        "entries": entries,
    }


def get_workspace_text_file(
    path: str,
    *,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    target = resolve_admin_workspace_path(
        path,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    if not target.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="파일만 불러올 수 있습니다.")
    if not is_admin_text_file(target):
        raise HTTPException(status_code=400, detail="텍스트/코드 파일만 불러올 수 있습니다.")

    return {
        "path": str(target),
        "size_bytes": target.stat().st_size,
        "content": read_admin_text_file(target),
    }
