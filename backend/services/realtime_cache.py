"""실시간 외부 API 응답 캐시 — 소스별 TTL 정책(컴플라이언스 §6).

목적
- 외부 실시간 API(OSM/Nominatim·SerpAPI·Bing·웹검색)의 반복 호출을 줄여
  레이트리밋(Nominatim 1req/s) 보호 + 비용 절감 + 응답 지연 완화.
- **약관상 캐시 보관 기한**을 코드로 강제: Google 위경도/지도 결과는 30일 초과 캐시 금지
  (Google Maps Platform Service Specific Terms §"No Caching" 예외 한도). 본 앱은 Google Maps
  그라운딩을 기본 비활성(VOICE_FRIEND_MAPS_GROUNDING=0)하므로 통상 적용되지 않으나, 활성 시에도
  상한을 넘지 못하도록 namespace 'maps' TTL 을 30일로 캡한다.

구현
- 기존 `backend/marketplace/cache_service.py`(Redis, fail-open) 재사용. Redis 미연결 시 그대로 통과(no-op).
- 결과가 truthy(비어있지 않음)일 때만 캐시 — 실패/빈 결과를 길게 물고 있지 않도록.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any, Callable, Iterable, Optional

logger = logging.getLogger(__name__)

# 하루(초)
_DAY = 86_400

# namespace -> 기본 TTL(초). 환경변수 REALTIME_CACHE_TTL_<NS>(대문자) 로 개별 오버라이드.
_DEFAULT_TTL = {
    "osm": 7 * _DAY,      # OSM/Nominatim 지오코딩·POI: 변화 느림 → 길게(레이트리밋 보호)
    "web": 600,          # 일반 웹/뉴스 검색: 10분
    "news": 600,         # 뉴스: 10분
    "weather": 600,      # 날씨: 10분
    "exchange": 600,     # 환율/시세: 10분
    "serp": 900,         # 기타 SerpAPI 엔진(영상/트렌드 등): 15분
    "maps": 30 * _DAY,   # Google 지도/위경도: 약관 상한 30일(초과 금지) — 기본 Maps off
    "media": 7 * _DAY,   # Wikimedia Commons/Wikidata 이미지·라이선스: 변화 느림(CC, 캐시 제약 없음)
}
# 약관상 절대 상한(초). 초과 설정은 이 값으로 캡.
_TTL_CEILING = {
    "maps": 30 * _DAY,
}

_DEFAULT_FALLBACK_TTL = 600

# 가벼운 인프로세스 히트/미스 카운터(운영 가시성).
_stats_lock = threading.Lock()
_stats = {"hit": 0, "miss": 0, "skip": 0}


def _cache_enabled() -> bool:
    return os.getenv("REALTIME_CACHE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off", ""}


def ttl_for(namespace: str) -> int:
    env = os.getenv(f"REALTIME_CACHE_TTL_{namespace.upper()}")
    if env is not None:
        try:
            ttl = int(env)
        except ValueError:
            ttl = _DEFAULT_TTL.get(namespace, _DEFAULT_FALLBACK_TTL)
    else:
        ttl = _DEFAULT_TTL.get(namespace, _DEFAULT_FALLBACK_TTL)
    ceiling = _TTL_CEILING.get(namespace)
    if ceiling is not None and ttl > ceiling:
        logger.warning(
            "[realtime_cache] ns=%s TTL %ds > 약관 상한 %ds → 캡 적용", namespace, ttl, ceiling
        )
        ttl = ceiling
    return max(1, ttl)


def _build_key(namespace: str, key_parts: Iterable[Any]) -> str:
    raw = "|".join(str(p) for p in key_parts)
    digest = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:32]
    return f"rtc:{namespace}:{digest}"


def get_stats() -> dict:
    with _stats_lock:
        snap = dict(_stats)
    total = snap["hit"] + snap["miss"]
    snap["hit_rate"] = round(snap["hit"] / total, 3) if total else 0.0
    return snap


def cached_fetch(
    namespace: str,
    key_parts: Iterable[Any],
    fetch_fn: Callable[[], Any],
    *,
    ttl: Optional[int] = None,
    enabled: bool = True,
) -> Any:
    """캐시 우선 외부호출 래퍼.

    - 캐시 히트 시 저장값 반환, 미스 시 fetch_fn() 실행 후 truthy 결과만 캐시.
    - Redis 미가용/비활성 시 fetch_fn() 을 그대로 호출(no-op 폴백).
    """
    if not enabled or not _cache_enabled():
        return fetch_fn()

    try:
        from backend.marketplace.cache_service import cache_service
    except Exception:
        return fetch_fn()

    key = _build_key(namespace, key_parts)
    try:
        hit = cache_service.get(key)
    except Exception:
        hit = None
    if hit is not None:
        with _stats_lock:
            _stats["hit"] += 1
        logger.debug("[realtime_cache] HIT ns=%s", namespace)
        return hit

    with _stats_lock:
        _stats["miss"] += 1
    value = fetch_fn()
    if value:  # truthy 결과만 저장(빈/실패 결과 장기 보관 방지)
        try:
            cache_service.set(key, value, ttl or ttl_for(namespace))
        except Exception as exc:
            with _stats_lock:
                _stats["skip"] += 1
            logger.debug("[realtime_cache] set 실패(ns=%s): %s", namespace, exc)
    return value
