#!/usr/bin/env python3
"""Analyze real-device face/sorisae turn timing from ReactNativeJS logs.

Expected input lines include:
- [FACE_CONVERSATION] {"event":"...", ...}
- [COMPANION_VOICE_CALL] {"event":"...", ...}

Primary KPI:
- segment_response roundtrip_ms per route(translate/sorisae)
- fallback latency from last vad_end -> segment_response
    when roundtrip_ms is absent
- cut/wait instability counters
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

LOG_RE = re.compile(
    r"^(?P<ts>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}).*?"
    r"\[(?P<tag>FACE_CONVERSATION|COMPANION_VOICE_CALL)\]\s+"
    r"(?P<payload>\{.*\})\s*$"
)

LOG_RE_QUOTED = re.compile(
    r"^(?P<ts>\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}).*?"
    r"'\[(?P<tag>FACE_CONVERSATION|COMPANION_VOICE_CALL)\]'\s*,\s*"
    r"'(?P<payload>\{.*\})'\s*$"
)


@dataclass
class ParsedEvent:
    ts: datetime
    tag: str
    payload: dict[str, Any]


def parse_line(line: str, year: int) -> ParsedEvent | None:
    text = line.strip()
    m = LOG_RE.match(text) or LOG_RE_QUOTED.match(text)
    if not m:
        return None
    try:
        ts = datetime.strptime(
            f"{year}-{m.group('ts')}",
            "%Y-%m-%d %H:%M:%S.%f",
        )
        payload = json.loads(m.group("payload"))
        if not isinstance(payload, dict):
            return None
        return ParsedEvent(ts=ts, tag=m.group("tag"), payload=payload)
    except (ValueError, json.JSONDecodeError):
        return None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return math.nan
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * (p / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return float(values[lo])
    frac = idx - lo
    return float(values[lo] + (values[hi] - values[lo]) * frac)


def summarize_latencies(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "avg_ms": math.nan,
            "p50_ms": math.nan,
            "p95_ms": math.nan,
            "max_ms": math.nan,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "avg_ms": round(mean(ordered), 1),
        "p50_ms": round(median(ordered), 1),
        "p95_ms": round(percentile(ordered, 95), 1),
        "max_ms": round(max(ordered), 1),
    }


def build_report(
    events: list[ParsedEvent],
    face_ok_min: int,
    sorisae_ok_min: int,
    face_p95_max_ms: int,
    sorisae_p95_max_ms: int,
    max_cut_signals: int,
) -> dict[str, Any]:
    face_route_ms: list[float] = []
    sorisae_route_ms: list[float] = []
    face_ok = 0
    sorisae_ok = 0

    last_vad_end_ts: datetime | None = None
    fallback_used = 0

    counters = {
        "vad_flush_deferred": 0,
        "silero_speech_end_deferred": 0,
        "segment_skip_silent": 0,
        "sorisae_segment_skip_preupload": 0,
        "scan_segment_too_short": 0,
        "capture_blocked_speaking": 0,
        "mic_watchdog_recover": 0,
    }

    for ev in events:
        event_name = str(ev.payload.get("event", ""))

        if event_name in counters:
            counters[event_name] += 1

        if ev.tag == "FACE_CONVERSATION" and event_name == "vad_end":
            last_vad_end_ts = ev.ts
            continue

        if ev.tag == "FACE_CONVERSATION" and event_name == "segment_response":
            ok = bool(ev.payload.get("ok"))
            route = str(ev.payload.get("route") or "")
            rt = ev.payload.get("roundtrip_ms")
            rt_ms: float | None

            if isinstance(rt, (int, float)) and float(rt) > 0:
                rt_ms = float(rt)
            elif last_vad_end_ts is not None:
                rt_ms = (ev.ts - last_vad_end_ts).total_seconds() * 1000.0
                fallback_used += 1
            else:
                rt_ms = None

            if ok and route == "translate":
                face_ok += 1
                if rt_ms is not None:
                    face_route_ms.append(rt_ms)
            elif ok and route == "sorisae":
                sorisae_ok += 1
                if rt_ms is not None:
                    sorisae_route_ms.append(rt_ms)

    face_summary = summarize_latencies(face_route_ms)
    sorisae_summary = summarize_latencies(sorisae_route_ms)

    cut_signal_count = (
        counters["vad_flush_deferred"]
        + counters["silero_speech_end_deferred"]
        + counters["segment_skip_silent"]
        + counters["sorisae_segment_skip_preupload"]
        + counters["scan_segment_too_short"]
    )

    def is_pass_latency(summary: dict[str, Any], threshold: int) -> bool:
        p95 = summary.get("p95_ms")
        if not isinstance(p95, (int, float)) or math.isnan(float(p95)):
            return False
        return float(p95) <= threshold

    checks = {
        "face_ok_turns": {
            "expected_min": face_ok_min,
            "actual": face_ok,
            "pass": face_ok >= face_ok_min,
        },
        "sorisae_ok_turns": {
            "expected_min": sorisae_ok_min,
            "actual": sorisae_ok,
            "pass": sorisae_ok >= sorisae_ok_min,
        },
        "face_p95_roundtrip_ms": {
            "max": face_p95_max_ms,
            "actual": face_summary.get("p95_ms"),
            "pass": is_pass_latency(face_summary, face_p95_max_ms),
        },
        "sorisae_p95_roundtrip_ms": {
            "max": sorisae_p95_max_ms,
            "actual": sorisae_summary.get("p95_ms"),
            "pass": is_pass_latency(sorisae_summary, sorisae_p95_max_ms),
        },
        "cut_signals": {
            "max": max_cut_signals,
            "actual": cut_signal_count,
            "pass": cut_signal_count <= max_cut_signals,
        },
    }

    overall_pass = all(bool(v.get("pass")) for v in checks.values())

    return {
        "overall_pass": overall_pass,
        "timing": {
            "face_translate": face_summary,
            "sorisae_chat": sorisae_summary,
            "fallback_roundtrip_count": fallback_used,
        },
        "instability_counters": counters,
        "cut_signal_total": cut_signal_count,
        "checks": checks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    face = report["timing"]["face_translate"]
    sorisae = report["timing"]["sorisae_chat"]
    face_row = (
        f"| face_translate | {face['count']} | {face['avg_ms']} | "
        f"{face['p50_ms']} | {face['p95_ms']} | {face['max_ms']} |"
    )
    sorisae_row = (
        f"| sorisae_chat | {sorisae['count']} | {sorisae['avg_ms']} | "
        f"{sorisae['p50_ms']} | {sorisae['p95_ms']} | {sorisae['max_ms']} |"
    )
    lines: list[str] = [
        "# Face + Sorisae Turn Timing Report",
        "",
        f"- overall_pass: {'PASS' if report['overall_pass'] else 'FAIL'}",
        (
            "- fallback_roundtrip_count: "
            f"{report['timing']['fallback_roundtrip_count']}"
        ),
        "",
        "## Timing",
        "",
        "| route | count | avg_ms | p50_ms | p95_ms | max_ms |",
        "|---|---:|---:|---:|---:|---:|",
        face_row,
        sorisae_row,
        "",
        "## Stability Counters",
        "",
    ]
    counter_lines = [
        f"- {key}: {val}"
        for key, val in report["instability_counters"].items()
    ]
    lines.extend(counter_lines)

    lines.extend(["", "## Checks", ""])
    checks = report["checks"]
    for key, item in checks.items():
        state = 'PASS' if item['pass'] else 'FAIL'
        lines.append(f"- {key}: {state} (actual={item['actual']})")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze face/sorisae turn timing "
            "from adb logcat dump."
        )
    )
    parser.add_argument(
        "--log",
        required=True,
        help="Path to log file captured from adb logcat",
    )
    parser.add_argument("--out", help="Optional output JSON path")
    parser.add_argument(
        "--out-md",
        help="Optional output Markdown summary path",
    )
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--face-ok-min", type=int, default=1)
    parser.add_argument("--sorisae-ok-min", type=int, default=1)
    parser.add_argument("--face-p95-max-ms", type=int, default=9000)
    parser.add_argument("--sorisae-p95-max-ms", type=int, default=12000)
    parser.add_argument("--max-cut-signals", type=int, default=4)
    args = parser.parse_args()

    path = Path(args.log)
    if not path.is_file():
        raise SystemExit(f"log file not found: {path}")

    events: list[ParsedEvent] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parsed = parse_line(line, args.year)
        if parsed is not None:
            events.append(parsed)

    report = build_report(
        events,
        face_ok_min=args.face_ok_min,
        sorisae_ok_min=args.sorisae_ok_min,
        face_p95_max_ms=args.face_p95_max_ms,
        sorisae_p95_max_ms=args.sorisae_p95_max_ms,
        max_cut_signals=args.max_cut_signals,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.out:
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        Path(args.out).write_text(output, encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")

    return 0 if report.get("overall_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
