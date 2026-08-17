from pathlib import Path

from PIL import Image

from backend.movie_studio.generation.local_shot_sequence_runtime import (
    prepare_local_shot_sequence_plan,
    render_local_shot_sequence_video,
    run_local_shot_sequence_frames,
)
from backend.movie_studio.generation.local_gpu_runtime import prepare_local_gpu_runtime_plan
from backend.movie_studio.generation.self_hosted_generation_engine import build_self_hosted_generation_bundle


def test_prepare_local_shot_sequence_plan_creates_scene_entries(tmp_path: Path):
    reference_path = tmp_path / "identity.png"
    Image.new("RGB", (512, 512), color=(90, 90, 90)).save(reference_path)

    payload = {
        "title": "shot runtime test",
        "synopsis": "실사형 장면 시퀀스 테스트",
        "identity_references": [str(reference_path)],
        "environment_references": [str(reference_path)],
        "target_duration_seconds": 60,
        "target_fps": 8,
        "target_resolution": "1280x720",
    }
    scene_generation_requests = [
        {"scene_id": "scene-01", "sequence_id": "seq-01", "director_notes": ["opening reveal"]},
        {"scene_id": "scene-02", "sequence_id": "seq-02", "director_notes": ["hero cta"]},
    ]
    sequence_plan = [
        {"sequence_id": "seq-01", "objective": "opening reveal", "cta_required": False},
        {"sequence_id": "seq-02", "objective": "hero cta", "cta_required": True},
    ]
    generation_bundle = build_self_hosted_generation_bundle(payload, "project-local-shot-test")
    local_gpu_runtime_plan = prepare_local_gpu_runtime_plan(
        project_id="project-local-shot-test",
        payload=payload,
        scene_generation_requests=scene_generation_requests,
        self_hosted_generation_bundle=generation_bundle,
        continuity_contract=["real human continuity", "environment realism"],
        environment_contract={"location_summary": "showroom"},
        actor_identity={"display_name": "lead actor"},
    )

    plan = prepare_local_shot_sequence_plan(
        project_id="project-local-shot-test",
        payload=payload,
        sequence_plan=sequence_plan,
        scene_generation_requests=scene_generation_requests,
        local_gpu_runtime_plan=local_gpu_runtime_plan,
    )

    assert plan["provider"] == "self-hosted-local-shot-sequence-runtime"
    assert plan["scene_count"] == 2
    assert plan["expected_total_frames"] == 480
    assert plan["ready_for_execution"] is False


def test_run_local_shot_sequence_frames_and_render_video(tmp_path: Path):
    project_id = "project-local-shot-render"
    artifact_root = tmp_path / project_id
    scene_one = artifact_root / "scene-01" / "keyframe.png"
    scene_two = artifact_root / "scene-02" / "keyframe.png"
    scene_one.parent.mkdir(parents=True, exist_ok=True)
    scene_two.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 720), color=(120, 120, 120)).save(scene_one)
    Image.new("RGB", (1280, 720), color=(150, 150, 150)).save(scene_two)

    plan = {
        "provider": "self-hosted-local-shot-sequence-runtime",
        "project_id": project_id,
        "artifact_root": str(artifact_root),
        "frames_per_second": 8,
        "duration_seconds": 60,
        "expected_total_frames": 480,
        "scene_count": 2,
        "width": 1280,
        "height": 720,
        "scenes": [
            {
                "scene_id": "scene-01",
                "title": "opening reveal",
                "duration_seconds": 30,
                "frame_count": 240,
                "start_frame": 1,
                "end_frame": 240,
                "keyframe_path": str(scene_one),
                "frames_dir": str(artifact_root / "scene-01" / "frames"),
                "motion_profile": {
                    "zoom_start": 1.0,
                    "zoom_end": 1.08,
                    "pan_x_start": -0.02,
                    "pan_x_end": 0.02,
                    "pan_y_start": 0.01,
                    "pan_y_end": -0.01,
                    "roll": 0.0,
                },
                "prompt": "opening reveal",
            },
            {
                "scene_id": "scene-02",
                "title": "hero cta",
                "duration_seconds": 30,
                "frame_count": 240,
                "start_frame": 241,
                "end_frame": 480,
                "keyframe_path": str(scene_two),
                "frames_dir": str(artifact_root / "scene-02" / "frames"),
                "motion_profile": {
                    "zoom_start": 1.03,
                    "zoom_end": 1.16,
                    "pan_x_start": -0.04,
                    "pan_x_end": 0.05,
                    "pan_y_start": 0.02,
                    "pan_y_end": -0.02,
                    "roll": 0.008,
                },
                "prompt": "hero cta",
            },
        ],
    }

    frames_manifest = run_local_shot_sequence_frames(plan)
    assert frames_manifest["frame_count"] == 480
    assert Path(frames_manifest["frames"][0]["image_path"]).exists()

    render_manifest = render_local_shot_sequence_video(plan, frames_manifest)
    assert render_manifest["render_result"]["status"] == "completed"
    assert Path(render_manifest["render_result"]["output_mp4_path"]).exists()
