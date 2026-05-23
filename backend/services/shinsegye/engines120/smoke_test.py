"""
소리새 120엔진 레일별 Smoke Test 자동화 스크립트
=========================================
레일 1개 = 20 슬롯 단위 import 검증.

실행 방법:
    # 전체 6레일 순서대로
    python smoke_test.py

    # 특정 레일만
    python smoke_test.py --rail RAIL-01

    # 실제 main() 호출 포함
    python smoke_test.py --no-dry-run

    # 결과를 JSON 파일로 저장
    python smoke_test.py --output smoke_results.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── 설정 ───────────────────────────────────────────────────────────────────
ENGINES_DIR = Path(__file__).resolve().parent
RAIL_RANGES: Dict[str, tuple[int, int]] = {
    "RAIL-01": (1, 20),
    "RAIL-02": (21, 40),
    "RAIL-03": (41, 60),
    "RAIL-04": (61, 80),
    "RAIL-05": (81, 100),
    "RAIL-06": (101, 120),
}
TIMEOUT_PER_SLOT = 5.0  # seconds


# ── 단일 슬롯 테스트 ─────────────────────────────────────────────────────
def _smoke_one_slot(slot_num: int, dry_run: bool = True, timeout: float = TIMEOUT_PER_SLOT) -> Dict[str, Any]:
    pattern = f"slot{slot_num:03d}_*.py"
    matches = sorted(ENGINES_DIR.glob(pattern))

    result: Dict[str, Any] = {
        "slot": slot_num,
        "file": None,
        "status": "not_found",
        "error": None,
        "imported": False,
        "executed": False,
    }

    if not matches:
        return result

    target = matches[0]
    result["file"] = target.name

    exc_holder: Dict[str, Any] = {}

    def _do_import(path: str, holder: Dict[str, Any]) -> None:
        try:
            spec = importlib.util.spec_from_file_location(f"smoke_{slot_num:03d}", path)
            if spec is None or spec.loader is None:
                holder["error"] = "spec 생성 실패"
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            holder["module"] = mod
            holder["ok"] = True
        except Exception as exc:  # noqa: BLE001
            holder["error"] = str(exc)
            holder["tb"] = traceback.format_exc(limit=3)

    t = threading.Thread(target=_do_import, args=(str(target), exc_holder), daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        result["status"] = "timeout"
        result["error"] = f"{timeout:.0f}s 초과"
        return result

    if not exc_holder.get("ok"):
        result["status"] = "failed"
        result["error"] = exc_holder.get("error", "unknown")
        return result

    result["imported"] = True

    if not dry_run:
        mod = exc_holder.get("module")
        fn = None
        if mod:
            fn = getattr(mod, "main", None) or getattr(mod, "run", None)
        if fn and callable(fn):
            try:
                fn()
                result["executed"] = True
                result["status"] = "passed"
            except Exception as exc:  # noqa: BLE001
                result["status"] = "exec_error"
                result["error"] = str(exc)
                return result
        else:
            result["status"] = "passed"  # import OK, no main
    else:
        result["status"] = "passed"

    return result


# ── 레일 단위 실행 ────────────────────────────────────────────────────────
def smoke_rail(rail_id: str, dry_run: bool = True, verbose: bool = True) -> Dict[str, Any]:
    key = rail_id.upper().strip()
    if key not in RAIL_RANGES:
        raise ValueError(f"알 수 없는 rail_id: {rail_id}")
    slot_start, slot_end = RAIL_RANGES[key]

    results: List[Dict[str, Any]] = []
    passed = failed = timeout = not_found = 0

    for slot_num in range(slot_start, slot_end + 1):
        r = _smoke_one_slot(slot_num, dry_run=dry_run)
        results.append(r)
        if r["status"] == "passed":
            passed += 1
        elif r["status"] == "timeout":
            timeout += 1
            failed += 1
        elif r["status"] == "not_found":
            not_found += 1
            failed += 1
        else:
            failed += 1

        if verbose:
            icon = "✓" if r["status"] == "passed" else ("⏱" if r["status"] == "timeout" else ("?" if r["status"] == "not_found" else "✗"))
            msg = f"  [{icon}] slot{slot_num:03d} {r['file'] or '(없음)':<50} {r['status']}"
            if r["error"]:
                msg += f"  — {r['error']}"
            print(msg)

    total = slot_end - slot_start + 1
    summary: Dict[str, Any] = {
        "rail_id": key,
        "slot_range": f"{slot_start}-{slot_end}",
        "total": total,
        "passed": passed,
        "failed": failed,
        "not_found": not_found,
        "timeout": timeout,
        "pass_rate_pct": round(passed / total * 100, 1),
        "dry_run": dry_run,
        "results": results,
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return summary


# ── 전체 실행 ─────────────────────────────────────────────────────────────
def smoke_all(dry_run: bool = True, verbose: bool = True) -> Dict[str, Any]:
    all_results: List[Dict[str, Any]] = []
    grand_passed = grand_failed = 0

    for rail_id in RAIL_RANGES:
        if verbose:
            print(f"\n{'='*60}")
            print(f"  {rail_id}  ({RAIL_RANGES[rail_id][0]}~{RAIL_RANGES[rail_id][1]})")
            print(f"{'='*60}")
        rail_result = smoke_rail(rail_id, dry_run=dry_run, verbose=verbose)
        all_results.append(rail_result)
        grand_passed += rail_result["passed"]
        grand_failed += rail_result["failed"]

    total = 120
    summary: Dict[str, Any] = {
        "status": "ok",
        "total_slots": total,
        "total_passed": grand_passed,
        "total_failed": grand_failed,
        "pass_rate_pct": round(grand_passed / total * 100, 1),
        "dry_run": dry_run,
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "rails": all_results,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"  전체 결과: 통과 {grand_passed}/120  ({summary['pass_rate_pct']}%)")
        print(f"{'='*60}\n")

    return summary


# ── CLI 진입점 ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="소리새 120엔진 smoke test")
    parser.add_argument("--rail", default=None, help="단일 레일 실행 (예: RAIL-01)")
    parser.add_argument("--no-dry-run", action="store_true", help="main()/run() 실제 호출 포함")
    parser.add_argument("--output", default=None, help="결과 JSON 저장 경로")
    parser.add_argument("--quiet", action="store_true", help="상세 출력 끄기")
    args = parser.parse_args()

    dry_run = not args.no_dry_run
    verbose = not args.quiet

    if args.rail:
        result = smoke_rail(args.rail, dry_run=dry_run, verbose=verbose)
        output = {"status": "ok", "rail": result}
    else:
        output = smoke_all(dry_run=dry_run, verbose=verbose)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"결과 저장: {out_path.resolve()}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
