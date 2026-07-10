from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, func
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio
import logging
import os
import io
import zipfile
import re
import json
import sys
import queue
import threading
import subprocess
import tempfile
import time
import shutil
import socket
import requests
import hashlib
import base64
import binascii
import hmac as _hmac_module
from urllib.parse import quote, urlparse
from uuid import uuid4

from redis.exceptions import RedisError
from . import models, schemas, crud
from .subscription_service import subscription_service
from .ad_strategy_engine import plan_ad_strategy
from .audience_profile_engine import infer_audience_profiles
from .campaign_orchestrator_engine import plan_local_campaign
from .caption_engine import build_caption_package
from .creative_variant_engine import build_creative_variants
from .ffmpeg_render_executor import render_final_video
from .image_generation_engine import run_image_generation_engine
from .image_to_video_pipeline import run_image_to_video_pipeline
from .local_designer_engine import render_local_designer_sequence
from .local_video_connector import plan_local_video_connector
from .platform_formatter import build_platform_formats
from .self_run_video_worker import enqueue_self_run_video_job, get_self_run_video_job, get_self_run_video_worker_status
from .story_state_engine import build_story_states
from .video_generation_engine import run_video_generation_engine
from .database import get_db, engine, SessionLocal, check_database_availability, init_db
from .subscription_router import build_subscription_router
from .feature_orchestrator.engines.spreadsheet_generation_engine import (
    build_spreadsheet_preview,
    render_spreadsheet_final,
    review_spreadsheet_quality,
)
from .feature_orchestrator.engines.powerpoint_generation_engine import (
    build_powerpoint_preview,
    render_powerpoint_final,
    review_powerpoint_quality,
)
from .feature_orchestrator.engines.document_generation_engine import (
    build_document_preview,
    render_document_final,
    review_document_quality,
)
from .minio_service import minio_service
from .payment_service import payment_service, download_token_service
from .campaign_orchestrate_router import build_campaign_orchestrate_router
from .categories_router import build_categories_router
from .code_generator_router import build_code_generator_router
from .ad_order_runtime import (
    VIDEO_RENDER_QUEUE_NAME,
    _enqueue_ad_order,
    _mark_ad_worker_heartbeat,
    _require_video_queue_redis,
    discard_enqueued_ad_order,
    ensure_ad_order_runtime_ready,
    ensure_ad_video_orders_schema,
    get_ad_queue_runtime_status,
)
from .ad_order_processing import (
    build_ad_package_zip,
    process_ad_order_job,
    reset_ad_order_for_retry,
)
from .face_recognition_router import build_face_recognition_router
from .feature_orchestrate_router import build_feature_orchestrate_router
from .interpreter_router import build_interpreter_router
from .nadotongryoksa_lbs_router import build_nadotongryoksa_lbs_router
from .ml_detectors_router import build_ml_detectors_router
from .music_router import build_music_router
from .extras_router import build_extras_router
from .sorisae_engine_router import build_sorisae_engine_router
from .shinsegye_products_router import build_shinsegye_products_router
from .search_router import build_search_router
from .customer_orchestrate_router import build_customer_orchestrate_router
from .video_worker_router import build_video_worker_router
from .marketplace_categories_cache import (
    _MARKETPLACE_CATEGORIES_CACHE,
    _MARKETPLACE_CATEGORIES_CACHE_LOCK,
    _MARKETPLACE_CATEGORIES_CACHE_TTL_SEC,
    _MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC,
    _apply_marketplace_categories_degraded_headers,
    _apply_short_marketplace_categories_cache_headers,
    _build_marketplace_categories_degraded_payload,
    _invalidate_marketplace_categories_cache,
    _should_throttle_marketplace_categories,
)
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
from backend.auth import get_current_user
from backend.orchestration_stage_service import (
    ORCHESTRATION_STAGE_DEFINITIONS,
    build_stage_tracking_payload,
    initialize_stage_run,
    load_stage_run,
    save_stage_run,
    update_stage_run,
)
from backend.orchestrator.chat import AutoConnectMeta, OrchestratorChatRequest, OrchestratorChatResponse, OrchestratorStageChatContext
import secrets
from .customer_orchestrate_context import (
    _customer_orchestrate_run_locks,
    _customer_orchestrate_run_locks_guard,
)
from .ad_video_order_engine import (
    MARKETPLACE_QUALITY_PASS_SCORE,
    MARKETPLACE_MAX_AUTO_QUALITY_RETRIES,
    _ad_order_queue,
    _maybe_run_marketplace_storage_cleanup,
    _evaluate_ad_order_quality,
    _generate_video_by_engine,
    _get_reference_image_prompt,
    _order_audio_volume,
    _order_cut_count,
    _order_cut_seconds,
    _order_duration_seconds,
    _order_render_quality,
    _order_subtitle_speed,
    _serialize_ad_video_order,
    _compose_storyboard,
    _get_product_image_prompts,
    _validate_ad_engine_preflight,
    _build_scene_keyframes,
    _generate_video_internal_ffmpeg,
    _generate_video_movie_studio,
    _generate_video_external_api,
    _generate_video_dedicated_engine,
    _assert_engine_endpoint_reachable,
    _safe_filename,
    _stability_profile_for_order,
    _resolve_scene_source,
    _build_movie_studio_payload_from_order,
    MARKETPLACE_AD_QUALITY_CRITERIA,
    AD_TOTAL_SECONDS,
    AD_FRAME_HINTS_PER_SECOND,
    AD_TOTAL_FRAME_HINT,
    AD_CUT_COUNT,
    AD_CUT_SECONDS,
)

logger = logging.getLogger(__name__)


async def _run_async_request_in_thread(coro):
    return await asyncio.to_thread(lambda: asyncio.run(coro))


def _schedule_marketplace_storage_cleanup() -> None:
    def _runner() -> None:
        try:
            _maybe_run_marketplace_storage_cleanup()
        except Exception:
            logger.warning("marketplace storage cleanup scheduling failed", exc_info=True)

    threading.Thread(
        target=_runner,
        name="marketplace-storage-cleanup",
        daemon=True,
    ).start()

router = APIRouter()


class FeatureOrchestrateAcceptedRequest(BaseModel):
    feature_id: str
    project_name: str
    prompt: str
    template_id: Optional[str] = None
    photo_reference: Optional[str] = None
    photo_content_type: Optional[str] = None
    photo_size: Optional[int] = None
    final_enabled: bool = True
    context_tags: List[str] = []


class FeatureOrchestrateStreamRequest(BaseModel):
    run_id: str


class FeatureOrchestrateAcceptedResponse(BaseModel):
    accepted: bool
    run_id: str
    stage_run: Dict[str, Any]
    status: str
    stream_url: str
    poll_url: str


