from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.auth import get_current_user


router = APIRouter(tags=["external-search"])


class ExternalSearchError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    http_status: int = 500
    details: Dict[str, Any] = Field(default_factory=dict)


class ExternalSearchMeta(BaseModel):
    provider: str
    engine: str
    query: str
    total_items: int
    elapsed_ms: float
    request_id: str


class ExternalSearchItem(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: str = ""
    source: Optional[str] = None
    published_at: Optional[str] = None
    thumbnail: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    price: Optional[str] = None
    channel: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ExternalSearchResponse(BaseModel):
    status: Literal["ok", "error"]
    endpoint: str
    data: List[ExternalSearchItem] = Field(default_factory=list)
    meta: Optional[ExternalSearchMeta] = None
    error: Optional[ExternalSearchError] = None


_ERROR_MAP: Dict[str, Dict[str, Any]] = {
    "MISSING_API_KEY": {
        "http_status": 401,
        "message": "Provider API key is missing.",
        "retryable": False,
    },
    "INVALID_PROVIDER": {
        "http_status": 400,
        "message": "Requested provider is not supported.",
        "retryable": False,
    },
    "UNSUPPORTED_PROVIDER": {
        "http_status": 400,
        "message": "Endpoint is not supported by the selected provider.",
        "retryable": False,
    },
    "INVALID_REQUEST": {
        "http_status": 400,
        "message": "Request parameter is invalid.",
        "retryable": False,
    },
    "UPSTREAM_AUTH_FAILED": {
        "http_status": 401,
        "message": "Upstream authentication failed.",
        "retryable": False,
    },
    "UPSTREAM_FORBIDDEN": {
        "http_status": 403,
        "message": "Upstream provider rejected the request.",
        "retryable": False,
    },
    "UPSTREAM_NOT_FOUND": {
        "http_status": 404,
        "message": "Upstream resource not found.",
        "retryable": False,
    },
    "RATE_LIMITED": {
        "http_status": 429,
        "message": "Rate limit exceeded.",
        "retryable": True,
    },
    "UPSTREAM_TIMEOUT": {
        "http_status": 504,
        "message": "Upstream provider timeout.",
        "retryable": True,
    },
    "UPSTREAM_ERROR": {
        "http_status": 502,
        "message": "Upstream provider error.",
        "retryable": True,
    },
    "UNKNOWN_ERROR": {
        "http_status": 500,
        "message": "Unknown internal error.",
        "retryable": False,
    },
}


def _resolve_provider(requested: str) -> str:
    normalized = str(requested or "auto").strip().lower()
    if normalized not in {"auto", "serpapi", "bing"}:
        return "invalid"
    if normalized != "auto":
        return normalized

    if str(os.getenv("SERPAPI_API_KEY", "")).strip():
        return "serpapi"
    if str(os.getenv("BING_SEARCH_API_KEY", "")).strip():
        return "bing"
    return "auto"


def _safe_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()  # type: ignore[call-arg]


def _error_response(
    *,
    endpoint: str,
    code: str,
    request_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> ExternalSearchResponse:
    mapped = _ERROR_MAP.get(code, _ERROR_MAP["UNKNOWN_ERROR"])
    elapsed_raw = details.get("elapsed_ms") if details else 0.0
    elapsed_ms = _to_float(elapsed_raw)
    payload = ExternalSearchResponse(
        status="error",
        endpoint=endpoint,
        data=[],
        meta=ExternalSearchMeta(
            provider=str(details.get("provider") if details else "unknown"),
            engine=str(details.get("engine") if details else "unknown"),
            query=str(details.get("query") if details else ""),
            total_items=0,
            elapsed_ms=elapsed_ms if elapsed_ms is not None else 0.0,
            request_id=request_id,
        ),
        error=ExternalSearchError(
            code=code,
            message=str(mapped["message"]),
            retryable=bool(mapped["retryable"]),
            http_status=int(mapped["http_status"]),
            details=details or {},
        ),
    )
    return payload


def _http_json(url: str, headers: Dict[str, str], timeout_sec: float) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _serpapi_call(engine: str, query: str, limit: int, timeout_sec: float, **extra: Any) -> Dict[str, Any]:
    api_key = str(os.getenv("SERPAPI_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("MISSING_API_KEY")

    params: Dict[str, Any] = {
        "engine": engine,
        "q": query,
        "hl": "ko",
        "gl": "kr",
        "api_key": api_key,
    }
    params.update(extra)
    if engine in {"google_news", "google_shopping", "youtube"}:
        params["num"] = max(1, min(limit, 20))

    query_string = urllib.parse.urlencode(params)
    url = f"https://serpapi.com/search.json?{query_string}"
    try:
        return _http_json(url, {"Accept": "application/json"}, timeout_sec)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("UPSTREAM_AUTH_FAILED") from exc
        if exc.code == 403:
            raise PermissionError("UPSTREAM_FORBIDDEN") from exc
        if exc.code == 404:
            raise FileNotFoundError("UPSTREAM_NOT_FOUND") from exc
        if exc.code == 429:
            raise RuntimeError("RATE_LIMITED") from exc
        raise RuntimeError("UPSTREAM_ERROR") from exc
    except urllib.error.URLError as exc:
        raise TimeoutError("UPSTREAM_TIMEOUT") from exc


def _bing_news_call(query: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    api_key = str(os.getenv("BING_SEARCH_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("MISSING_API_KEY")
    endpoint = str(os.getenv("BING_NEWS_ENDPOINT", "https://api.bing.microsoft.com/v7.0/news/search")).strip()
    params = urllib.parse.urlencode({"q": query, "count": max(1, min(limit, 20)), "mkt": "ko-KR"})
    url = f"{endpoint}?{params}"
    try:
        return _http_json(url, {"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"}, timeout_sec)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("UPSTREAM_AUTH_FAILED") from exc
        if exc.code == 403:
            raise PermissionError("UPSTREAM_FORBIDDEN") from exc
        if exc.code == 404:
            raise FileNotFoundError("UPSTREAM_NOT_FOUND") from exc
        if exc.code == 429:
            raise RuntimeError("RATE_LIMITED") from exc
        raise RuntimeError("UPSTREAM_ERROR") from exc
    except urllib.error.URLError as exc:
        raise TimeoutError("UPSTREAM_TIMEOUT") from exc


def _bing_image_call(query: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    api_key = str(os.getenv("BING_SEARCH_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("MISSING_API_KEY")
    endpoint = str(os.getenv("BING_IMAGE_ENDPOINT", "https://api.bing.microsoft.com/v7.0/images/search")).strip()
    params = urllib.parse.urlencode({"q": query, "count": max(1, min(limit, 20)), "mkt": "ko-KR"})
    url = f"{endpoint}?{params}"
    try:
        return _http_json(url, {"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"}, timeout_sec)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("UPSTREAM_AUTH_FAILED") from exc
        if exc.code == 403:
            raise PermissionError("UPSTREAM_FORBIDDEN") from exc
        if exc.code == 404:
            raise FileNotFoundError("UPSTREAM_NOT_FOUND") from exc
        if exc.code == 429:
            raise RuntimeError("RATE_LIMITED") from exc
        raise RuntimeError("UPSTREAM_ERROR") from exc
    except urllib.error.URLError as exc:
        raise TimeoutError("UPSTREAM_TIMEOUT") from exc


def _bing_video_call(query: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    api_key = str(os.getenv("BING_SEARCH_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("MISSING_API_KEY")
    endpoint = str(os.getenv("BING_VIDEO_ENDPOINT", "https://api.bing.microsoft.com/v7.0/videos/search")).strip()
    params = urllib.parse.urlencode({"q": query, "count": max(1, min(limit, 20)), "mkt": "ko-KR"})
    url = f"{endpoint}?{params}"
    try:
        return _http_json(url, {"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"}, timeout_sec)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("UPSTREAM_AUTH_FAILED") from exc
        if exc.code == 403:
            raise PermissionError("UPSTREAM_FORBIDDEN") from exc
        if exc.code == 404:
            raise FileNotFoundError("UPSTREAM_NOT_FOUND") from exc
        if exc.code == 429:
            raise RuntimeError("RATE_LIMITED") from exc
        raise RuntimeError("UPSTREAM_ERROR") from exc
    except urllib.error.URLError as exc:
        raise TimeoutError("UPSTREAM_TIMEOUT") from exc


def _parse_news(payload: Dict[str, Any], *, provider: str, limit: int) -> List[ExternalSearchItem]:
    if provider == "bing":
        values = payload.get("value") or []
        parsed: List[ExternalSearchItem] = []
        for item in values[:limit]:
            if not isinstance(item, dict):
                continue
            parsed.append(
                ExternalSearchItem(
                    title=str(item.get("name") or "Untitled"),
                    url=str(item.get("url") or "") or None,
                    snippet=str(item.get("description") or ""),
                    source=str((item.get("provider") or [{}])[0].get("name") if isinstance(item.get("provider"), list) and item.get("provider") else "") or None,
                    published_at=str(item.get("datePublished") or "") or None,
                    thumbnail=str((((item.get("image") or {}).get("thumbnail") or {}).get("contentUrl")) or "") or None,
                )
            )
        return parsed

    values = payload.get("news_results") or []
    parsed: List[ExternalSearchItem] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        raw_stories = item.get("stories")
        candidates: List[Any] = raw_stories if isinstance(raw_stories, list) and raw_stories else [item]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            source_obj = candidate.get("source")
            source_name = source_obj.get("name") if isinstance(source_obj, dict) else source_obj
            parsed.append(
                ExternalSearchItem(
                    title=str(candidate.get("title") or "Untitled"),
                    url=str(candidate.get("link") or "") or None,
                    snippet=str(candidate.get("snippet") or item.get("snippet") or ""),
                    source=str(source_name or "") or None,
                    published_at=str(candidate.get("date") or candidate.get("iso_date") or "") or None,
                    thumbnail=str(candidate.get("thumbnail") or candidate.get("thumbnail_small") or "") or None,
                )
            )
            if len(parsed) >= limit:
                return parsed
    return parsed


def _parse_maps_reviews(payload: Dict[str, Any], *, limit: int) -> List[ExternalSearchItem]:
    place_context_obj = payload.get("place_info") or payload.get("place_results") or payload.get("search_information") or {}
    place_context = place_context_obj if isinstance(place_context_obj, dict) else {}
    review_items = payload.get("reviews") or []
    if isinstance(review_items, list) and review_items:
        parsed: List[ExternalSearchItem] = []
        for item in review_items[:limit]:
            if not isinstance(item, dict):
                continue
            parsed.append(
                ExternalSearchItem(
                    title=str(item.get("user") or item.get("user_name") or "Reviewer"),
                    url=str(item.get("link") or "") or None,
                    snippet=str(item.get("snippet") or item.get("snippet_original") or ""),
                    published_at=str(item.get("date") or "") or None,
                    rating=_to_float(item.get("rating")),
                    source=str(place_context.get("title") or place_context.get("address") or "google-maps-review-detail") or "google-maps-review-detail",
                    extra={
                        "likes": item.get("likes"),
                        "photos": item.get("photos"),
                        "review_id": item.get("review_id"),
                        "reviewer_id": item.get("user_id") or item.get("local_guide"),
                        "response_from_owner": item.get("owner_answer") or item.get("owner_response"),
                        "place_id": place_context.get("place_id"),
                        "data_id": place_context.get("data_id"),
                        "address": place_context.get("address"),
                        "category": place_context.get("type") or place_context.get("category"),
                    },
                )
            )
        return parsed

    local_items = payload.get("local_results") or []
    parsed = []
    for item in local_items[:limit]:
        if not isinstance(item, dict):
            continue
        reviews_count: Optional[int] = None
        if item.get("reviews") is not None:
            reviews_count = _to_int(item.get("reviews"))
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("title") or "Untitled place"),
                url=str(item.get("website") or item.get("links") or "") or None,
                snippet=str(item.get("address") or item.get("type") or ""),
                source="google-maps",
                rating=_to_float(item.get("rating")),
                reviews_count=reviews_count,
                thumbnail=str(item.get("thumbnail") or "") or None,
                extra={
                    "phone": item.get("phone"),
                    "place_id": item.get("place_id"),
                    "data_id": item.get("data_id"),
                },
            )
        )
    return parsed


def _parse_images(payload: Dict[str, Any], *, provider: str, limit: int) -> List[ExternalSearchItem]:
    if provider != "bing":
        return []
    values = payload.get("value") or []
    parsed: List[ExternalSearchItem] = []
    for item in values[:limit]:
        if not isinstance(item, dict):
            continue
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("name") or "Untitled image"),
                url=str(item.get("hostPageUrl") or item.get("contentUrl") or "") or None,
                snippet=str(item.get("hostPageDisplayUrl") or item.get("accentColor") or ""),
                source=str(item.get("hostPageDomainFriendlyName") or "bing-images") or "bing-images",
                thumbnail=str(item.get("thumbnailUrl") or item.get("contentUrl") or "") or None,
                extra={
                    "content_url": item.get("contentUrl"),
                    "encoding_format": item.get("encodingFormat"),
                    "image_size": {"width": item.get("width"), "height": item.get("height")},
                },
            )
        )
    return parsed


def _parse_videos(payload: Dict[str, Any], *, provider: str, limit: int) -> List[ExternalSearchItem]:
    if provider != "bing":
        return []
    values = payload.get("value") or []
    parsed: List[ExternalSearchItem] = []
    for item in values[:limit]:
        if not isinstance(item, dict):
            continue
        creator_obj = item.get("creator")
        creator = creator_obj[0] if isinstance(creator_obj, list) and creator_obj and isinstance(creator_obj[0], dict) else {}
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("name") or "Untitled video"),
                url=str(item.get("hostPageUrl") or item.get("contentUrl") or "") or None,
                snippet=str(item.get("description") or ""),
                source=str(item.get("publisher") or item.get("hostPageDisplayUrl") or "bing-videos") or "bing-videos",
                published_at=str(item.get("datePublished") or "") or None,
                thumbnail=str(item.get("thumbnailUrl") or "") or None,
                channel=str(creator.get("name") or "") or None,
                extra={
                    "content_url": item.get("contentUrl"),
                    "duration": item.get("duration"),
                    "motion_thumbnail_url": item.get("motionThumbnailUrl"),
                    "view_count": item.get("viewCount"),
                },
            )
        )
    return parsed


def _extract_maps_place_candidate(payload: Dict[str, Any], place_id: str) -> Dict[str, Any]:
    normalized = place_id.strip()
    place_result = payload.get("place_results")
    if isinstance(place_result, dict):
        values = {
            str(place_result.get("place_id") or "").strip(),
            str(place_result.get("data_id") or "").strip(),
            str(place_result.get("cid") or place_result.get("data_cid") or "").strip(),
        }
        if normalized in values:
            return place_result

    candidates = payload.get("local_results") or []
    if not isinstance(candidates, list):
        return {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        values = {
            str(item.get("place_id") or "").strip(),
            str(item.get("data_id") or "").strip(),
            str(item.get("cid") or item.get("data_cid") or "").strip(),
        }
        if normalized in values:
            return item
    return {}


def _resolve_maps_review_payload(query: str, place_id: Optional[str], limit: int, timeout_sec: float) -> Dict[str, Any]:
    if not place_id:
        payload = _serpapi_call("google_maps", query, limit, timeout_sec)
        return {"engine": "google_maps", "payload": payload}

    lookup_query = query if query.strip() else place_id
    lookup_payload = _serpapi_call("google_maps", lookup_query, max(limit, 10), timeout_sec, place_id=place_id)
    place_candidate = _extract_maps_place_candidate(lookup_payload, place_id)
    resolved_data_id = str(place_candidate.get("data_id") or "").strip()
    if not resolved_data_id:
        raise FileNotFoundError("UPSTREAM_NOT_FOUND")
    review_query = str(place_candidate.get("title") or lookup_query)
    review_payload = _serpapi_call(
        "google_maps_reviews",
        review_query,
        limit,
        timeout_sec,
        data_id=resolved_data_id,
        sort_by="newestFirst",
    )

    place_info_obj = review_payload.get("place_info")
    if not isinstance(place_info_obj, dict):
        review_payload["place_info"] = {}
    review_payload["place_info"].update(
        {
            "place_id": place_candidate.get("place_id") or place_id,
            "data_id": resolved_data_id,
            "title": place_candidate.get("title") or review_payload["place_info"].get("title"),
            "address": place_candidate.get("address") or review_payload["place_info"].get("address"),
            "type": place_candidate.get("type") or review_payload["place_info"].get("type"),
            "rating": place_candidate.get("rating") or review_payload["place_info"].get("rating"),
            "reviews": place_candidate.get("reviews") or review_payload["place_info"].get("reviews"),
            "thumbnail": place_candidate.get("thumbnail") or review_payload["place_info"].get("thumbnail"),
            "phone": place_candidate.get("phone") or review_payload["place_info"].get("phone"),
        }
    )
    return {"engine": "google_maps_reviews", "payload": review_payload}


def _parse_youtube(payload: Dict[str, Any], *, limit: int) -> List[ExternalSearchItem]:
    values = payload.get("video_results") or payload.get("organic_results") or []
    parsed: List[ExternalSearchItem] = []
    for item in values[:limit]:
        if not isinstance(item, dict):
            continue
        channel_obj = item.get("channel")
        channel: Dict[str, Any] = channel_obj if isinstance(channel_obj, dict) else {}
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("title") or "Untitled"),
                url=str(item.get("link") or "") or None,
                snippet=str(item.get("description") or ""),
                channel=str(channel.get("name") or "") or None,
                published_at=str(item.get("published_date") or "") or None,
                thumbnail=str(item.get("thumbnail") or "") or None,
                extra={
                    "views": item.get("views"),
                    "length": item.get("length"),
                },
            )
        )
    return parsed


def _parse_trends(payload: Dict[str, Any], *, limit: int) -> List[ExternalSearchItem]:
    timeline = (((payload.get("interest_over_time") or {}).get("timeline_data")) or [])
    parsed: List[ExternalSearchItem] = []
    for item in timeline[:limit]:
        if not isinstance(item, dict):
            continue
        values = item.get("values") or []
        score: Optional[float] = None
        if isinstance(values, list) and values:
            raw_score = values[0].get("extracted_value") if isinstance(values[0], dict) else None
            try:
                score = float(raw_score) if raw_score is not None else None
            except (TypeError, ValueError):
                score = None
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("date") or item.get("timestamp") or "trend-point"),
                snippet=f"trend_score={score if score is not None else 'n/a'}",
                source="google-trends",
                rating=score,
                extra={"values": values},
            )
        )
    if parsed:
        return parsed

    related_queries = (payload.get("related_queries") or {}).get("rising") or []
    for item in related_queries[:limit]:
        if not isinstance(item, dict):
            continue
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("query") or "trend-query"),
                snippet=str(item.get("value") or ""),
                source="google-trends",
                extra={"link": item.get("link")},
            )
        )
    return parsed


