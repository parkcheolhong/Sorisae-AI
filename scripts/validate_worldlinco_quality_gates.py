from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
RELAY_DIR = ROOT / "evidence" / "voip-voice-relay-orchestrator"
ROUTING_CASES_PATH = (
    ROOT
    / "backend"
    / "tests"
    / "fixtures"
    / "voice_gateway_routing_false_positive_cases.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_fact100_report() -> tuple[Path | None, dict | None]:
    candidates = sorted(
        REPORTS_DIR.glob("friend-chat-fact100-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        data = _load_json(path)
        if data.get("total_cases") == 100:
            return path, data
    return None, None


def _latest_relay_runs(limit: int = 2) -> list[tuple[Path, dict]]:
    results: list[tuple[Path, dict]] = []
    runs = sorted(
        RELAY_DIR.glob("run_*/summary.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in runs:
        data = _load_json(path)
        if data.get("hard_pass") and data.get("relay_pass"):
            results.append((path, data))
        if len(results) >= limit:
            break
    return results


def _routing_regression_case_count() -> int:
    if not ROUTING_CASES_PATH.is_file():
        return 0
    data = _load_json(ROUTING_CASES_PATH)
    if not isinstance(data, list):
        return 0
    return len(data)


def main() -> int:
    findings: list[str] = []

    fact_path, fact = _latest_fact100_report()
    if not fact_path or not fact:
        findings.append("missing 100-case fact100 report")
    elif not fact.get("passed"):
        findings.append(f"fact100 gate failed: {fact_path}")

    relay_runs = _latest_relay_runs(limit=2)
    if len(relay_runs) < 2:
        findings.append("need 2 consecutive passing relay probe runs")

    routing_case_count = _routing_regression_case_count()
    if routing_case_count != 50:
        findings.append(
            "routing regression case count must be 50 "
            f"(got {routing_case_count})"
        )

    summary = {
        "fact100_report": (
            str(fact_path.relative_to(ROOT)) if fact_path else None
        ),
        "fact100_passed": bool(fact and fact.get("passed")),
        "relay_runs": [str(path.relative_to(ROOT)) for path, _ in relay_runs],
        "relay_two_passes": len(relay_runs) >= 2,
        "routing_regression_cases": (
            str(ROUTING_CASES_PATH.relative_to(ROOT))
            if ROUTING_CASES_PATH.exists()
            else None
        ),
        "routing_case_count": routing_case_count,
        "passed": not findings,
        "findings": findings,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
