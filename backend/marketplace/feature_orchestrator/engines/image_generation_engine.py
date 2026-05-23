"""Image engine with local preview/final artifact packaging."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, Optional
from uuid import uuid4

from ..contracts import extract_prompt_keywords, summarize_prompt


_TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5v2h8AAAAASUVORK5CYII="
)


def _build_output_root() -> Path:
    root = Path(gettempdir()) / "codeai-marketplace-image"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_delivery_asset(path: Path, format_name: str, mime_type: str) -> Dict[str, Any]:
    exists = path.exists()
    return {
        "format": format_name,
        "path": str(path),
        "path_hint": str(path),
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size if exists else 0,
        "exists": exists,
        "generated_at": _utc_now(),
    }


def _write_png(path: Path) -> None:
    path.write_bytes(base64.b64decode(_TINY_PNG_BASE64))


def build_image_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    project_name = str(payload.get("project_name") or "marketplace-image-run")
    template_id = str(payload.get("template_id") or "ad-photo-template")
    photo_reference = str(payload.get("photo_reference") or "").strip() or "none"
    keywords = extract_prompt_keywords(prompt, limit=6)

    return {
        "artifact_id": f"ai-image-preview-{uuid4().hex[:8]}",
        "feature_id": "ai-image",
        "phase": "preview",
        "state": "completed",
        "status": "ready",
        "title": project_name,
        "content_type": "image/png",
        "image_data_url": f"data:image/png;base64,{_TINY_PNG_BASE64}",
        "prompt_summary": summarize_prompt(prompt),
        "keywords": keywords,
        "composition": {
            "template_id": template_id,
            "photo_reference": photo_reference,
            "warnings": [],
        },
        "notes": [
            "preview 단계에서는 저해상도 시안 결과를 먼저 제공합니다.",
        ],
        "generated_at": _utc_now(),
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def render_image_final(payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
    seed = uuid4().hex[:8]
    output_root = _build_output_root() / seed
    output_root.mkdir(parents=True, exist_ok=True)
    png_path = output_root / f"{seed}.png"
    meta_path = output_root / f"{seed}.txt"
    _write_png(png_path)
    meta_path.write_text(
        "\n".join([
            f"prompt_summary={preview_artifact.get('prompt_summary') or ''}",
            f"keywords={','.join(list(preview_artifact.get('keywords') or []))}",
        ]),
        encoding="utf-8",
    )
    delivery_assets = [
        _build_delivery_asset(png_path, "png", "image/png"),
        _build_delivery_asset(meta_path, "txt", "text/plain"),
    ]

    return {
        "artifact_id": f"ai-image-final-{seed}",
        "feature_id": "ai-image",
        "phase": "final",
        "state": "completed",
        "status": "generated",
        "title": "최종 이미지 패키지",
        "content_type": "image/png",
        "image_data_url": f"data:image/png;base64,{_TINY_PNG_BASE64}",
        "prompt_summary": str(preview_artifact.get("prompt_summary") or ""),
        "keywords": list(preview_artifact.get("keywords") or []),
        "composition": dict(preview_artifact.get("composition") or {}),
        "delivery_assets": delivery_assets,
        "generated_at": _utc_now(),
        "notes": [f"output_root={output_root}", "png/txt 산출물을 생성했습니다."],
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def review_image_quality(
    payload: Dict[str, Any],
    preview_artifact: Dict[str, Any],
    final_artifact: Dict[str, Any],
) -> Dict[str, Any]:
    del payload
    formats = {
        str(item.get("format") or "").lower()
        for item in list(final_artifact.get("delivery_assets") or [])
        if item.get("exists") and Path(str(item.get("path") or "")).exists()
    }
    passed = {"png", "txt"}.issubset(formats)
    return {
        "passed": passed,
        "status": "approved" if passed else "needs-review",
        "feature_id": "ai-image",
        "fallback_state": "completed" if passed else "completed_preview_only",
        "score": 86 if passed else 58,
        "review_summary": "이미지 preview/final delivery asset 계약을 검증했습니다.",
        "failure_tags": [] if passed else ["image-delivery-assets-missing"],
        "checks": {
            "png_exists": "png" in formats,
            "txt_exists": "txt" in formats,
        },
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "final_artifact_id": final_artifact.get("artifact_id"),
    }


class ImageGenerationEngine:
    """Legacy engine class wrapper."""

    ENGINE_ID = "hybrid-image"

    async def run_preview(
        self,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "ad-banner",
        reference_image_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "prompt": prompt,
            "project_name": project_name or "marketplace-image-run",
            "template_id": template,
            "photo_reference": reference_image_path,
            "bridge_payload": dict(options or {}),
        }
        return build_image_preview(payload)

    async def run_final(
        self,
        preview_artifact_id: str,
        *,
        preview_artifact: Dict[str, Any] | None = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        del preview_artifact_id
        return render_image_final({"bridge_payload": dict(options or {})}, preview_artifact or {})