def _parse_shopping(payload: Dict[str, Any], *, limit: int) -> List[ExternalSearchItem]:
    values = payload.get("shopping_results") or []
    parsed: List[ExternalSearchItem] = []
    for item in values[:limit]:
        if not isinstance(item, dict):
            continue
        parsed.append(
            ExternalSearchItem(
                title=str(item.get("title") or "Untitled product"),
                    url=str(item.get("link") or item.get("product_link") or "") or None,
                snippet=str(item.get("source") or ""),
                source=str(item.get("source") or "") or None,
                thumbnail=str(item.get("thumbnail") or "") or None,
                rating=_to_float(item.get("rating")),
                reviews_count=_to_int(item.get("reviews")),
                price=str(item.get("price") or "") or None,
                extra={
                    "delivery": item.get("delivery"),
                    "position": item.get("position"),
                    "old_price": item.get("old_price"),
                },
            )
        )
    return parsed


def _ok_response(
    *,
    endpoint: str,
    request_id: str,
    provider: str,
    engine: str,
    query: str,
    elapsed_ms: float,
    data: List[ExternalSearchItem],
) -> ExternalSearchResponse:
    return ExternalSearchResponse(
        status="ok",
        endpoint=endpoint,
        data=data,
        meta=ExternalSearchMeta(
            provider=provider,
            engine=engine,
            query=query,
            total_items=len(data),
            elapsed_ms=elapsed_ms,
            request_id=request_id,
        ),
    )


