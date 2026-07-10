from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict


_SAFE_SESSION_ID = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _session_root() -> Path:
    configured = os.getenv("ORCHESTRATOR_CHAT_SESSION_DIR", "").strip()
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / "codeai_orchestrator_chat_sessions"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(root, 0o700)
    except Exception:
        pass
    return root.resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _session_path(session_id: str, *, session_owner_id: str | None = None) -> Path | None:
    normalized = _SAFE_SESSION_ID.sub("_", str(session_id or "").strip())[:160]
    if not normalized:
        return None
    normalized_owner = _SAFE_SESSION_ID.sub("_", str(session_owner_id or "").strip())[:160] if session_owner_id is not None else ""
    root = _session_root()
    digest_source = f"{normalized_owner}\0{normalized}" if normalized_owner else normalized
    digest = hashlib.sha256(digest_source.encode("utf-8", errors="ignore")).hexdigest()
    candidate = (root / f"{digest}.json").resolve()
    if not _is_relative_to(candidate, root):
        return None
    return candidate


def load_chat_session_snapshot(session_id: str, *, session_owner_id: str | None = None) -> Dict[str, Any]:
    path = _session_path(session_id, session_owner_id=session_owner_id)
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    expected_owner = str(session_owner_id or "").strip()
    payload_owner = str(payload.get("session_owner_id") or "").strip()
    if payload_owner != expected_owner:
        return {}
    return payload


def save_chat_session_snapshot(session_id: str, snapshot: Dict[str, Any], *, session_owner_id: str | None = None) -> None:
    path = _session_path(session_id, session_owner_id=session_owner_id)
    if path is None:
        return
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    try:
        os.chmod(tmp_path, 0o600)
    except Exception:
        pass
    os.replace(tmp_path, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
