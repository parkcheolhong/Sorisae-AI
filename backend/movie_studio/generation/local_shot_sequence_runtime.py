from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import math

from PIL import Image, ImageChops

from backend.marketplace.ffmpeg_render_executor import render_final_video
from backend.marketplace.local_video_connector import plan_local_video_connector
from backend.movie_studio.generation.local_gpu_runtime import run_local_gpu_storyboard_keyframes
from backend.movie_studio.storage.scene_bundle_store import scene_bundle_root
from backend.movie_studio.generation.video_diffusion_foundation_backend import run_video_diffusion_foundation_backend
from backend.movie_studio.utils.json_tools import write_json
from backend.movie_studio.utils.path_tools import ensure_directory
MOVIE_STUDIO_OPERATION_SECONDS = 60
MOVIE_STUDIO_OPERATION_FPS = 8
MOVIE_STUDIO_OPERATION_TOTAL_FRAMES = MOVIE_STUDIO_OPERATION_SECONDS * MOVIE_STUDIO_OPERATION_FPS


def _ensure_scene_keyframes(plan: Dict[str, object], runtime_plan: Dict[str, object]) -> Dict[str, object] | None:
    if not runtime_plan:
        return None

    scenes = list(plan.get("scenes") or [])
    missing_keyframes = [
        str(scene.get("keyframe_path") or "").strip()
        for scene in scenes
        if not Path(str(scene.get("keyframe_path") or "").strip()).exists()
    ]

    if not missing_keyframes:
        return None

    return run_local_gpu_storyboard_keyframes(runtime_plan)


def _parse_resolution(value: str) -> Tuple[int, int]:
    normalized = str(value or "1280x720").lower().replace("*", "x")
    if "x" not in normalized:
        return (1280, 720)
    left, right = normalized.split("x", 1)
    try:
        return (max(256, int(left)), max(256, int(right)))
    except ValueError:
        return (1280, 720)


def _normalized_sequence_entry(sequence_plan: List[Dict[str, object]], index: int) -> Dict[str, object]:
    if index < len(sequence_plan):
        return dict(sequence_plan[index])
    return {
        "sequence_id": f"seq-{index + 1:02d}",
        "objective": f"sequence {index + 1}",
        "emotional_state": "controlled realism",
        "blocking_summary": "hero motion progression",
        "cta_required": False,
    }


def _motion_profile(sequence_entry: Dict[str, object], index: int, total: int) -> Dict[str, float | str]:
    objective = str(sequence_entry.get("objective") or "").lower()
    cta_required = bool(sequence_entry.get("cta_required", False)) or "cta" in objective
    if cta_required:
        return {
            "name": "cta_push",
            "zoom_start": 1.02,
            "zoom_end": 1.18,
            "pan_x_start": -0.04,
            "pan_x_end": 0.06,
            "pan_y_start": 0.03,
            "pan_y_end": -0.02,
            "roll": 0.01,
        }
    if index == 0:
        return {
            "name": "hero_reveal",
            "zoom_start": 1.0,
            "zoom_end": 1.1,
            "pan_x_start": -0.03,
            "pan_x_end": 0.03,
            "pan_y_start": 0.02,
            "pan_y_end": -0.01,
            "roll": 0.0,
        }
    return {
        "name": "continuity_glide",
        "zoom_start": 1.04,
        "zoom_end": 1.12,
        "pan_x_start": 0.02,
        "pan_x_end": -0.02,
        "pan_y_start": 0.01,
        "pan_y_end": -0.02,
        "roll": -0.008 if index == total - 1 else 0.006,
    }


def _narrative_phase(progress: float) -> Dict[str, float]:
    eased = _ease_in_out(progress)
    return {
        "forward_drive": max(0.0, min(1.0, eased)),
        "micro_shift": math.sin(progress * math.pi * 2.0) * 0.04,
        "focus_breath": math.sin(progress * math.pi) * 0.03,
    }


