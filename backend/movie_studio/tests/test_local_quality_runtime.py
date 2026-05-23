from pathlib import Path

from PIL import Image

from backend.movie_studio.quality.local_quality_runtime import (
    prepare_local_quality_runtime_plan,
    run_local_quality_gate,
)


def test_prepare_local_quality_runtime_plan_creates_scene_checks(tmp_path: Path):
    keyframe = tmp_path / "scene-01" / "keyframe.png"
    keyframe.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 360), color=(120, 120, 120)).save(keyframe)

    plan = prepare_local_quality_runtime_plan(
        project_id="quality-runtime-test",
        payload={"realism_level": "photoreal"},
        local_shot_sequence_plan={
            "scenes": [
                {
                    "scene_id": "scene-01",
                    "keyframe_path": str(keyframe),
                    "start_frame": 1,
                    "end_frame": 24,
                    "cta_required": False,
                }
            ]
        },
        self_hosted_quality_requirements={
            "required_detectors": ["face-consistency-detector", "hand-anatomy-detector"],
        },
    )

    assert plan["provider"] == "self-hosted-local-quality-runtime"
    assert plan["scene_count"] == 1
    assert plan["required_detectors"]


def test_run_local_quality_gate_scores_rendered_frames(tmp_path: Path):
    artifact_root = tmp_path / "quality-artifacts"
    keyframe = artifact_root / "scene-01" / "keyframe.png"
    keyframe.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 360), color=(140, 140, 140)).save(keyframe)

    frame_paths = []
    for index in range(1, 9):
        output = artifact_root / "scene-01" / "frames" / f"frame_{index:04d}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 360), color=(140 + index, 140 + index, 140 + index)).save(output)
        frame_paths.append(output)

    plan = {
        "provider": "self-hosted-local-quality-runtime",
        "project_id": "quality-runtime-test",
        "artifact_root": str(artifact_root),
        "scenes": [
            {
                "scene_id": "scene-01",
                "keyframe_path": str(keyframe),
                "frame_start": 1,
                "frame_end": 8,
                "cta_required": True,
            }
        ],
    }
    frames_manifest = {
        "frames": [
            {"scene_id": "scene-01", "frame_index": index + 1, "image_path": str(path)}
            for index, path in enumerate(frame_paths)
        ]
    }

    result = run_local_quality_gate(plan, frames_manifest)

    assert result["provider"] == "self-hosted-local-quality-runtime"
    assert result["scene_scores"]
    assert "quality_result" in result
    assert Path(artifact_root / "quality_runtime_results.json").exists()
