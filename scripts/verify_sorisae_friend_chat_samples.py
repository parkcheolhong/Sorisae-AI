"""Run 5 Sorisae friend-chat API sample checks with request payloads and expected checklist.

Usage:
  .\\.venv\\Scripts\\python scripts\\verify_sorisae_friend_chat_samples.py
  .\\.venv\\Scripts\\python scripts\\verify_sorisae_friend_chat_samples.py --base-url http://127.0.0.1:8000
  .\\.venv\\Scripts\\python scripts\\verify_sorisae_friend_chat_samples.py --dry-run

This script calls:
  POST /api/llm/voice/friend-chat

It includes 5 practical samples:
  1) nearby place query (ko)
  2) region overview query (ko)
  3) emotional companion chat (ko)
  4) nearby practical query (en)
  5) safe night travel query (ja)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_PATH = "/api/llm/voice/friend-chat"


@dataclass
class CheckItem:
    name: str
    kind: str
    value: Any
    required: bool = True


@dataclass
class SampleCase:
    case_id: str
    category: str
    payload: dict[str, Any]
    checklist: list[CheckItem]


def _contains_any(text: str, candidates: list[str]) -> bool:
    low = text.lower()
    return any(token.lower() in low for token in candidates)


def _contains_all(text: str, candidates: list[str]) -> bool:
    low = text.lower()
    return all(token.lower() in low for token in candidates)


def _has_question(text: str) -> bool:
    return "?" in text or "？" in text


def _evaluate_check(item: CheckItem, response_text: str, body: dict[str, Any]) -> tuple[bool, str]:
    if item.kind == "min_length":
        limit = int(item.value)
        ok = len(response_text.strip()) >= limit
        return ok, f"len(response_text) >= {limit}"

    if item.kind == "contains_any":
        tokens = list(item.value)
        ok = _contains_any(response_text, tokens)
        return ok, f"response_text contains any of {tokens}"

    if item.kind == "contains_all":
        tokens = list(item.value)
        ok = _contains_all(response_text, tokens)
        return ok, f"response_text contains all of {tokens}"

    if item.kind == "question_follow_up":
        ok = _has_question(response_text)
        return ok, "response_text includes a follow-up question"

    if item.kind == "detected_language_in":
        allowed = set(item.value)
        detected = str(body.get("detected_language") or "").lower()
        ok = (not detected) or (detected in allowed)
        return ok, f"detected_language in {sorted(allowed)} (empty allowed for text input)"

    if item.kind == "not_contains_any":
        tokens = list(item.value)
        ok = not _contains_any(response_text, tokens)
        return ok, f"response_text does not contain any of {tokens}"

    return False, f"unsupported check kind: {item.kind}"


def _build_samples() -> list[SampleCase]:
    return [
        SampleCase(
            case_id="sample-01-nearby-ko",
            category="근처 질의",
            payload={
                "transcript": "여기 근처 카페 추천해줘.",
                "language": "ko",
                "tts": False,
                "region_hint": "명동",
                "country_code": "KR",
                "latitude": 37.5636,
                "longitude": 126.9834,
                "accuracy_m": 25,
                "conversation": [],
            },
            checklist=[
                CheckItem("최소 길이", "min_length", 30, True),
                CheckItem("근거리 맥락 어휘", "contains_any", ["근처", "가까", "도보", "주변"], True),
                CheckItem("후속 질문", "question_follow_up", True, False),
            ],
        ),
        SampleCase(
            case_id="sample-02-overview-ko",
            category="지역 개요 질의",
            payload={
                "transcript": "오사카 2박 3일 여행 동선 개요를 짜줘.",
                "language": "ko",
                "tts": False,
                "region_hint": "Osaka",
                "country_code": "JP",
                "latitude": 34.6937,
                "longitude": 135.5023,
                "accuracy_m": 30,
                "conversation": [],
            },
            checklist=[
                CheckItem("최소 길이", "min_length", 45, True),
                CheckItem("일정/동선 맥락", "contains_any", ["동선", "일정", "1일", "2일", "코스"], True),
                CheckItem("후속 질문", "question_follow_up", True, False),
            ],
        ),
        SampleCase(
            case_id="sample-03-emotion-ko",
            category="감정 대화 질의",
            payload={
                "transcript": "요즘 너무 지치고 마음이 복잡해.",
                "language": "ko",
                "tts": False,
                "region_hint": "서울",
                "country_code": "KR",
                "latitude": 37.5665,
                "longitude": 126.9780,
                "accuracy_m": 40,
                "conversation": [],
            },
            checklist=[
                CheckItem("최소 길이", "min_length", 30, True),
                CheckItem("공감 어휘", "contains_any", ["힘들", "지쳤", "괜찮", "버거"], True),
                CheckItem("후속 질문", "question_follow_up", True, True),
                CheckItem("기계적 문구 회피", "not_contains_any", ["저는 ai", "도움이 필요하면 다시 입력"], False),
            ],
        ),
        SampleCase(
            case_id="sample-04-nearby-en",
            category="nearby query",
            payload={
                "transcript": "Find me a pharmacy near me.",
                "language": "en",
                "tts": False,
                "region_hint": "Shinjuku",
                "country_code": "JP",
                "latitude": 35.6896,
                "longitude": 139.7006,
                "accuracy_m": 30,
                "conversation": [],
            },
            checklist=[
                CheckItem("최소 길이", "min_length", 25, True),
                CheckItem("영어 근거리 맥락", "contains_any", ["near", "nearby", "walk", "closest"], True),
                CheckItem("감지 언어 합리성", "detected_language_in", ["", "en"], False),
            ],
        ),
        SampleCase(
            case_id="sample-05-safety-ja",
            category="安全/夜間観光",
            payload={
                "transcript": "この辺で夜に安全な観光スポットある？",
                "language": "ja",
                "tts": False,
                "region_hint": "Shibuya",
                "country_code": "JP",
                "latitude": 35.6580,
                "longitude": 139.7016,
                "accuracy_m": 35,
                "conversation": [],
            },
            checklist=[
                CheckItem("최소 길이", "min_length", 25, True),
                CheckItem("안전 맥락", "contains_any", ["安全", "注意", "夜", "人通り"], True),
                CheckItem("후속 질문", "question_follow_up", True, False),
                CheckItem("감지 언어 합리성", "detected_language_in", ["", "ja"], False),
            ],
        ),
    ]


def _post_json(url: str, payload: dict[str, Any], timeout_sec: float) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status = int(resp.status)
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            return status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return int(exc.code), body


def _render_checklist_result(
    sample: SampleCase,
    status: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    text = str(body.get("response_text") or "")
    check_results: list[dict[str, Any]] = []
    hard_fail = False

    for item in sample.checklist:
        ok, detail = _evaluate_check(item, text, body)
        state = "PASS" if ok else ("FAIL" if item.required else "WARN")
        if (not ok) and item.required:
            hard_fail = True
        check_results.append(
            {
                "name": item.name,
                "required": item.required,
                "status": state,
                "detail": detail,
            }
        )

    overall = "PASS"
    if status != 200:
        overall = "FAIL"
    elif hard_fail:
        overall = "FAIL"
    elif any(row["status"] == "WARN" for row in check_results):
        overall = "PASS_WITH_WARN"

    return {
        "case_id": sample.case_id,
        "category": sample.category,
        "request": sample.payload,
        "http_status": status,
        "response": {
            "transcript": body.get("transcript"),
            "response_text": body.get("response_text"),
            "detected_language": body.get("detected_language"),
            "audio_format": body.get("audio_format"),
        },
        "checks": check_results,
        "overall": overall,
    }


def _print_case_summary(row: dict[str, Any]) -> None:
    print(f"\n[{row['case_id']}] {row['category']} | HTTP {row['http_status']} | {row['overall']}")
    response_text = str(row["response"].get("response_text") or "").strip()
    snippet = response_text.replace("\n", " ")[:220]
    print(f"- response: {snippet}")
    for c in row["checks"]:
        required = "required" if c["required"] else "optional"
        print(f"  - {c['status']:<14} [{required}] {c['name']} :: {c['detail']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sorisae friend-chat 5-sample API verification")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=float, default=45.0, help="HTTP timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="Print 5 request payloads/checklists only")
    parser.add_argument(
        "--out",
        default=".tmp/sorisae_friend_chat_samples_report.json",
        help="Output JSON report path",
    )
    args = parser.parse_args()

    samples = _build_samples()

    if args.dry_run:
        print("[DRY-RUN] 5 sample payloads + expected checklist")
        for sample in samples:
            print(f"\n[{sample.case_id}] {sample.category}")
            print(json.dumps(sample.payload, ensure_ascii=False, indent=2))
            for check in sample.checklist:
                print(
                    f"- {'required' if check.required else 'optional'} | {check.name} "
                    f"| kind={check.kind} | value={check.value}"
                )
        return 0

    endpoint = args.base_url.rstrip("/") + API_PATH
    report_rows: list[dict[str, Any]] = []

    print(f"Target endpoint: {endpoint}")
    for sample in samples:
        status, body = _post_json(endpoint, sample.payload, args.timeout)
        row = _render_checklist_result(sample, status, body)
        report_rows.append(row)
        _print_case_summary(row)

    summary = {
        "timestamp": int(time.time()),
        "endpoint": endpoint,
        "total": len(report_rows),
        "pass": sum(1 for r in report_rows if r["overall"] == "PASS"),
        "pass_with_warn": sum(1 for r in report_rows if r["overall"] == "PASS_WITH_WARN"),
        "fail": sum(1 for r in report_rows if r["overall"] == "FAIL"),
    }
    report = {"summary": summary, "results": report_rows}

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== FINAL SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report saved: {out_path}")

    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