def _scene_phase_seed(scene: Dict[str, object]) -> float:
    scene_id = str(scene.get("scene_id") or scene.get("title") or "scene")
    return float((sum(ord(char) for char in scene_id) % 17) + 1)


def _cross_scene_bridge(
    progress: float,
    motion_profile: Dict[str, float | str],
    scene: Dict[str, object],
    previous_scene: Dict[str, object] | None,
    next_scene: Dict[str, object] | None,
) -> Dict[str, float]:
    phase_seed = _scene_phase_seed(scene)
    bridge_strength = max(0.0, min(1.0, float(progress)))
    previous_bias = 0.0 if previous_scene is None else 0.012 * (1.0 - bridge_strength)
    next_bias = 0.0 if next_scene is None else 0.014 * bridge_strength
    return {
        "pan_bridge": math.sin((bridge_strength + phase_seed) * math.pi) * 0.01,
        "zoom_bridge": previous_bias + next_bias,
        "roll_bridge": float(motion_profile.get("roll") or 0.0) * 0.25 * (bridge_strength - 0.5),
    }


def _blend_chunk_edge(previous_frame: Image.Image | None, current_frame: Image.Image, progress: float) -> Image.Image:
    if previous_frame is None:
        return current_frame
    if progress > 0.12:
        return current_frame
    blend_ratio = max(0.0, 0.35 * (1.0 - (progress / 0.12)))
    return Image.blend(previous_frame.convert("RGB"), current_frame.convert("RGB"), max(0.0, min(1.0, 1.0 - blend_ratio)))


def prepare_local_shot_sequence_plan(
    project_id: str,
    payload: Dict[str, object],
    sequence_plan: List[Dict[str, object]],
    scene_generation_requests: List[Dict[str, object]],
    local_gpu_runtime_plan: Dict[str, object],
) -> Dict[str, object]:
    artifact_root = ensure_directory(scene_bundle_root(project_id) / "local_shot_sequence")
    fps = MOVIE_STUDIO_OPERATION_FPS
    width, height = _parse_resolution(str(payload.get("target_resolution") or "1280x720"))
    total_duration_seconds = MOVIE_STUDIO_OPERATION_SECONDS
    total_scenes = max(1, len(scene_generation_requests))
    total_frames = 0
    scenes: List[Dict[str, object]] = []
    keyframe_tasks = {str(task.get("scene_id") or ""): task for task in list(local_gpu_runtime_plan.get("tasks") or [])}
    base_frame_count = MOVIE_STUDIO_OPERATION_TOTAL_FRAMES // total_scenes
    frame_remainder = MOVIE_STUDIO_OPERATION_TOTAL_FRAMES % total_scenes

    for index, scene_request in enumerate(scene_generation_requests):
        sequence_entry = _normalized_sequence_entry(sequence_plan, index)
        scene_id = str(scene_request.get("scene_id") or f"scene-{index + 1:02d}")
        requested_frame_count = int(scene_request.get("frame_count") or 0)
        frame_count = requested_frame_count if requested_frame_count > 0 else base_frame_count + (1 if index < frame_remainder else 0)
        start_frame = total_frames + 1
        end_frame = total_frames + frame_count
        start_second = round((start_frame - 1) / fps, 3)
        end_second = round(end_frame / fps, 3)
        keyframe_task = dict(keyframe_tasks.get(scene_id) or {})
        scenes.append(
            {
                "scene_id": scene_id,
                "sequence_id": str(scene_request.get("sequence_id") or sequence_entry.get("sequence_id") or f"seq-{index + 1:02d}"),
                "title": str(sequence_entry.get("objective") or scene_id),
                "duration_seconds": round(frame_count / fps, 3),
                "frame_count": frame_count,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_second": start_second,
                "end_second": end_second,
                "keyframe_path": str(keyframe_task.get("output_image_path") or artifact_root / scene_id / "keyframe.png"),
                "frames_dir": str(ensure_directory(artifact_root / scene_id / "frames")),
                "motion_profile": _motion_profile(sequence_entry, index, total_scenes),
                "cta_required": bool(sequence_entry.get("cta_required", False)),
                "prompt": str(keyframe_task.get("prompt") or sequence_entry.get("objective") or scene_id),
                "narrative_prompt": str(keyframe_task.get("narrative_prompt") or scene_request.get("narrative_prompt") or ""),
                "interpolation_strategy": str(keyframe_task.get("interpolation_strategy") or scene_request.get("interpolation_strategy") or "dual_keyframe_narrative_morph"),
                "continuity_checks": list(keyframe_task.get("continuity_checks") or scene_request.get("continuity_checks") or []),
                "performance_unit": "full_body_human_motion",
                "walking_pattern": "motivated cinematic walking with stride continuity",
                "gesture_pattern": "hand and arm gesture synchronized with emotional beats",
                "speaking_mode": "dialogue_sync_required",
                "lip_sync_requirement": "phoneme_visible",
                "performance_actions": list(scene_request.get("performance_actions") or []),
                "physical_continuity_laws": list(scene_request.get("physical_continuity_laws") or []),
                "guidance_schedule": dict(scene_request.get("guidance_schedule") or {}),
            }
        )
        total_frames += frame_count

    quality_gate_failed = total_frames != MOVIE_STUDIO_OPERATION_TOTAL_FRAMES

    plan = {
        "provider": "self-hosted-local-shot-sequence-runtime",
        "project_id": project_id,
        "artifact_root": str(artifact_root),
        "generation_backend": "video_diffusion_foundation_backend",
        "runtime_plan": local_gpu_runtime_plan,
        "frames_per_second": fps,
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
        "duration_seconds": total_duration_seconds,
        "expected_total_frames": total_frames,
        "operation_required_total_frames": MOVIE_STUDIO_OPERATION_TOTAL_FRAMES,
        "scene_count": len(scenes),
        "scenes": scenes,
        "stabilization": {
            "chunk_overlap_frames": 4,
            "seam_blend_ratio": 0.35,
            "max_blur_radius": 0.12,
        },
        "quality_gate_failed": quality_gate_failed,
        "quality_gate_reason": None if not quality_gate_failed else f"expected 480 frames, got {total_frames}",
        "ready_for_execution": all(Path(str(scene.get("keyframe_path") or "")).exists() for scene in scenes),
    }
    write_json(artifact_root / "shot_sequence_plan.json", plan)
    return plan


