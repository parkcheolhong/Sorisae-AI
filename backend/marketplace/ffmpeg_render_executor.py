from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
from typing import Dict, List
from uuid import uuid4

from .execution_flow_registry import build_execution_identity

def _output_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "uploads" / "tmp" / "final_video_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _parse_ffconcat(ffconcat_path: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for raw_line in ffconcat_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("ffconcat"):
            continue
        if line.startswith("file "):
            source = line[5:].strip().strip("'")
            entries.append({"path": source, "duration": None})
            continue
        if line.startswith("duration ") and entries:
            try:
                entries[-1]["duration"] = float(line.split(" ", 1)[1].strip())
            except Exception:
                entries[-1]["duration"] = None
    return entries


def _probe_rendered_video(output_mp4_path: Path) -> Dict[str, object]:
    probe_cmd = [
        shutil.which("ffprobe") or "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate,nb_frames",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(output_mp4_path),
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "ffprobe failed").strip())
    data = json.loads(result.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    nb_frames_raw = stream.get("nb_frames") or 0
    try:
        nb_frames = int(nb_frames_raw)
    except Exception:
        nb_frames = 0
    avg_frame_rate = str(stream.get("avg_frame_rate") or "0/0")
    return {
        "duration_seconds": duration,
        "nb_frames": nb_frames,
        "avg_frame_rate": avg_frame_rate,
    }


def _find_numbered_frame_sequence(output_dir: Path, expected_total_frames: int) -> tuple[Path, int] | tuple[None, int]:
    frames_dir = (output_dir / "frames").resolve()
    if not frames_dir.exists():
        return None, 0
    frame_files = sorted(
        p for p in frames_dir.glob("frame_*.png")
        if p.is_file()
    )
    if not frame_files:
        return None, 0
    if expected_total_frames > 0 and len(frame_files) < expected_total_frames:
        return None, len(frame_files)
    return frames_dir / "frame_%04d.png", len(frame_files)

def render_final_video(payload: Dict[str, object]) -> Dict[str, object]:
    render_id = f"render-{uuid4().hex[:10]}"
    ffconcat_path = Path(str(payload.get("ffconcat_path") or "")).resolve()
    output_dir_value = str(payload.get("output_dir") or "").strip()
    output_dir = Path(output_dir_value).resolve() if output_dir_value else (_output_root() / render_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_basename = str(payload.get("output_basename") or "final_output.mp4").strip() or "final_output.mp4"
    if not output_basename.lower().endswith(".mp4"):
        output_basename = f"{output_basename}.mp4"
    output_mp4_path = output_dir / output_basename
    log_path = output_dir / f"{output_mp4_path.stem}.log"
    ffmpeg_binary = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffmpeg_path = shutil.which(ffmpeg_binary)
    if not ffmpeg_path:
        message = f"ffmpeg binary not found: {ffmpeg_binary}"
        log_path.write_text(message, encoding="utf-8")
        return {"render_id": render_id, "status": "failed", "ffconcat_path": str(ffconcat_path), "output_mp4_path": str(output_mp4_path), "log_path": str(log_path), "error_message": message, "execution": build_execution_identity("final_render")}
    ffconcat_entries = _parse_ffconcat(ffconcat_path)
    expected_duration_seconds = float(payload.get("duration_seconds") or 0)
    if expected_duration_seconds <= 0:
        expected_duration_seconds = sum(
            float(entry.get("duration") or 0.0)
            for entry in ffconcat_entries
            if entry.get("duration") is not None
        )
    frames_per_second = max(1, int(payload.get("frames_per_second") or 8))
    expected_total_frames = int(payload.get("expected_total_frames") or 0)
    if expected_total_frames <= 0 and expected_duration_seconds > 0:
        expected_total_frames = int(round(expected_duration_seconds * frames_per_second))

    sequence_pattern, sequence_count = _find_numbered_frame_sequence(output_dir, expected_total_frames)
    render_mode = "image_sequence" if sequence_pattern else "concat"
    if sequence_pattern:
        command = [
            ffmpeg_path,
            "-y",
            "-framerate",
            str(frames_per_second),
            "-start_number",
            "1",
            "-i",
            str(sequence_pattern),
            "-frames:v",
            str(max(1, expected_total_frames)),
            "-r",
            str(frames_per_second),
            "-t",
            f"{expected_duration_seconds:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_mp4_path),
        ]
    else:
        command = [
            ffmpeg_path,
            "-y",
            "-safe",
            "0",
            "-f",
            "concat",
            "-i",
            str(ffconcat_path),
            "-vf",
            f"fps={frames_per_second}",
            "-r",
            str(frames_per_second),
            "-frames:v",
            str(max(1, expected_total_frames)),
            "-t",
            f"{expected_duration_seconds:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_mp4_path),
        ]
    result = subprocess.run(command, capture_output=True, text=True)
    log_path.write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
    if result.returncode != 0:
        return {"render_id": render_id, "status": "failed", "ffconcat_path": str(ffconcat_path), "output_mp4_path": str(output_mp4_path), "log_path": str(log_path), "error_message": (result.stderr or "").strip() or f"ffmpeg exited with code {result.returncode}", "execution": build_execution_identity("final_render")}

    probe = _probe_rendered_video(output_mp4_path)
    duration_gap = abs(float(probe.get("duration_seconds") or 0.0) - expected_duration_seconds)
    frame_gap = abs(int(probe.get("nb_frames") or 0) - expected_total_frames)
    render_manifest_path = output_dir / f"{output_mp4_path.stem}.manifest.json"
    render_manifest_path.write_text(
        json.dumps(
            {
                "ffconcat_path": str(ffconcat_path),
                "render_mode": render_mode,
                "sequence_frame_count": sequence_count,
                "frames_per_second": frames_per_second,
                "expected_duration_seconds": expected_duration_seconds,
                "expected_total_frames": expected_total_frames,
                "actual_duration_seconds": probe.get("duration_seconds"),
                "actual_total_frames": probe.get("nb_frames"),
                "actual_avg_frame_rate": probe.get("avg_frame_rate"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if duration_gap > 0.2 or frame_gap > 1:
        return {
            "render_id": render_id,
            "status": "failed",
            "ffconcat_path": str(ffconcat_path),
            "output_mp4_path": str(output_mp4_path),
            "log_path": str(log_path),
            "error_message": (
                f"render verification failed: duration={probe.get('duration_seconds')}s, "
                f"frames={probe.get('nb_frames')} (expected {expected_duration_seconds}s / {expected_total_frames} frames)"
            ),
            "execution": build_execution_identity("final_render"),
        }
    return {"render_id": render_id, "status": "completed", "ffconcat_path": str(ffconcat_path), "output_mp4_path": str(output_mp4_path), "log_path": str(log_path), "error_message": None, "execution": build_execution_identity("final_render")}
