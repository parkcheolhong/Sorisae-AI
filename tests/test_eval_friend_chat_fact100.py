from collections import Counter, defaultdict

from scripts.eval_friend_chat_fact100 import (
    COUNTRY_FACTS,
    REQUIRED_TOPICS,
    build_fact100_cases,
    summarize_topic_results,
    validate_fact100_cases,
)


def test_fact100_cases_cover_20_countries_x_5_topics():
    cases = build_fact100_cases()
    assert len(cases) == 100

    by_country = Counter(case.country for case in cases)
    assert set(by_country) == set(COUNTRY_FACTS)
    assert all(count == 5 for count in by_country.values())

    by_country_topic = defaultdict(set)
    for case in cases:
        by_country_topic[case.country].add(case.topic)

# sourcery skip: no-loop-in-tests
    for country in COUNTRY_FACTS:
        assert by_country_topic[country] == set(REQUIRED_TOPICS)


def test_fact100_cases_are_tourism_framed_and_validated():
    cases = build_fact100_cases()
    validate_fact100_cases(cases)
    assert all(case.prompt for case in cases)
    assert all(case.expected_keywords for case in cases)
    assert all(case.country in case.prompt.lower() for case in cases)
    assert sum(1 for case in cases if case.expect_uncertainty) == 40


def test_topic_summary_aggregates_by_topic():
    summary = summarize_topic_results(
        [
            {
                "topic": "travel_currency",
                "ok": True,
                "keyword_ok": True,
                "expect_uncertainty": False,
                "uncertainty_detected": False,
            },
            {
                "topic": "travel_currency",
                "ok": False,
                "keyword_ok": False,
                "expect_uncertainty": False,
                "uncertainty_detected": False,
            },
            {
                "topic": "live_weather_uncertainty",
                "ok": True,
                "keyword_ok": True,
                "expect_uncertainty": True,
                "uncertainty_detected": True,
            },
        ]
    )

    assert summary["travel_currency"] == {
        "total": 2,
        "ok": 1,
        "keyword_ok": 1,
        "uncertainty_ok": 0,
    }
    assert summary["live_weather_uncertainty"] == {
        "total": 1,
        "ok": 1,
        "keyword_ok": 1,
        "uncertainty_ok": 1,
    }