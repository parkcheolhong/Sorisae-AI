from pathlib import Path

from PIL import Image

import backend.movie_studio.orchestration.local_rerender_loop as local_rerender_loop

from backend.movie_studio.orchestration.local_rerender_loop import run_local_quality_rerender_loop


def test_run_local_quality_rerender_loop_records_attempts(tmp_path: Path):
    artifact_root = tmp_path / "rerender-runtime"
    scene_dir = artifact_root / "scene-01"
    scene_dir.mkdir(parents=True, exist_ok=True)
    reference_image = artifact_root / "reference.png"
    keyframe_path = scene_dir / "keyframe.png"
    Image.new("RGB", (640, 360), color=(100, 100, 100)).save(reference_image)
    Image.new("RGB", (640, 360), color=(110, 110, 110)).save(keyframe_path)

    runtime_plan = {
        "project_id": "rerender-project",
        "artifact_root": str(artifact_root),
        "tasks": [
            {
                "scene_id": "scene-01",
                "prompt": "photoreal actor in showroom",
                "negative_prompt": "cartoon, deformed hands",
                "output_image_path": str(scene_dir / "keyframe.png"),
                "reference_image_path": str(reference_image),
                "width": 640,
                "height": 360,
                "steps": 6,
                "guidance_scale": 5.0,
                "strength": 0.35,
                "image_model_key": "sdxl-turbo",
            }
        ],
    }
    sequence_plan = [{"sequence_id": "seq-01", "objective": "hero cta", "cta_required": True}]
    scene_generation_requests = [{"scene_id": "scene-01", "sequence_id": "seq-01", "director_notes": ["hero cta"]}]
    quality_runtime_plan = {
        "project_id": "rerender-project",
        "artifact_root": str(artifact_root),
        "scenes": [
            {
                "scene_id": "scene-01",
                "keyframe_path": str(scene_dir / "keyframe.png"),
                "frame_start": 1,
                "frame_end": 8,
                "cta_required": True,
            }
        ],
    }
    shot_sequence_plan = {
        "frames_per_second": 4,
        "duration_seconds": 2,
        "resolution": "640x360",
    }

    local_rerender_loop.run_local_gpu_storyboard_keyframes = lambda runtime_plan: {
        "provider": "self-hosted-local-gpu-runtime",
        "project_id": runtime_plan["project_id"],
        "result_count": 1,
        "results": [
            {
                "scene_id": "scene-01",
                "generation_mode": "img2img",
                "output_image_path": str(keyframe_path),
                "model_used": "sdxl-turbo",
                "seed": 1,
                "generation_time": 0.1,
            }
        ],
    }

    manifest = run_local_quality_rerender_loop(
        runtime_plan=runtime_plan,
        sequence_plan=sequence_plan,
        scene_generation_requests=scene_generation_requests,
        quality_runtime_plan=quality_runtime_plan,
        shot_sequence_plan=shot_sequence_plan,
        max_attempts=1,
    )

    assert manifest["provider"] == "self-hosted-local-rerender-loop"
    assert manifest["attempt_count"] == 1
    assert manifest["final_render_manifest"]["render_result"]["status"] == "completed"
    assert Path(artifact_root / "local_rerender_loop.json").exists()
