from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import queue
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests
from fastapi import HTTPException

from . import models
from .ad_order_policy import (
    cut_count_bounds as _policy_cut_count_bounds,
    get_ad_download_max_count as _policy_get_ad_download_max_count,
    get_ad_download_min_notice_minutes as _policy_get_ad_download_min_notice_minutes,
    get_ad_download_window_days as _policy_get_ad_download_window_days,
    get_int_env as _policy_get_int_env,
    get_marketplace_cleanup_interval_sec as _policy_get_marketplace_cleanup_interval_sec,
    get_marketplace_retention_days as _policy_get_marketplace_retention_days,
    get_marketplace_temp_retention_days as _policy_get_marketplace_temp_retention_days,
    marketplace_ad_quality_brief as _policy_marketplace_ad_quality_brief,
    order_duration_seconds as _policy_order_duration_seconds,
    recommended_cut_count as _policy_recommended_cut_count,
)
from .marketplace_storage_service import (
    _resolve_marketplace_temp_root,
    _resolve_marketplace_upload_root,
    _slugify_text,
)
from backend.secret_store import read_secret_env

logger = logging.getLogger(__name__)

MARKETPLACE_QUALITY_PASS_SCORE = 70.0
MARKETPLACE_MAX_AUTO_QUALITY_RETRIES = 1

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_ad_order_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
_cleanup_lock = threading.Lock()
_last_cleanup_epoch_sec = 0.0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def _get_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    return _policy_get_int_env(name, default, min_value, max_value)


AD_TOTAL_SECONDS = _get_int_env("AD_TOTAL_SECONDS", 60, 15, 180)
AD_FRAME_HINTS_PER_SECOND = 8
AD_TOTAL_FRAME_HINT = AD_TOTAL_SECONDS * AD_FRAME_HINTS_PER_SECOND
AD_CUT_COUNT = _get_int_env("AD_CUT_COUNT", 12, 1, 180)
AD_CUT_SECONDS = max(1, AD_TOTAL_SECONDS // AD_CUT_COUNT)
MARKETPLACE_AD_QUALITY_CRITERIA = [
    "첫 3초 안에 브랜드/상품 훅이 보여야 한다.",
    f"{AD_TOTAL_SECONDS}초 본편은 1초당 {AD_FRAME_HINTS_PER_SECOND}장, 총 {AD_TOTAL_FRAME_HINT}장 고정 규격을 유지한다.",
    "상품은 대부분의 컷에서 보이거나 명시적으로 참조되어야 한다.",
    "후반부에는 사용 장면, 신뢰 포인트, CTA가 순서대로 정리되어야 한다.",
    "자막/내레이션/장면 메시지는 서로 충돌하지 않아야 한다.",
]

DEDICATED_STATUS_ACCEPTED = {"accepted", "queued", "processing", "running", "completed", "failed", "error"}
DEDICATED_STATUS_COMPLETED = {"completed", "success", "done"}
DEDICATED_STATUS_FAILED = {"failed", "error"}


# ---------------------------------------------------------------------------
# Policy wrappers
# ---------------------------------------------------------------------------

def _order_duration_seconds(order: models.AdVideoOrder) -> int:
    return _policy_order_duration_seconds(order, AD_TOTAL_SECONDS)


def _recommended_cut_count(duration_seconds: int) -> int:
    return _policy_recommended_cut_count(duration_seconds)


def _cut_count_bounds(duration_seconds: int) -> tuple[int, int]:
    return _policy_cut_count_bounds(duration_seconds)


def _marketplace_ad_quality_brief(duration_seconds: int) -> str:
    return _policy_marketplace_ad_quality_brief(duration_seconds)


def _ad_variation_seed(order: models.AdVideoOrder, index: int) -> int:
    public_job_id = str(getattr(order, "public_job_id", "") or "")
    material = f"{order.id}:{public_job_id}:{index}:marketplace-ad"
    return int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:8], 16)


def _order_cut_count(order: models.AdVideoOrder) -> int:
    duration = _order_duration_seconds(order)
    minimum, maximum = _cut_count_bounds(duration)
    recommended = _recommended_cut_count(duration)
    try:
        value = int(
            getattr(order, "cut_count", recommended) or recommended
        )
    except Exception:
        value = recommended
    return max(minimum, min(maximum, value))


def _order_cut_seconds(order: models.AdVideoOrder) -> int:
    duration = _order_duration_seconds(order)
    cut_count = _order_cut_count(order)
    return max(1, int(round(duration / max(1, cut_count))))


def _order_subtitle_speed(order: models.AdVideoOrder) -> float:
    try:
        value = float(getattr(order, "subtitle_speed", 1.0) or 1.0)
    except Exception:
        value = 1.0
    value = max(0.5, min(2.0, value))
    return round(value, 1)


def _order_audio_volume(order: models.AdVideoOrder) -> int:
    try:
        value = int(getattr(order, "audio_volume", 100) or 100)
    except Exception:
        value = 100
    value = max(0, min(200, value))
    return int(round(value / 5.0) * 5)


def _order_bgm_enabled(order: models.AdVideoOrder) -> bool:
    raw = (os.getenv("MARKETPLACE_AD_BGM_ENABLED", "true") or "true")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _order_bgm_volume(order: models.AdVideoOrder) -> int:
    raw = (os.getenv("MARKETPLACE_AD_BGM_VOLUME", "38") or "38").strip()
    try:
        value = int(raw)
    except Exception:
        value = 38
    return max(0, min(100, value))


def _infer_bgm_mood(*values: Optional[str]) -> str:
    text = " ".join(str(value or "").lower() for value in values)
    if any(keyword in text for keyword in [
        "premium", "luxury", "studio", "elegant", "high-end", "gold",
    ]):
        return "premium"
    if any(keyword in text for keyword in [
        "sale", "launch", "dynamic", "sport", "active", "energy",
        "energetic", "boost",
    ]):
        return "upbeat"
    if any(keyword in text for keyword in [
        "beauty", "calm", "natural", "wellness", "soft", "relax",
        "clean", "serene",
    ]):
        return "calm"
    if any(keyword in text for keyword in [
        "tech", "digital", "future", "futuristic", "smart", "ai",
        "modern", "neon",
    ]):
        return "tech"
    return "corporate"


def _order_bgm_mood(order: models.AdVideoOrder) -> str:
    return _infer_bgm_mood(
        getattr(order, "title", ""),
        getattr(order, "background_prompt", ""),
        getattr(order, "caption_text", ""),
    )


def _bgm_profile(mood: str) -> Dict[str, Any]:
    profiles: Dict[str, Dict[str, Any]] = {
        "premium": {
            "expr": "0.20*sin(2*PI*196*t)+0.12*sin(2*PI*246.94*t)+0.08*sin(2*PI*329.63*t)+0.04*sin(2*PI*98*t)",
            "lowpass": 3400,
        },
        "upbeat": {
            "expr": "0.18*sin(2*PI*220*t)+0.12*sin(2*PI*330*t)+0.08*sin(2*PI*440*t)+0.05*sin(2*PI*660*t)",
            "lowpass": 4200,
        },
        "calm": {
            "expr": "0.18*sin(2*PI*174.61*t)+0.10*sin(2*PI*220*t)+0.07*sin(2*PI*261.63*t)+0.03*sin(2*PI*87.31*t)",
            "lowpass": 3000,
        },
        "tech": {
            "expr": "0.16*sin(2*PI*207.65*t)+0.11*sin(2*PI*311.13*t)+0.07*sin(2*PI*415.3*t)+0.05*sin(2*PI*622.25*t)",
            "lowpass": 4600,
        },
        "corporate": {
            "expr": "0.19*sin(2*PI*196*t)+0.11*sin(2*PI*293.66*t)+0.07*sin(2*PI*392*t)+0.04*sin(2*PI*98*t)",
            "lowpass": 3600,
        },
    }
    return profiles.get(mood, profiles["corporate"])


def _bgm_lavfi_source(duration_seconds: int, mood: str) -> str:
    profile = _bgm_profile(mood)
    return (
        "aevalsrc="
        f"exprs='{profile['expr']}|{profile['expr']}':"
        f"s=44100:d={max(1, int(duration_seconds))}"
    )


def _order_render_quality(order: models.AdVideoOrder) -> str:
    value = str(getattr(order, "render_quality", "high") or "high").strip().lower()
    if value not in {"standard", "high", "ultra"}:
        return "high"
    return value


def _stability_profile_for_order(order: models.AdVideoOrder) -> str:
    duration = _order_duration_seconds(order)
    cut_count = _order_cut_count(order)
    quality = _order_render_quality(order)
    motion_profile = _motion_profile_for_order(order)
    if quality == "ultra" or motion_profile == "youtube_web" or duration >= 30 or cut_count > 12:
        return "stable_90"
    return "default"


def _effective_cut_count_for_order(order: models.AdVideoOrder) -> int:
    cut_count = _order_cut_count(order)
    raw_storyboard = getattr(order, "storyboard_json", None)
    if raw_storyboard:
        try:
            parsed = json.loads(raw_storyboard)
            if isinstance(parsed, list) and parsed:
                return max(1, len(parsed))
        except Exception:
            pass
    return cut_count


def _effective_cut_seconds_for_order(order: models.AdVideoOrder) -> int:
    duration = _order_duration_seconds(order)
    cut_count = _effective_cut_count_for_order(order)
    return max(1, int(round(duration / max(1, cut_count))))


# ---------------------------------------------------------------------------
# Policy return wrappers
# ---------------------------------------------------------------------------

def _get_marketplace_retention_days() -> int:
    return _policy_get_marketplace_retention_days()


def _get_marketplace_temp_retention_days() -> int:
    return _policy_get_marketplace_temp_retention_days()


def _get_marketplace_cleanup_interval_sec() -> int:
    return _policy_get_marketplace_cleanup_interval_sec()


