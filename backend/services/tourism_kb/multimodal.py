"""관광 KB 멀티모달(CLIP) — 텍스트·이미지 정렬 임베딩(설계 §3 멀티모달).

목적: POI 이미지(Wikimedia 등, 저작권 게이트 통과분)를 CLIP-vision 으로 임베딩하고,
질의는 CLIP-text 로 임베딩해 **같은 512차원 공간**에서 교차검색(text→image, image→image).
기존 dense(다국어 e5)+sparse(BM25) hybrid 에 'clip' named vector 를 **추가**해 RRF 융합한다.

- 백엔드: fastembed(ONNX, torch 불필요) — CPU 에서 동작(GPU 없어도 가능).
  · 이미지:  Qdrant/clip-ViT-B-32-vision
  · 텍스트:  Qdrant/clip-ViT-B-32-text  (vision 과 동일 공간으로 정렬)
- 모든 의존성 지연 로딩 + 실패 시 graceful unavailable → 미설치/오프라인 환경 import 안전.
- 기본 비활성(`TOURISM_CLIP_ENABLED=0`). 이미지 백필 적재 후 운영에서 켠다.
"""

from __future__ import annotations

import io
import logging
import os
import threading
import urllib.request
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

TOURISM_CLIP_ENABLED = os.getenv("TOURISM_CLIP_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")
TOURISM_CLIP_TEXT_MODEL = os.getenv("TOURISM_CLIP_TEXT_MODEL", "Qdrant/clip-ViT-B-32-text")
TOURISM_CLIP_IMAGE_MODEL = os.getenv("TOURISM_CLIP_IMAGE_MODEL", "Qdrant/clip-ViT-B-32-vision")
TOURISM_CLIP_DIM = int(os.getenv("TOURISM_CLIP_DIM", "512"))

_UA = "MetaNova-TourismBot/1.0 (https://devanalysis114.com; contact: ops@devanalysis114.com)"
_IMG_TIMEOUT = 8.0
_MAX_IMG_BYTES = 8 * 1024 * 1024  # 8MB 가드


def _normalize(vec: List[float]) -> List[float]:
    norm = sum(x * x for x in vec) ** 0.5
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


class TourismClipEmbedder:
    """CLIP 텍스트/이미지 임베더(fastembed). 두 모델은 동일 정렬 공간(512d)을 공유한다.
    최초 사용 시 1회 로드(lazy). 로드 실패 시 unavailable → 상위에서 graceful 폴백."""

    _instance: Optional["TourismClipEmbedder"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._text_model = None
        self._image_model = None
        self._unavailable = False

    @classmethod
    def shared(cls) -> "TourismClipEmbedder":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_text(self):
        if self._text_model is not None or self._unavailable:
            return self._text_model
        try:
            from fastembed import TextEmbedding

            logger.info("[tourism_kb.clip] CLIP-text 로드: %s", TOURISM_CLIP_TEXT_MODEL)
            self._text_model = TextEmbedding(model_name=TOURISM_CLIP_TEXT_MODEL)
        except Exception as exc:
            logger.warning("[tourism_kb.clip] CLIP-text 로드 실패(멀티모달 비활성): %s", exc)
            self._unavailable = True
            self._text_model = None
        return self._text_model

    def _ensure_image(self):
        if self._image_model is not None or self._unavailable:
            return self._image_model
        try:
            from fastembed import ImageEmbedding

            logger.info("[tourism_kb.clip] CLIP-vision 로드: %s", TOURISM_CLIP_IMAGE_MODEL)
            self._image_model = ImageEmbedding(model_name=TOURISM_CLIP_IMAGE_MODEL)
        except Exception as exc:
            logger.warning("[tourism_kb.clip] CLIP-vision 로드 실패(멀티모달 비활성): %s", exc)
            self._unavailable = True
            self._image_model = None
        return self._image_model

    @property
    def available(self) -> bool:
        """텍스트 검색 경로 가용성(질의 임베딩). 이미지 적재는 embed_images 가용성 별도."""
        return self._ensure_text() is not None

    @property
    def dim(self) -> int:
        return TOURISM_CLIP_DIM

    # ── 텍스트(질의) ─────────────────────────────────────────────────────
    def embed_text(self, texts: List[str], *, batch_size: int = 32) -> List[List[float]]:
        model = self._ensure_text()
        if model is None or not texts:
            return []
        try:
            out = [list(map(float, v)) for v in model.embed(list(texts), batch_size=batch_size)]
            return [_normalize(v) for v in out]
        except Exception as exc:
            logger.warning("[tourism_kb.clip] text embed 실패: %s", exc)
            return []

    def embed_text_one(self, text: str) -> List[float]:
        out = self.embed_text([text])
        return out[0] if out else []

    # ── 이미지(적재) ─────────────────────────────────────────────────────
    @staticmethod
    def _fetch_image(url: str) -> Optional["Any"]:
        """이미지 URL → PIL.Image(RGB). 실패 시 None(fail-open)."""
        try:
            from PIL import Image
        except Exception as exc:
            logger.warning("[tourism_kb.clip] Pillow 미설치(이미지 임베딩 불가): %s", exc)
            return None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=_IMG_TIMEOUT) as resp:  # noqa: S310
                if getattr(resp, "status", 200) != 200:
                    return None
                raw = resp.read(_MAX_IMG_BYTES + 1)
            if len(raw) > _MAX_IMG_BYTES:
                logger.debug("[tourism_kb.clip] 이미지 과대(스킵): %s", url)
                return None
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as exc:
            logger.debug("[tourism_kb.clip] 이미지 취득 실패: %s (%s)", url, exc)
            return None

    def embed_images(self, images: List[Any], *, batch_size: int = 8) -> List[List[float]]:
        """images: PIL.Image 또는 로컬 경로 리스트 → 정규화 512d. 실패 시 []."""
        model = self._ensure_image()
        if model is None or not images:
            return []
        try:
            out = [list(map(float, v)) for v in model.embed(images, batch_size=batch_size)]
            return [_normalize(v) for v in out]
        except Exception as exc:
            logger.warning("[tourism_kb.clip] image embed 실패: %s", exc)
            return []

    def embed_image_url(self, url: str) -> List[float]:
        """이미지 URL 1건 → 정규화 512d(다운로드+임베딩). 실패 시 []."""
        if not url:
            return []
        img = self._fetch_image(url)
        if img is None:
            return []
        out = self.embed_images([img])
        return out[0] if out else []


def get_clip_embedder() -> TourismClipEmbedder:
    return TourismClipEmbedder.shared()
