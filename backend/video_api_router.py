from datetime import datetime
from io import BytesIO
import json
from typing import Any, List, Literal, Optional
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.marketplace import models as marketplace_models
from backend.marketplace.router import (
    _enqueue_ad_order,
    _read_file_from_storage,
    ensure_ad_order_runtime_ready,
)


router = APIRouter(prefix="/api/video", tags=["video-api"])


class VideoGenerateRequest(BaseModel):
    user_id: Optional[str] = None
    images: List[str] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    video_length: Literal[15, 30, 60]
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    delivery_profile: Literal["general", "youtube_web"] = "general"
    engine_type: Literal["external_api", "internal_ffmpeg", "dedicated_engine"] = "dedicated_engine"
    music_template: Optional[str] = None


class VideoGenerateResponse(BaseModel):
    job_id: str
    status: str


class VideoStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int


def _order_int(order: Any, name: str, default: int = 0) -> int:
    value = getattr(order, name, default)
    if value is None:
        return default
    return int(value)


def _order_str(order: Any, name: str, default: str = "") -> str:
    value = getattr(order, name, default)
    if value is None:
        return default
    return str(value)


def _target_cut_count(video_length: int) -> int:
    if video_length == 15:
        return 10
    if video_length == 30:
        return 18
    return 32


def _render_quality_for_delivery_profile(delivery_profile: str) -> str:
    profile = (delivery_profile or "general").strip().lower()
    if profile == "youtube_web":
        return "ultra"
    return "high"


def _find_video_order(
    db: Session,
    job_id: str,
) -> Optional[marketplace_models.AdVideoOrder]:
    value = (job_id or "").strip()
    if not value:
        return None

    order = (
        db.query(marketplace_models.AdVideoOrder)
        .filter(marketplace_models.AdVideoOrder.public_job_id == value)
        .first()
    )
    if order is not None:
        return order

    if value.isdigit():
        return (
            db.query(marketplace_models.AdVideoOrder)
            .filter(marketplace_models.AdVideoOrder.id == int(value))
            .first()
        )
    return None


def _primary_image(images: List[str]) -> str:
    for image in images:
        value = (image or "").strip()
        if value:
            return value
    raise HTTPException(status_code=400, detail="최소 1개의 이미지가 필요합니다.")


def _normalized_product_images(images: List[str]) -> List[str]:
    normalized = []
    for image in images:
        value = (image or "").strip()
        if value:
            normalized.append(value)
    return normalized[:3]


@router.post(
    "/generate",
    response_model=VideoGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_video(
    payload: VideoGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = (
        db.query(marketplace_models.User)
        .filter(marketplace_models.User.id == current_user.id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if int(getattr(user, "credit_balance", 0) or 0) <= 0:
        raise HTTPException(status_code=402, detail="credit이 부족합니다.")

    primary_image = _primary_image(payload.images)
    product_images = _normalized_product_images(payload.images)
    description = payload.description.strip()
    public_job_id = str(uuid4())

    order = marketplace_models.AdVideoOrder(
        public_job_id=public_job_id,
        user_id=current_user.id,
        title=payload.title.strip(),
        image_prompt=primary_image,
        portrait_image_prompt=None,
        product_image_prompts=None,
        background_prompt=description,
        caption_text=description,
        voice_gender="female",
        engine_type=payload.engine_type,
        duration_seconds=payload.video_length,
        visual_style=f"spec:{payload.aspect_ratio}:{payload.delivery_profile}",
        cut_count=_target_cut_count(payload.video_length),
        subtitle_speed=1.0,
        render_quality=_render_quality_for_delivery_profile(payload.delivery_profile),
        audio_volume=100,
        status=marketplace_models.AdVideoOrderStatus.QUEUED.value,
        progress_percent=0,
    )
    if len(product_images) >= 3:
        setattr(
            order,
            "product_image_prompts",
            json.dumps(product_images, ensure_ascii=False),
        )

    db.add(order)
    user.credit_balance = max(0, int(getattr(user, "credit_balance", 0) or 0) - 1)
    db.commit()
    db.refresh(order)

    ensure_ad_order_runtime_ready()
    _enqueue_ad_order(_order_int(order, "id"), public_job_id)

    return {
        "job_id": public_job_id,
        "status": "queued",
    }


@router.get("/status/{job_id}", response_model=VideoStatusResponse)
def get_video_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = _find_video_order(db, job_id)
    if not order:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인 작업만 조회할 수 있습니다.")

    return {
        "job_id": _order_str(order, "public_job_id") or str(_order_int(order, "id")),
        "status": _order_str(order, "status"),
        "progress": _order_int(order, "progress_percent"),
    }


@router.get("/download/{job_id}")
def download_video(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = _find_video_order(db, job_id)
    if not order:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="본인 작업만 다운로드할 수 있습니다.")
    if (
        _order_str(order, "status")
        != marketplace_models.AdVideoOrderStatus.COMPLETED.value
    ):
        raise HTTPException(status_code=400, detail="완료된 작업만 다운로드할 수 있습니다.")

    file_key = _order_str(order, "output_video_key") or _order_str(
        order,
        "output_file_key",
    )
    if not file_key:
        raise HTTPException(status_code=404, detail="다운로드 파일이 없습니다.")

    file_bytes = _read_file_from_storage(file_key)
    if file_bytes is None:
        raise HTTPException(status_code=404, detail="파일 내용을 찾을 수 없습니다.")

    current_download_count = _order_int(order, "download_count")
    setattr(order, "download_count", current_download_count + 1)
    db.commit()

    filename = _order_str(order, "output_video_filename") or (
        f"video_job_{_order_int(order, 'id')}.mp4"
    )
    encoded_name = quote(filename)
    return StreamingResponse(
        BytesIO(file_bytes),
        media_type="video/mp4",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{encoded_name}"
            ),
        },
    )
