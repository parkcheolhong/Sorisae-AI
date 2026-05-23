"""Tool-backed file writing helpers for the LLM orchestrator."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


ToolEventCallback = Optional[Callable[[str, Dict[str, Any]], None]]


def normalize_rel(path: str) -> str:
    return str(path or "").replace("\\", "/").strip().lower()


def _decode_file_content(item: Dict[str, Any]) -> str:
    content_b64 = item.get("content_b64")
    if isinstance(content_b64, str) and content_b64:
        try:
            return base64.b64decode(content_b64).decode("utf-8")
        except Exception:
            pass
    return str(item.get("content", ""))


def _emit(
    callback: ToolEventCallback,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    if not callback:
        return
    try:
        callback(event_type, payload)
    except Exception:
        return


def _seed_manifest(base_dir: Path) -> None:
    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = docs_dir / "file_manifest.md"
    if manifest_path.exists():
        return
    manifest_path.write_text(
        (
            "# File Manifest\n\n"
            "| Path | Purpose | Signature | Connection |\n"
            "|---|---|---|---|\n"
        ),
        encoding="utf-8",
    )


def _prune_empty_dirs(target_dir: Path) -> int:
    removed = 0
    for dir_path in sorted(
        target_dir.rglob("*"),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if not dir_path.is_dir():
            continue
        try:
            if any(dir_path.iterdir()):
                continue
            dir_path.rmdir()
            removed += 1
        except Exception:
            continue
    return removed


def _collect_empty_dirs(target_dir: Path) -> List[str]:
    empty_dirs: List[str] = []
    for dir_path in sorted(target_dir.rglob("*")):
        if not dir_path.is_dir():
            continue
        try:
            if any(dir_path.iterdir()):
                continue
        except Exception:
            continue
        rel = str(dir_path.relative_to(target_dir)).replace("\\", "/")
        if rel:
            empty_dirs.append(rel)
    return empty_dirs


def write_file_tool(
    base_dir: Path,
    files: List[Dict[str, Any]],
    *,
    emit: ToolEventCallback = None,
    indexer: Any = None,
) -> List[str]:
    """Write files through a single tool boundary.

    The orchestrator delegates all file creation to this helper.
    """
    written: List[str] = []
    base_dir.mkdir(parents=True, exist_ok=True)
    _seed_manifest(base_dir)

    for item in files:
        rel_path = str(item.get("path", "")).strip().replace("\\", "/")
        if not rel_path:
            continue

        target = (base_dir / rel_path).resolve()
        base_resolved = base_dir.resolve()
        if not str(target).startswith(str(base_resolved)):
            _emit(
                emit,
                "tool_error",
                {
                    "tool": "file_writer",
                    "path": rel_path,
                    "error": "path_outside_workspace",
                },
            )
            continue

        content = _decode_file_content(item)
        if not content.strip():
            _emit(
                emit,
                "tool_error",
                {
                    "tool": "file_writer",
                    "path": rel_path,
                    "error": "empty_content",
                },
            )
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        rel_written = str(target.relative_to(base_resolved)).replace("\\", "/")
        written.append(rel_written)
        _emit(
            emit,
            "file_change",
            {
                "tool": "file_writer",
                "path": rel_written,
                "bytes": len(content.encode("utf-8")),
            },
        )

        if indexer is not None:
            try:
                indexer.index_file(base_dir, rel_written, content)
            except Exception:
                pass

    empty_dirs = _collect_empty_dirs(base_dir)
    if empty_dirs:
        _emit(
            emit,
            "tool_warning",
            {
                "tool": "file_writer",
                "warning": "empty_dirs_preserved",
                "empty_dirs": empty_dirs[:50],
                "count": len(empty_dirs),
            },
        )
    _emit(
        emit,
        "tool_result",
        {
            "tool": "file_writer",
            "written_files": written,
            "count": len(written),
            "empty_dirs_detected": len(empty_dirs),
        },
    )
    return written
