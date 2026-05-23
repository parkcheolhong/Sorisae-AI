"""Music engine with local artifact packaging."""
from __future__ import annotations

import wave
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, Optional
from uuid import uuid4

from ..contracts import extract_prompt_keywords, summarize_prompt


def _build_output_root() -> Path:
    root = Path(gettempdir()) / "codeai-marketplace-music"
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


def _write_silent_wav(path: Path, seconds: float = 1.0, sample_rate: int = 16000) -> None:
    frame_count = max(1, int(seconds * sample_rate))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def build_music_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    keywords = extract_prompt_keywords(prompt, limit=6)
    template_id = str(payload.get("template_id") or "music-track-template")
    project_name = str(payload.get("project_name") or "marketplace-music-run")
    track_structure = [
        {"title": "Intro", "summary": "브랜드 분위기를 전달하는 도입", "duration": "0:00-0:10", "mood": keywords[0] if keywords else "calm"},
        {"title": "Build", "summary": "리듬과 레이어를 확장", "duration": "0:10-0:20", "mood": keywords[1] if len(keywords) > 1 else "focus"},
        {"title": "Peak", "summary": "후반 고조와 CTA 구간", "duration": "0:20-0:30", "mood": keywords[2] if len(keywords) > 2 else "impact"},
    ]
    return {
        "artifact_id": f"ai-music-preview-{uuid4().hex[:8]}",
        "feature_id": "ai-music",
        "phase": "preview",
        "state": "completed",
        "status": "ready",
        "title": project_name,
        "content_type": "audio/wav",
        "prompt_summary": summarize_prompt(prompt),
        "keywords": keywords,
        "track_structure": track_structure,
        "package_assets": [{"label": "preview", "value": "30sec plan"}],
        "notes": [f"template_id={template_id}", "preview 단계에서는 트랙 구조를 먼저 확정합니다."],
        "generated_at": _utc_now(),
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def render_music_final(payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
    seed = uuid4().hex[:8]
    output_root = _build_output_root() / seed
    output_root.mkdir(parents=True, exist_ok=True)
    wav_path = output_root / f"{seed}.wav"
    structure_path = output_root / f"{seed}.txt"
    _write_silent_wav(wav_path, seconds=1.2)
    structure_path.write_text(
        "\n".join(
            [
                f"prompt_summary={preview_artifact.get('prompt_summary') or ''}",
                "track_structure=Intro,Build,Peak",
            ]
        ),
        encoding="utf-8",
    )
    delivery_assets = [
        _build_delivery_asset(wav_path, "wav", "audio/wav"),
        _build_delivery_asset(structure_path, "txt", "text/plain"),
    ]
    return {
        "artifact_id": f"ai-music-final-{seed}",
        "feature_id": "ai-music",
        "phase": "final",
        "state": "completed",
        "status": "generated",
        "title": "최종 음악 패키지",
        "content_type": "audio/wav",
        "prompt_summary": str(preview_artifact.get("prompt_summary") or ""),
        "keywords": list(preview_artifact.get("keywords") or []),
        "track_structure": list(preview_artifact.get("track_structure") or []),
        "package_assets": [
            {"label": "wav", "value": wav_path.name},
            {"label": "structure", "value": structure_path.name},
        ],
        "delivery_assets": delivery_assets,
        "generated_at": _utc_now(),
        "notes": [f"output_root={output_root}", "wav/txt 산출물을 생성했습니다."],
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def review_music_quality(
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
    passed = {"wav", "txt"}.issubset(formats)
    return {
        "passed": passed,
        "status": "approved" if passed else "needs-review",
        "feature_id": "ai-music",
        "fallback_state": "completed" if passed else "completed_preview_only",
        "score": 85 if passed else 57,
        "review_summary": "오디오 패키지 산출물(wav/txt) 계약을 검증했습니다.",
        "failure_tags": [] if passed else ["music-delivery-assets-missing"],
        "checks": {
            "wav_exists": "wav" in formats,
            "txt_exists": "txt" in formats,
        },
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "final_artifact_id": final_artifact.get("artifact_id"),
    }


class MusicGenerationEngine:
    """Legacy engine class wrapper."""

    ENGINE_ID = "music-generator"

    async def run_preview(
        self,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "bgm-cinematic",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return build_music_preview(
            {
                "prompt": prompt,
                "project_name": project_name or "marketplace-music-run",
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
        return render_music_final({"bridge_payload": dict(options or {})}, preview_artifact or {})
