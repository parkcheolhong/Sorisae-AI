from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .service import (
    build_image_translation_response,
    extract_text_from_image,
    validate_image_upload,
)

router = APIRouter(prefix="/api/mobile", tags=["mobile-image-translation"])


@router.post("/image-translation")
async def image_translation(
    source_language: str = Form(default="ko"),
    target_language: str = Form(default="en"),
    region_hint: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> dict:
    file_name = str(file.filename or "upload.bin")
    content_type = str(file.content_type or "application/octet-stream")
    try:
        validate_image_upload(file_name, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 이미지 파일입니다")

    try:
        return build_image_translation_response(
            file_name=file_name,
            content_type=content_type,
            image_bytes=image_bytes,
            source_language=source_language,
            target_language=target_language,
            region_hint=(str(region_hint).strip() or None) if region_hint else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"이미지 번역 실패: {exc}") from exc
