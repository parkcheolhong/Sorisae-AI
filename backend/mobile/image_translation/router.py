from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.security_gates import require_public_image_quota

from .service import (
    build_image_translation_response,
    extract_text_from_image,
    validate_image_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile", tags=["mobile-image-translation"])

# [보안 보강] 업로드 용량 상한(기본 8MB). nginx 는 100m 까지 허용하므로, 무인증 OCR 경로가
# 거대한 파일을 통째로 메모리에 적재(연산/메모리 DoS)하지 못하도록 애플리케이션단에서 캡한다.
_MAX_IMAGE_BYTES = max(256 * 1024, int(os.getenv("IMAGE_TRANSLATION_MAX_BYTES", str(8 * 1024 * 1024))))
_READ_CHUNK = 1024 * 1024


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """청크 단위로 읽되 상한을 초과하면 즉시 413 으로 중단(전체 메모리 적재 방지)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"이미지 용량이 너무 큽니다(최대 {max_bytes // (1024 * 1024)}MB).",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/image-translation")
async def image_translation(
    request: Request,
    source_language: str = Form(default="ko"),
    target_language: str = Form(default="en"),
    region_hint: str | None = Form(default=None),
    high_density: str = Form(default="0"),
    file: UploadFile = File(...),
    # [보안 보강] 무인증 경로 + RapidOCR(CPU 무거움) → IP 단위 레이트리밋으로 연산 DoS 1차 차단.
    _image_quota: None = Depends(require_public_image_quota),
) -> dict:
    file_name = str(file.filename or "upload.bin")
    content_type = str(file.content_type or "application/octet-stream")
    try:
        validate_image_upload(file_name, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    image_bytes = await _read_capped(file, _MAX_IMAGE_BYTES)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 이미지 파일입니다")

    try:
        high_density_flag = str(high_density).strip().lower() in ("1", "true", "yes", "on")
        return build_image_translation_response(
            file_name=file_name,
            content_type=content_type,
            image_bytes=image_bytes,
            source_language=source_language,
            target_language=target_language,
            region_hint=(str(region_hint).strip() or None) if region_hint else None,
            high_density=high_density_flag,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # [보안 보강] 내부 예외 본문을 클라이언트에 노출하지 않는다(정보 누출 방지). 상세는 서버 로그로만.
        logger.exception("[image-translation] 처리 실패 file=%s type=%s", file_name, content_type)
        raise HTTPException(status_code=500, detail="이미지 번역 처리 중 오류가 발생했습니다.") from exc
