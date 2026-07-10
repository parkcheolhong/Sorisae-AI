from backend.admin_router import _build_travel_fallback_alerts, _compute_travel_fallback_payload


def test_fallback_ratio_represents_rule_level_ratio_not_runtime_failure_rate():
    rules = [
        {
            "country_code": "KR",
            "city_code": None,
            "fallback_partner_ids": ["partner-a"],
            "active": True,
        },
        {
            "country_code": "JP",
            "city_code": None,
            "fallback_partner_ids": [],
            "active": True,
        },
        {
            "country_code": "KR",
            "city_code": "SEL",
            "fallback_partner_ids": ["partner-b"],
            "active": True,
        },
    ]

    payload = _compute_travel_fallback_payload(
        rules,
        default_partner_recommendation_total=40,
        recommendation_total=50,
    )

    # Current KPI semantics: city-scoped rules are also counted in country rules
    # when country_code is present. So 2 fallback-enabled rules / 3 rules = 0.6667.
    assert payload["country_rule_count"] == 3
    assert payload["country_fallback_ratio"] == 0.6667

    # City fallback ratio = 1 fallback-enabled city rule / 1 city rule = 1.0
    assert payload["city_rule_count"] == 1
    assert payload["city_fallback_ratio"] == 1.0

    # Default partner usage keeps event-based ratio semantics
    assert payload["default_partner_usage_ratio"] == 0.8


def test_fallback_alerts_follow_threshold_semantics_for_warning_and_ok():
    fallback_payload = {
        "country_fallback_ratio": 1.0,
        "city_fallback_ratio": 0.5,
        "default_partner_usage_ratio": 0.96,
    }

    strict_thresholds = {
        "fallback_country_ratio_max": 0.8,
        "fallback_city_ratio_max": 0.8,
        "default_partner_usage_ratio_max": 0.95,
    }
    alerts_strict = _build_travel_fallback_alerts(fallback_payload, strict_thresholds)
    alert_map_strict = {item["id"]: item for item in alerts_strict}

    assert alert_map_strict["country_fallback_ratio"]["severity"] == "warning"
    assert alert_map_strict["city_fallback_ratio"]["severity"] == "ok"
    assert alert_map_strict["default_partner_usage_ratio"]["severity"] == "warning"

    relaxed_thresholds = {
        "fallback_country_ratio_max": 1.0,
        "fallback_city_ratio_max": 0.5,
        "default_partner_usage_ratio_max": 1.0,
    }
    alerts_relaxed = _build_travel_fallback_alerts(fallback_payload, relaxed_thresholds)
    alert_map_relaxed = {item["id"]: item for item in alerts_relaxed}

    # Boundary value is ok because warning triggers only on strict greater-than
    assert alert_map_relaxed["country_fallback_ratio"]["severity"] == "ok"
    assert alert_map_relaxed["city_fallback_ratio"]["severity"] == "ok"
    assert alert_map_relaxed["default_partner_usage_ratio"]["severity"] == "ok"