def _ease_in_out(value: float) -> float:
    normalized = max(0.0, min(1.0, float(value)))
    return 0.5 - (0.5 * math.cos(normalized * math.pi))


def _lerp(start: float, end: float, amount: float) -> float:
    return start + ((end - start) * amount)


def _render_motion_frame(
    image: Image.Image,
    width: int,
    height: int,
    progress: float,
    motion_profile: Dict[str, float | str],
    scene: Dict[str, object],
    previous_scene: Dict[str, object] | None,
    next_scene: Dict[str, object] | None,
) -> Image.Image:
    eased = _ease_in_out(progress)
    narrative_phase = _narrative_phase(progress)
    bridge_phase = _cross_scene_bridge(progress, motion_profile, scene, previous_scene, next_scene)
    zoom = _lerp(float(motion_profile.get("zoom_start") or 1.0), float(motion_profile.get("zoom_end") or 1.08), eased)
    pan_x = _lerp(float(motion_profile.get("pan_x_start") or 0.0), float(motion_profile.get("pan_x_end") or 0.0), eased)
    pan_y = _lerp(float(motion_profile.get("pan_y_start") or 0.0), float(motion_profile.get("pan_y_end") or 0.0), eased)
    roll = _lerp(0.0, float(motion_profile.get("roll") or 0.0), eased)
    zoom += narrative_phase["focus_breath"] + bridge_phase["zoom_bridge"]
    pan_x += narrative_phase["micro_shift"] + bridge_phase["pan_bridge"]
    pan_y += (narrative_phase["forward_drive"] - 0.5) * 0.03
    roll += bridge_phase["roll_bridge"]

    source = image.convert("RGB")
    source_width, source_height = source.size
    scaled_width = max(width, int(source_width * zoom))
    scaled_height = max(height, int(source_height * zoom))
    scaled = source.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    offset_x = int((scaled_width - width) * (0.5 + (pan_x / 2.0)))
    offset_y = int((scaled_height - height) * (0.5 + (pan_y / 2.0)))
    offset_x = max(0, min(offset_x, max(0, scaled_width - width)))
    offset_y = max(0, min(offset_y, max(0, scaled_height - height)))
    frame = scaled.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    if abs(roll) > 0.0001:
        frame = frame.rotate(roll * 180.0, resample=Image.Resampling.BICUBIC, expand=False)
    return frame


