from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict, List

from backend.movie_studio.generation.local_gpu_runtime import run_local_gpu_storyboard_keyframes
from backend.movie_studio.generation.local_shot_sequence_runtime import (
    prepare_local_shot_sequence_plan,
    render_local_shot_sequence_video,
    run_local_shot_sequence_frames,
)
from backend.movie_studio.orchestration.failure_recovery_engine import build_failure_recovery_plan
from backend.movie_studio.orchestration.retry_loop_engine import build_retry_policy
from backend.movie_studio.quality.local_quality_runtime import run_local_quality_gate
from backend.movie_studio.utils.json_tools import write_json


def _failure_codes(quality_manifest: Dict[str, object]) -> List[str]:
    failures = list((quality_manifest.get("quality_result") or {}).get("failures") or [])
    return [str(item.get("code") or "").strip() for item in failures if str(item.get("code") or "").strip()]


def _apply_rerender_recovery(runtime_plan: Dict[str, object], failure_codes: List[str], attempt: int) -> Dict[str, object]:
    next_plan = deepcopy(runtime_plan)
    recovery_plan = build_failure_recovery_plan()
    for task in list(next_plan.get("tasks") or []):
        guidance_scale = float(task.get("guidance_scale") or 6.0)
        strength = float(task.get("strength") or 0.42)
        steps = int(task.get("steps") or 20)
        negative_prompt = str(task.get("negative_prompt") or "")

        if "face_drift" in failure_codes:
            task["guidance_scale"] = min(9.0, guidance_scale + 0.45)
            task["strength"] = min(0.55, strength + 0.03)
            task["negative_prompt"] = f"{negative_prompt}, face asymmetry, identity drift".strip(", ")
        if "hand_collapse" in failure_codes:
            task["steps"] = min(32, steps + 4)
            task["negative_prompt"] = f"{task['negative_prompt']}, bad hands, broken fingers, fused fingers".strip(", ")
        if "body_ratio_break" in failure_codes:
            task["negative_prompt"] = f"{task['negative_prompt']}, bad anatomy, broken body, duplicate limbs".strip(", ")
        if "background_flicker" in failure_codes:
            task["guidance_scale"] = min(9.5, float(task.get("guidance_scale") or guidance_scale) + 0.3)
        if "freeze_like_cta" in failure_codes:
            task["guidance_scale"] = min(9.5, float(task.get("guidance_scale") or guidance_scale) + 0.2)
            task["strength"] = min(0.6, float(task.get("strength") or strength) + 0.04)

        task.setdefault("recovery_actions", [])
        task["recovery_actions"] = list(task.get("recovery_actions") or []) + [
            {
                "attempt": attempt,
                "failure_codes": failure_codes,
                "actions": [recovery_plan.get(code, ["rerender"]) for code in failure_codes],
            }
        ]
    return next_plan


def run_local_quality_rerender_loop(
    runtime_plan: Dict[str, object],
    sequence_plan: List[Dict[str, object]],
    scene_generation_requests: List[Dict[str, object]],
    quality_runtime_plan: Dict[str, object],
    shot_sequence_plan: Dict[str, object],
    max_attempts: int | None = None,
) -> Dict[str, object]:
    retry_policy = build_retry_policy()
    allowed_attempts = max_attempts or int(retry_policy.get("max_scene_rerenders") or 3)
    current_runtime_plan = deepcopy(runtime_plan)
    attempt_results: List[Dict[str, object]] = []
    final_quality_manifest: Dict[str, object] | None = None
    final_render_manifest: Dict[str, object] | None = None
    final_frames_manifest: Dict[str, object] | None = None
    final_shot_plan: Dict[str, object] | None = None

    for attempt in range(1, allowed_attempts + 1):
        keyframe_manifest = run_local_gpu_storyboard_keyframes(current_runtime_plan)
        shot_plan = prepare_local_shot_sequence_plan(
            project_id=str(current_runtime_plan.get("project_id") or quality_runtime_plan.get("project_id") or "movie-studio"),
            payload={
                "target_fps": shot_sequence_plan.get("frames_per_second") or 24,
                "target_duration_seconds": shot_sequence_plan.get("duration_seconds") or 60,
                "target_resolution": shot_sequence_plan.get("resolution") or "1280x720",
            },
            sequence_plan=sequence_plan,
            scene_generation_requests=scene_generation_requests,
            local_gpu_runtime_plan=current_runtime_plan,
        )
        frames_manifest = run_local_shot_sequence_frames(shot_plan)
        quality_manifest = run_local_quality_gate(quality_runtime_plan, frames_manifest)
        render_manifest = render_local_shot_sequence_video(shot_plan, frames_manifest)
        failure_codes = _failure_codes(quality_manifest)
        attempt_payload = {
            "attempt": attempt,
            "failure_codes": failure_codes,
            "quality_manifest": quality_manifest,
            "render_manifest": render_manifest,
        }
        attempt_results.append(attempt_payload)
        final_quality_manifest = quality_manifest
        final_render_manifest = render_manifest
        final_frames_manifest = frames_manifest
        final_shot_plan = shot_plan
        if not failure_codes:
            break
        current_runtime_plan = _apply_rerender_recovery(current_runtime_plan, failure_codes, attempt)

    artifact_root = Path(str(runtime_plan.get("artifact_root") or ""))
    manifest = {
        "provider": "self-hosted-local-rerender-loop",
        "project_id": str(runtime_plan.get("project_id") or ""),
        "attempt_count": len(attempt_results),
        "attempt_results": attempt_results,
        "final_quality_manifest": final_quality_manifest,
        "final_render_manifest": final_render_manifest,
        "final_frames_manifest": final_frames_manifest,
        "final_shot_plan": final_shot_plan,
    }
    if str(artifact_root):
        write_json(artifact_root / "local_rerender_loop.json", manifest)
    return manifest
