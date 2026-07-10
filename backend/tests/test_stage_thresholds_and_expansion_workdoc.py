from backend.llm.admin_capabilities import (
    _build_expansion_experiment_work_document,
    _code_generator,
)
from backend.orchestrator.autonomous.stage_coder_scope import compute_autonomous_stage_thresholds


def test_compute_autonomous_stage_thresholds_stage1_baseline():
    thresholds = compute_autonomous_stage_thresholds("python_fastapi")
    assert thresholds["stage_min_files"] == 9
    assert thresholds["stage_min_dirs"] >= 3
    assert thresholds["stage11_min_files"] > thresholds["stage_min_files"]
    assert thresholds["stage11_min_dirs"] >= thresholds["stage_min_dirs"]
    assert thresholds["stage_count"] >= 10


def test_code_generator_includes_expansion_experiment_payload():
    project_scan = {
        "workspace_root": "/workspace",
        "missing_expected": [],
        "entrypoints": [{"label": "backend", "path": "backend/main.py", "exists": True}],
    }
    dependency_graph = {
        "packages": [{}, {}, {"dependencies": ["react"]}],
        "integration_points": [{"id": "api"}],
        "compose_services": [],
    }
    runtime_diagnostics = {
        "scope_label": "11단계 Autonomous probe",
        "latest_status": "probe_passed",
        "findings": [],
        "actions": [],
        "source_inspection": {
            "source_file_count": 0,
            "tiny_source_count": 0,
            "tiny_sources": [],
            "average_source_size": 0,
        },
    }
    security_guard = {
        "python_policy": {"error_count": 0, "warning_count": 0, "findings": []},
        "findings": [],
    }
    model_control = {
        "available_models": ["test-model"],
        "gpu_runtime": {"available": True},
    }

    payload = _code_generator(
        project_scan,
        dependency_graph,
        runtime_diagnostics,
        security_guard,
        model_control,
    )
    expansion = payload.get("expansion_experiment") or {}
    assert expansion.get("work_document")
    assert len(expansion.get("tower_crane_options") or []) == 3
    assert expansion.get("recommended_self_run", {}).get("execution_mode") == "full"
    assert expansion.get("recommended_self_run", {}).get("mode") == "self-expansion"


def test_build_expansion_experiment_work_document_references_stage_thresholds():
    doc = _build_expansion_experiment_work_document(
        project_scan={"workspace_root": "/w", "missing_expected": [], "entrypoints": []},
        dependency_graph={"integration_points": []},
        runtime_diagnostics={"scope_label": "probe", "latest_status": "probe_passed", "findings": []},
        security_guard={"python_policy": {"error_count": 0, "warning_count": 0, "findings": []}},
        model_control={"available_models": [], "gpu_runtime": {"available": False}},
    )
    thresholds = doc.get("stage_thresholds") or {}
    text = str(doc.get("work_document") or "")
    assert str(thresholds.get("stage_min_files")) in text
    assert str(thresholds.get("stage11_min_files")) in text
    assert "self-expansion" in text
    assert "full" in text
    assert doc.get("checklist_kpi", {}).get("checklist_path")


def test_build_expansion_experiment_includes_checklist_kpi_instruction():
    doc = _build_expansion_experiment_work_document(
        project_scan={"workspace_root": "/w", "missing_expected": [], "entrypoints": []},
        dependency_graph={"integration_points": []},
        runtime_diagnostics={"scope_label": "probe", "latest_status": "probe_passed", "findings": []},
        security_guard={"python_policy": {"error_count": 0, "warning_count": 0, "findings": []}},
        model_control={"available_models": [], "gpu_runtime": {"available": False}},
    )
    kpi = doc.get("checklist_kpi") or {}
    text = str(doc.get("work_document") or "")
    assert kpi.get("checklist_path")
    assert "Self-expansion KPI" in text
    assert str(kpi.get("kpi_instruction") or "") in text or "체크리스트" in text


def test_self_expansion_execution_mode_is_full():
    from backend.admin_router import _self_run_execution_mode, _suggested_self_mode

    assert _self_run_execution_mode("self-expansion") == "full"
    assert _suggested_self_mode("self-expansion") == "full"
    assert _self_run_execution_mode("self-diagnosis") == "review"
