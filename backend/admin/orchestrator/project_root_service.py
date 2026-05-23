from __future__ import annotations

from pathlib import Path
import re

from fastapi import HTTPException

from .path_utils import admin_workspace_root


def resolve_admin_project_root(project_root: str, *, allow_workspace_default: bool = False) -> Path:
    raw = str(project_root or '').strip()
    if not raw:
        if allow_workspace_default:
            return admin_workspace_root().resolve()
        raise HTTPException(status_code=400, detail='project_root가 필요합니다.')
    normalized = raw.replace('\\', '/')
    workspace_root = admin_workspace_root().resolve()
    workspace_root_posix = str(workspace_root).replace('\\', '/')
    candidates = [Path(raw).expanduser()]
    if normalized.lower().startswith(workspace_root_posix.lower()):
        relative = normalized[len(workspace_root_posix):].lstrip('/')
        candidates.append(workspace_root / Path(relative))
    elif re.match(r'^[A-Za-z]:/', normalized):
        drive_relative = normalized.split(':', 1)[1].lstrip('/')
        path_parts = [part for part in drive_relative.split('/') if part]
        if 'codeAI' in path_parts:
            codeai_index = path_parts.index('codeAI')
            relative_parts = path_parts[codeai_index + 1:]
            if relative_parts:
                candidates.append(workspace_root.joinpath(*relative_parts))
            else:
                candidates.append(workspace_root)
        candidates.append(workspace_root / Path(drive_relative))
    else:
        candidates.append(workspace_root / Path(normalized))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_dir():
            return resolved
    raise HTTPException(status_code=400, detail='유효한 project_root 디렉터리가 필요합니다.')