def _search_news(query: str, provider: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    if provider == "serpapi":
        return _serpapi_call("google_news", query, limit, timeout_sec)
    if provider == "bing":
        return _bing_news_call(query, limit, timeout_sec)
    raise ValueError("INVALID_PROVIDER")


def _search_images(query: str, provider: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    if provider == "bing":
        return _bing_image_call(query, limit, timeout_sec)
    raise ValueError("INVALID_PROVIDER")


def _search_videos(query: str, provider: str, limit: int, timeout_sec: float) -> Dict[str, Any]:
    if provider == "bing":
        return _bing_video_call(query, limit, timeout_sec)
    raise ValueError("INVALID_PROVIDER")


@router.get("/api/external-search/status-codes")
def external_search_status_codes(_current_user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    return {
        "status": "ok",
        "codes": _ERROR_MAP,
        "schema": {
            "status": "ok|error",
            "endpoint": "string",
            "data": "ExternalSearchItem[]",
            "meta": {
                "provider": "string",
                "engine": "string",
                "query": "string",
                "total_items": "number",
                "elapsed_ms": "number",
                "request_id": "string",
            },
            "error": {
                "code": "string",
                "message": "string",
                "retryable": "boolean",
                "http_status": "number",
                "details": "object",
            },
        },
    }


@router.get("/api/external-search/news", response_model=ExternalSearchResponse)
def external_search_news(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "invalid":
        return _error_response(endpoint="news", code="INVALID_PROVIDER", request_id=request_id, details={"provider": provider, "query": q})
    if resolved_provider == "auto":
        return _error_response(endpoint="news", code="MISSING_API_KEY", request_id=request_id, details={"provider": provider, "query": q})
    try:
        payload = _search_news(q, resolved_provider, limit, timeout_sec)
        data = _parse_news(payload, provider=resolved_provider, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="news",
            request_id=request_id,
            provider=resolved_provider,
            engine="google_news" if resolved_provider == "serpapi" else "bing_news",
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="news",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/maps-reviews", response_model=ExternalSearchResponse)
def external_search_maps_reviews(
    q: str = Query("", min_length=0),
    place_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider != "serpapi":
        return _error_response(endpoint="maps-reviews", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "query": q})
    if not q.strip() and not place_id:
        return _error_response(endpoint="maps-reviews", code="INVALID_REQUEST", request_id=request_id, details={"provider": resolved_provider, "query": q, "place_id": place_id})
    try:
        resolved = _resolve_maps_review_payload(q, place_id, limit, timeout_sec)
        payload = resolved["payload"]
        engine = str(resolved["engine"])
        data = _parse_maps_reviews(payload, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="maps-reviews",
            request_id=request_id,
            provider=resolved_provider,
            engine=engine,
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="maps-reviews",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "place_id": place_id, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/images", response_model=ExternalSearchResponse)
def external_search_images(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "invalid":
        return _error_response(endpoint="images", code="INVALID_PROVIDER", request_id=request_id, details={"provider": provider, "query": q})
    if resolved_provider != "bing":
        return _error_response(endpoint="images", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "query": q})
    try:
        payload = _search_images(q, resolved_provider, limit, timeout_sec)
        data = _parse_images(payload, provider=resolved_provider, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="images",
            request_id=request_id,
            provider=resolved_provider,
            engine="bing_images",
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="images",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/videos", response_model=ExternalSearchResponse)
def external_search_videos(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider == "invalid":
        return _error_response(endpoint="videos", code="INVALID_PROVIDER", request_id=request_id, details={"provider": provider, "query": q})
    if resolved_provider != "bing":
        return _error_response(endpoint="videos", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "query": q})
    try:
        payload = _search_videos(q, resolved_provider, limit, timeout_sec)
        data = _parse_videos(payload, provider=resolved_provider, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="videos",
            request_id=request_id,
            provider=resolved_provider,
            engine="bing_videos",
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="videos",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/youtube", response_model=ExternalSearchResponse)
def external_search_youtube(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider != "serpapi":
        return _error_response(endpoint="youtube", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "engine": "youtube", "query": q})
    try:
        engine = "youtube"
        try:
            payload = _serpapi_call("youtube", q, limit, timeout_sec)
        except Exception:
            # Fallback to Google Videos when YouTube engine is temporarily unavailable.
            payload = _serpapi_call("google_videos", q, limit, timeout_sec)
            engine = "google_videos"
        data = _parse_youtube(payload, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="youtube",
            request_id=request_id,
            provider=resolved_provider,
            engine=engine,
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="youtube",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "engine": "youtube", "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/trends", response_model=ExternalSearchResponse)
def external_search_trends(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider != "serpapi":
        return _error_response(endpoint="trends", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "query": q})
    try:
        payload = _serpapi_call("google_trends", q, limit, timeout_sec)
        data = _parse_trends(payload, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="trends",
            request_id=request_id,
            provider=resolved_provider,
            engine="google_trends",
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="trends",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )


@router.get("/api/external-search/shopping", response_model=ExternalSearchResponse)
def external_search_shopping(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    provider: str = Query("auto"),
    timeout_sec: float = Query(12.0, ge=2.0, le=30.0),
    _current_user: Any = Depends(get_current_user),
) -> ExternalSearchResponse:
    request_id = uuid4().hex
    started = time.perf_counter()
    resolved_provider = _resolve_provider(provider)
    if resolved_provider != "serpapi":
        return _error_response(endpoint="shopping", code="UNSUPPORTED_PROVIDER", request_id=request_id, details={"provider": resolved_provider, "query": q})
    try:
        payload = _serpapi_call("google_shopping", q, limit, timeout_sec)
        data = _parse_shopping(payload, limit=limit)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return _ok_response(
            endpoint="shopping",
            request_id=request_id,
            provider=resolved_provider,
            engine="google_shopping",
            query=q,
            elapsed_ms=elapsed_ms,
            data=data,
        )
    except Exception as exc:
        code = str(exc) if str(exc) in _ERROR_MAP else "UPSTREAM_ERROR"
        return _error_response(
            endpoint="shopping",
            code=code,
            request_id=request_id,
            details={"provider": resolved_provider, "query": q, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)},
        )
