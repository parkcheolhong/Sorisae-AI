#!/usr/bin/env python3
"""Compare two face/sorisae timing reports (e.g. version 301 vs 300)."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid json object: {path}")
    return data


def as_float(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    val = float(value)
    return None if math.isnan(val) else val


def delta(new_val: Any, old_val: Any) -> float | None:
    n = as_float(new_val)
    o = as_float(old_val)
    return None if (n is None or o is None) else round(n - o, 1)


def get(report: dict[str, Any], *keys: str) -> Any:
    cur: Any = report
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def route_summary(report: dict[str, Any], route_key: str) -> dict[str, Any]:
    return {
        "count": get(report, "timing", route_key, "count"),
        "avg_ms": get(report, "timing", route_key, "avg_ms"),
        "p50_ms": get(report, "timing", route_key, "p50_ms"),
        "p95_ms": get(report, "timing", route_key, "p95_ms"),
        "max_ms": get(report, "timing", route_key, "max_ms"),
    }


def build_compare(
    newer: dict[str, Any],
    older: dict[str, Any],
    newer_meta: dict[str, Any] | None,
    older_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    n_face = route_summary(newer, "face_translate")
    o_face = route_summary(older, "face_translate")
    n_sor = route_summary(newer, "sorisae_chat")
    o_sor = route_summary(older, "sorisae_chat")

    keys = [
        "vad_flush_deferred",
        "silero_speech_end_deferred",
        "segment_skip_silent",
        "sorisae_segment_skip_preupload",
        "scan_segment_too_short",
        "capture_blocked_speaking",
        "mic_watchdog_recover",
    ]

    counters = {}
    for k in keys:
        n = get(newer, "instability_counters", k)
        o = get(older, "instability_counters", k)
        counters[k] = {
            "new": n,
            "old": o,
            "delta": delta(n, o),
        }

    return {
        "new": {
            "meta": newer_meta or {},
            "overall_pass": get(newer, "overall_pass"),
            "timing": {
                "face_translate": n_face,
                "sorisae_chat": n_sor,
                "cut_signal_total": get(newer, "cut_signal_total"),
            },
        },
        "old": {
            "meta": older_meta or {},
            "overall_pass": get(older, "overall_pass"),
            "timing": {
                "face_translate": o_face,
                "sorisae_chat": o_sor,
                "cut_signal_total": get(older, "cut_signal_total"),
            },
        },
        "delta": {
            "face_translate": {
                "count": delta(n_face["count"], o_face["count"]),
                "avg_ms": delta(n_face["avg_ms"], o_face["avg_ms"]),
                "p50_ms": delta(n_face["p50_ms"], o_face["p50_ms"]),
                "p95_ms": delta(n_face["p95_ms"], o_face["p95_ms"]),
                "max_ms": delta(n_face["max_ms"], o_face["max_ms"]),
            },
            "sorisae_chat": {
                "count": delta(n_sor["count"], o_sor["count"]),
                "avg_ms": delta(n_sor["avg_ms"], o_sor["avg_ms"]),
                "p50_ms": delta(n_sor["p50_ms"], o_sor["p50_ms"]),
                "p95_ms": delta(n_sor["p95_ms"], o_sor["p95_ms"]),
                "max_ms": delta(n_sor["max_ms"], o_sor["max_ms"]),
            },
            "cut_signal_total": delta(
                get(newer, "cut_signal_total"),
                get(older, "cut_signal_total"),
            ),
            "instability_counters": counters,
        },
    }


def to_md(compare: dict[str, Any]) -> str:
    new_meta = compare["new"]["meta"]
    old_meta = compare["old"]["meta"]
    face_delta = compare["delta"]["face_translate"]
    sorisae_delta = compare["delta"]["sorisae_chat"]

    new_line = (
        f"- new: label={new_meta.get('label', '')}, "
        f"serial={new_meta.get('serial', '')}, "
        f"versionCode={new_meta.get('app_version_code', '')}, "
        f"model={new_meta.get('device_model', '')}"
    )
    old_line = (
        f"- old: label={old_meta.get('label', '')}, "
        f"serial={old_meta.get('serial', '')}, "
        f"versionCode={old_meta.get('app_version_code', '')}, "
        f"model={old_meta.get('device_model', '')}"
    )

    face_row = (
        f"| face_translate | {face_delta.get('count')} "
        f"| {face_delta.get('avg_ms')} | {face_delta.get('p50_ms')} "
        f"| {face_delta.get('p95_ms')} | {face_delta.get('max_ms')} |"
    )
    sorisae_row = (
        f"| sorisae_chat | {sorisae_delta.get('count')} "
        f"| {sorisae_delta.get('avg_ms')} | {sorisae_delta.get('p50_ms')} "
        f"| {sorisae_delta.get('p95_ms')} | {sorisae_delta.get('max_ms')} |"
    )
    cut_row = (
        "| cut_signal_total "
        f"| {compare['delta'].get('cut_signal_total')} |  |  |  |  |"
    )
    counter_lines = [
        f"- {key}: new={item.get('new')} old={item.get('old')} "
        f"delta={item.get('delta')}"
        for key, item in compare["delta"]["instability_counters"].items()
    ]

    lines: list[str] = [
        "# Voice Timing Compare (new vs old)",
        "",
        "## Device/App",
        "",
        new_line,
        old_line,
        "",
        "## Timing Delta (new - old)",
        "",
        "| route | count | avg_ms | p50_ms | p95_ms | max_ms |",
        "|---|---:|---:|---:|---:|---:|",
        face_row,
        sorisae_row,
        cut_row,
        "",
        "## Instability Counter Delta",
        "",
        *counter_lines,
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two face/sorisae timing report.json files."
    )
    parser.add_argument("--new-report", required=True)
    parser.add_argument("--old-report", required=True)
    parser.add_argument("--new-meta")
    parser.add_argument("--old-meta")
    parser.add_argument("--out")
    parser.add_argument("--out-md")
    args = parser.parse_args()

    new_report = load_json(args.new_report)
    old_report = load_json(args.old_report)
    new_meta = load_json(args.new_meta) if args.new_meta else None
    old_meta = load_json(args.old_meta) if args.old_meta else None

    compare = build_compare(new_report, old_report, new_meta, old_meta)
    rendered = json.dumps(compare, ensure_ascii=False, indent=2)
    print(rendered)

    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(to_md(compare), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