def _build_frame_prompt(scene: Dict[str, object], progress: float, absolute_index: int) -> str:
    title = str(scene.get("title") or scene.get("scene_id") or "scene")
    base_prompt = str(scene.get("prompt") or "").strip()
    narrative_prompt = str(scene.get("narrative_prompt") or "").strip()
    interpolation_strategy = str(scene.get("interpolation_strategy") or "dual_keyframe_narrative_morph").strip()
    checks = [str(item).strip() for item in list(scene.get("continuity_checks") or []) if str(item).strip()]
    return " ".join(
        part for part in [
            f"scene: {title}",
            base_prompt,
            narrative_prompt,
            f"frame_progress: {progress:.4f}",
            f"absolute_frame: {absolute_index}",
            f"interpolation_strategy: {interpolation_strategy}",
            f"continuity_checks: {'; '.join(checks)}" if checks else "",
        ] if part
    )


def _run_motion_interpolation_fallback(plan: Dict[str, object]) -> Dict[str, object]:
    width = int(plan.get("width") or 1280)
    height = int(plan.get("height") or 720)
    scenes = list(plan.get("scenes") or [])
    frame_records: List[Dict[str, object]] = []

    for scene_index, scene in enumerate(scenes):
        previous_scene = scenes[scene_index - 1] if scene_index > 0 else None
        next_scene = scenes[scene_index + 1] if scene_index < len(scenes) - 1 else None
        keyframe_path = Path(str(scene.get("keyframe_path") or ""))
        if not keyframe_path.exists():
            raise FileNotFoundError(f"shot sequence keyframe missing: {keyframe_path}")
        image = Image.open(keyframe_path).convert("RGB")
        frames_dir = ensure_directory(Path(str(scene.get("frames_dir") or "")))
        frame_count = max(1, int(scene.get("frame_count") or 1))
        start_frame = int(scene.get("start_frame") or 1)
        motion_profile = dict(scene.get("motion_profile") or {})
        for local_index in range(frame_count):
            absolute_index = start_frame + local_index
            progress = local_index / max(1, frame_count - 1)
            frame = _render_motion_frame(
                image,
                width,
                height,
                progress,
                motion_profile,
                scene,
                previous_scene,
                next_scene,
            )
            output_path = frames_dir / f"frame_{absolute_index:04d}.png"
            frame.save(output_path, format="PNG")
            frame_records.append(
                {
                    "scene_id": str(scene.get("scene_id") or ""),
                    "frame_index": absolute_index,
                    "image_path": str(output_path),
                    "prompt": _build_frame_prompt(scene, progress, absolute_index),
                    "narrative_prompt": str(scene.get("narrative_prompt") or ""),
                    "interpolation_strategy": str(scene.get("interpolation_strategy") or "dual_keyframe_narrative_morph"),
                    "continuity_checks": list(scene.get("continuity_checks") or []),
                    "start_second": float(scene.get("start_second") or 0.0),
                    "end_second": float(scene.get("end_second") or 0.0),
                }
            )

    manifest = {
        "provider": "self-hosted-local-shot-sequence-runtime",
        "project_id": str(plan.get("project_id") or ""),
        "frame_count": len(frame_records),
        "expected_total_frames": int(plan.get("operation_required_total_frames") or MOVIE_STUDIO_OPERATION_TOTAL_FRAMES),
        "quality_gate_failed": len(frame_records) != int(plan.get("operation_required_total_frames") or MOVIE_STUDIO_OPERATION_TOTAL_FRAMES),
        "generation_backend": str(plan.get("generation_backend") or "motion_interpolation_fallback"),
        "frames": frame_records,
    }
    artifact_root = Path(str(plan.get("artifact_root") or ""))
    write_json(artifact_root / "shot_sequence_frames.json", manifest)
    return manifest


