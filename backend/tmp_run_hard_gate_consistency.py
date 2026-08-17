import asyncio
import json
from datetime import datetime
from pathlib import Path

from backend.llm.orchestrator import OrchestrationRequest, execute_orchestration
from backend.tmp_hard_gate_paths import (
    hard_gate_progress_path,
    hard_gate_target_dir,
    hard_gate_temp_root,
)


LOG_PATH = hard_gate_progress_path()


def _write_progress(event: str, **payload: object) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        **payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main() -> None:
    output_dir = hard_gate_target_dir()
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    request = OrchestrationRequest(
        task="FastAPI 기반 운영형 샘플 서비스를 생성하고 hard gate 산출물 consistency를 확인한다. health API, docs 산출물, traceability map, output audit를 포함하라.",
        mode="code",
        project_name="hard-gate-consistency-rerun-container",
        output_base_dir=str(hard_gate_temp_root()),
        output_dir=str(output_dir),
        continue_in_place=False,
        auto_apply=True,
        run_postcheck=True,
        retry_on_postcheck_fail=True,
        forensic_on_fail=True,
        companion_mode="project",
        manual_mode=False,
    )
    _write_progress("request_created", output_dir=str(output_dir), mode=request.mode, project_name=request.project_name)

    def progress_callback(message: str, level: str = "info") -> None:
        _write_progress("orchestration_progress", level=level, message=message)

    try:
        response = await execute_orchestration(request, progress_callback=progress_callback)
        payload = response.model_dump()
        _write_progress(
            "orchestration_completed",
            output_dir=str(payload.get("output_dir") or ""),
            completion_gate_ok=payload.get("completion_gate_ok"),
            archive_path=payload.get("archive_path"),
            written_files_count=len(list(payload.get("written_files") or [])),
        )
        print(json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        _write_progress("orchestration_failed", error_type=type(exc).__name__, error=str(exc))
        raise


if __name__ == "__main__":
    asyncio.run(main())
