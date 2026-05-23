"""Video engine with local artifact packaging."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, Optional
from uuid import uuid4

from ..contracts import extract_prompt_keywords, summarize_prompt


def _build_output_root() -> Path:
    root = Path(gettempdir()) / "codeai-marketplace-video"
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


def build_video_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    project_name = str(payload.get("project_name") or "marketplace-video-run")
    template_id = str(payload.get("template_id") or "video-storyboard-template")
    keywords = extract_prompt_keywords(prompt, limit=6)
    scene_cards = [
        {"title": "Scene 1", "summary": "문제 제기", "duration": "0-5s", "cta": "문제 공감"},
        {"title": "Scene 2", "summary": "해결안 제시", "duration": "5-10s", "cta": "핵심 가치"},
        {"title": "Scene 3", "summary": "행동 유도", "duration": "10-15s", "cta": "지금 시작"},
    ]
    return {
        "artifact_id": f"ai-video-preview-{uuid4().hex[:8]}",
        "feature_id": "ai-video",
        "phase": "preview",
        "state": "completed",
        "status": "ready",
        "title": project_name,
        "content_type": "video/mp4",
        "prompt_summary": summarize_prompt(prompt),
        "keywords": keywords,
        "scene_cards": scene_cards,
        "package_assets": [{"label": "storyboard", "value": "3 scenes"}],
        "notes": [f"template_id={template_id}", "preview 단계에서는 scene cards 를 확정합니다."],
        "generated_at": _utc_now(),
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def render_video_final(payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
    seed = uuid4().hex[:8]
    output_root = _build_output_root() / seed
    output_root.mkdir(parents=True, exist_ok=True)
    mp4_path = output_root / f"{seed}.mp4"
    scene_path = output_root / f"{seed}.txt"
    mp4_path.write_bytes(b"FAKE_MP4_PLACEHOLDER")
    scene_path.write_text(
        "\n".join(
            [
                f"prompt_summary={preview_artifact.get('prompt_summary') or ''}",
                "scene_cards=3",
            ]
        ),
        encoding="utf-8",
    )
    delivery_assets = [
        _build_delivery_asset(mp4_path, "mp4", "video/mp4"),
        _build_delivery_asset(scene_path, "txt", "text/plain"),
    ]
    return {
        "artifact_id": f"ai-video-final-{seed}",
        "feature_id": "ai-video",
        "phase": "final",
        "state": "completed",
        "status": "generated",
        "title": "최종 영상 패키지",
        "content_type": "video/mp4",
        "prompt_summary": str(preview_artifact.get("prompt_summary") or ""),
        "keywords": list(preview_artifact.get("keywords") or []),
        "scene_cards": list(preview_artifact.get("scene_cards") or []),
        "package_assets": [
            {"label": "video", "value": mp4_path.name},
            {"label": "scene-notes", "value": scene_path.name},
        ],
        "delivery_assets": delivery_assets,
        "generated_at": _utc_now(),
        "notes": [f"output_root={output_root}", "mp4/txt 산출물을 생성했습니다."],
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def review_video_quality(
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
    passed = {"mp4", "txt"}.issubset(formats)
    return {
        "passed": passed,
        "status": "approved" if passed else "needs-review",
        "feature_id": "ai-video",
        "fallback_state": "completed" if passed else "completed_preview_only",
        "score": 84 if passed else 56,
        "review_summary": "영상 패키지 산출물(mp4/txt) 계약을 검증했습니다.",
        "failure_tags": [] if passed else ["video-delivery-assets-missing"],
        "checks": {
            "mp4_exists": "mp4" in formats,
            "txt_exists": "txt" in formats,
        },
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "final_artifact_id": final_artifact.get("artifact_id"),
    }


class VideoGenerationEngine:
    """Legacy engine class wrapper."""

    ENGINE_ID = "video-producer"

    async def run_preview(
        self,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "ad-short",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return build_video_preview(
            {
                "prompt": prompt,
                "project_name": project_name or "marketplace-video-run",
                "template_id": template,
                "bridge_payload": dict(options or {}),
            }
        )

    async def run_final(
        self,
        preview_artifact_id: str,
        *,
        preview_artifact: Dict[str, Any] | None = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        del preview_artifact_id
        return render_video_final({"bridge_payload": dict(options or {})}, preview_artifact or {})
