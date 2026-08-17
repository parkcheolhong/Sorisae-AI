from __future__ import annotations

import os
from typing import Any, Tuple


def get_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(min_value, min(parsed, max_value))


def order_duration_seconds(order: Any, default_seconds: int) -> int:
    raw_duration = getattr(order, "duration_seconds", None)
    if raw_duration is None:
        return int(default_seconds)
    try:
        return max(15, min(180, int(raw_duration)))
    except (TypeError, ValueError):
        return int(default_seconds)


def recommended_cut_count(duration_seconds: int) -> int:
    return max(1, int(round(max(15, duration_seconds) / 5.0)))


def cut_count_bounds(duration_seconds: int) -> Tuple[int, int]:
    recommended = recommended_cut_count(duration_seconds)
    return max(1, recommended - 2), max(recommended + 2, recommended)


def minimum_product_image_count_for_duration(duration_seconds: int) -> int:
    return max(3, min(24, int(round(max(15, duration_seconds) / 6.0))))


def marketplace_ad_quality_brief(duration_seconds: int) -> str:
    cut_count = recommended_cut_count(duration_seconds)
    min_images = minimum_product_image_count_for_duration(duration_seconds)
    return (
        f"minimum {cut_count} cinematic cuts with {min_images}+ distinct product/context images, "
        "premium cinematic storytelling, multilingual subtitle readability, and final CTA must all pass"
    )


def get_marketplace_retention_days() -> int:
    return get_int_env("MARKETPLACE_RETENTION_DAYS", 30, 1, 365)


def get_marketplace_temp_retention_days() -> int:
    return get_int_env("MARKETPLACE_TEMP_RETENTION_DAYS", 7, 1, 90)


def get_marketplace_cleanup_interval_sec() -> int:
    return get_int_env("MARKETPLACE_CLEANUP_INTERVAL_SEC", 3600, 60, 86400)


def get_ad_download_min_notice_minutes() -> int:
    return get_int_env("AD_DOWNLOAD_MIN_NOTICE_MINUTES", 60, 0, 10080)


def get_ad_download_window_days() -> int:
    return get_int_env("AD_DOWNLOAD_WINDOW_DAYS", 30, 1, 365)


def get_ad_download_max_count() -> int:
    return get_int_env("AD_DOWNLOAD_MAX_COUNT", 2, 1, 20)
