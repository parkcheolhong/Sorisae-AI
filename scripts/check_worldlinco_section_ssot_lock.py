#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / "knowledge" / "worldlinco_section_freeze.json"


def _load_locked_snippets() -> Dict[str, List[str]]:
    payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    locked = payload.get("locked_file_snippets")
    if not isinstance(locked, dict):
        raise ValueError("worldlinco_section_freeze.json missing locked_file_snippets")
    return {
        str(path): [str(snippet) for snippet in snippets]
        for path, snippets in locked.items()
    }


def main() -> int:
    violations: List[str] = []

    try:
        locked_snippets = _load_locked_snippets()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[worldlinco-ssot-lock] failed to load lock: {exc}")
        return 1

    for rel_path, snippets in sorted(locked_snippets.items()):
        path = REPO_ROOT / rel_path
        if not path.is_file():
            violations.append(f"{rel_path}: file is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in snippets:
            if snippet not in text:
                violations.append(f"{rel_path}: missing locked snippet {snippet!r}")

    if violations:
        print("[worldlinco-ssot-lock] blocked:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("[worldlinco-ssot-lock] passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
