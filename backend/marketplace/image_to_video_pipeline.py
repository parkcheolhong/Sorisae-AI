from __future__ import annotations

from typing import Dict
from uuid import uuid4

from .execution_flow_registry import build_execution_identity
from .image_generation_engine import run_image_generation_engine
from .video_generation_engine import run_video_generation_engine


VIDEO_AD_OPERATION_STANDARD_SECONDS = 60


def _scenario_alignment_summary(payload: Dict[str, object], image_line: Dict[str, object], video_line: Dict[str, object]) -> Dict[str, object]:
    scenario_script = str(payload.get("scenario_script") or image_line.get("scenario_script") or "").strip()
    scenario_sentences = [item.strip() for item in scenario_script.split(".") if item.strip()]
    storyboard = list(image_line.get("storyboard") or [])
    sections = list(video_line.get("sections") or [])
    duration_seconds = int(image_line.get("duration_seconds") or payload.get("duration_seconds") or VIDEO_AD_OPERATION_STANDARD_SECONDS)
    motion_guard_failed = bool(image_line.get("motion_guard_failed"))
    static_motion_warning = str(image_line.get("static_motion_warning") or "").strip()
    alignment_failed = bool(scenario_script) and len(storyboard) < max(2, len(scenario_sentences))
    section_alignment_failed = len(sections) < len(storyboard)
    quality_gate_failed = motion_guard_failed or alignment_failed or section_alignment_failed
    failure_reasons = []

    if duration_seconds < VIDEO_AD_OPERATION_STANDARD_SECONDS:
        failure_reasons.append(f"duration under operating standard: {duration_seconds}s < {VIDEO_AD_OPERATION_STANDARD_SECONDS}s")
    if motion_guard_failed:
        failure_reasons.append("motion guard failed: stagnant visual run detected")
    if static_motion_warning:
        failure_reasons.append(static_motion_warning)
    if alignment_failed:
        failure_reasons.append(
            f"scenario-storyboard mismatch: sentences={len(scenario_sentences)}, storyboard={len(storyboard)}"
        )
    if section_alignment_failed:
        failure_reasons.append(
            f"storyboard-section mismatch: storyboard={len(storyboard)}, sections={len(sections)}"
        )

    return {
        "operation_standard_seconds": VIDEO_AD_OPERATION_STANDARD_SECONDS,
        "scenario_sentence_count": len(scenario_sentences),
        "storyboard_count": len(storyboard),
        "section_count": len(sections),
        "motion_guard_failed": motion_guard_failed,
        "static_motion_warning": static_motion_warning or None,
        "quality_gate_failed": quality_gate_failed,
        "failure_reasons": failure_reasons,
    }


def run_image_to_video_pipeline(payload: Dict[str, object]) -> Dict[str, object]:
    image_engine = run_image_generation_engine(payload)
    image_line = dict(image_engine.get("image_line") or {})
    video_engine = run_video_generation_engine({
        "title": payload.get("title") or image_line.get("title") or "비디오 연결 라인",
        "scenario_script": payload.get("scenario_script") or image_line.get("scenario_script") or "",
        "duration_seconds": image_line.get("duration_seconds") or payload.get("duration_seconds") or VIDEO_AD_OPERATION_STANDARD_SECONDS,
        "frames_per_second": image_line.get("frames_per_second") or payload.get("frames_per_second") or 8,
        "total_frames": image_line.get("total_frames") or 0,
        "storyboard": image_line.get("storyboard") or [],
        "frames": image_line.get("frames") or [],
        "subtitle_cues": image_line.get("subtitle_cues") or [],
    })
    quality_summary = _scenario_alignment_summary(payload, image_line, dict(video_engine.get("video_line") or {}))
    return {
        "pipeline_id": f"image-to-video-{uuid4().hex[:10]}",
        "image_engine": image_engine,
        "video_engine": video_engine,
        "quality_summary": quality_summary,
        "execution": build_execution_identity("image_to_video"),
    }