class _FeatureRuntimeHandler:
    def __init__(
        self,
        *,
        preview_runner,
        final_runner,
        quality_runner,
    ):
        self._preview_runner = preview_runner
        self._final_runner = final_runner
        self._quality_runner = quality_runner

    def run_preview_phase(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._preview_runner(payload)

    def run_final_phase(self, payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
        return self._final_runner(payload, preview_artifact)

    def run_quality_gate(
        self,
        payload: Dict[str, Any],
        preview_artifact: Dict[str, Any],
        final_artifact: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._quality_runner(payload, preview_artifact, final_artifact)

    def build_artifact_manifest(
        self,
        preview_artifact: Dict[str, Any],
        final_artifact: Dict[str, Any],
        quality_review: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "preview_artifact": preview_artifact,
            "final_artifact": final_artifact,
            "quality_review": quality_review,
        }


class FeatureOrchestratorRuntimeService:
    def get_catalog(self) -> List[Dict[str, Any]]:
        return list(_FEATURE_CATALOG)

    def get_service(self, feature_id: str) -> _FeatureRuntimeHandler:
        normalized = str(feature_id or "").strip().lower()
        runtime_registry: Dict[str, _FeatureRuntimeHandler] = {
            "ai-sheet": _FeatureRuntimeHandler(
                preview_runner=build_spreadsheet_preview,
                final_runner=render_spreadsheet_final,
                quality_runner=review_spreadsheet_quality,
            ),
            "ai-document": _FeatureRuntimeHandler(
                preview_runner=build_document_preview,
                final_runner=render_document_final,
                quality_runner=review_document_quality,
            ),
            "ai-powerpoint": _FeatureRuntimeHandler(
                preview_runner=build_powerpoint_preview,
                final_runner=render_powerpoint_final,
                quality_runner=review_powerpoint_quality,
            ),
        }
        runtime_handler = runtime_registry.get(normalized)
        if runtime_handler is None:
            raise ValueError("지원하지 않는 feature_id 입니다.")
        return runtime_handler


_FEATURE_CATALOG: List[Dict[str, Any]] = [
    {
        "feature_id": "ai-sheet",
        "title": "AI 엑셀 시트",
        "summary": "프롬프트 기반으로 시트 schema preview 와 최종 workbook 패키지를 생성합니다.",
        "popup_mode": "spreadsheet-builder",
        "status": "enabled",
        "supports_photo_upload": False,
        "supports_final_phase": True,
    },
    {
        "feature_id": "ai-document",
        "title": "AI 문서 엔진",
        "summary": "문서 outline preview 와 최종 pdf/md 패키지를 생성합니다.",
        "popup_mode": "doc-writer",
        "status": "enabled",
        "supports_photo_upload": False,
        "supports_final_phase": True,
    },
    {
        "feature_id": "ai-powerpoint",
        "title": "AI 파워포인트 엔진",
        "summary": "프롬프트 기반으로 슬라이드 구성 preview 와 최종 pptx 패키지를 생성합니다.",
        "popup_mode": "powerpoint-builder",
        "status": "enabled",
        "supports_photo_upload": False,
        "supports_final_phase": True,
    },
]

_feature_runtime_service = FeatureOrchestratorRuntimeService()

_FEATURE_POPUP_STAGE_MAP = {
    "accepted": "ARCH-001",
    "preview_running": "ARCH-007",
    "preview_ready": "ARCH-008",
    "final_running": "ARCH-009",
    "quality_review": "ARCH-010",
    "completed": "ARCH-010",
    "completed_preview_only": "ARCH-010",
    "failed": "ARCH-010",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_feature_sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps({'event': event, 'payload': payload}, ensure_ascii=False)}\n\n"


def _build_feature_progress_payload(
    run_id: str,
    *,
    percent: int,
    step: str,
    state: str,
    message: str,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "state": state,
        "progress": {
            "percent": max(0, min(100, int(percent))),
            "step": step,
            "message": message,
            "updated_at": _utc_now_iso(),
        },
    }


def _get_feature_stage_run_or_404(run_id: str) -> Dict[str, Any]:
    payload = load_stage_run(run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="feature stage run을 찾을 수 없습니다.")
    return payload


def _get_feature_metadata(stage_run_payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(stage_run_payload.get("metadata") or {})
    return dict(metadata.get("feature_orchestrator") or {})


def _set_feature_metadata(stage_run_payload: Dict[str, Any], feature_metadata: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(stage_run_payload.get("metadata") or {})
    metadata["feature_orchestrator"] = feature_metadata
    stage_run_payload["metadata"] = metadata
    return stage_run_payload


def _apply_feature_popup_state(stage_run_payload: Dict[str, Any], popup_state: str, note: str = "") -> Dict[str, Any]:
    target_stage_id = _FEATURE_POPUP_STAGE_MAP.get(popup_state, "ARCH-010")
    ordered_ids = [item["id"] for item in ORCHESTRATION_STAGE_DEFINITIONS]
    target_index = ordered_ids.index(target_stage_id) if target_stage_id in ordered_ids else len(ordered_ids) - 1
    now = _utc_now_iso()
    for index, stage in enumerate(stage_run_payload.get("stages") or []):
        if index < target_index:
            stage["status"] = "passed"
            stage["check_label"] = "통과"
        elif index == target_index:
            if popup_state == "failed":
                stage["status"] = "failed"
                stage["check_label"] = "미통과"
            elif popup_state in {"completed", "completed_preview_only"}:
                stage["status"] = "passed"
                stage["check_label"] = "통과"
            else:
                stage["status"] = "running"
                stage["check_label"] = "진행 중"
            if note:
                stage["note"] = note
        else:
            stage["status"] = "pending"
            stage["check_label"] = "대기"
        stage["updated_at"] = now
    stage_run_payload["current_stage_id"] = target_stage_id
    stage_run_payload["status"] = "blocked" if popup_state == "failed" else "completed" if popup_state in {"completed", "completed_preview_only"} else "running"
    stage_run_payload["final_completed"] = popup_state == "completed"
    return stage_run_payload


def _iter_feature_artifacts(feature_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for key in ("preview_artifact", "final_artifact"):
        artifact = feature_metadata.get(key)
        if isinstance(artifact, dict):
            artifacts.append(dict(artifact))
    manifest = feature_metadata.get("artifact_manifest")
    if isinstance(manifest, dict):
        for key in ("preview_artifact", "final_artifact"):
            artifact = manifest.get(key)
            if isinstance(artifact, dict):
                artifacts.append(dict(artifact))
    return artifacts


def _resolve_feature_delivery_asset_or_404(run_id: str, asset_format: str) -> Dict[str, Any]:
    stage_run = _get_feature_stage_run_or_404(run_id)
    feature_metadata = _get_feature_metadata(stage_run)
    normalized_format = str(asset_format or "").strip().lower()
    if not normalized_format:
        raise HTTPException(status_code=400, detail="asset format 이 필요합니다.")

    for artifact in _iter_feature_artifacts(feature_metadata):
        for asset in list(artifact.get("delivery_assets") or []):
            if str(asset.get("format") or "").strip().lower() != normalized_format:
                continue
            asset_path = Path(str(asset.get("path") or "")).expanduser()
            if not asset_path.exists() or not asset_path.is_file():
                raise HTTPException(status_code=404, detail="delivery asset 파일이 존재하지 않습니다.")
            return {
                "artifact": artifact,
                "asset": asset,
                "path": asset_path.resolve(),
            }

    raise HTTPException(status_code=404, detail="요청한 delivery asset 을 찾을 수 없습니다.")


@router.get("/feature-orchestrate/stage-runs/{run_id}/delivery-assets/{asset_format}")
def download_marketplace_feature_delivery_asset(run_id: str, asset_format: str):
    resolved = _resolve_feature_delivery_asset_or_404(run_id, asset_format)
    asset = dict(resolved.get("asset") or {})
    asset_path = Path(str(resolved.get("path") or ""))
    media_type = str(asset.get("mime_type") or "application/octet-stream")
    download_name = asset_path.name
    return FileResponse(path=str(asset_path), media_type=media_type, filename=download_name)



def _sign_test_download_token(filename: str, user_id: int, secret: str, expires_in: int = 3600) -> str:
    """HMAC-SHA256 서명 기반 임시 다운로드 토큰 생성 (DB 불필요)"""
    exp = int(time.time()) + expires_in
    msg = f"{filename}:{user_id}:{exp}"
    sig = _hmac_module.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    payload = base64.urlsafe_b64encode(f"{msg}:{sig}".encode()).decode()
    return payload


def _verify_test_download_token(token: str, filename: str, secret: str) -> bool:
    """HMAC-SHA256 토큰 검증. 만료 또는 서명 불일치 시 False 반환"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode() + b"==").decode()
        # 마지막 ':' 기준으로 sig 분리
        last_colon = decoded.rfind(":")
        if last_colon < 0:
            return False
        msg, sig = decoded[:last_colon], decoded[last_colon + 1:]
        parts = msg.split(":")
        if len(parts) != 3:
            return False
        fname, _uid, exp_str = parts
        if fname != filename:
            return False
        if int(exp_str) < int(time.time()):
            return False
        expected_sig = _hmac_module.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return _hmac_module.compare_digest(sig, expected_sig)
    except Exception:
        return False


def _resolve_marketplace_apk_dir() -> Path:
    workspace_root = Path(__file__).resolve().parents[2]
    return (workspace_root / "uploads" / "marketplace_local" / "apk").resolve()


def _resolve_latest_marketplace_apk_path() -> Path:
    apk_dir = _resolve_marketplace_apk_dir()
    if not apk_dir.exists() or not apk_dir.is_dir():
        raise HTTPException(status_code=404, detail="APK 저장 경로를 찾을 수 없습니다.")

    preferred_name = str(os.getenv("MARKETPLACE_LATEST_APK_FILENAME", "")).strip()
    if preferred_name:
        safe_name = Path(preferred_name).name
        target = (apk_dir / safe_name).resolve()
        if str(target).startswith(str(apk_dir)) and target.exists() and target.suffix.lower() == ".apk":
            return target

    apk_candidates = [
        path.resolve()
        for path in apk_dir.glob("*.apk")
        if path.is_file()
    ]
    if not apk_candidates:
        raise HTTPException(status_code=404, detail="배포 가능한 APK 파일이 없습니다.")

    apk_candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return apk_candidates[0]


@router.get("/latest.apk")
def download_latest_marketplace_apk() -> Any:
    """모바일 자동업데이트용 고정 APK URL 엔드포인트."""
    target = _resolve_latest_marketplace_apk_path()
    return FileResponse(
        path=str(target),
        media_type="application/vnd.android.package-archive",
        filename="latest.apk",
        headers={
            "Content-Disposition": 'attachment; filename="latest.apk"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post("/apk/test-token/{filename}")
def issue_apk_test_download_token(
    filename: str,
    current_user: Any = Depends(get_current_user),
):
    """테스트 기간 APK 다운로드용 단기 서명 토큰 발급
    
    구매 이력 없이 로그인한 사용자에게 7일 유효 토큰 발급.
    토큰은 HMAC-SHA256 서명이며 DB 레코드 없이 검증됨.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    allowed_extensions = {".apk", ".zip"}
    if Path(safe_name).suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
    from backend.auth import SECRET_KEY
    token = _sign_test_download_token(
        filename=safe_name,
        user_id=int(current_user.id),
        secret=SECRET_KEY,
        expires_in=7 * 24 * 3600,  # 7일
    )
    download_url = f"/api/marketplace/apk/{safe_name}?test_token={token}"
    return {"token": token, "download_url": download_url, "expires_in": 7 * 24 * 3600}


@router.get("/apk/{filename}")
def download_marketplace_apk(
    filename: str,
    token: Optional[str] = None,
    test_token: Optional[str] = None,
    current_user: Any = None,
) -> Any:
    """모바일 APK 직접 다운로드 엔드포인트 — 신세계소리새 나도통역사 등
    
    인증 필수: 구매자 또는 유효한 다운로드 토큰 보유
    토큰은 query parameter로 전달: /apk/file.apk?token=abc123
    test_token 보유 시 Bearer 인증 없이도 HMAC 검증으로 다운로드 허용
    """
    # 경로 탐색(path traversal) 방어 — 인증 검증 전에 수행
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    allowed_extensions = {".apk", ".zip"}
    suffix = Path(safe_name).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    apk_dir = _resolve_marketplace_apk_dir()
    target = (apk_dir / safe_name).resolve()
    if not str(target).startswith(str(apk_dir)):
        raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")
    if not target.exists():
        raise HTTPException(status_code=404, detail="APK 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")

    # 다운로드 토큰 검증: test_token은 HMAC 서명 자체가 인증 대체 수단 (브라우저 직접 다운로드 지원)
    if test_token:
        from backend.auth import SECRET_KEY
        if not _verify_test_download_token(test_token, safe_name, SECRET_KEY):
            raise HTTPException(status_code=403, detail="테스트 다운로드 토큰이 만료되었거나 올바르지 않습니다.")
    elif token:
        try:
            with SessionLocal() as token_db:
                download_token = download_token_service.validate_token(token_db, token)
                # 토큰 사용 표시 (1회 사용 제한)
                download_token_service.use_token(token_db, token)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=f"다운로드 토큰 검증 실패: {str(e)}")
    else:
        # 토큰 없는 경우 — 로그인 사용자의 구매 여부 확인 또는 401
        if not current_user:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        # TODO: 구매 기록 확인 로직 구현

    media_type = "application/vnd.android.package-archive" if suffix == ".apk" else "application/zip"
    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/zip/{filename}")
def download_marketplace_zip(
    filename: str,
    token: Optional[str] = None,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Python/소프트웨어 ZIP 직접 다운로드 엔드포인트 — 소리새 통번역 패키지 등
    
    인증 필수: 구매자 또는 유효한 다운로드 토큰 보유
    토큰은 query parameter로 전달: /zip/file.zip?token=abc123
    """
    # 인증 확인 (current_user가 None이면 401 자동 반환됨)
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    if Path(safe_name).suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="ZIP 파일만 지원합니다.")

    workspace_root = Path(__file__).resolve().parents[2]
    zip_dir = (workspace_root / "uploads" / "marketplace_local" / "zip").resolve()
    target = (zip_dir / safe_name).resolve()
    if not str(target).startswith(str(zip_dir)):
        raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")
    if not target.exists():
        raise HTTPException(status_code=404, detail="ZIP 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")

    # 다운로드 토큰 검증 (토큰이 전달된 경우)
    if token:
        try:
            download_token = download_token_service.validate_token(db, token)
            # 토큰 사용 표시 (1회 사용 제한)
            download_token_service.use_token(db, token)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=f"다운로드 토큰 검증 실패: {str(e)}")
    else:
        # 토큰이 없는 경우, 현재 사용자의 구매 여부 확인
        # TODO: 구매 기록 확인 로직 구현
        pass

    return FileResponse(
        path=str(target),
        media_type="application/zip",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/projects", response_model=schemas.ProjectList)
def list_marketplace_projects(
    skip: int = 0,
    limit: int = 12,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    projects, total = crud.get_projects(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        order=sort_order,
    )
    linked_subscriptions = subscription_service.list_project_subscription_links(
        db,
        project_ids=[int(project.id) for project in projects], # type: ignore
    )
    serialized_projects: list[dict[str, Any]] = []
    for project in projects:
        payload = schemas.Project.model_validate(project).model_dump()
        payload["subscription"] = linked_subscriptions.get(int(project.id)) # type: ignore
        serialized_projects.append(payload)
    return {
        "projects": serialized_projects,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/projects/{project_id}", response_model=schemas.Project)
def get_marketplace_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")
    linked_subscriptions = subscription_service.list_project_subscription_links(
        db,
        project_ids=[int(project.id)], # type: ignore
    )
    payload = schemas.Project.model_validate(project).model_dump()
    payload["subscription"] = linked_subscriptions.get(int(project.id)) # type: ignore
    return payload


# ── 마켓플레이스 구매/결제/다운로드 API ──────────────────────

class PurchaseCreateRequest(BaseModel):
    project_id: int
    amount: float
    payment_method: str = "card"


class DownloadTokenRequest(BaseModel):
    project_id: int


@router.post("/purchase")
def create_marketplace_purchase(
    request: PurchaseCreateRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Purchase:
    """구매 기록 생성
    
    인증 필수: 로그인한 사용자만
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    project = crud.get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    
    purchase = payment_service.create_purchase(
        db=db,
        project_id=request.project_id,
        buyer_id=current_user.id,
        amount=request.amount or float(project.price or 0),
        payment_method=request.payment_method,
    )
    
    return schemas.Purchase.model_validate(purchase)


@router.post("/purchase/{purchase_id}/pay")
def initiate_marketplace_payment(
    purchase_id: int,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PaymentInitResult:
    """결제 초기화 (PG사 결제 URL 반환)
    
    인증 필수: 해당 구매의 소유자만
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    purchase = payment_service.get_purchase_by_id(db, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="구매 기록을 찾을 수 없습니다.")
    
    if purchase.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인의 구매만 결제할 수 있습니다.")
    
    result = payment_service.initiate_payment(
        purchase_id=purchase_id,
        purchase=purchase,
    )
    
    return schemas.PaymentInitResult(**result)


@router.get("/purchases")
def list_user_purchases(
    skip: int = 0,
    limit: int = 20,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """사용자 구매 내역 조회
    
    인증 필수: 로그인한 사용자
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    purchases, total = payment_service.get_user_purchases(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    
    serialized = [
        schemas.Purchase.model_validate(p).model_dump()
        for p in purchases
    ]
    
    return {
        "purchases": serialized,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/purchase/{purchase_id}/refund")
def request_marketplace_refund(
    purchase_id: int,
    request: BaseModel,  # type: ignore
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.Purchase:
    """구매 환불 요청
    
    인증 필수: 해당 구매의 소유자만
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    purchase = payment_service.get_purchase_by_id(db, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="구매 기록을 찾을 수 없습니다.")
    
    if purchase.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인의 구매만 환불할 수 있습니다.")
    
    # 상태를 "refunded"로 변경
    purchase = payment_service.confirm_payment(
        db=db,
        purchase_id=purchase_id,
        transaction_id=purchase.transaction_id or f"REFUND_{uuid4().hex[:12]}",
        status="refunded",
    )
    
    return schemas.Purchase.model_validate(purchase)


@router.post("/download-token")
def create_marketplace_download_token(
    request: DownloadTokenRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """다운로드 토큰 생성
    
    인증 필수: 로그인한 사용자
    다운로드 권한이 있는 경우에만 토큰 발급
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    
    project = crud.get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    
    # 구매 여부 확인 (구매하지 않았으면 토큰 발급 거부)
    purchases = db.query(models.Purchase).filter(
        models.Purchase.project_id == request.project_id,
        models.Purchase.buyer_id == current_user.id,
        models.Purchase.status.in_(["completed", "pending"]),
    ).all()
    
    if not purchases:
        raise HTTPException(status_code=403, detail="구매 이력이 없어 다운로드할 수 없습니다.")
    
    # 토큰 생성 (1시간 유효)
    download_token = download_token_service.create_token(
        db=db,
        project_id=request.project_id,
        user_id=current_user.id,
        expires_in=3600,
    )
    
    return {
        "token": download_token.token,
        "expires_at": download_token.expires_at.isoformat(),
    }


router.include_router(build_subscription_router(sys.modules[__name__]))


router.include_router(build_categories_router(sys.modules[__name__]))


router.include_router(build_feature_orchestrate_router(sys.modules[__name__]))


# ── Campaign Orchestrator API ──────────────────────────────

class CampaignPlanRequest(BaseModel):
    title: str = ""
    scenario_script: str = ""
    campaign_goal: str = "conversion"
    creative_modes: List[str] = []
    duration_profiles: List[int] = [60]
    preview_fps: int = 8
    subtitle_speed: float = 1.0
    background_prompt: str = ""
    caption_text: str = ""
    portrait_image_prompt: str = ""
    product_catalog: List[str] = []
    action_template_key: Optional[str] = None
    motion_tempo: Optional[str] = None
    storyboard: List[Dict[str, Any]] = []


router.include_router(build_campaign_orchestrate_router(sys.modules[__name__]))


# ── Video Worker Monitoring API ────────────────────────────

class VideoJobRequest(BaseModel):
    title: str = ""
    scenario_script: str = ""
    duration_seconds: int = 60
    frames_per_second: int = 8


router.include_router(build_video_worker_router(sys.modules[__name__]))


# ── Vector Search (Qdrant) API ─────────────────────────────

router.include_router(build_search_router(sys.modules[__name__]))


# ── Code Generator API ─────────────────────────────────────

router.include_router(build_code_generator_router(sys.modules[__name__]))


# ── ArcFace Face Recognition API ───────────────────────────

router.include_router(build_face_recognition_router(sys.modules[__name__]))


# ── ML Detector Runtime API ────────────────────────────────

router.include_router(build_ml_detectors_router(sys.modules[__name__]))


# ── Interpreter API ────────────────────────────────────────

router.include_router(build_interpreter_router(sys.modules[__name__]))


# ── Nadotongryoksa LBS API ─────────────────────────────────

router.include_router(build_nadotongryoksa_lbs_router(sys.modules[__name__]))


# ── Music System API ───────────────────────────────────────

router.include_router(build_music_router(sys.modules[__name__]))


# ── Extras API (IoT, 게임경제, 복구) ──────────────────────
router.include_router(build_extras_router(sys.modules[__name__]))

# ── Sorisae AI Engine Control Tower ───────────────────────
router.include_router(build_sorisae_engine_router(sys.modules[__name__]))

# ── Shinsegye 18 Projects Marketplace ─────────────────────
router.include_router(build_shinsegye_products_router(sys.modules[__name__]))

def _compose_trace_fields(flow_id: str, step_id: str, action: str) -> Dict[str, str]:
    return {
        "flow_id": flow_id,
        "step_id": step_id,
        "action": action,
        "trace_id": f"{flow_id}:{step_id}:{action}",
    }


def _write_feature_execution_log(
    db: Session,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: str,
    flow_id: str,
    step_id: str,
    action: str,
    status: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
) -> models.FeatureExecutionLog: # type: ignore
    trace_fields = _compose_trace_fields(flow_id, step_id, action)
    row = models.FeatureExecutionLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        flow_id=trace_fields["flow_id"],
        step_id=trace_fields["step_id"],
        action=trace_fields["action"],
        trace_id=trace_fields["trace_id"],
        status=status,
        message=message,
        payload_json=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
    )
    db.add(row)
    db.flush()


def _enqueue_feature_retry_record(
    db: Session,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: str,
    flow_id: str,
    step_id: str,
    action: str,
    queue_name: str,
    payload: Optional[Dict[str, Any]] = None,
    last_error: Optional[str] = None,
    status: str = "queued",
    attempt_count: int = 0,
) -> models.FeatureRetryQueue:
    trace_fields = _compose_trace_fields(flow_id, step_id, action)
    row = models.FeatureRetryQueue(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        flow_id=trace_fields["flow_id"],
        step_id=trace_fields["step_id"],
        action=trace_fields["action"],
        trace_id=trace_fields["trace_id"],
        queue_name=queue_name,
        status=status,
        payload_json=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
        last_error=last_error,
        attempt_count=attempt_count,
    )
    db.add(row)
    db.flush()
    return row


def _resolve_frontend_origin(request: Request) -> str:
    configured = (os.getenv("FRONTEND_PUBLIC_URL", "") or "").strip().rstrip("/")
    if configured:
        return configured

    origin = (request.headers.get("origin", "") or "").strip().rstrip("/")
    if origin:
        return origin

    host = (request.headers.get("host", "") or "").strip()
    if host:
        if host.startswith("127.0.0.1:8000") or host.startswith("localhost:8000"):
            return "http://localhost:3000"
        scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
        return f"{scheme}://{host}".rstrip("/")

    return "http://localhost:3000"

# 초기 데이터 생성 (첫 요청 시)
_initialized = False


def _ensure_video_service_user_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("users"): # type: ignore
        return

    with engine.begin() as conn:
        conn_inspector = inspect(conn)
        existing_columns = {
            column["name"]
            for column in conn_inspector.get_columns("users")
        }
        if "credit_balance" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN credit_balance INTEGER"
            ))
        conn.execute(text(
            "UPDATE users SET credit_balance=10 WHERE credit_balance IS NULL"
        ))


def ensure_marketplace_runtime_schema() -> None:
    init_db()
    ensure_ad_video_orders_schema()
    _ensure_video_service_user_schema()
    db = SessionLocal()
    try:
        subscription_service.ensure_runtime_bootstrap(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class CustomerOrchestrateRequest(BaseModel):
    task: str
    mode: str = "auto"
    project_name: Optional[str] = None
    output_dir: Optional[str] = None
    allow_new_output_dir: bool = False
    refinement_request: Optional[str] = None
    max_improvement_cycles: int = 1
    stage_run_id: Optional[str] = None
    stage_id: Optional[str] = None
    manual_correction: Optional[str] = None


class CustomerOrchestrateStageUpdateRequest(BaseModel):
    run_id: str
    stage_id: str
    status: str
    note: str = ""
    manual_correction: str = ""
    substep_checks: Optional[Dict[str, bool]] = None
    revision_note: str = ""


class CustomerOrchestratorChatRequest(BaseModel):
    message: str
    task: str = ""
    conversation: List[Dict[str, Any]] = []
    run_id: Optional[str] = None
    stage_id: Optional[str] = None
    project_name: Optional[str] = None
    output_dir: Optional[str] = None
    project_memory: Dict[str, Any] = {}
    context_tags: List[str] = []
    conversation_mode: str = "auto"
    companion_mode: str = "hybrid"
    response_style: str = "balanced"
    tone_preset: str = "auto"
    max_tokens: int = 768


class CustomerOrchestrateAcceptedResponse(BaseModel):
    accepted: bool = True
    run_id: Optional[str] = None
    stage_run: Optional[Dict[str, Any]] = None
    status: str = "accepted"
    message: str = "고객 오케스트레이터 요청을 수락했습니다. 이어지는 stream 호출에서 실제 실행 결과를 반환합니다."


def _build_customer_stage_chat_context(stage_run: Optional[Dict[str, Any]], request: CustomerOrchestratorChatRequest) -> OrchestratorStageChatContext:
    active_stage: Dict[str, Any] = {}
    if isinstance(stage_run, dict):
        active_stage = next((stage for stage in (stage_run.get("stages") or []) if stage.get("id") == stage_run.get("current_stage_id")), {}) or {}
    return OrchestratorStageChatContext(
        run_id=str((stage_run or {}).get("run_id") or request.run_id or "") or None,
        stage_id=str((active_stage or {}).get("id") or request.stage_id or "") or None,
        stage_label=str((active_stage or {}).get("label") or "") or None,
        stage_title=str((active_stage or {}).get("title") or "") or None,
        stage_status=str((active_stage or {}).get("status") or (stage_run or {}).get("status") or "running") or None,
        scope=str((stage_run or {}).get("scope") or "marketplace") or None,
        project_name=str((stage_run or {}).get("project_name") or request.project_name or "") or None,
        pending_revision_note=str(request.message or "").strip() or None,
        last_command=(str(request.message or "").strip().split()[0] if str(request.message or "").strip().startswith("/") else None),
    )


def _build_customer_orchestrate_sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps({'event': event, 'payload': payload}, ensure_ascii=False)}\n\n"


def _get_customer_orchestrate_run_lock(run_id: str) -> threading.Lock:
    with _customer_orchestrate_run_locks_guard:
        lock = _customer_orchestrate_run_locks.get(run_id)
        if lock is None:
            lock = threading.Lock()
            _customer_orchestrate_run_locks[run_id] = lock
        return lock


def _get_customer_stage_execution_metadata(stage_run_payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(stage_run_payload.get("metadata") or {})
    return dict(metadata.get("orchestration_execution") or {})


def _update_customer_stage_execution_metadata(run_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    payload = load_stage_run(run_id)
    if not payload:
        return None
    metadata = dict(payload.get("metadata") or {})
    execution_metadata = dict(metadata.get("orchestration_execution") or {})
    execution_metadata.update(fields)
    metadata["orchestration_execution"] = execution_metadata
    payload["metadata"] = metadata
    return save_stage_run(payload)


def _guard_customer_orchestrate_execution(stage_run_payload: Dict[str, Any]) -> None:
    execution_metadata = _get_customer_stage_execution_metadata(stage_run_payload)
    execution_status = str(execution_metadata.get("status") or "").strip().lower()
    if execution_status == "running":
        raise HTTPException(status_code=409, detail="같은 stage run 생성이 이미 실행 중입니다.")
    if execution_status == "completed":
        raise HTTPException(status_code=409, detail="이미 생성이 끝난 stage run입니다. 새 stage run으로 다시 시작하세요.")


def _ensure_customer_stage_run_payload(
    request: CustomerOrchestrateRequest,
    current_user: models.User,
) -> Dict[str, Any]:
    stage_run_payload = _resolve_stage_run_for_request(request, current_user)
    if not stage_run_payload:
        raise HTTPException(status_code=404, detail="고객 stage run을 찾을 수 없습니다.")
    return stage_run_payload


async def _run_customer_orchestration_request(orchestration_request):
    from backend.llm.orchestrator import execute_orchestration as execute_orchestration_handler

    return await execute_orchestration_handler(orchestration_request)


def _build_customer_orchestrate_result_payload(
    *,
    response: Any,
    request: CustomerOrchestrateRequest,
    current_user: models.User,
    stage_run_payload: Dict[str, Any],
) -> Dict[str, Any]:
    result_payload = _normalize_customer_orchestrate_result_payload(response, request.task)
    synced_stage_run = _sync_stage_run_after_result(
        stage_run_id=str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
        stage_id=str(request.stage_id or stage_run_payload.get("current_stage_id") or "ARCH-001").strip() or None,
        result_payload=result_payload,
    )
    if synced_stage_run:
        result_payload["stage_run"] = synced_stage_run
    return {
        "requested_by": {
            "id": getattr(current_user, "id", None),
            "email": getattr(current_user, "email", None),
        },
        "result": result_payload,
    }


def _build_customer_orchestrate_error_payload(
    *,
    error_message: str,
    request: CustomerOrchestrateRequest,
    stage_run_payload: Dict[str, Any],
) -> Dict[str, Any]:
    stage_run_error_payload = {
        "completion_summary": "고객 오케스트레이터 실행 실패",
        "failure_summary": error_message,
        "apply_error": error_message,
        "completion_gate_error": error_message,
        "completion_judge": {
            "product_ready": False,
            "failed_reasons": [error_message],
        },
    }
    synced_stage_run = _sync_stage_run_after_result(
        stage_run_id=str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
        stage_id=str(request.stage_id or stage_run_payload.get("current_stage_id") or "ARCH-001").strip() or None,
        result_payload=stage_run_error_payload,
        error_message=error_message,
    )
    payload: Dict[str, Any] = {"message": error_message}
    if synced_stage_run:
        payload["stage_run"] = synced_stage_run
    return payload


_CUSTOMER_ORCHESTRATE_TRACKING_KEY_MAP = {
    "현재 아키텍처 단계 ID": "architecture_id",
    "active_flow_id": "flow_id",
    "active_step_id": "step_id",
    "active_action": "action",
    "next_architecture_id": "next_architecture_id",
    "next_flow_step_id": "next_step_id",
    "next_flow_action": "next_action",
}


def _extract_customer_orchestrate_tracking_context(task: str) -> Dict[str, Optional[str]]:
    tracking: Dict[str, Optional[str]] = {
        "architecture_id": None,
        "flow_id": None,
        "step_id": None,
        "action": None,
        "next_architecture_id": None,
        "next_step_id": None,
        "next_action": None,
    }
    for raw_line in str(task or "").splitlines():
        line = raw_line.strip()
        match = re.match(r"^-\s*([^:]+):\s*(.+)$", line)
        if not match:
            continue
        raw_key = match.group(1).strip()
        raw_value = match.group(2).strip()
        mapped_key = _CUSTOMER_ORCHESTRATE_TRACKING_KEY_MAP.get(raw_key)
        if not mapped_key:
            continue
        if raw_value in {"-", "END", ""}:
            tracking[mapped_key] = raw_value
        else:
            tracking[mapped_key] = raw_value
    return tracking


def _normalize_customer_orchestrate_result_payload(result: Any, task: str) -> Dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
    elif isinstance(result, dict):
        payload = dict(result)
    else:
        payload = {"result": result}

    tracking = _extract_customer_orchestrate_tracking_context(task)
    payload.update({key: value for key, value in tracking.items() if value})
    payload["marketplace_delivery_gate"] = {
        "product_ready": bool((payload.get("completion_judge") or {}).get("product_ready")),
        "packaging_ready": bool((payload.get("packaging_audit") or {}).get("packaging_ready")),
        "required_tests": list((payload.get("integration_test_plan") or {}).get("required_tests") or []),
        "marketplace_quality_aligned": bool(payload.get("completion_gate_ok")),
        "output_archive_path": payload.get("output_archive_path"),
        "shipping_readme_path": (payload.get("packaging_audit") or {}).get("shipping_readme_path"),
        "operations_guide_path": (payload.get("packaging_audit") or {}).get("operations_guide_path"),
        "integration_test_engine_ok": bool(((payload.get("completion_judge") or {}).get("integration_test_engine") or {}).get("ok")),
        "improvement_loop_enabled": bool((payload.get("completion_judge") or {}).get("improvement_loop_enabled")),
        "improvement_loop_strategy": list((payload.get("completion_judge") or {}).get("improvement_loop_strategy") or []),
        "improvement_loop": payload.get("improvement_loop") or {},
        "framework_e2e_validation": payload.get("framework_e2e_validation") or {},
        "external_integration_validation": payload.get("external_integration_validation") or {},
    }
    payload.setdefault("orchestration_stage_definitions", ORCHESTRATION_STAGE_DEFINITIONS)
    return payload


def _persist_customer_orchestrator_completion(
    db: Session,
    *,
    current_user: models.User,
    request: CustomerOrchestrateRequest,
    result_payload: Dict[str, Any],
) -> None:
    completion = models.CustomerOrchestratorCompletion(
        user_id=current_user.id,
        trace_id=str(result_payload.get("trace_id") or "") or None,
        flow_id=str(result_payload.get("flow_id") or "") or None,
        step_id=str(result_payload.get("step_id") or "") or None,
        action=str(result_payload.get("action") or "") or None,
        project_name=((request.project_name or "customer-product").strip() or "customer-product"),
        mode=str(request.mode or "auto").strip() or "auto",
        attempts=1,
        output_dir=str(result_payload.get("output_dir") or "") or None,
        postcheck_ok=result_payload.get("postcheck_ok"),
        gate_passed=bool((result_payload.get("completion_judge") or {}).get("product_ready")),
        override_used=False,
    )
    db.add(completion)
    _write_feature_execution_log(
        db,
        user_id=current_user.id, # type: ignore
        entity_type="customer_orchestrator_completion",
        entity_id=str(completion.project_name),
        flow_id=str(result_payload.get("flow_id") or "FLOW-001"),
        step_id=str(result_payload.get("step_id") or "FLOW-001-4"),
        action=str(result_payload.get("action") or "SAVE_COMPLETION"),
        status="saved",
        message="고객 오케스트레이터 completion 자동 저장",
        payload={
            "project_name": completion.project_name,
            "mode": completion.mode,
            "output_dir": completion.output_dir,
            "postcheck_ok": completion.postcheck_ok,
            "gate_passed": completion.gate_passed,
            "completion_gate_ok": result_payload.get("completion_gate_ok"),
            "failed_reasons": list((result_payload.get("completion_judge") or {}).get("failed_reasons") or []),
        },
    )


def _resolve_stage_run_for_request(
    request: CustomerOrchestrateRequest,
    current_user: models.User,
) -> Optional[Dict[str, Any]]:
    if request.stage_run_id:
        return load_stage_run(request.stage_run_id)
    project_name = (request.project_name or "customer-product").strip() or "customer-product"
    return initialize_stage_run(
        scope="marketplace",
        project_name=project_name,
        mode=request.mode,
        requested_by={
            "id": current_user.id,
            "email": getattr(current_user, "email", ""),
        },
        metadata={
            "task": request.task,
        },
    )


def _merge_stage_tracking_into_task(task: str, stage_id: str, manual_correction: Optional[str] = None) -> str:
    tracking_payload = build_stage_tracking_payload(stage_id)
    if not tracking_payload:
        return task
    lines = [str(task or "").strip(), "", "[9단계 Stage Tracking]"]
    for key, value in tracking_payload.items():
        if key == "architecture_id":
            lines.append(f"- 현재 아키텍처 단계 ID: {value}")
        elif key == "flow_id":
            lines.append(f"- active_flow_id: {value}")
        elif key == "step_id":
            lines.append(f"- active_step_id: {value}")
        elif key == "action":
            lines.append(f"- active_action: {value}")
        elif key == "next_architecture_id":
            lines.append(f"- next_architecture_id: {value}")
        elif key == "next_step_id":
            lines.append(f"- next_flow_step_id: {value}")
        elif key == "next_action":
            lines.append(f"- next_flow_action: {value}")
    if str(manual_correction or "").strip():
        lines.extend(["", "[수동 보정 메모]", str(manual_correction or "").strip()])
    return "\n".join(lines).strip()


def _sync_stage_run_after_result(
    *,
    stage_run_id: Optional[str],
    stage_id: Optional[str],
    result_payload: Dict[str, Any],
    error_message: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not stage_run_id or not stage_id:
        return None
    normalized_stage_id = str(stage_id or "").strip().upper()
    if not normalized_stage_id:
        return None

    completion_judge = result_payload.get("completion_judge") or {}
    product_ready = bool(completion_judge.get("product_ready"))
    apply_error = str(result_payload.get("apply_error") or "").strip()
    postcheck_error = str(result_payload.get("postcheck_error") or "").strip()
    completion_gate_error = str(result_payload.get("completion_gate_error") or "").strip()
    failure_summary = str(result_payload.get("failure_summary") or "").strip()
    combined_error = error_message or apply_error or postcheck_error or completion_gate_error or failure_summary

    scaffold_only = bool(completion_judge.get("scaffold_only"))
    next_status = "passed" if product_ready and not combined_error and not scaffold_only else "manual_correction"
    note_parts = [
        str(result_payload.get("completion_summary") or "").strip(),
        combined_error,
        "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]),
    ]
    note = "\n".join([part for part in note_parts if part])

    synced = update_stage_run(
        run_id=stage_run_id,
        stage_id=normalized_stage_id,
        status=next_status,
        note=note,
        manual_correction=combined_error if next_status != "passed" else "",
    )
    if next_status == "passed":
        # Customer stream execution is a single-shot run, so close the stage run
        # as completed instead of leaving it on the next ARCH-* step.
        synced["status"] = "completed"
        synced["final_completed"] = True
        synced["current_stage_id"] = normalized_stage_id
        for stage in list(synced.get("stages") or []):
            if str(stage.get("id") or "").upper() == normalized_stage_id:
                continue
            if str(stage.get("status") or "").lower() == "running":
                stage["status"] = "pending"
                stage["check_label"] = "대기"
        synced = save_stage_run(synced)
    return synced


def _build_customer_orchestrate_log_event(
    message: str,
    level: str,
    tracking: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "event": "log",
        "level": level,
        "message": message,
    }
    if tracking:
        if tracking.get("flow_id"):
            event["flow_id"] = tracking["flow_id"]
        if tracking.get("step_id"):
            event["step_id"] = tracking["step_id"]
        if tracking.get("action"):
            event["action"] = tracking["action"]
    return event


class CustomerPublishRequest(BaseModel):
    output_dir: str
    title: str
    description: str
    price: float = 99000
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    demo_url: Optional[str] = None
    github_url: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomerGeneratedProgramSummary(BaseModel):
    output_dir: Optional[str] = None
    output_archive_path: Optional[str] = None
    delivery_gate_blocked: bool = False
    delivery_gate_message: Optional[str] = None
    publish_ready: bool = False
    publish_targets: List[str] = []
    shipping_zip_ok: bool = False
    validation_profile: Optional[str] = None
    required_tests: List[str] = []
    priority_average_score: int = 0
    priority_peak_score: int = 0
    priority_latest_score: int = 0
    priority_previous_score: Optional[int] = None
    priority_momentum: int = 0
    priority_cumulative_score: int = 0
    approval_history_count: int = 0
    stage_run_status: Optional[str] = None
    hard_gate_failed_stages: List[str] = []


def _customer_follow_up_history_path() -> Path:
    runtime_root = Path(os.getenv("ADMIN_RUNTIME_ROOT", "")).expanduser().resolve() if os.getenv("ADMIN_RUNTIME_ROOT", "").strip() else (Path(tempfile.gettempdir()) / "codeai_admin_runtime").resolve()
    return runtime_root / "capability_cache" / "customer_follow_up_history.json"


def _read_customer_follow_up_history() -> Dict[str, List[Dict[str, Any]]]:
    path = _customer_follow_up_history_path()
    try:
        if not path.exists() or not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_customer_follow_up_history(payload: Dict[str, List[Dict[str, Any]]]) -> None:
    path = _customer_follow_up_history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _append_customer_follow_up_history(*, history_id: str, score: int, limit: int = 24) -> Dict[str, Any]:
    payload = _read_customer_follow_up_history()
    entries = list(payload.get(history_id) or [])
    normalized_score = max(0, min(100, int(score)))
    if not entries or int(entries[-1].get("score") or -1) != normalized_score:
        entries.append({
            "recorded_at": datetime.utcnow().isoformat() + "Z",
            "score": normalized_score,
        })
    entries = entries[-max(2, limit):]
    payload[history_id] = entries
    _write_customer_follow_up_history(payload)
    scores = [max(0, min(100, int(item.get("score") or 0))) for item in entries]
    average_score = round(sum(scores) / len(scores)) if scores else normalized_score
    peak_score = max(scores) if scores else normalized_score
    previous_score = scores[-2] if len(scores) > 1 else None
    momentum = normalized_score - previous_score if previous_score is not None else 0
    cumulative_score = max(0, min(100, round((normalized_score * 0.45) + (average_score * 0.3) + (peak_score * 0.15) + (max(0, momentum) * 0.1))))
    return {
        "average_score": average_score,
        "peak_score": peak_score,
        "latest_score": normalized_score,
        "previous_score": previous_score,
        "momentum": momentum,
        "cumulative_score": cumulative_score,
    }


def _customer_orchestrate_connection_id(trace_id: Optional[str], flow_id: Optional[str], step_id: Optional[str], action: Optional[str]) -> Optional[str]:
    if flow_id and step_id and action:
        return f"{flow_id}:{step_id}:{action}"
    return trace_id


router.include_router(build_customer_orchestrate_router(sys.modules[__name__]))


def _build_customer_orchestrate_request(
    request: CustomerOrchestrateRequest,
    user_id: int,
):
    from backend.llm.orchestrator import OrchestrationRequest

    safe_mode = request.mode if request.mode in {"auto", "code", "design", "plan", "review", "full", "program_5step"} else "auto"
    _schedule_marketplace_storage_cleanup()
    user_dir_path = _resolve_customer_orchestrator_run_root(user_id)
    user_dir = str(user_dir_path)
    requested_output_dir = str(request.output_dir or "").strip() or None
    validated_output_dir: Optional[str] = None
    if requested_output_dir:
        if bool(request.allow_new_output_dir):
            requested_path = Path(requested_output_dir)
            requested_path.mkdir(parents=True, exist_ok=True)
            validated_output_dir = str(requested_path.resolve())
        else:
            # 고객 재실행은 기존 생성 결과 폴더 내부에서만 이어서 수정되도록 경로를 강제 검증한다.
            validated_output_dir = str(
                _validate_customer_generated_output_dir(
                    Path(requested_output_dir),
                    user_id,
                )
            )
    else:
        # 고객 신규 실행도 시작 시점에 단일 작업 폴더를 선할당해
        # 내부 강제 재시도가 retry_* 폴더를 연쇄 생성하지 않도록 고정한다.
        validated_output_dir = str(
            _allocate_customer_orchestrator_output_dir(
                user_dir_path,
                request.project_name,
            )
        )

    return OrchestrationRequest(
        task=_merge_stage_tracking_into_task(
            (request.task or "").strip(),
            request.stage_id or "ARCH-001",
            request.manual_correction,
        ),
        mode=safe_mode,
        project_name=request.project_name,
        output_base_dir=user_dir,
        output_dir=validated_output_dir,
        continue_in_place=bool(requested_output_dir),
        auto_apply=True,
        run_postcheck=True,
        retry_on_postcheck_fail=True,
        forensic_on_fail=True,
        refinement_request=request.refinement_request,
        max_improvement_cycles=request.max_improvement_cycles,
    )


def _slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣_-]", "-", (value or "project").strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "project"


def _has_mojibake(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = str(value)
    if re.search(r"\?{3,}", text):
        return True
    if "�" in text:
        return True
    if re.search(r"[\u0080-\u009F]", text):
        return True
    if re.search(r"(?:Ã.|Â.|ì.|ë.|ê.|í.){2,}", text):
        return True
    return False


def _validate_text_fields(fields: List[tuple[str, Optional[str]]]):
    broken = [name for name, value in fields if _has_mojibake(value)]
    if broken:
        raise HTTPException(
            status_code=400,
            detail=f"문자 인코딩이 깨진 텍스트가 감지되었습니다: {', '.join(broken)}",
        )


def _resolve_marketplace_upload_root() -> Path:
    configured_root = (os.getenv("MARKETPLACE_UPLOAD_ROOT", "") or "").strip()
    if configured_root:
        if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", configured_root):
            mounted_upload_root = Path("/app/uploads")
            if mounted_upload_root.exists():
                return mounted_upload_root.resolve()
        return Path(configured_root).expanduser().resolve()
    workspace_root = Path(__file__).resolve().parents[2]
    return (workspace_root / "uploads").resolve()


def _resolve_marketplace_temp_root() -> Path:
    temp_root = (_resolve_marketplace_upload_root() / "tmp").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def _resolve_customer_orchestrator_run_root(user_id: int) -> Path:
    run_root = (
        _resolve_marketplace_upload_root()
        / "projects"
        / f"customer_{user_id}"
        / "runs"
    ).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    return run_root


def _allocate_customer_orchestrator_output_dir(
    run_root: Path,
    project_name: Optional[str],
) -> Path:
    slug = _slugify_text(project_name or "project")
    candidate = (run_root / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}").resolve()
    if not str(candidate).startswith(str(run_root)):
        raise HTTPException(status_code=500, detail="출력 경로 계산 실패")
    suffix = 1
    while candidate.exists():
        candidate = (run_root / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{suffix:02d}").resolve()
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _validate_customer_generated_output_dir(
    output_dir: Path,
    current_user_id: int,
) -> Path:
    base_allowed = _resolve_customer_orchestrator_run_root(current_user_id)
    resolved_output = output_dir.resolve()

    if not str(resolved_output).startswith(str(base_allowed)):
        raise HTTPException(
            status_code=403,
            detail="허용되지 않은 출력 경로입니다.",
        )
    if resolved_output == base_allowed:
        raise HTTPException(
            status_code=400,
            detail="실행 루트 전체가 아닌 개별 결과 폴더를 선택해야 합니다.",
        )
    if resolved_output.parent != base_allowed:
        raise HTTPException(
            status_code=400,
            detail="개별 실행 결과 폴더만 게시할 수 있습니다.",
        )
    if str(resolved_output.name).startswith("_archive"):
        raise HTTPException(
            status_code=400,
            detail="보관 폴더는 게시 대상으로 사용할 수 없습니다.",
        )
    return resolved_output


def _ensure_customer_publish_deploy_handoff(
    output_dir: Path,
    request: "CustomerPublishRequest",
    current_user_id: int,
) -> None:
    handoff_path = (output_dir / "deploy_handoff.json").resolve()
    if handoff_path.parent != output_dir.resolve():
        raise HTTPException(status_code=500, detail="배포 인계 파일 경로 계산 실패")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": current_user_id,
        "output_dir": str(output_dir),
        "publish": {
            "title": request.title.strip(),
            "description": request.description.strip(),
            "price": float(request.price),
            "category_id": request.category_id,
            "image_url": request.image_url,
            "demo_url": request.demo_url,
            "github_url": request.github_url,
            "tags": [tag.strip() for tag in (request.tags or []) if str(tag).strip()],
        },
    }
    handoff_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_file_from_storage(file_key: str) -> Optional[bytes]:
    if not file_key:
        return None

    if file_key.startswith("local:"):
        rel = file_key[len("local:"):].lstrip("/").replace("\\", "/")
        local_base = (_resolve_marketplace_upload_root() / "marketplace_local").resolve()
        local_path = (local_base / rel).resolve()
        if not str(local_path).startswith(str(local_base)):
            return None
        if not local_path.exists() or not local_path.is_file():
            return None
        return local_path.read_bytes()

    return minio_service.download_file(file_key)


def _store_bytes_with_fallback(file_bytes: bytes, object_key: str, content_type: str) -> str:
    uploaded = minio_service.upload_file(file_bytes, object_key, content_type)
    if uploaded:
        return object_key

    local_base = (_resolve_marketplace_upload_root() / "marketplace_local").resolve()
    local_target = (local_base / object_key).resolve()
    if not str(local_target).startswith(str(local_base)):
        raise HTTPException(status_code=500, detail="로컬 저장 경로 계산 실패")
    local_target.parent.mkdir(parents=True, exist_ok=True)
    local_target.write_bytes(file_bytes)
    return f"local:{object_key}"


def _process_ad_order_job(order_id: int) -> None:
    process_ad_order_job(sys.modules[__name__], order_id)


def _reset_ad_order_for_retry(
    db: Session,
    order: models.AdVideoOrder,
    retry_reason: Optional[str] = None,
    preserve_quality_feedback: bool = False,
) -> models.AdVideoOrder:
    return reset_ad_order_for_retry(
        sys.modules[__name__],
        db,
        order,
        retry_reason=retry_reason,
        preserve_quality_feedback=preserve_quality_feedback,
    )


def _ad_order_worker_loop() -> None:
    while True:
        queue_item: Optional[Dict[str, Any]] = None
        _mark_ad_worker_heartbeat()
        try:
            redis_client = _require_video_queue_redis()
            result = redis_client.brpop(VIDEO_RENDER_QUEUE_NAME, timeout=5) # type: ignore
            if result:
                _, raw_item = result # type: ignore
                queue_item = json.loads(raw_item)
        except HTTPException:
            time.sleep(2)
            continue
        except (RedisError, json.JSONDecodeError):
            time.sleep(2)
            continue

        if queue_item is None:
            continue

        order_id = int(queue_item.get("order_id") or 0)
        _mark_ad_worker_heartbeat(order_id)
        try:
            _maybe_run_marketplace_storage_cleanup()
            _process_ad_order_job(order_id)
        finally:
            discard_enqueued_ad_order(order_id)


def run_ad_order_worker() -> None:
    db_ok, db_message = check_database_availability()
    if not db_ok:
        raise RuntimeError(f"ad-order worker database unavailable: {db_message}")
    _mark_ad_worker_heartbeat()
    logger.info(
        "[marketplace] video render worker consuming Redis queue '%s'",
        VIDEO_RENDER_QUEUE_NAME,
    )
    _ad_order_worker_loop()


def _ensure_ad_order_worker_started() -> None:
    ensure_ad_order_runtime_ready()


def _build_ad_package_zip(order: models.AdVideoOrder) -> bytes:
    return build_ad_package_zip(sys.modules[__name__], order)
