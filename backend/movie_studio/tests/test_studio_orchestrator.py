from pathlib import Path

from backend.movie_studio.orchestration.studio_orchestrator import build_movie_studio_project, execute_movie_studio_project


def test_build_movie_studio_project_generates_photoreal_contract_bundle():
    result = build_movie_studio_project(
        {
            "title": "photoreal studio pilot",
            "synopsis": "현실적인 인간 형상과 건물 배경을 유지한 실사형 광고 영화 프로젝트",
            "species": "human",
            "environment_type": "architecture",
            "sequence_beats": [
                {"objective": "opening reveal", "emotional_state": "controlled confidence", "blocking_summary": "lead actor reveals the product", "cta_required": False},
                {"objective": "hero cta", "emotional_state": "conversion intent", "blocking_summary": "lead actor closes with CTA motion", "cta_required": True},
            ],
            "hero_props": ["hero product"],
            "wardrobe": ["dark tailored suit"],
            "target_duration_seconds": 60,
            "target_fps": 24,
            "target_resolution": "1920x1080",
        }
    )

    assert result["project_id"]
    assert result["director_output"]["theme"]["realism_level"] == "photoreal"
    assert len(result["sequence_plan"]) == 2
    assert len(result["shot_plan"]) == 2
    assert result["sovereign_pipeline_contract"]["external_dependency_allowed"] is False
    assert result["internal_runtime_policy"]["runtime_mode"] == "self-hosted-commercial-staged-engine"
    assert result["self_hosted_generation_bundle"]["provider"] == "self-hosted-movie-studio"
    assert result["self_hosted_generation_bundle"]["external_dependency_allowed"] is False
    assert result["self_hosted_generation_bundle"]["foundation_backend"]["runtime_mode"] == "commercial-staged-foundation-generation"
    assert result["self_hosted_generation_bundle"]["foundation_backend"]["shape_preservation_required"] is True
    assert result["local_gpu_runtime_plan"]["provider"] == "self-hosted-local-gpu-runtime"
    assert result["local_gpu_runtime_plan"]["task_count"] == 12
    assert result["local_shot_sequence_plan"]["provider"] == "self-hosted-local-shot-sequence-runtime"
    assert result["local_shot_sequence_plan"]["scene_count"] == 12
    assert result["local_quality_runtime_plan"]["provider"] == "self-hosted-local-quality-runtime"
    assert result["local_quality_runtime_plan"]["scene_count"] == 12
    assert result["actor_identity"]["species"] == "human"
    assert result["environment_contract"]["environment_type"] == "architecture"
    assert result["quality_result"]["rerender_required"] is True
    assert result["self_hosted_quality_requirements"]["external_dependency_allowed"] is False
    assert result["editorial_timeline"]["items"]


def test_execute_movie_studio_project_runs_render_and_quality(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "movie.mp4"
    output_path.write_bytes(b"movie")

    def fake_frames(plan):
        return {
            "provider": "self-hosted-local-shot-sequence-runtime",
            "project_id": plan["project_id"],
            "frame_count": 480,
            "quality_gate_failed": False,
            "frames": [],
        }

    def fake_render(plan, frames_manifest):
        return {
            "render_result": {
                "status": "completed",
                "output_mp4_path": str(output_path),
                "error_message": None,
            }
        }

    def fake_quality(plan, frames_manifest):
        return {
            "quality_result": {
                "passed": True,
                "score": 100.0,
                "rerender_required": False,
                "failures": [],
            }
        }

    monkeypatch.setattr("backend.movie_studio.orchestration.studio_orchestrator.run_local_shot_sequence_frames", fake_frames)
    monkeypatch.setattr("backend.movie_studio.orchestration.studio_orchestrator.render_local_shot_sequence_video", fake_render)
    monkeypatch.setattr("backend.movie_studio.orchestration.studio_orchestrator.run_local_quality_gate", fake_quality)

    result = execute_movie_studio_project(
        {
            "title": "movie studio execution",
            "synopsis": "실사형 장면 흐름을 실제 렌더 경로까지 연결한다",
            "sequence_beats": [
                {"objective": "opening reveal", "emotional_state": "controlled confidence", "blocking_summary": "lead actor reveals the product", "cta_required": False},
                {"objective": "hero cta", "emotional_state": "conversion intent", "blocking_summary": "lead actor closes with CTA motion", "cta_required": True},
            ],
        }
    )

    assert result["frames_manifest"]["frame_count"] == 480
    assert result["render_manifest"]["render_result"]["status"] == "completed"
    assert result["quality_result"]["passed"] is True
    assert result["output_mp4_path"] == str(output_path)
