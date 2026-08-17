from __future__ import annotations

import datetime
import json
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    old_bundle = repo / "evidence" / "device-validation-20260816-150743"
    new_bundle_rel = (repo / ".runtime" / "last_rerun_bundle_path.txt").read_text(encoding="utf-8").strip()
    new_bundle = repo / new_bundle_rel

    old_report = json.loads((old_bundle / "sorisae_probe_report.json").read_text(encoding="utf-8"))
    new_report = json.loads((new_bundle / "sorisae_probe_report.json").read_text(encoding="utf-8"))

    old_checks = {row.get("name", ""): row for row in old_report.get("checks", [])}
    new_checks = {row.get("name", ""): row for row in new_report.get("checks", [])}
    all_names = sorted(set(old_checks) | set(new_checks))

    lines: list[str] = []
    lines.append("# Device Validation Bundle Compare")
    lines.append("")
    lines.append(f"- old_bundle: {old_bundle.relative_to(repo)}")
    lines.append(f"- new_bundle: {new_bundle.relative_to(repo)}")
    lines.append(f"- old_probe_passed: {old_report.get('passed')}")
    lines.append(f"- new_probe_passed: {new_report.get('passed')}")
    lines.append("")
    lines.append("## Probe Check Diff")
    lines.append("| check | old_ok | new_ok | changed | old_detail | new_detail |")
    lines.append("|---|---:|---:|---:|---|---|")

    for name in all_names:
        old = old_checks.get(name, {})
        new = new_checks.get(name, {})
        old_ok = str(old.get("ok", "(missing)"))
        new_ok = str(new.get("ok", "(missing)"))
        changed = "yes" if old_ok != new_ok else "no"
        old_detail = str(old.get("detail", "")).replace("|", "/")
        new_detail = str(new.get("detail", "")).replace("|", "/")
        lines.append(f"| {name} | {old_ok} | {new_ok} | {changed} | {old_detail} | {new_detail} |")

    lines.append("")
    lines.append("## Auth E2E (rerun bundle)")
    lines.append("```json")
    lines.append((new_bundle / "auth_duplicate_login_e2e.json").read_text(encoding="utf-8").strip())
    lines.append("```")
    lines.append("")
    lines.append("## Runtime Tail (new)")
    lines.append("```text")
    tail = str(new_checks.get("adb_sorisae_runtime", {}).get("log_tail", ""))
    if len(tail) > 2500:
        tail = tail[:2500] + " ...[truncated]"
    lines.append(tail)
    lines.append("```")

    compare_path = repo / "evidence" / f"device-validation-compare-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    compare_path.write_text("\n".join(lines), encoding="utf-8")
    (repo / ".runtime" / "last_compare_report_path.txt").write_text(str(compare_path.relative_to(repo)), encoding="utf-8")

    print(f"COMPARE_REPORT={compare_path.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
