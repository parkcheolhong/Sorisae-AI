from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import shutil
from typing import Dict, List
from uuid import uuid4

from .execution_flow_registry import build_execution_identity


VIDEO_AD_OPERATION_STANDARD_SECONDS = 60


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _output_root() -> Path:
    root = _repo_root() / "uploads" / "tmp" / "video_connector_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _transition_for_section(index: int, total: int) -> str:
    if index == 0:
        return "scene_open"
    if index == total - 1:
        return "scene_close"
    return "match_cut_continuity"


def _subtitle_window(section: Dict[str, object], subtitle_cues: List[Dict[str, object]]) -> tuple[int, int]:
    start_frame = int(section["frame_start"])
    end_frame = int(section["frame_end"])
    candidates = []
    for cue in subtitle_cues:
        cue_start = int(cue.get("start_ms") or 0)
        cue_end = int(cue.get("end_ms") or 0)
        if cue_end <= cue_start:
            continue
        if cue_end >= start_frame and cue_start <= end_frame:
            candidates.append((cue_start, cue_end))
    if not candidates:
        return 0, 0
    return min(item[0] for item in candidates), max(item[1] for item in candidates)


def plan_local_video_connector(payload: Dict[str, object]) -> Dict[str, object]:
    title = _normalize_text(payload.get("title") or "비디오 연결 라인") or "비디오 연결 라인"
    scenario_script = _normalize_text(payload.get("scenario_script") or "")
    duration_seconds = int(payload.get("duration_seconds") or VIDEO_AD_OPERATION_STANDARD_SECONDS)
    frames_per_second = int(payload.get("frames_per_second") or 8)
    storyboard = list(payload.get("storyboard") or [])
    frames = list(payload.get("frames") or [])
    subtitle_cues = list(payload.get("subtitle_cues") or [])

    run_id = f"video-connector-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    output_dir = _output_root() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    sections: List[Dict[str, object]] = []
    ffconcat_lines = ["ffconcat version 1.0"]
    total_sections = len(storyboard)
    frame_duration = 1 / max(1, frames_per_second)
    preserved_frame_count = 0

    def _preserve_frame(frame: Dict[str, object]) -> str:
        nonlocal preserved_frame_count
        source_path = Path(str(frame.get("image_path") or "")).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"video connector source frame not found: {source_path}")
        suffix = source_path.suffix or ".png"
        frame_index = int(frame.get("frame_index") or (preserved_frame_count + 1))
        target_path = frames_dir / f"frame_{frame_index:04d}{suffix}"
        if not target_path.exists():
            shutil.copy2(source_path, target_path)
            preserved_frame_count += 1
        return target_path.as_posix()

    for index, cut in enumerate(storyboard, start=1):
        cut_id = int(cut.get("cut") or index)
        frame_start = int(cut.get("start_frame") or 1)
        frame_end = int(cut.get("end_frame") or frame_start)
        section_frames = [
            frame for frame in frames
            if frame_start <= int(frame.get("frame_index") or 0) <= frame_end
        ]
        transition = _transition_for_section(index - 1, total_sections)
        subtitle_start_ms, subtitle_end_ms = _subtitle_window({"frame_start": frame_start, "frame_end": frame_end}, subtitle_cues)
        editorial_prompt = " ".join([
            "비디오 연결 라인 section prompt.",
            f"section: {cut.get('title') or f'섹션 {index}'}.",
            f"transition: {transition}.",
            f"frame range: {frame_start}-{frame_end}.",
            f"scene prompt: {cut.get('scene_prompt') or ''}.",
            "이 section은 앞뒤 section과 위치, 시선, 손동작, 객체 크기가 자연스럽게 이어져야 한다.",
        ]).strip()
        manifest_path = output_dir / f"section_{index:02d}_frames.ffconcat"
        section_lines = ["ffconcat version 1.0"]
        last_frame_path = ""
        for frame in section_frames:
            frame_path = _preserve_frame(frame)
            if not frame_path:
                continue
            section_lines.append(f"file '{frame_path}'")
            section_lines.append(f"duration {frame_duration:.6f}")
            ffconcat_lines.append(f"file '{frame_path}'")
            ffconcat_lines.append(f"duration {frame_duration:.6f}")
            last_frame_path = frame_path
        if last_frame_path:
            section_lines.append(f"file '{last_frame_path}'")
            ffconcat_lines.append(f"file '{last_frame_path}'")
        manifest_path.write_text("\n".join(section_lines) + "\n", encoding="utf-8")
        sections.append({
            "section_id": f"section-{index:02d}",
            "title": _normalize_text(cut.get("title") or f"섹션 {index}"),
            "cut_start": cut_id,
            "cut_end": cut_id,
            "frame_start": frame_start,
            "frame_end": frame_end,
            "duration_sec": float(cut.get("duration_sec") or 0),
            "transition": transition,
            "editorial_prompt": editorial_prompt,
            "subtitle_start_ms": subtitle_start_ms,
            "subtitle_end_ms": subtitle_end_ms,
            "manifest_path": str(manifest_path),
        })

    ffconcat_path = output_dir / "video_line.ffconcat"
    ffconcat_path.write_text("\n".join(ffconcat_lines) + "\n", encoding="utf-8")
    (output_dir / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "frame_manifest.json").write_text(
        json.dumps(
            {
                "duration_seconds": duration_seconds,
                "frames_per_second": frames_per_second,
                "expected_total_frames": duration_seconds * frames_per_second,
                "preserved_frame_count": preserved_frame_count,
                "frames_dir": str(frames_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "run_id": run_id,
        "title": title,
        "scenario_script": scenario_script,
        "output_dir": str(output_dir),
        "ffconcat_path": str(ffconcat_path),
        "sections": sections,
        "frames_dir": str(frames_dir),
        "total_frames": duration_seconds * frames_per_second,
        "duration_seconds": duration_seconds,
        "frames_per_second": frames_per_second,
        "operation_standard_seconds": VIDEO_AD_OPERATION_STANDARD_SECONDS,
        "quality_gate_failed": len(sections) == 0 or duration_seconds < VIDEO_AD_OPERATION_STANDARD_SECONDS,
        "execution": build_execution_identity("video_engine"),
    }
