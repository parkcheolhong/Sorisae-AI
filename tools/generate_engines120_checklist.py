from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINES_DIR = ROOT / "backend" / "services" / "shinsegye" / "engines120"
MANIFEST_PATH = ENGINES_DIR / "engines120_manifest.json"
OUTPUT_PATH = ROOT / "docs" / "checklists" / "engines120-realfile-verification-20260502.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 120-engine checklist markdown.")
    parser.add_argument("--run1", choices=["pass", "fail", "pending"], default="pending")
    parser.add_argument("--run2", choices=["pass", "fail", "pending"], default="pending")
    return parser.parse_args()


def checkbox(state: bool) -> str:
    return "[x]" if state else "[ ]"


def state_badge(state: str) -> str:
    if state == "pass":
        return "PASS"
    if state == "fail":
        return "FAIL"
    return "PENDING"


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def file_parseable(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        return True
    except Exception:
        return False


def build_lines(run1: str, run2: str) -> list[str]:
    manifest = load_manifest()
    run_closed = run1 == "pass" and run2 == "pass"
    now = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []
    lines.append("# 120 Engine Real-File Verification Checklist (2026-05-02)")
    lines.append("")
    lines.append(f"- Generated at (UTC): {now}")
    lines.append(f"- Run #1 pytest status: {state_badge(run1)}")
    lines.append(f"- Run #2 pytest status: {state_badge(run2)}")
    lines.append("")
    lines.append("## Global Checklist")
    lines.append(f"- {checkbox(len(manifest) == 120)} manifest has exactly 120 entries")
    lines.append(f"- {checkbox(run1 == 'pass')} pytest run #1 passed")
    lines.append(f"- {checkbox(run2 == 'pass')} pytest run #2 passed")
    lines.append(f"- {checkbox(run_closed)} close condition met (run #1 and run #2 both pass)")
    lines.append("")
    lines.append("## Engine-by-Engine Checklist")
    lines.append("")
    lines.append("| Slot | Engine Name | Target File | Exists | Parseable | Run1 | Run2 | Closed |")
    lines.append("|---:|---|---|:---:|:---:|:---:|:---:|:---:|")

    for entry in manifest:
        slot = int(entry["slot"])
        engine_name = str(entry["source_name"])
        target_file = str(entry["target_file"])
        target_path = ENGINES_DIR / target_file
        exists = target_path.exists()
        parseable = file_parseable(target_path) if exists else False
        closed = exists and parseable and run_closed
        lines.append(
            f"| {slot:03d} | {engine_name} | {target_file} | {checkbox(exists)} | {checkbox(parseable)} | {state_badge(run1)} | {state_badge(run2)} | {checkbox(closed)} |"
        )

    lines.append("")
    lines.append("## Status")
    if run_closed:
        lines.append("- 완료됨")
    elif run1 == "fail" or run2 == "fail":
        lines.append("- 실패")
    else:
        lines.append("- 구현됨")
    lines.append("")
    return lines


def main() -> None:
    args = parse_args()
    lines = build_lines(run1=args.run1, run2=args.run2)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