def run_local_shot_sequence_frames(plan: Dict[str, object]) -> Dict[str, object]:
    generation_backend = str(plan.get("generation_backend") or "video_diffusion_foundation_backend")
    runtime_plan = dict(plan.get("runtime_plan") or {})
    _ensure_scene_keyframes(plan, runtime_plan)
    if generation_backend == "video_diffusion_foundation_backend":
        foundation_manifest = run_video_diffusion_foundation_backend(plan, runtime_plan)
        if not foundation_manifest.get("quality_gate_failed"):
            previous_frame: Image.Image | None = None
            for frame_record in list(foundation_manifest.get("frames") or []):
                image_path = Path(str(frame_record.get("image_path") or ""))
                if not image_path.exists():
                    continue
                current_frame = Image.open(image_path).convert("RGB")
                start_frame = int(frame_record.get("frame_index") or 1)
                scene_frame_start = ((max(1, start_frame) - 1) % 40) / 40.0
                stabilized = _blend_chunk_edge(previous_frame, current_frame, scene_frame_start)
                stabilized.save(image_path, format="PNG")
                previous_frame = stabilized
            foundation_manifest["frame_count"] = len(list(foundation_manifest.get("frames") or []))
            return foundation_manifest
    return _run_motion_interpolation_fallback(plan)


def render_local_shot_sequence_video(plan: Dict[str, object], frames_manifest: Dict[str, object]) -> Dict[str, object]:
    storyboard = []
    for index, scene in enumerate(list(plan.get("scenes") or []), start=1):
        storyboard.append(
            {
                "cut": index,
                "title": str(scene.get("title") or scene.get("scene_id") or f"scene {index}"),
                "duration_sec": float(scene.get("duration_seconds") or 1),
                "start_frame": int(scene.get("start_frame") or 1),
                "end_frame": int(scene.get("end_frame") or 1),
                "scene_prompt": str(scene.get("prompt") or ""),
            }
        )
    connector_payload = {
        "title": f"{plan.get('project_id') or 'movie-studio'} shot-sequence",
        "scenario_script": "self-hosted local shot sequence runtime",
        "duration_seconds": int(plan.get("duration_seconds") or 1),
        "frames_per_second": int(plan.get("frames_per_second") or 24),
        "storyboard": storyboard,
        "frames": list(frames_manifest.get("frames") or []),
        "subtitle_cues": [],
    }
    connector_result = plan_local_video_connector(connector_payload)
    render_result = render_final_video(
        {
            "title": connector_payload["title"],
            "ffconcat_path": connector_result["ffconcat_path"],
            "frames_per_second": connector_payload["frames_per_second"],
            "duration_seconds": connector_payload["duration_seconds"],
            "expected_total_frames": int(plan.get("expected_total_frames") or 0),
            "output_dir": connector_result["output_dir"],
            "output_basename": f"{plan.get('project_id') or 'movie-studio'}_shot_sequence.mp4",
        }
    )
    manifest = {
        "provider": "self-hosted-local-shot-sequence-runtime",
        "project_id": str(plan.get("project_id") or ""),
        "connector_result": connector_result,
        "render_result": render_result,
        "quality_gate_failed": bool(plan.get("quality_gate_failed")) or bool(connector_result.get("quality_gate_failed")),
    }
    artifact_root = Path(str(plan.get("artifact_root") or ""))
    write_json(artifact_root / "shot_sequence_render.json", manifest)
    return manifest
