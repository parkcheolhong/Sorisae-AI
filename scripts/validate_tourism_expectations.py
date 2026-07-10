"""관광 데이터 품질 검증 CLI — GE 호환 expectation suite 를 tourism_places 에 실행.

사용(호스트):
  $env:QDRANT_URL="http://127.0.0.1:6333"
  python scripts/validate_tourism_expectations.py [--min-rows 100] [--limit N]

종료코드: suite 전체 통과=0, 실패=1, 데이터 없음=2. 리포트는 reports/ 에 JSON 저장.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.tourism_kb.quality import load_points_from_qdrant, run_expectation_suite  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="tourism_places GE-style 품질 검증")
    ap.add_argument("--min-rows", type=int, default=100, help="최소 행 수 기대값")
    ap.add_argument("--limit", type=int, default=None, help="검사 행 수 상한(기본 전수)")
    args = ap.parse_args()

    rows = load_points_from_qdrant(limit=args.limit)
    if not rows:
        print("[expectations] 데이터 없음 — QDRANT_URL/컬렉션을 확인하세요.")
        return 2

    report = run_expectation_suite(rows, min_rows=args.min_rows)

    print(f"[expectations] rows={report['element_count']} "
          f"pass={report['successful_expectations']}/{report['evaluated_expectations']} "
          f"suite_success={report['success']} ({report['run_time_sec']}s)")
    for r in report["results"]:
        flag = "OK " if r["success"] else "FAIL"
        res = r["result"]
        detail = res.get("observed_value")
        if detail is None:
            detail = f"bad={res.get('unexpected_count')}/{res.get('element_count')} ({res.get('unexpected_percent')}%)"
        print(f"  [{flag}] {r['expectation_type']} {r['kwargs']} → {detail}")

    out_dir = Path(__file__).resolve().parents[1] / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "tourism_expectations_report.json"
    report["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[expectations] 리포트 저장: {out_path}")

    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
