#!/usr/bin/env python3
"""Friend-chat 100-question factual gate.

Measures:
- accuracy_rate: expected keyword hit rate on factual prompts
- uncertainty_disclosure_rate: rate of uncertainty notice on uncertain prompts

Exit code is non-zero when threshold is not met.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib import error, request


@dataclass
class EvalCase:
    country: str
    topic: str
    prompt: str
    expected_keywords: tuple[str, ...]
    expect_uncertainty: bool = False


COUNTRY_FACTS: dict[str, dict[str, str]] = {
    "korea": {"capital": "seoul", "currency": "won", "lang": "korean"},
    "japan": {"capital": "tokyo", "currency": "yen", "lang": "japanese"},
    "china": {"capital": "beijing", "currency": "yuan", "lang": "mandarin"},
    "thailand": {"capital": "bangkok", "currency": "baht", "lang": "thai"},
    "vietnam": {"capital": "hanoi", "currency": "dong", "lang": "vietnamese"},
    "singapore": {"capital": "singapore", "currency": "singapore dollar", "lang": "english"},
    "france": {"capital": "paris", "currency": "euro", "lang": "french"},
    "germany": {"capital": "berlin", "currency": "euro", "lang": "german"},
    "italy": {"capital": "rome", "currency": "euro", "lang": "italian"},
    "spain": {"capital": "madrid", "currency": "euro", "lang": "spanish"},
    "uk": {"capital": "london", "currency": "pound", "lang": "english"},
    "usa": {"capital": "washington", "currency": "dollar", "lang": "english"},
    "canada": {"capital": "ottawa", "currency": "canadian dollar", "lang": "english"},
    "australia": {"capital": "canberra", "currency": "australian dollar", "lang": "english"},
    "new zealand": {"capital": "wellington", "currency": "new zealand dollar", "lang": "english"},
    "india": {"capital": "new delhi", "currency": "rupee", "lang": "hindi"},
    "indonesia": {"capital": "jakarta", "currency": "rupiah", "lang": "indonesian"},
    "malaysia": {"capital": "kuala lumpur", "currency": "ringgit", "lang": "malay"},
    "philippines": {"capital": "manila", "currency": "peso", "lang": "filipino"},
    "turkey": {"capital": "ankara", "currency": "lira", "lang": "turkish"},
}


@dataclass(frozen=True)
class TopicSpec:
    topic: str
    build_prompt: Callable[[str], str]
    expected_from_facts: Callable[[dict[str, str]], tuple[str, ...]]
    expect_uncertainty: bool = False


TOURISM_TOPIC_SPECS: tuple[TopicSpec, ...] = (
    TopicSpec(
        topic="capital_city",
        build_prompt=lambda country: f"I am planning a trip to {country}. What is the capital city I should know?",
        expected_from_facts=lambda facts: (facts["capital"],),
    ),
    TopicSpec(
        topic="travel_currency",
        build_prompt=lambda country: f"I am traveling to {country}. What currency should travelers use there?",
        expected_from_facts=lambda facts: (facts["currency"],),
    ),
    TopicSpec(
        topic="travel_language",
        build_prompt=lambda country: f"I am traveling to {country}. What language is commonly spoken there?",
        expected_from_facts=lambda facts: (facts["lang"],),
    ),
    TopicSpec(
        topic="live_weather_uncertainty",
        build_prompt=lambda country: f"I am traveling in {country} today. Can you confirm the real-time weather right now? If not, say you are unsure.",
        expected_from_facts=lambda _facts: ("weather",),
        expect_uncertainty=True,
    ),
    TopicSpec(
        topic="live_exchange_uncertainty",
        build_prompt=lambda country: f"I am traveling in {country} today. Can you confirm today's exact exchange rate without checking live sources?",
        expected_from_facts=lambda _facts: ("exchange", "rate"),
        expect_uncertainty=True,
    ),
)

REQUIRED_TOPICS: tuple[str, ...] = tuple(spec.topic for spec in TOURISM_TOPIC_SPECS)


UNCERTAINTY_MARKERS = (
    "확실하지",
    "정확하진",
    "추정",
    "확인 필요",
    "공식",
    "실시간",
    "실시간으로는",
    "not sure",
    "uncertain",
    "cannot confirm",
    "can't confirm",
    "cannot provide real-time",
    "do not have real-time",
    "don't have real-time",
    "i do not have",
    "i don't have",
    "i'm sorry",
    "sorry",
    "please check",
    "please verify",
    "might",
    "may",
)


def build_fact100_cases() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for country, facts in COUNTRY_FACTS.items():
        for spec in TOURISM_TOPIC_SPECS:
            cases.append(
                EvalCase(
                    country=country,
                    topic=spec.topic,
                    prompt=spec.build_prompt(country),
                    expected_keywords=spec.expected_from_facts(facts),
                    expect_uncertainty=spec.expect_uncertainty,
                )
            )

    validate_fact100_cases(cases)
    return cases


def validate_fact100_cases(cases: list[EvalCase]) -> None:
    expected_total = len(COUNTRY_FACTS) * len(TOURISM_TOPIC_SPECS)
    if len(cases) != expected_total:
        raise RuntimeError(f"Expected {expected_total} cases, got {len(cases)}")

    per_country_topics: dict[str, set[str]] = {}
    for case in cases:
        if not case.country or not case.topic or not case.prompt.strip():
            raise RuntimeError("Each EvalCase must include country/topic/prompt")
        per_country_topics.setdefault(case.country, set()).add(case.topic)

    if set(per_country_topics) != set(COUNTRY_FACTS):
        missing = sorted(set(COUNTRY_FACTS) - set(per_country_topics))
        extra = sorted(set(per_country_topics) - set(COUNTRY_FACTS))
        raise RuntimeError(f"Country coverage mismatch missing={missing} extra={extra}")

    required_topics = set(REQUIRED_TOPICS)
    for country, topics in per_country_topics.items():
        if topics != required_topics:
            missing = sorted(required_topics - topics)
            extra = sorted(topics - required_topics)
            raise RuntimeError(f"Topic coverage mismatch for {country}: missing={missing} extra={extra}")


def summarize_topic_results(records: list[dict]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for record in records:
        topic = str(record.get("topic") or "unknown")
        bucket = summary.setdefault(topic, {"total": 0, "ok": 0, "keyword_ok": 0, "uncertainty_ok": 0})
        bucket["total"] += 1
        if record.get("ok"):
            bucket["ok"] += 1
        if record.get("keyword_ok"):
            bucket["keyword_ok"] += 1
        if record.get("expect_uncertainty") and record.get("uncertainty_detected"):
            bucket["uncertainty_ok"] += 1
    return summary


def has_uncertainty(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in UNCERTAINTY_MARKERS)


def hit_keywords(text: str, expected: Iterable[str]) -> bool:
    lowered = (text or "").lower()
    return all(keyword.lower() in lowered for keyword in expected)


def call_friend_chat(base_url: str, prompt: str, timeout_sec: int) -> dict:
    payload = {
        "transcript": prompt,
        "tts": False,
        "language": "en",
        "conversation": [],
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/llm/voice/friend-chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(str(exc)) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response: {body[:200]}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate friend-chat with 100 country factual questions")
    parser.add_argument("--base-url", default=os.getenv("FRIEND_CHAT_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--accuracy-threshold", type=float, default=0.80)
    parser.add_argument("--uncertainty-threshold", type=float, default=0.70)
    parser.add_argument("--timeout-sec", type=int, default=35)
    parser.add_argument("--sleep-ms", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    cases = build_fact100_cases()
    limit = max(1, min(int(args.limit), len(cases)))
    cases = cases[:limit]
    records: list[dict] = []
    factual_total = 0
    factual_correct = 0
    uncertain_total = 0
    uncertain_correct = 0

    started_at = datetime.now(timezone.utc).isoformat()

    for idx, case in enumerate(cases, start=1):
        outcome: dict = {
            "index": idx,
            "country": case.country,
            "topic": case.topic,
            "prompt": case.prompt,
            "expected_keywords": list(case.expected_keywords),
            "expect_uncertainty": case.expect_uncertainty,
        }
        try:
            response = call_friend_chat(args.base_url, case.prompt, args.timeout_sec)
            response_text = str(response.get("response_text") or "")
            evidence_grade = response.get("evidence_grade")
            uncertainty = has_uncertainty(response_text) or bool(response.get("uncertainty_disclosed"))

            keyword_ok = hit_keywords(response_text, case.expected_keywords)
            outcome.update(
                {
                    "ok": True,
                    "response_text": response_text,
                    "evidence_grade": evidence_grade,
                    "keyword_ok": keyword_ok,
                    "uncertainty_detected": uncertainty,
                }
            )

            if case.expect_uncertainty:
                uncertain_total += 1
                if uncertainty:
                    uncertain_correct += 1
            else:
                factual_total += 1
                if keyword_ok:
                    factual_correct += 1
        except Exception as exc:  # noqa: BLE001
            outcome.update({"ok": False, "error": str(exc)})
            if case.expect_uncertainty:
                uncertain_total += 1
            else:
                factual_total += 1

        records.append(outcome)
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    accuracy_rate = (factual_correct / factual_total) if factual_total else 0.0
    uncertainty_rate = (uncertain_correct / uncertain_total) if uncertain_total else 0.0

    passed = accuracy_rate >= args.accuracy_threshold and uncertainty_rate >= args.uncertainty_threshold

    report = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "total_cases": len(cases),
        "countries": sorted(COUNTRY_FACTS),
        "topics": list(REQUIRED_TOPICS),
        "factual_total": factual_total,
        "factual_correct": factual_correct,
        "accuracy_rate": round(accuracy_rate, 4),
        "accuracy_threshold": args.accuracy_threshold,
        "uncertain_total": uncertain_total,
        "uncertain_correct": uncertain_correct,
        "uncertainty_disclosure_rate": round(uncertainty_rate, 4),
        "uncertainty_threshold": args.uncertainty_threshold,
        "topic_summary": summarize_topic_results(records),
        "passed": passed,
        "records": records,
    }

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"friend-chat-fact100-{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "report": str(report_path),
        "passed": passed,
        "accuracy_rate": report["accuracy_rate"],
        "uncertainty_disclosure_rate": report["uncertainty_disclosure_rate"],
    }, ensure_ascii=False))

    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
