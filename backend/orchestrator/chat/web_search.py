from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, List

from .models import WebGroundingItem


def _env_bool(name: str, default: bool) -> bool:
    value = str(os.getenv(name, "")).strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def should_use_web_search(message: str, message_kind: str) -> bool:
    normalized = " ".join(str(message or "").strip().split()).lower()
    if not normalized:
        return False
    if normalized.startswith(("/search", "/news")):
        return True
    if message_kind not in {"question", "directive"}:
        return False

    keywords = [
        "최신",
        "지금",
        "현재",
        "오늘",
        "올해",
        "트렌드",
        "뉴스",
        "발표",
        "업데이트",
        "release",
        "breaking",
        "recent",
        "latest",
        "today",
        "2025",
        "2026",
        "2027",
    ]
    return any(token in normalized for token in keywords)


def fetch_web_grounding(
    query: str,
    *,
    max_items: int = 5,
    timeout_sec: float = 8.0,
    logger: Any = None,
) -> List[WebGroundingItem]:
    if not _env_bool("WEB_SEARCH_ENABLED", True):
        return []

    provider = str(os.getenv("WEB_SEARCH_PROVIDER", "auto")).strip().lower()
    bing_key = str(os.getenv("BING_SEARCH_API_KEY", "")).strip()
    serp_key = str(os.getenv("SERPAPI_API_KEY", "")).strip()

    if provider == "off":
        return []

    if provider == "auto":
        if bing_key:
            provider = "bing"
        elif serp_key:
            provider = "serpapi"
        else:
            return []

    if provider == "bing":
        return _search_bing(query, bing_key, max_items=max_items, timeout_sec=timeout_sec, logger=logger)
    if provider == "serpapi":
        return _search_serpapi(query, serp_key, max_items=max_items, timeout_sec=timeout_sec, logger=logger)
    return []


def _search_bing(
    query: str,
    api_key: str,
    *,
    max_items: int,
    timeout_sec: float,
    logger: Any,
) -> List[WebGroundingItem]:
    if not api_key:
        return []
    endpoint = str(
        os.getenv("BING_SEARCH_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")
    ).strip()
    params = urllib.parse.urlencode({"q": query, "count": max(1, min(max_items, 10)), "mkt": "ko-KR"})
    req = urllib.request.Request(
        f"{endpoint}?{params}",
        headers={"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        if logger:
            logger.warning("web search(bing) failed: %s", exc)
        return []

    values = (((payload or {}).get("webPages") or {}).get("value") or [])
    results: List[WebGroundingItem] = []
    for item in values[:max_items]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip() or None
        title = str(item.get("name") or "").strip() or "제목 없음"
        snippet = str(item.get("snippet") or "").strip()
        domain = None
        if url:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or None
        if not snippet:
            continue
        results.append(
            WebGroundingItem(
                title=title,
                url=url,
                snippet=snippet,
                domain=domain,
                source_type="web-search-bing",
                trust_score=0.72,
            )
        )
    return results


def _search_serpapi(
    query: str,
    api_key: str,
    *,
    max_items: int,
    timeout_sec: float,
    logger: Any,
) -> List[WebGroundingItem]:
    if not api_key:
        return []
    params = urllib.parse.urlencode(
        {
            "q": query,
            "hl": "ko",
            "gl": "kr",
            "num": max(1, min(max_items, 10)),
            "api_key": api_key,
        }
    )
    url = f"https://serpapi.com/search.json?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        if logger:
            logger.warning("web search(serpapi) failed: %s", exc)
        return []

    values = (payload or {}).get("organic_results") or []
    results: List[WebGroundingItem] = []
    for item in values[:max_items]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip() or "제목 없음"
        snippet = str(item.get("snippet") or "").strip()
        raw_url = str(item.get("link") or "").strip()
        domain = str(item.get("displayed_link") or "").strip() or None
        if not snippet:
            continue
        results.append(
            WebGroundingItem(
                title=title,
                url=raw_url or None,
                snippet=snippet,
                domain=domain,
                source_type="web-search-serpapi",
                trust_score=0.68,
            )
        )
    return results


def build_web_grounding_block(results: List[WebGroundingItem]) -> str:
    if not results:
        return ""
    lines = ["[웹 검색 근거]"]
    for idx, item in enumerate(results[:5], start=1):
        lines.append(f"{idx}. {item.title}")
        if item.url:
            lines.append(f"   - URL: {item.url}")
        lines.append(f"   - 요약: {item.snippet}")
        if item.domain:
            lines.append(f"   - 출처: {item.domain}")
    lines.append("위 검색 근거를 우선 사용하되, 불확실하면 불확실성을 명시하세요.")
    return "\n".join(lines)