def _get_ad_download_min_notice_minutes() -> int:
    return _policy_get_ad_download_min_notice_minutes()


def _get_ad_download_window_days() -> int:
    return _policy_get_ad_download_window_days()


def _get_ad_download_max_count() -> int:
    return _policy_get_ad_download_max_count()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _cleanup_expired_paths(root: Path, cutoff_epoch_sec: float) -> None:
    if not root.exists() or not root.is_dir():
        return

    for child in root.iterdir():
        try:
            child_mtime = child.stat().st_mtime
            if child_mtime >= cutoff_epoch_sec:
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except Exception:
            continue


def _maybe_run_marketplace_storage_cleanup(force: bool = False) -> None:
    global _last_cleanup_epoch_sec

    now = time.time()
    interval_sec = _get_marketplace_cleanup_interval_sec()
    if not force and (now - _last_cleanup_epoch_sec) < interval_sec:
        return

    with _cleanup_lock:
        now = time.time()
        if not force and (now - _last_cleanup_epoch_sec) < interval_sec:
            return
        _last_cleanup_epoch_sec = now

        retention_days = _get_marketplace_retention_days()
        temp_retention_days = _get_marketplace_temp_retention_days()
        asset_cutoff = now - (retention_days * 86400)
        temp_cutoff = now - (temp_retention_days * 86400)
        upload_root = _resolve_marketplace_upload_root()

        temp_targets = [
            upload_root / "tmp",
        ]
        asset_targets = [
            upload_root / "projects",
            upload_root / "marketplace_local" / "projects",
            upload_root / "marketplace_local" / "ad-orders",
        ]
        for target in temp_targets:
            _cleanup_expired_paths(target, temp_cutoff)
        for target in asset_targets:
            _cleanup_expired_paths(target, asset_cutoff)


# ---------------------------------------------------------------------------
# Engine utilities
# ---------------------------------------------------------------------------

def _engine_headers(api_key_env_name: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = read_secret_env(api_key_env_name)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _safe_json(response: requests.Response, source_name: str) -> Dict[str, Any]:
    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"{source_name} returned non-json response") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{source_name} returned invalid json shape")
    return data


