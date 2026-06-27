import textwrap
from pathlib import Path

from backend.orchestrator.autonomous.runnable_proof import evaluate_runnable_proof


def _write_fastapi_health_app(root: Path) -> None:
    main_py = root / "main.py"
    main_py.write_text(
        textwrap.dedent(
            """
            from fastapi import FastAPI

            app = FastAPI()

            @app.get("/health")
            def health_check():
                return {"status": "ok"}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def test_runnable_proof_passes_with_compile_and_health(tmp_path: Path):
    _write_fastapi_health_app(tmp_path)
    proof = evaluate_runnable_proof(
        output_dir=str(tmp_path),
        written_files=["main.py"],
        validation_profile="python_fastapi",
        agent_results=[],
    )
    assert proof["compile_passed"] is True
    assert proof["health_route_detected"] is True
    assert proof["ok"] is True
    assert proof["proof_kind"] == "fastapi_compile_and_health"


def test_runnable_proof_fails_without_output_dir():
    proof = evaluate_runnable_proof(output_dir=None, written_files=[])
    assert proof["ok"] is False
    assert "output_dir" in proof["detail"]


def test_runnable_proof_non_fastapi_requires_validator(tmp_path: Path):
    script = tmp_path / "util.py"
    script.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    proof = evaluate_runnable_proof(
        output_dir=str(tmp_path),
        written_files=["util.py"],
        validation_profile="python_script",
        agent_results=[{"agent": "validator", "status": "success", "artifacts": {"passed": True}}],
    )
    assert proof["compile_passed"] is True
    assert proof["validator_passed"] is True
    assert proof["ok"] is True
    assert proof["proof_kind"] == "compile_and_validator"
