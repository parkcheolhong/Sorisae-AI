"""Parse ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md for next expansion KPI target."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional


def _checklist_path() -> Path:
    return Path(__file__).resolve().parents[3] / "ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md"


def pick_next_checklist_kpi() -> Dict[str, Any]:
    path = _checklist_path()
    if not path.is_file():
        return {
            "available": False,
            "checklist_path": str(path),
            "pending_count": 0,
            "next_target_line": "",
            "next_target_id": "",
        }

    text = path.read_text(encoding="utf-8")
    pending_lines = [line.strip() for line in text.splitlines() if "[~]" in line]
    done_count = len(re.findall(r"\[x\]", text, flags=re.IGNORECASE))
    pending_count = len(pending_lines)

    next_line = pending_lines[0] if pending_lines else ""
    target_id = ""
    match = re.search(r"\(([A-Za-z0-9-]+)\)", next_line)
    if match:
        target_id = match.group(1)

    return {
        "available": bool(next_line),
        "checklist_path": str(path),
        "pending_count": pending_count,
        "done_marker_count": done_count,
        "next_target_line": next_line,
        "next_target_id": target_id,
        "kpi_instruction": (
            f"self-expansion 1회 = 체크리스트 항목 `{target_id}` 를 [~] → [x] 로 전환"
            if target_id
            else "self-expansion 1회 = 체크리스트 [~] 항목 1개 완료"
        ),
    }
