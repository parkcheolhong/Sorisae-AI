"""OCR 업로드 이미지 정규화 — 용량·해상도 상한 내로 리사이즈/재압축."""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

_DEFAULT_MAX_BYTES = 6 * 1024 * 1024
_DEFAULT_MAX_SIDE = 2560
_JPEG_QUALITY = 85


def normalize_image_bytes_for_ocr(
    image_bytes: bytes,
    *,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    max_side: int = _DEFAULT_MAX_SIDE,
) -> bytes:
    if not image_bytes:
        return image_bytes
    try:
        from PIL import Image
    except Exception:
        return image_bytes

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.load()
            width, height = im.size
            needs_resize = max(width, height) > max_side
            needs_compress = len(image_bytes) > max_bytes
            if not needs_resize and not needs_compress:
                return image_bytes

            if needs_resize:
                scale = max_side / float(max(width, height))
                new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                im = im.resize(new_size, Image.Resampling.LANCZOS)

            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")

            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
            out = buf.getvalue()
            if out and len(out) < len(image_bytes):
                logger.info(
                    "[ocr-image] normalized %dx%d %dKB -> %dKB",
                    width,
                    height,
                    len(image_bytes) // 1024,
                    len(out) // 1024,
                )
                return out
            return image_bytes if not needs_resize else out
    except Exception as exc:
        logger.warning("[ocr-image] normalize skipped: %s", exc)
        return image_bytes