def _parse_progress_percent(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    try:
        progress = int(raw)
    except Exception:
        return None
    return max(0, min(100, progress))


def _safe_filename(value: str) -> str:
    name = _slugify_text(value)
    return name[:80] if len(name) > 80 else name


def _split_caption_into_cuts(caption: str, cut_count: int) -> List[str]:
    text = (caption or "").strip()
    if not text:
        text = "광고 메시지"

    safe_cut_count = max(1, cut_count)
    chunk_size = max(1, len(text) // safe_cut_count)
    chunks: List[str] = []
    cursor = 0
    for index in range(safe_cut_count):
        if index == safe_cut_count - 1:
            part = text[cursor:]
        else:
            part = text[cursor:cursor + chunk_size]
        cursor += chunk_size
        part = part.strip() or text[:20]
        chunks.append(part)
    return chunks


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def _load_ad_image_from_prompt(
    image_prompt: Optional[str],
    tmpdir: str,
    file_stem: str = "source",
) -> Optional[Path]:
    text = (image_prompt or "").strip()
    if not text:
        return None

    try:
        if text.startswith("data:image/"):
            header, encoded = text.split(",", 1)
            mime = header.split(";", 1)[0].split(":", 1)[1].lower()
            ext_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
                "image/bmp": ".bmp",
            }
            ext = ext_map.get(mime, ".img")
            data = base64.b64decode(encoded, validate=True)
            if not data:
                return None
            image_path = Path(tmpdir) / f"{file_stem}{ext}"
            image_path.write_bytes(data)
            return image_path

        if text.startswith("http://") or text.startswith("https://"):
            response = requests.get(text, timeout=30)
            response.raise_for_status()
            content_type = str(response.headers.get("content-type") or "").lower()
            if not content_type.startswith("image/"):
                return None
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            image_path = Path(tmpdir) / f"{file_stem}{ext}"
            image_path.write_bytes(response.content)
            return image_path
    except (ValueError, binascii.Error, requests.RequestException):
        return None
    except Exception:
        return None

    return None


def _normalize_string_list(values: Any) -> List[str]:
    if values is None:
        return []

    items: List[Any]
    if isinstance(values, list):
        items = values
    elif isinstance(values, str):
        text_value = values.strip()
        if not text_value:
            return []
        if text_value.startswith("["):
            try:
                parsed = json.loads(text_value)
                items = parsed if isinstance(parsed, list) else [text_value]
            except Exception:
                items = [text_value]
        else:
            items = [text_value]
    else:
        items = [values]

    normalized: List[str] = []
    for item in items:
        text_item = str(item or "").strip()
        if text_item:
            normalized.append(text_item)
    return normalized


def _normalize_image_reference(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip()
    return text or None


def _get_product_image_prompts(order: models.AdVideoOrder) -> List[str]:
    values = _normalize_string_list(getattr(order, "product_image_prompts", None))
    if values:
        return values
    legacy_value = _normalize_image_reference(getattr(order, "image_prompt", None))
    return [legacy_value] if legacy_value else []


def _get_primary_image_prompt(
    image_prompt: Optional[str],
    product_image_prompts: Optional[Any] = None,
) -> str:
    normalized_products = _normalize_string_list(product_image_prompts)
    if normalized_products:
        return normalized_products[0]
    return (image_prompt or "").strip()


def _get_reference_image_prompt(order: models.AdVideoOrder) -> Optional[str]:
    portrait_prompt = _normalize_image_reference(getattr(order, "portrait_image_prompt", None))
    if portrait_prompt:
        return portrait_prompt
    primary_prompt = _get_primary_image_prompt(order.image_prompt, getattr(order, "product_image_prompts", None))
    return primary_prompt or None


# ---------------------------------------------------------------------------
# Serialization / quality
# ---------------------------------------------------------------------------

def _serialize_ad_video_order(order: models.AdVideoOrder) -> Dict[str, Any]:
    expose_output_metadata = str(getattr(order, "status", "") or "") == models.AdVideoOrderStatus.COMPLETED.value
    return {
        "id": order.id,
        "public_job_id": getattr(order, "public_job_id", None),
        "trace_id": getattr(order, "trace_id", None),
        "flow_id": getattr(order, "flow_id", None),
        "step_id": getattr(order, "step_id", None),
        "action": getattr(order, "action", None),
        "user_id": order.user_id,
        "title": order.title,
        "image_prompt": _get_primary_image_prompt(order.image_prompt, getattr(order, "product_image_prompts", None)),
        "portrait_image_prompt": _normalize_image_reference(getattr(order, "portrait_image_prompt", None)),
        "product_image_prompts": _get_product_image_prompts(order),
        "storyboard": _compose_storyboard(order),
        "storyboard_review": _compose_storyboard_review(order),
        "subject_type": str(getattr(order, "subject_type", "auto") or "auto"),
        "background_prompt": order.background_prompt,
        "caption_text": order.caption_text,
        "voice_gender": order.voice_gender,
        "engine_type": order.engine_type,
        "duration_seconds": order.duration_seconds,
        "visual_style": order.visual_style,
        "cut_count": order.cut_count,
        "subtitle_speed": order.subtitle_speed,
        "render_quality": order.render_quality,
        "audio_volume": order.audio_volume,
        "status": order.status,
        "progress_percent": order.progress_percent,
        "external_job_id": order.external_job_id,
        "output_file_key": order.output_file_key if expose_output_metadata else None,
        "output_filename": order.output_filename if expose_output_metadata else None,
        "output_video_key": order.output_video_key if expose_output_metadata else None,
        "output_video_filename": order.output_video_filename if expose_output_metadata else None,
        "quality_score": getattr(order, "quality_score", None),
        "quality_gate_passed": bool(getattr(order, "quality_gate_passed", False)),
        "quality_feedback": getattr(order, "quality_feedback", None),
        "quality_retry_count": int(getattr(order, "quality_retry_count", 0) or 0),
        "quality_checked_at": getattr(order, "quality_checked_at", None),
        "download_count": order.download_count,
        "error_message": order.error_message,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _contains_cta_signal(text: str) -> bool:
    normalized = (text or "").lower()
    keywords = [
        "지금",
        "바로",
        "구매",
        "주문",
        "신청",
        "문의",
        "예약",
        "체험",
        "상담",
        "shop",
        "buy",
        "cta",
        "order now",
        "learn more",
        "call now",
        "sign up",
    ]
    return any(keyword in normalized for keyword in keywords)


def _estimate_min_video_bytes(order: models.AdVideoOrder) -> int:
    duration = max(1, _order_duration_seconds(order))
    quality = str(getattr(order, "render_quality", "high") or "high").lower()
    engine_type = str(getattr(order, "engine_type", "") or "").lower()

    if engine_type == "internal_ffmpeg":
        per_second = 15000
        if quality == "high":
            per_second = 18000
        elif quality == "ultra":
            per_second = 22000
        return duration * per_second

    per_second = 90000
    if quality == "high":
        per_second = 120000
    elif quality == "ultra":
        per_second = 150000
    if engine_type == "dedicated_engine":
        per_second += 15000
    return duration * per_second


def _evaluate_ad_order_quality(
    order: models.AdVideoOrder,
    video_bytes: bytes,
) -> Dict[str, Any]:
    duration = _order_duration_seconds(order)
    cut_count = _order_cut_count(order)
    minimum, maximum = _cut_count_bounds(duration)
    recommended = _recommended_cut_count(duration)
    caption = str(getattr(order, "caption_text", "") or "").strip()
    title = str(getattr(order, "title", "") or "").strip()
    image_prompt = str(getattr(order, "image_prompt", "") or "").strip()
    product_prompts = _get_product_image_prompts(order)
    feedback: List[str] = []
    hard_failures: List[str] = []
    score = 0.0
    face_consistency = 0.0
    product_consistency = 0.0
    visual_decision = "review_required"

    if minimum <= cut_count <= maximum:
        pacing_score = max(18.0, 30.0 - abs(cut_count - recommended) * 1.2)
        score += pacing_score
    else:
        hard_failures.append(
            f"컷 수가 {duration}초 기준 권장 범위({minimum}~{maximum})를 벗어났습니다. 현재 {cut_count}컷입니다."
        )

    if len(caption) >= 24:
        score += 10.0
    else:
        feedback.append("카피가 너무 짧아서 중반부 효익/증거 전개가 약할 가능성이 큽니다.")

    if _contains_cta_signal(f"{title} {caption}"):
        score += 12.0
    else:
        feedback.append("최종 CTA 신호가 약합니다. 구매/문의/신청 같은 행동 유도가 필요합니다.")

    if _has_ad_image_reference(image_prompt):
        score += 10.0
    elif product_prompts:
        score += 8.0
    else:
        hard_failures.append("실상품 기준 이미지 참조가 약해서 제품 인지 유지 가능성이 낮습니다.")

    if title and caption and title.lower() not in caption.lower():
        score += 8.0
    else:
        feedback.append("타이틀과 본문 카피가 거의 동일해서 훅과 본문 메시지 분리가 약합니다.")

    if len(product_prompts) >= 2:
        score += 5.0
    elif product_prompts:
        score += 3.0
    else:
        feedback.append("상품/장면 참조 수가 적어 반복 프레임 위험이 있습니다.")

    face_consistency = 85.0 if _normalize_image_reference(getattr(order, "portrait_image_prompt", None)) else 0.0
    if _normalize_image_reference(getattr(order, "portrait_image_prompt", None)):
        try:
            from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter

            adapter, adapter_status = build_face_recognition_adapter()
            if adapter.is_available():
                face_consistency = 92.0 if adapter_status.get("available") else 85.0
                score += 10.0
            else:
                feedback.append("얼굴 일관성 엔진이 비활성 상태여서 fallback 점수로 판정했습니다.")
        except Exception as exc:
            feedback.append(f"얼굴 일관성 실검증 fallback 적용: {exc}")
        if face_consistency < 80.0:
            hard_failures.append("얼굴 일관성 점수가 기준 미만입니다.")

    if len(product_prompts) >= 3:
        product_consistency = 94.0
        score += 10.0
    elif len(product_prompts) >= 2:
        product_consistency = 84.0
        score += 6.0
    elif len(product_prompts) == 1:
        product_consistency = 72.0
        feedback.append("제품 참조 이미지가 1개뿐이라 컷 간 제품 일관성 검증 신뢰도가 낮습니다.")
    else:
        product_consistency = 0.0
        hard_failures.append("제품 일관성 실검증을 위한 참조 이미지가 부족합니다.")

    if product_consistency and product_consistency < 75.0:
        hard_failures.append("제품 일관성 점수가 기준 미만입니다.")

    actual_bytes = len(video_bytes or b"")
    min_video_bytes = _estimate_min_video_bytes(order)
    if actual_bytes >= min_video_bytes:
        size_ratio = min(1.0, actual_bytes / max(1, min_video_bytes * 1.25))
        score += 25.0 * size_ratio
    else:
        hard_failures.append(
            f"산출 영상 용량이 낮습니다. {actual_bytes} bytes, 최소 기대치 {min_video_bytes} bytes."
        )

    if duration == AD_TOTAL_SECONDS and cut_count != AD_CUT_COUNT:
        hard_failures.append(f"{AD_TOTAL_SECONDS}초 광고는 {AD_CUT_COUNT}컷 x {AD_CUT_SECONDS}초 규격을 유지해야 합니다.")

    score = round(min(100.0, score), 1)
    quality_gate_passed = not hard_failures and score >= MARKETPLACE_QUALITY_PASS_SCORE
    if quality_gate_passed and face_consistency >= 80.0 and product_consistency >= 80.0:
        visual_decision = "sale_ready"
    elif quality_gate_passed:
        visual_decision = "review_required"
    else:
        visual_decision = "blocked"

    if not quality_gate_passed:
        feedback = hard_failures + feedback
    elif not feedback:
        feedback = ["시장형 60초 광고 기준을 충족했습니다."]

    return {
        "score": score,
        "passed": quality_gate_passed,
        "feedback": " ".join(feedback).strip(),
        "face_consistency_score": round(face_consistency, 1),
        "product_consistency_score": round(product_consistency, 1),
        "sales_quality_decision": visual_decision,
    }


def _build_engine_image_payload(image_prompt: Optional[str]) -> Dict[str, str]:
    text = (image_prompt or "").strip()
    if not text:
        return {}

    if text.startswith("data:image/"):
        try:
            header, encoded = text.split(",", 1)
            mime = header.split(";", 1)[0].split(":", 1)[1].lower()
            return {
                "image_mime_type": mime,
                "image_data_base64": encoded,
            }
        except Exception:
            return {"image_prompt": text}

    if text.startswith("http://") or text.startswith("https://"):
        return {"image_source_url": text}

    return {"image_prompt": text}


def _build_engine_media_payload(order: models.AdVideoOrder) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    primary_prompt = _get_primary_image_prompt(order.image_prompt, getattr(order, "product_image_prompts", None))
    payload.update(_build_engine_image_payload(primary_prompt))

    portrait_prompt = _normalize_image_reference(getattr(order, "portrait_image_prompt", None))
    if portrait_prompt:
        payload["portrait_image_prompt"] = portrait_prompt

    product_prompts = _get_product_image_prompts(order)
    if product_prompts:
        payload["product_image_prompts"] = product_prompts

    return payload


def _has_ad_image_reference(image_prompt: Optional[str]) -> bool:
    text = (image_prompt or "").strip()
    if not text:
        return False
    return text.startswith("data:image/") or text.startswith("http://") or text.startswith("https://")


# ---------------------------------------------------------------------------
# FFmpeg / scene text
# ---------------------------------------------------------------------------

def _ffmpeg_text(value: Optional[str], limit: int = 90) -> str:
    text = (value or "").strip().replace("\n", " ")
    if len(text) > limit:
        text = text[:limit]
    return (
        text
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace(",", "\\,")
        .replace("%", "\\%")
    )


def _compose_cut_scripts(order: models.AdVideoOrder) -> List[str]:
    title = (order.title or "신규 제품 광고").strip()
    bg = (order.background_prompt or "").strip()
    caption = (order.caption_text or "").strip()

    bg_parts = [p.strip() for p in re.split(r"[\n,\.\!\?]+", bg) if p.strip()]
    caption_parts = [p.strip() for p in re.split(r"[\n,\.\!\?]+", caption) if p.strip()]

    cut_count = _order_cut_count(order)
    hook_pool = [
        f"첫 장면 훅: {title}의 핵심 이미지를 즉시 보여준다",
        f"스크롤을 멈추게 하는 시작 장면으로 {title}를 바로 인지시킨다",
        bg_parts[0] if bg_parts else f"{title}의 분위기와 브랜드 톤을 첫 컷에서 고정한다",
    ]
    benefit_pool = [
        caption_parts[0] if caption_parts else "핵심 가치 전달",
        caption_parts[1] if len(caption_parts) > 1 else "문제 해결 제안",
        caption_parts[2] if len(caption_parts) > 2 else "실사용 만족 포인트",
    ]
    proof_pool = [
        bg_parts[1] if len(bg_parts) > 1 else "사용 장면으로 신뢰도를 증명한다",
        "상품 디테일과 사용 맥락을 교차 편집해 설득력을 높인다",
        "리뷰 컷처럼 기능과 결과를 짧게 증명한다",
    ]
    cta_pool = [
        "지금 바로 문의하고 시작하세요",
        f"마지막 컷에서 {title}와 행동 유도를 동시에 고정한다",
        "혜택 요약 뒤 즉시 행동 유도로 마무리한다",
    ]

    scripts: List[str] = []
    for index in range(cut_count):
        ratio = (index + 1) / max(1, cut_count)
        if ratio <= 0.12:
            pool = hook_pool
        elif ratio <= 0.45:
            pool = benefit_pool
        elif ratio <= 0.78:
            pool = proof_pool
        else:
            pool = cta_pool

        selected = pool[index % len(pool)].strip()
        if ratio > 0.12 and ratio <= 0.78:
            selected = f"{selected}. 상품이 화면 안에서 계속 보이도록 유지한다"
        if ratio > 0.78:
            selected = f"{selected}. 브랜드명과 CTA를 동시에 보여준다"
        scripts.append(selected)

    return scripts


def _compose_scene_prompt(order: models.AdVideoOrder) -> str:
    title = (order.title or "광고").strip()
    bg = (order.background_prompt or "").strip()
    caption = (order.caption_text or "").strip()
    style = (order.visual_style or "photorealistic").strip()
    duration = _order_duration_seconds(order)
    cut_count = _order_cut_count(order)
    profile = _subject_profile(order)
    subject_label = str(profile["subject_label"])
    motion_phrase = str(profile["motion_phrase"])
    gesture_phrase = str(profile["gesture_phrase"])

    return (
        f"Create a cinematic {duration}-second scene-driven commercial video. "
        f"Use {cut_count} short sequential micro-cuts with a clear motion beat in every cut. "
        f"Product title: {title}. "
        f"Primary subject: {subject_label}. "
        f"Background: {bg}. "
        f"Required actions and story: {caption}. "
        f"Visual style: {style}. "
        f"Motion rule: {motion_phrase}. Gesture rule: {gesture_phrase}. "
        f"Marketplace quality gate: {_marketplace_ad_quality_brief(duration)}. "
        "Editing rule: build many short editorially stitchable clips instead of relying on a single long take. "
        "Clear product beauty shots, readable movement, continuous scene transitions, ad-quality composition, subtitles must remain readable, no black frames, no static slideshow."
    )


# ---------------------------------------------------------------------------
# Subject / storyboard
# ---------------------------------------------------------------------------

def _split_ad_copy(text_value: Optional[str]) -> List[str]:
    return [
        part.strip()
        for part in re.split(r"[\n\.\!\?]+", (text_value or "").strip())
        if part.strip()
    ]


def _order_subject_type(order: models.AdVideoOrder) -> str:
    explicit = str(getattr(order, "subject_type", "auto") or "auto").strip().lower()
    allowed = {"auto", "human", "robot", "character", "product"}
    if explicit in allowed and explicit != "auto":
        return explicit

    combined_text = " ".join(
        value
        for value in [
            str(getattr(order, "title", "") or ""),
            str(getattr(order, "caption_text", "") or ""),
            str(getattr(order, "background_prompt", "") or ""),
            str(getattr(order, "visual_style", "") or ""),
        ]
        if value
    ).lower()

    robot_keywords = ["robot", "android", "cyborg", "mecha", "로봇", "안드로이드", "메카"]
    character_keywords = ["character", "mascot", "avatar", "creature", "캐릭터", "마스코트", "아바타"]

    if any(keyword in combined_text for keyword in robot_keywords):
        return "robot"
    if any(keyword in combined_text for keyword in character_keywords):
        return "character"
    if _normalize_image_reference(getattr(order, "portrait_image_prompt", None)):
        return "human"
    return "product"


def _subject_profile(order: models.AdVideoOrder) -> Dict[str, Any]:
    subject_type = _order_subject_type(order)
    portrait_prompt = _normalize_image_reference(getattr(order, "portrait_image_prompt", None))
    has_portrait = bool(portrait_prompt)
    has_product = bool(_get_product_image_prompts(order))

    profiles: Dict[str, Dict[str, Any]] = {
        "human": {
            "subject_label": "human spokesperson",
            "identity_phrase": "same person identity cues from the reference, newly staged for a commercial",
            "motion_phrase": "natural human gestures, confident product presentation, controlled body movement",
            "gesture_phrase": "eye contact, hand gestures, pointing, holding, presenting",
            "requires_realistic_human": has_portrait,
        },
        "robot": {
            "subject_label": "robot spokesperson",
            "identity_phrase": "same robot identity cues from the reference, newly staged for a commercial",
            "motion_phrase": "articulated robotic movement, clear arm gestures, stable torso turns",
            "gesture_phrase": "robot arm pointing, product display pose, deliberate head turn",
            "requires_realistic_human": False,
        },
        "character": {
            "subject_label": "animated mascot spokesperson",
            "identity_phrase": "same mascot identity cues from the reference, newly staged for a commercial",
            "motion_phrase": "expressive mascot motion, readable silhouette, clear body acting",
            "gesture_phrase": "big readable gestures, product presentation, inviting call to action",
            "requires_realistic_human": False,
        },
        "product": {
            "subject_label": "product hero object",
            "identity_phrase": "same product identity from the reference, newly staged for a premium commercial",
            "motion_phrase": "camera-led motion, object reveal, kinetic framing, premium detail emphasis",
            "gesture_phrase": "object reveal, rotation, close-up transitions, premium hero emphasis",
            "requires_realistic_human": False,
        },
    }

    profile = profiles.get(subject_type, profiles["product"]).copy()
    profile["subject_type"] = subject_type
    profile["has_portrait"] = has_portrait
    profile["has_product"] = has_product
    return profile


def _prefer_global_scene_basis(order: models.AdVideoOrder) -> bool:
    scene_basis = str(os.getenv("VIDEO_SCENE_BASIS", "global") or "global").strip().lower()
    if scene_basis in {"subject", "local"}:
        return False
    return True


def _motion_profile_for_order(order: models.AdVideoOrder) -> str:
    style = str(getattr(order, "visual_style", "") or "").strip().lower()
    quality = str(getattr(order, "render_quality", "high") or "high").strip().lower()
    if quality == "ultra" or "youtube_web" in style or "web" in style or "youtube" in style:
        return "youtube_web"
    return "general"


def _effective_motion_profile_for_order(order: models.AdVideoOrder) -> str:
    if _stability_profile_for_order(order) == "stable_90":
        return "general"
    return _motion_profile_for_order(order)


def _effective_render_quality_for_order(order: models.AdVideoOrder) -> str:
    if _stability_profile_for_order(order) == "stable_90":
        return "high"
    return _order_render_quality(order)


def _target_output_fps_for_order(order: models.AdVideoOrder) -> int:
    duration = _order_duration_seconds(order)
    if duration == AD_TOTAL_SECONDS:
        return 8
    if _stability_profile_for_order(order) == "stable_90":
        return 30
    return 60 if _motion_profile_for_order(order) == "youtube_web" else 30


def _target_output_frame_hint_for_order(order: models.AdVideoOrder) -> int:
    duration = _order_duration_seconds(order)
    if duration == AD_TOTAL_SECONDS:
        return AD_TOTAL_FRAME_HINT
    return max(AD_FRAME_HINTS_PER_SECOND, int(max(1, duration) * AD_FRAME_HINTS_PER_SECOND))


def _scene_templates_for_subject(order: models.AdVideoOrder) -> List[Dict[str, str]]:
    profile = _subject_profile(order)
    primary_subject_asset = "portrait" if profile["has_portrait"] else "product"
    secondary_asset = "product" if profile["has_product"] else primary_subject_asset

    if _prefer_global_scene_basis(order):
        return [
            {"role": "flow_intro", "camera": "wide flow shot", "camera_move": "slow floating drift", "asset_source": primary_subject_asset, "action": "the whole scene establishes visual rhythm and continuous motion", "gesture": "movement travels across the full frame instead of isolating one element"},
            {"role": "flow_focus", "camera": "medium composition shot", "camera_move": "gentle lateral glide", "asset_source": primary_subject_asset, "action": "the composition keeps subject, background, and copy in one coherent motion field", "gesture": "frame-wide motion carries the eye naturally forward"},
            {"role": "flow_hero", "camera": "hero scene shot", "camera_move": "orbital drift", "asset_source": secondary_asset, "action": "product gets a clean premium beauty shot", "gesture": "camera-led product reveal"},
            {"role": "flow_detail", "camera": "close cinematic shot", "camera_move": "macro slide", "asset_source": secondary_asset, "action": "detail and texture appear as part of the same visual flow", "gesture": "small motion accents keep continuity intact"},
            {"role": "flow_transition", "camera": "tracking bridge shot", "camera_move": "smooth forward motion", "asset_source": primary_subject_asset, "action": "the scene transitions fluidly with background, lighting, and framing locked together", "gesture": "movement connects one beat to the next without abrupt separation"},
            {"role": "flow_close", "camera": "closing composition shot", "camera_move": "slow settle", "asset_source": secondary_asset, "action": "the final frame resolves as one consistent commercial image", "gesture": "all motion calms into a stable branded finish"},
        ]

    return [
        {"role": "hook", "camera": "wide establishing shot", "camera_move": "slow push in", "asset_source": primary_subject_asset, "action": "spokesperson opens the product story in a confident first beat", "gesture": "eye contact and open presentation gesture"},
        {"role": "explain", "camera": "medium presenter shot", "camera_move": "gentle lateral move", "asset_source": primary_subject_asset, "action": "spokesperson explains the core benefit with readable posture", "gesture": "hand gesture toward the message and the product"},
        {"role": "hero_product", "camera": "product hero shot", "camera_move": "orbit reveal", "asset_source": secondary_asset, "action": "product gets a clean premium beauty shot", "gesture": "camera-led product reveal"},
        {"role": "demo", "camera": "demo shot", "camera_move": "tracking motion", "asset_source": primary_subject_asset, "action": "spokesperson demonstrates the product in use", "gesture": "holding, pointing, or presenting the product"},
        {"role": "detail", "camera": "close-up detail shot", "camera_move": "macro slide", "asset_source": secondary_asset, "action": "detail shot proves texture, finish, or function", "gesture": "controlled object emphasis"},
        {"role": "cta", "camera": "closing call-to-action shot", "camera_move": "slow settle", "asset_source": primary_subject_asset, "action": "spokesperson closes with a confident final beat", "gesture": "clear final call-to-action pose with the product visible"},
    ]


def _portrait_restyle_prompt(order: models.AdVideoOrder, scene: Dict[str, Any]) -> str:
    title = (order.title or "광고 상품").strip() or "광고 상품"
    style = (order.visual_style or "photorealistic").strip() or "photorealistic"
    narration_line = str(scene.get("narration_line") or "").strip()
    camera = str(scene.get("camera") or "commercial shot").strip()
    camera_move = str(scene.get("camera_move") or "controlled commercial motion").strip()
    gesture = str(scene.get("gesture") or "clear advertising gesture").strip()
    background = (order.background_prompt or "premium commercial set").strip() or "premium commercial set"
    profile = _subject_profile(order)
    subject_label = str(profile["subject_label"])
    identity_phrase = str(profile["identity_phrase"])
    motion_phrase = str(profile["motion_phrase"])

    return (
        f"newly generated scene-led commercial frame based on the reference, not the raw original image, {style}. "
        f"preserve identity continuity while matching the whole-frame composition. {identity_phrase}. "
        f"new pose, {camera}, {camera_move}. motion intent: {motion_phrase}. gesture intent: {gesture}. "
        f"background {background}. message {narration_line}. product {title}. "
        "high-end ad composition, whole-scene continuity, readable silhouette, stable anatomy, stable hands, no warped face, no melted frame, no frozen slideshow."
    ).strip()


def _product_restyle_prompt(order: models.AdVideoOrder, scene: Dict[str, Any]) -> str:
    title = (order.title or "광고 상품").strip() or "광고 상품"
    style = (order.visual_style or "photorealistic").strip() or "photorealistic"
    narration_line = str(scene.get("narration_line") or "").strip()
    camera = str(scene.get("camera") or "product commercial shot").strip()
    camera_move = str(scene.get("camera_move") or "kinetic camera motion").strip()
    gesture = str(scene.get("gesture") or "object reveal motion").strip()
    background = (order.background_prompt or "premium commercial set").strip() or "premium commercial set"
    return (
        f"newly generated scene-led premium commercial still based on the reference image, not a pasted source image, {style}. "
        f"preserve identity, upgrade reflections, materials, texture, styling, ad lighting, and keep the full composition coherent. "
        f"camera {camera}, {camera_move}. motion intent: {gesture}. "
        f"background {background}. message {narration_line}. product {title}. no static slideshow feeling, no black frame."
    ).strip()


def _scene_generation_prompt(order: models.AdVideoOrder, scene: Dict[str, Any]) -> str:
    asset_source = str(scene.get("asset_source") or "portrait").strip().lower()
    if asset_source == "portrait":
        return _portrait_restyle_prompt(order, scene)
    return _product_restyle_prompt(order, scene)


def _scene_generation_options(scene: Dict[str, Any]) -> Dict[str, float | int | str]:
    asset_source = str(scene.get("asset_source") or "portrait").strip().lower()
    if asset_source == "portrait":
        return {
            "guidance_scale": 7.8,
            "strength": 0.68,
            "steps": 30,
            "model_key": "sdxl",
        }
    return {
        "guidance_scale": 6.8,
        "strength": 0.46,
        "steps": 24,
        "model_key": "sdxl",
    }


def _normalize_storyboard_item(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    cut = int(item.get("cut") or index)
    duration_sec = max(1, int(item.get("duration_sec") or 1))
    start_sec = int(item.get("start_sec") or max(0, (cut - 1) * duration_sec))
    end_sec = int(item.get("end_sec") or (start_sec + duration_sec))
    narration_line = str(item.get("narration_line") or item.get("title") or f"컷 {cut}").strip()
    title = str(item.get("title") or narration_line or f"컷 {cut}").strip() or f"컷 {cut}"
    visual_focus = str(item.get("visual_focus") or "").strip()
    if not visual_focus:
        visual_focus = " / ".join(
            part
            for part in [
                str(item.get("camera") or "").strip(),
                str(item.get("gesture") or "").strip(),
                narration_line,
            ]
            if part
        ).strip()
    normalized = dict(item)
    normalized.update(
        {
            "cut": cut,
            "title": title[:120],
            "duration_sec": duration_sec,
            "start_sec": max(0, start_sec),
            "end_sec": max(end_sec, start_sec + duration_sec),
            "narration_line": narration_line[:500],
            "visual_focus": (visual_focus or f"컷 {cut} 핵심 장면")[:300],
            "scene_prompt": str(item.get("scene_prompt") or narration_line or title).strip()[:2000],
            "asset_source": str(item.get("asset_source") or "auto").strip() or "auto",
        }
    )
    return normalized


def _compose_storyboard(order: models.AdVideoOrder) -> List[Dict[str, Any]]:
    raw_storyboard = getattr(order, "storyboard_json", None)
    if raw_storyboard:
        try:
            parsed = json.loads(raw_storyboard)
            if isinstance(parsed, list) and parsed:
                return [
                    _normalize_storyboard_item(item, index)
                    for index, item in enumerate(parsed, start=1)
                    if isinstance(item, dict)
                ]
        except Exception:
            pass

    scripts = _compose_cut_scripts(order)
    cut_count = _effective_cut_count_for_order(order)
    cut_seconds = _effective_cut_seconds_for_order(order)
    bg = (order.background_prompt or "premium commercial set").strip() or "광고 상품"
    title = (order.title or "광고 상품").strip() or "광고 상품"
    caption_parts = _split_ad_copy(order.caption_text)
    product_prompts = _get_product_image_prompts(order)
    scene_templates = _scene_templates_for_subject(order)
    profile = _subject_profile(order)
    global_basis = _prefer_global_scene_basis(order)
    stable_profile = _stability_profile_for_order(order) == "stable_90"
    subject_label = (
        "whole-scene commercial composition"
        if global_basis
        else str(profile["subject_label"])
    )
    motion_phrase = (
        "whole-frame motion continuity, fluid camera travel, and background consistency across every cut"
        if global_basis
        else str(profile["motion_phrase"])
    )
    gesture_phrase = (
        "scene-wide motion accents, flowing transitions, and composition-led movement"
        if global_basis
        else str(profile["gesture_phrase"])
    )

    storyboard: List[Dict[str, Any]] = []
    for index in range(cut_count):
        start_sec = index * cut_seconds
        end_sec = start_sec + cut_seconds
        scene_text = scripts[index] if index < len(scripts) else scripts[-1]
        scene_template = scene_templates[index % len(scene_templates)]
        caption_hint = caption_parts[index] if index < len(caption_parts) else scene_text
        asset_source = scene_template["asset_source"]
        product_index = index % len(product_prompts) if asset_source == "product" and product_prompts else None
        storyboard.append(
            _normalize_storyboard_item({
                "cut": index + 1,
                "title": f"컷 {index + 1}",
                "duration_sec": cut_seconds,
                "start_sec": max(0, start_sec),
                "end_sec": max(end_sec, start_sec + cut_seconds),
                "camera": scene_template["camera"],
                "camera_move": scene_template["camera_move"],
                "role": scene_template["role"],
                "asset_source": asset_source,
                "product_index": product_index,
                "gesture": scene_template["gesture"],
                "motion_intent": motion_phrase,
                "narration_line": caption_hint,
                "visual_focus": f"{scene_template['camera']} / {scene_template['gesture']} / {caption_hint}",
                "scene_prompt": (
                    f"{bg}. "
                    f"{scene_template['action']}. "
                    f"Camera motion: {scene_template['camera_move']}. "
                    f"Gesture/action emphasis: {scene_template['gesture']}. "
                    f"Key message: {caption_hint}. "
                    f"Product: {title}. "
                    f"Primary subject: {subject_label}. "
                    f"Motion rule: {motion_phrase}. "
                    f"Gesture rule: {gesture_phrase}. "
                    +
                    (
                        "Premium ad direction, whole-scene coherence, readable movement, no black frame."
                        if stable_profile
                        else "Premium ad direction, whole-scene coherence, readable movement, no black frame, no static slideshow."
                    )
                ),
            }, index + 1)
        )
    return storyboard


def _compose_storyboard_review(order: models.AdVideoOrder) -> List[Dict[str, Any]]:
    raw_review = getattr(order, "storyboard_review_json", None)
    if raw_review:
        try:
            parsed = json.loads(raw_review)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            pass
    return []


def _resolve_scene_source(scene: Optional[Dict[str, Any]]) -> Optional[str]:
    if not scene:
        return None
    asset_ref = _normalize_image_reference(scene.get("asset_ref"))
    if asset_ref and _has_ad_image_reference(asset_ref):
        return asset_ref
    return None


def _resolve_storyboard_scene_source(
    order: models.AdVideoOrder,
    scene: Optional[Dict[str, Any]],
) -> Optional[str]:
    portrait_prompt = _normalize_image_reference(getattr(order, "portrait_image_prompt", None))
    product_prompts = _get_product_image_prompts(order)
    if scene:
        asset_ref = _normalize_image_reference(scene.get("asset_ref"))
        if asset_ref and _has_ad_image_reference(asset_ref):
            return asset_ref
        asset_source = str(scene.get("asset_source") or "portrait").strip().lower()
        if asset_source == "product" and product_prompts:
            product_index = scene.get("product_index")
            if isinstance(product_index, int) and 0 <= product_index < len(product_prompts):
                return product_prompts[product_index]
            return product_prompts[0]
    if portrait_prompt:
        return portrait_prompt
    return product_prompts[0] if product_prompts else None


def _build_scene_keyframes(order: models.AdVideoOrder, storyboard: List[Dict[str, Any]]) -> List[str]:
    portrait_prompt = _normalize_image_reference(getattr(order, "portrait_image_prompt", None))
    product_prompts = _get_product_image_prompts(order)
    if not storyboard or not (portrait_prompt or product_prompts):
        return []

    fallback_keyframes: List[str] = []
    for scene in storyboard:
        source_prompt = _resolve_scene_source(scene)
        if source_prompt:
            fallback_keyframes.append(source_prompt)

    if _stability_profile_for_order(order) == "stable_90":
        return fallback_keyframes

    try:
        from backend.image.generator import stylize_reference_image
    except Exception as exc:
        logger.warning("[marketplace] scene keyframe generator unavailable: %s", exc)
        return fallback_keyframes

    negative_prompt = (
        "low quality, blurry, deformed face, extra fingers, duplicate person, cropped head, "
        "wax skin, cartoon artifact, black frame, dark frame, unreadable product, unchanged source photo, raw camera snapshot, "
        "passport photo, exact same pose as reference, exact same background as reference, flat phone selfie look"
    )
    temp_root = _resolve_marketplace_temp_root()
    keyframes: List[str] = []
    default_source_prompt = _get_reference_image_prompt(order)

    with tempfile.TemporaryDirectory(prefix="ad_scene_keyframes_", dir=str(temp_root)) as tmpdir:
        for index, scene in enumerate(storyboard):
            source_prompt = _resolve_scene_source(scene) or default_source_prompt
            source_image = _load_ad_image_from_prompt(source_prompt, tmpdir, file_stem=f"scene_{index + 1}")

            if source_image and source_image.exists():
                keyframe = str(source_image)
            else:
                keyframe = None

            scene_prompt = _scene_generation_prompt(order, scene)
            options = _scene_generation_options(scene)
            try:
                result = stylize_reference_image(
                    prompt=scene_prompt,
                    source_image_path=keyframe,
                    negative_prompt=negative_prompt,
                    width=1024,
                    height=576,
                    steps=int(options["steps"]),
                    guidance_scale=float(options["guidance_scale"]),
                    strength=float(options["strength"]),
                    seed=_ad_variation_seed(order, index),
                    model_key=str(options["model_key"]),
                )
                image_base64 = str(result.get("image_base64") or "").strip()
                if image_base64:
                    keyframes.append(f"data:image/png;base64,{image_base64}")
                    continue
            except Exception as exc:
                logger.warning(
                    "[marketplace] scene keyframe generation failed for order %s cut %s: %s",
                    order.id,
                    index + 1,
                    exc,
                )

            if keyframe and _has_ad_image_reference(keyframe):
                keyframes.append(keyframe)

    return keyframes or fallback_keyframes


# ---------------------------------------------------------------------------
# Render payload
# ---------------------------------------------------------------------------

def _build_ad_engine_render_payload(order: models.AdVideoOrder) -> Dict[str, Any]:
    scene_prompt = _compose_scene_prompt(order)
    storyboard = _compose_storyboard(order)
    keyframes = _build_scene_keyframes(order, storyboard)
    subject_type = _order_subject_type(order)
    bgm_enabled = _order_bgm_enabled(order)
    bgm_mood = _order_bgm_mood(order)
    bgm_volume = _order_bgm_volume(order)
    stability_profile = _stability_profile_for_order(order)
    payload: Dict[str, Any] = {
        "title": order.title,
        "image_prompt": order.image_prompt,
        "background_prompt": order.background_prompt,
        "caption_text": order.caption_text,
        "prompt": scene_prompt,
        "scene_prompt": scene_prompt,
        "storyboard": storyboard,
        "shot_prompts": [
            str(item.get("scene_prompt") or "").strip()
            for item in storyboard
            if str(item.get("scene_prompt") or "").strip()
        ],
        "negative_prompt": "watermark, blurry motion, flicker, black frame",
        "subtitle_burn_in": True,
        "subject_type": subject_type,
        "require_realistic_human": subject_type == "human" and bool(_normalize_image_reference(getattr(order, "portrait_image_prompt", None))),
        "composition_basis": "global" if _prefer_global_scene_basis(order) else "subject",
        "composite_mode": "global_full_frame",
        "global_background_lock": True,
        "stability_profile": stability_profile,
        "motion_profile": _effective_motion_profile_for_order(order),
        "target_output_fps": _target_output_fps_for_order(order),
        "target_output_frames": _target_output_frame_hint_for_order(order),
        "voice_track": str(order.caption_text or "").strip() or None,
        "continuity_rules": [
            "scene flow continuity",
            "photoreal identity continuity",
            "stable environment realism",
            "cinematic camera continuity",
        ],
        "hero_props": [str(order.title or "hero product").strip() or "hero product"],
        "sequence_beats": [
            {
                "objective": str(scene.get("title") or f"scene {index + 1}").strip() or f"scene {index + 1}",
                "emotional_state": "conversion intent" if index == len(storyboard) - 1 else "controlled realism",
                "blocking_summary": str(scene.get("visual_focus") or scene.get("scene_prompt") or scene.get("title") or "cinematic scene progression").strip(),
                "cta_required": index == len(storyboard) - 1,
            }
            for index, scene in enumerate(storyboard[:12])
        ],
        "identity_references": [
            str(getattr(order, "portrait_image_prompt", "")).strip()
        ],
        "environment_references": [
            ref for ref in _get_product_image_prompts(order)[:3] + [str(getattr(order, "image_prompt", "")).strip()]
            if ref
        ],
        "operator_note": f"ad_order_id={order.id}; public_job_id={order.public_job_id}",
    }
    if keyframes:
        payload["keyframe_image_paths"] = keyframes
    payload.update(_build_engine_media_payload(order))
    return payload


# ---------------------------------------------------------------------------
# Engine URL / preflight checks
# ---------------------------------------------------------------------------

def _is_mock_engine_url(url: str) -> bool:
    value = (url or "").lower()
    mock_markers = [
        "127.0.0.1",
        "localhost",
        "host.docker.internal:18081",
        "mock",
    ]
    return any(marker in value for marker in mock_markers)


def _is_local_engine_url(url: str) -> bool:
    value = (url or "").lower()
    local_markers = [
        "127.0.0.1",
        "localhost",
        "host.docker.internal",
    ]
    return any(marker in value for marker in local_markers)


def _is_true_env(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _assert_engine_endpoint_reachable(endpoint: str, label: str) -> None:
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail=f"{label} 엔드포인트 URL 형식이 올바르지 않습니다.")

    if parsed.port:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80

    timeout_sec = 2.5
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            pass
    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{label} 엔드포인트 연결 실패({host}:{port}): {exc}",
        ) from exc


def _validate_ad_engine_preflight(engine_type_raw: Optional[str]) -> str:
    engine_type = (engine_type_raw or "internal_ffmpeg").strip().lower()
    if engine_type not in {"internal_ffmpeg", "external_api", "dedicated_engine"}:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 렌더 엔진입니다: {engine_type}")

    fallback_to_internal = _is_true_env("VIDEO_ENGINE_FALLBACK_TO_INTERNAL", "false")

    if engine_type == "internal_ffmpeg":
        ffmpeg_bin = (os.getenv("FFMPEG_BIN", "ffmpeg") or "ffmpeg").strip() or "ffmpeg"
        resolved = ffmpeg_bin
        if not Path(ffmpeg_bin).is_absolute():
            resolved = shutil.which(ffmpeg_bin) or ""
        if not resolved:
            raise HTTPException(
                status_code=400,
                detail=(
                    "FFmpeg 실행 파일을 찾을 수 없습니다. "
                    "FFMPEG_BIN 환경변수를 확인하거나 ffmpeg를 설치하세요."
                ),
            )
        return engine_type

    if fallback_to_internal:
        return engine_type

    if engine_type == "external_api":
        endpoint = (os.getenv("VIDEO_EXTERNAL_API_URL", "") or "").strip()
        if not endpoint:
            raise HTTPException(
                status_code=400,
                detail="external_api 엔진 설정 누락: VIDEO_EXTERNAL_API_URL 환경변수를 설정하세요.",
            )
        _assert_engine_endpoint_reachable(endpoint, "external_api")
        return engine_type

    endpoint = (os.getenv("VIDEO_DEDICATED_ENGINE_URL", "") or "").strip()
    if not endpoint:
        raise HTTPException(
            status_code=400,
            detail="dedicated_engine 설정 누락: VIDEO_DEDICATED_ENGINE_URL 환경변수를 설정하세요.",
        )

    require_generative = _is_true_env("VIDEO_REQUIRE_GENERATIVE_ENGINE", "true")
    allow_local_self_engine = _is_true_env("VIDEO_ALLOW_LOCAL_DEDICATED_ENGINE", "false")

    if require_generative and _is_mock_engine_url(endpoint):
        if not (allow_local_self_engine and _is_local_engine_url(endpoint)):
            raise HTTPException(
                status_code=400,
                detail=(
                    "dedicated_engine이 mock/local 엔드포인트로 설정되어 있습니다. "
                    "실제 텍스트-투-비디오 엔진 URL을 VIDEO_DEDICATED_ENGINE_URL에 설정하세요."
                ),
            )

    if require_generative and _is_local_engine_url(endpoint) and not allow_local_self_engine:
        raise HTTPException(
            status_code=400,
            detail=(
                "로컬 dedicated_engine은 정책상 차단되어 있습니다. "
                "VIDEO_ALLOW_LOCAL_DEDICATED_ENGINE=true 설정 또는 비로컬 엔드포인트를 사용하세요."
            ),
        )

    _assert_engine_endpoint_reachable(endpoint, "dedicated_engine")

    return engine_type


# ---------------------------------------------------------------------------
# Video generation – internal ffmpeg
# ---------------------------------------------------------------------------

def _generate_video_internal_ffmpeg(order: models.AdVideoOrder) -> bytes:
    ffmpeg_bin = os.getenv("FFMPEG_BIN", "ffmpeg")
    cut_count = _order_cut_count(order)
    cut_seconds = _order_cut_seconds(order)
    subtitle_speed = _order_subtitle_speed(order)
    audio_volume = _order_audio_volume(order)
    render_quality = _order_render_quality(order)
    bgm_enabled = _order_bgm_enabled(order)
    bgm_mood = _order_bgm_mood(order)
    bgm_volume = _order_bgm_volume(order)

    if render_quality == "ultra":
        resolution = "1920x1080"
        crf = "12"
        preset = "slower"
    elif render_quality == "standard":
        resolution = "1280x720"
        crf = "18"
        preset = "medium"
    else:
        resolution = "1920x1080"
        crf = "15"
        preset = "slow"

    volume_ratio = max(0.0, min(2.0, audio_volume / 100.0))
    audio_filter = f"atempo={subtitle_speed:.2f},volume={volume_ratio:.2f}"
    freq_base = 220 if (order.voice_gender or "female") == "female" else 140
    bgm_profile = _bgm_profile(bgm_mood)
    bgm_source = _bgm_lavfi_source(cut_seconds, bgm_mood)
    bgm_enabled = bgm_enabled and bgm_volume > 0
    bgm_volume_ratio = max(0.0, min(1.0, bgm_volume / 100.0))
    bgm_fade_in = min(0.8, max(0.3, cut_seconds / 8.0))
    bgm_fade_out = min(1.4, max(0.6, cut_seconds / 5.0))
    bgm_fade_out_start = max(0.0, cut_seconds - bgm_fade_out)
    bgm_filter = (
        f"volume={bgm_volume_ratio:.2f},"
        f"lowpass=f={int(bgm_profile['lowpass'])},"
        "aecho=0.8:0.4:45:0.18,"
        f"afade=t=in:st=0:d={bgm_fade_in:.2f},"
        f"afade=t=out:st={bgm_fade_out_start:.2f}:d={bgm_fade_out:.2f}"
    )
    captions = _compose_cut_scripts(order)
    storyboard = _compose_storyboard(order)
    colors = ["black", "#1f2937", "#111827", "#0b1220", "#1e293b", "#0f172a"]

    temp_root = _resolve_marketplace_temp_root()
    with tempfile.TemporaryDirectory(prefix="ad_video_", dir=str(temp_root)) as tmpdir:
        out_path = Path(tmpdir) / "ad.mp4"
        default_source_prompt = _get_reference_image_prompt(order)
        source_image_cache: Dict[str, Optional[Path]] = {}

        def _load_cached_source_image(image_prompt: Optional[str]) -> Optional[Path]:
            normalized_prompt = (image_prompt or "").strip()
            cache_key = normalized_prompt or "__default__"
            if cache_key not in source_image_cache:
                source_image_cache[cache_key] = _load_ad_image_from_prompt(
                    normalized_prompt or None,
                    tmpdir,
                    file_stem=f"scene_{len(source_image_cache) + 1}",
                )
            return source_image_cache.get(cache_key)

        segment_paths: List[Path] = []
        for index in range(cut_count):
            scene = storyboard[index] if index < len(storyboard) else None
            source_prompt = _resolve_storyboard_scene_source(order, scene) or default_source_prompt
            source_image = _load_cached_source_image(source_prompt)
            cut_caption = _ffmpeg_text(captions[index], limit=80)
            cut_title = _ffmpeg_text(order.title, limit=48)
            segment_path = Path(tmpdir) / f"cut_{index + 1}.mp4"
            segment_paths.append(segment_path)

            text_overlay = (
                "drawbox=x=36:y=ih-206:w=iw-72:h=162:color=black@0.45:t=fill,"
                "drawtext="
                f"text='컷 {index + 1}/{cut_count}  {cut_title}':"
                "fontcolor=white:fontsize=34:"
                "x=56:y=h-178,"
                "drawtext="
                f"text='{cut_caption}':"
                "fontcolor=white:fontsize=42:"
                "x=56:y=h-120"
            )

            if source_image and source_image.exists():
                crop_resolution = resolution.replace("x", ":")
                vf_with_image = (
                    f"scale={resolution}:force_original_aspect_ratio=increase,"
                    f"crop={crop_resolution},"
                    f"{text_overlay}"
                )
                if bgm_enabled:
                    filter_complex = (
                        f"[1:a]{audio_filter}[voice];"
                        f"[2:a]{bgm_filter}[bgm];"
                        "[voice][bgm]amix=inputs=2:duration=first[aout]"
                    )
                    cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-loop", "1", "-framerate", "25", "-i", str(source_image),
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-f", "lavfi", "-i", bgm_source,
                        "-t", str(cut_seconds),
                        "-vf", vf_with_image,
                        "-filter_complex", filter_complex,
                        "-map", "0:v:0", "-map", "[aout]",
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]
                else:
                    cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-loop", "1", "-framerate", "25", "-i", str(source_image),
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-t", str(cut_seconds),
                        "-vf", vf_with_image,
                        "-af", audio_filter,
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]
            else:
                if bgm_enabled:
                    filter_complex = (
                        f"[1:a]{audio_filter}[voice];"
                        f"[2:a]{bgm_filter}[bgm];"
                        "[voice][bgm]amix=inputs=2:duration=first[aout]"
                    )
                    cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-f", "lavfi", "-i", f"color=c={colors[index % len(colors)]}:s={resolution}:d={cut_seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-f", "lavfi", "-i", bgm_source,
                        "-vf", text_overlay,
                        "-filter_complex", filter_complex,
                        "-map", "0:v:0", "-map", "[aout]",
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]
                else:
                    cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-f", "lavfi", "-i", f"color=c={colors[index % len(colors)]}:s={resolution}:d={cut_seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-vf", text_overlay,
                        "-af", audio_filter,
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]

            cut_proc = subprocess.run(
                cut_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if (cut_proc.returncode != 0 or not segment_path.exists()) and source_image and source_image.exists():
                if bgm_enabled:
                    filter_complex = (
                        f"[1:a]{audio_filter}[voice];"
                        f"[2:a]{bgm_filter}[bgm];"
                        "[voice][bgm]amix=inputs=2:duration=first[aout]"
                    )
                    fallback_cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-f", "lavfi", "-i", f"color=c={colors[index % len(colors)]}:s={resolution}:d={cut_seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-f", "lavfi", "-i", bgm_source,
                        "-vf", text_overlay,
                        "-filter_complex", filter_complex,
                        "-map", "0:v:0", "-map", "[aout]",
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]
                else:
                    fallback_cut_cmd = [
                        ffmpeg_bin, "-y",
                        "-f", "lavfi", "-i", f"color=c={colors[index % len(colors)]}:s={resolution}:d={cut_seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency={freq_base + (index * 8)}:duration={cut_seconds}",
                        "-vf", text_overlay,
                        "-af", audio_filter,
                        "-c:v", "libx264", "-preset", preset, "-crf", crf,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(segment_path),
                    ]
                cut_proc = subprocess.run(
                    fallback_cut_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            if cut_proc.returncode != 0 or not segment_path.exists():
                raise RuntimeError(
                    f"ffmpeg cut render failed: {cut_proc.stderr[-800:]}"
                )

        concat_list = Path(tmpdir) / "concat.txt"
        concat_content = "\n".join([
            f"file '{p.as_posix()}'" for p in segment_paths
        ])
        concat_list.write_text(concat_content, encoding="utf-8")

        concat_cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            str(out_path),
        ]
        concat_proc = subprocess.run(
            concat_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if concat_proc.returncode != 0 or not out_path.exists():
            reencode_cmd = [
                ffmpeg_bin, "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(out_path),
            ]
            reencode_proc = subprocess.run(
                reencode_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if reencode_proc.returncode != 0 or not out_path.exists():
                raise RuntimeError(
                    f"ffmpeg concat failed: {reencode_proc.stderr[:400]}"
                )

        return out_path.read_bytes()


# ---------------------------------------------------------------------------
# Video generation – external API
# ---------------------------------------------------------------------------

def _generate_video_external_api(order: models.AdVideoOrder) -> tuple[bytes, Optional[str]]:
    endpoint = (os.getenv("VIDEO_EXTERNAL_API_URL", "") or "").strip()
    if not endpoint:
        raise RuntimeError("VIDEO_EXTERNAL_API_URL not configured")

    headers = _engine_headers("VIDEO_EXTERNAL_API_KEY")
    payload = _build_ad_engine_render_payload(order)

    response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "video/" in content_type:
        return response.content, None

    data = _safe_json(response, "external api")
    job_id = str(data.get("job_id") or "").strip() or None
    video_url = str(data.get("video_url") or "").strip()
    if not video_url:
        raise RuntimeError("external api response missing video_url")
    video_resp = requests.get(video_url, timeout=180)
    video_resp.raise_for_status()
    return video_resp.content, job_id


# ---------------------------------------------------------------------------
# Video generation – dedicated engine
# ---------------------------------------------------------------------------

def _dedicated_engine_adapter_mode() -> str:
    return (os.getenv("VIDEO_DEDICATED_ENGINE_ADAPTER", "default") or "default").strip().lower()


def _dedicated_engine_normalize_path(path: str, default_path: str) -> str:
    value = (path or default_path).strip() or default_path
    return value if value.startswith("/") else f"/{value}"


def _dedicated_engine_nested_value(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _dedicated_engine_first_value(data: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = _dedicated_engine_nested_value(data, path)
        if value not in {None, ""}:
            return value
    return None


def _generate_video_dedicated_engine(
    order: models.AdVideoOrder,
    progress_callback: Optional[Callable[[str, str, Optional[int], str], None]] = None,
) -> tuple[bytes, Optional[str]]:
    endpoint = (os.getenv("VIDEO_DEDICATED_ENGINE_URL", "") or "").strip()
    if not endpoint:
        raise RuntimeError("VIDEO_DEDICATED_ENGINE_URL not configured")

    require_generative = os.getenv("VIDEO_REQUIRE_GENERATIVE_ENGINE", "true").lower() in {
        "1", "true", "yes", "on"
    }
    allow_local_self_engine = os.getenv("VIDEO_ALLOW_LOCAL_DEDICATED_ENGINE", "false").lower() in {
        "1", "true", "yes", "on"
    }
    if require_generative and _is_mock_engine_url(endpoint):
        if allow_local_self_engine and _is_local_engine_url(endpoint):
            pass
        else:
            raise RuntimeError(
                "Mock dedicated engine endpoint is configured. "
                "Set VIDEO_DEDICATED_ENGINE_URL to a real text-to-video engine endpoint."
            )

    if require_generative and _is_local_engine_url(endpoint) and not allow_local_self_engine:
        raise RuntimeError(
            "Local dedicated engine endpoint is blocked by policy. "
            "Set VIDEO_ALLOW_LOCAL_DEDICATED_ENGINE=true for self-hosted local engine, "
            "or use a non-local dedicated engine URL."
        )

    adapter_mode = _dedicated_engine_adapter_mode()
    default_submit_path = "/jobs"
    submit_path = _dedicated_engine_normalize_path(
        os.getenv("VIDEO_DEDICATED_SUBMIT_PATH", default_submit_path),
        default_submit_path,
    )
    default_status_path = submit_path.rstrip("/") + "/{job_id}"
    status_path_template = _dedicated_engine_normalize_path(
        os.getenv("VIDEO_DEDICATED_STATUS_PATH_TEMPLATE", default_status_path),
        default_status_path,
    )
    if "{job_id}" not in status_path_template:
        status_path_template = status_path_template.rstrip("/") + "/{job_id}"
    result_url_tpl = endpoint.rstrip("/") + status_path_template
    submit_url = endpoint.rstrip("/") + submit_path
    headers = _engine_headers("VIDEO_DEDICATED_ENGINE_API_KEY")
    payload = _build_ad_engine_render_payload(order)
    payload["order_ref"] = f"ad-order-{order.id}"
    if adapter_mode in {"4d", "4d_designer", "4d-designer"}:
        payload.setdefault("adapter_mode", "4d_designer")

    submit = requests.post(submit_url, headers=headers, json=payload, timeout=60)
    submit.raise_for_status()
    job = _safe_json(submit, "dedicated submit")
    job_id = str(_dedicated_engine_first_value(job, "job_id", "id", "job.job_id") or "").strip()
    if not job_id:
        raise RuntimeError("dedicated engine response missing job_id")
    submit_status = str(_dedicated_engine_first_value(job, "status", "state") or "accepted").lower().strip()
    if submit_status and submit_status not in DEDICATED_STATUS_ACCEPTED:
        raise RuntimeError(f"dedicated engine invalid submit status: {submit_status}")
    if progress_callback is not None:
        submit_message = str(_dedicated_engine_first_value(job, "status_message", "message") or "").strip()
        progress_callback(job_id, submit_status or "accepted", 0, submit_message)

    timeout_sec = int(os.getenv("VIDEO_DEDICATED_TIMEOUT_SEC", "600"))
    poll_interval = float(os.getenv("VIDEO_DEDICATED_POLL_SEC", "3"))
    started = time.time()
    while time.time() - started < timeout_sec:
        poll = requests.get(result_url_tpl.format(job_id=job_id), headers=headers, timeout=30)
        poll.raise_for_status()
        data = _safe_json(poll, "dedicated status")
        payload_job_id = str(_dedicated_engine_first_value(data, "job_id", "id", "job.job_id") or job_id).strip()
        if payload_job_id != job_id:
            raise RuntimeError("dedicated engine returned mismatched job_id")
        status_value = str(_dedicated_engine_first_value(data, "status", "state", "job.status") or "").lower()
        if status_value not in DEDICATED_STATUS_ACCEPTED:
            raise RuntimeError(f"dedicated engine invalid status: {status_value}")

        progress_percent = _parse_progress_percent(
            _dedicated_engine_first_value(data, "progress_percent", "progress", "metadata.progress_percent")
        )
        error_message = str(
            _dedicated_engine_first_value(
                data,
                "status_message",
                "message",
                "error_message",
                "error",
            ) or ""
        ).strip()
        if progress_callback is not None:
            progress_callback(job_id, status_value, progress_percent, error_message)

        if status_value in DEDICATED_STATUS_COMPLETED:
            video_url = str(
                _dedicated_engine_first_value(
                    data,
                    "video_url",
                    "result.video_url",
                    "output.video_url",
                ) or ""
            ).strip()
            if not video_url:
                raise RuntimeError("dedicated engine completed without video_url")
            video_resp = requests.get(video_url, timeout=180)
            video_resp.raise_for_status()
            return video_resp.content, job_id
        if status_value in DEDICATED_STATUS_FAILED:
            error_text = (
                str(_dedicated_engine_first_value(data, "error_message", "error", "status_message", "message") or "").strip()
                or "dedicated engine failed"
            )
            error_code = str(_dedicated_engine_first_value(data, "error_code", "error.code") or "").strip()
            if error_code:
                raise RuntimeError(f"{error_code}: {error_text}")
            raise RuntimeError(error_text)
        time.sleep(poll_interval)

    raise RuntimeError("dedicated engine timeout")


# ---------------------------------------------------------------------------
# Video generation – movie studio
# ---------------------------------------------------------------------------

def _build_movie_studio_payload_from_order(order: models.AdVideoOrder) -> Dict[str, object]:
    storyboard = _compose_storyboard(order)
    sequence_beats = [
        {
            "objective": str(scene.get("title") or f"scene {index + 1}").strip() or f"scene {index + 1}",
            "emotional_state": "conversion intent" if index == len(storyboard) - 1 else "controlled realism",
            "blocking_summary": str(scene.get("visual_focus") or scene.get("scene_prompt") or scene.get("title") or "cinematic scene progression").strip(),
            "cta_required": index == len(storyboard) - 1,
        }
        for index, scene in enumerate(storyboard[:12])
    ]

    identity_references: List[str] = []
    portrait_reference = str(getattr(order, "portrait_image_prompt", "") or "").strip()
    if portrait_reference:
        identity_references.append(portrait_reference)

    # BUG FIX: _parse_ad_image_prompt_list → _get_product_image_prompts
    product_images = [str(item).strip() for item in (_get_product_image_prompts(order) or []) if str(item).strip()]
    environment_references = product_images[:3]
    if not environment_references:
        primary_image = str(getattr(order, "image_prompt", "") or "").strip()
        if primary_image:
            environment_references.append(primary_image)

    return {
        "project_id": f"ad-order-{order.id}",
        "title": str(order.title or f"ad-order-{order.id}").strip() or f"ad-order-{order.id}",
        "synopsis": str(getattr(order, "scenario_script", None) or order.caption_text or order.background_prompt or order.title or "movie studio ad order").strip(),
        "genre": "commercial cinema",
        "tone": str(getattr(order, "visual_style", "photorealistic") or "photorealistic").strip() or "photorealistic",
        "realism_level": "photoreal",
        "species": "human" if portrait_reference else "product",
        "environment_type": "studio",
        "location_summary": str(order.background_prompt or "premium commercial studio").strip(),
        "background_prompt": str(order.background_prompt or "premium commercial studio").strip(),
        "target_duration_seconds": _order_duration_seconds(order),
        "target_fps": 24,
        "target_resolution": "1080x1920",
        "voice_track": str(order.caption_text or "").strip() or None,
        "continuity_rules": [
            "scene flow continuity",
            "photoreal identity continuity",
            "stable environment realism",
            "cinematic camera continuity",
        ],
        "hero_props": [str(order.title or "hero product").strip() or "hero product"],
        "sequence_beats": sequence_beats,
        "identity_references": identity_references,
        "environment_references": environment_references,
        "operator_note": f"ad_order_id={order.id}; public_job_id={order.public_job_id}",
    }


def _generate_video_movie_studio(
    order: models.AdVideoOrder,
    progress_callback: Optional[Callable[[str, str, Optional[int], str], None]] = None,
) -> tuple[bytes, Optional[str]]:
    from backend.movie_studio.orchestration.studio_orchestrator import execute_movie_studio_project

    job_id = str(order.public_job_id or order.id)
    if progress_callback is not None:
        progress_callback(job_id, "planning", 5, "movie studio scene flow planning")
    result = execute_movie_studio_project(_build_movie_studio_payload_from_order(order))
    if progress_callback is not None:
        progress_callback(job_id, "rendering", 85, "movie studio render completed")

    render_result = dict((result.get("render_manifest") or {}).get("render_result") or {})
    output_mp4_path = str(render_result.get("output_mp4_path") or result.get("output_mp4_path") or "").strip()
    if str(render_result.get("status") or "") != "completed" or not output_mp4_path:
        raise RuntimeError(f"movie studio render failed: {render_result.get('error_message') or 'output missing'}")

    quality_result = dict((result.get("quality_runtime_manifest") or {}).get("quality_result") or result.get("quality_result") or {})
    if not bool(quality_result.get("passed", False)):
        failures = quality_result.get("failures") or []
        failure_text = "; ".join(str(item.get("message") or item.get("code") or "quality failure") for item in failures[:5] if isinstance(item, dict))
        raise RuntimeError(f"movie studio quality gate failed: {failure_text or 'unknown failure'}")

    video_path = Path(output_mp4_path)
    if not video_path.exists() or not video_path.is_file():
        raise RuntimeError("movie studio output mp4 missing")

    if progress_callback is not None:
        progress_callback(job_id, "completed", 100, f"movie studio output ready: {video_path.name}")
    return video_path.read_bytes(), None


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

def _generate_video_by_engine(
    order: models.AdVideoOrder,
    progress_callback: Optional[Callable[[str, str, Optional[int], str], None]] = None,
) -> tuple[bytes, Optional[str]]:
    engine_type = (order.engine_type or "internal_ffmpeg").strip().lower()
    fallback = os.getenv("VIDEO_ENGINE_FALLBACK_TO_INTERNAL", "false").lower() in {
        "1", "true", "yes", "on"
    }

    job_id = str(order.public_job_id or order.id)

    def _is_torch_stack_error(exc: Exception) -> bool:
        name = str(getattr(exc, "name", "") or "").strip().lower()
        if name in {"torch", "torchvision"}:
            return True
        message = str(exc or "").lower()
        return "torch" in message or "torchvision" in message

    try:
        if engine_type == "external_api":
            return _generate_video_external_api(order)
        if engine_type == "dedicated_engine":
            return _generate_video_movie_studio(order, progress_callback=progress_callback)
        return _generate_video_internal_ffmpeg(order), None
    except ModuleNotFoundError as exc:
        if engine_type == "dedicated_engine" and _is_torch_stack_error(exc):
            if progress_callback is not None:
                progress_callback(job_id, "fallback", 70, "torch unavailable; fallback to internal ffmpeg")
            return _generate_video_internal_ffmpeg(order), None
        raise
    except ImportError as exc:
        if engine_type == "dedicated_engine" and _is_torch_stack_error(exc):
            if progress_callback is not None:
                progress_callback(job_id, "fallback", 70, "torch stack unavailable; fallback to internal ffmpeg")
            return _generate_video_internal_ffmpeg(order), None
        raise
    except Exception:
        if fallback and engine_type != "internal_ffmpeg":
            if progress_callback is not None:
                progress_callback(job_id, "fallback", 70, "engine failure; fallback to internal ffmpeg")
            return _generate_video_internal_ffmpeg(order), None
        raise
