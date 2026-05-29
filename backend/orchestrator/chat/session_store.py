from __future__ import annotations

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
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_path(session_id: str) -> Path | None:
    normalized = _SAFE_SESSION_ID.sub("_", str(session_id or "").strip())[:160]
    if not normalized:
        return None
    return _session_root() / f"{normalized}.json"


def load_chat_session_snapshot(session_id: str) -> Dict[str, Any]:
    path = _session_path(session_id)
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_chat_session_snapshot(session_id: str, snapshot: Dict[str, Any]) -> None:
    path = _session_path(session_id)
    if path is None:
        return
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
