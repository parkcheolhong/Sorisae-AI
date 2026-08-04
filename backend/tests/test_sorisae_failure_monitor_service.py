from __future__ import annotations

import json
import os
from pathlib import Path

import backend.admin.sorisae_failure_monitor_service as service


def _write_monitor_artifact(
    root: Path,
    name: str,
    *,
    classification: str | None,
    mtime: int,
    result_file_name: str = "smoke_result.json",
    summary_file_name: str = "smoke_summary.txt",
    summary_text: str | None = None,
) -> Path:
    out_dir = root / name
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / result_file_name
    result_path.write_text(
        json.dumps(
            {
                "startedAt": "2026-07-05T00:00:00Z",
                "outDir": str(out_dir),
                "apiFail": 0,
                "uiFail": 0,
                **({"classification": classification} if classification is not None else {}),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if summary_text is None:
        summary_lines = [f"{key}={value}" for key, value in (("classification", classification),) if value is not None]
        if summary_lines:
            summary_text = "\n".join(summary_lines) + "\n"
    if summary_text is not None:
        (out_dir / summary_file_name).write_text(summary_text, encoding="utf-8")
    os.utime(out_dir, (mtime, mtime))
    os.utime(result_path, (mtime, mtime))
    return result_path


def test_get_latest_status_reports_default_monitor_roots_when_empty(
    monkeypatch,
    tmp_path,
):
    repo_root = tmp_path / "repo"
    (repo_root / "backend" / "tmp").mkdir(parents=True)
    (repo_root / "scripts").mkdir(parents=True)
    monkeypatch.delenv("SORISAE_FAILURE_MONITOR_ROOT", raising=False)
    monkeypatch.setattr(service, "_repo_root", lambda: repo_root)

    status = service.get_latest_sorisae_failure_status()

    assert status["status"] == "unknown"
    assert status["classification"] == "unknown"
    assert status["monitor_root"] == str(
        (repo_root / "backend" / "tmp").resolve()
    )
    assert status["monitor_roots"] == [
        str((repo_root / "backend" / "tmp").resolve()),
        str((repo_root / "scripts").resolve()),
    ]


def test_get_latest_status_selects_newest_artifact_across_default_roots(
    monkeypatch,
    tmp_path,
):
    repo_root = tmp_path / "repo"
    backend_tmp = repo_root / "backend" / "tmp"
    scripts_root = repo_root / "scripts"
    backend_tmp.mkdir(parents=True)
    scripts_root.mkdir(parents=True)
    monkeypatch.delenv("SORISAE_FAILURE_MONITOR_ROOT", raising=False)
    monkeypatch.setattr(service, "_repo_root", lambda: repo_root)

    older_result = _write_monitor_artifact(
        backend_tmp,
        "ui_api_failure_split_older",
        classification="ALL_PASS",
        mtime=1_700_000_000,
    )
    newer_result = _write_monitor_artifact(
        scripts_root,
        "ui_api_failure_split_newer",
        classification="UI_ONLY_FAILURE",
        mtime=1_700_000_100,
    )

    status = service.get_latest_sorisae_failure_status()

    assert older_result.exists()
    assert status["classification"] == "UI_ONLY_FAILURE"
    assert status["status"] == "critical"
    assert status["result_json_path"] == str(newer_result.resolve())
    assert status["out_dir"] == str(newer_result.parent.resolve())
    assert status["monitor_root"] == str(backend_tmp.resolve())
    assert status["monitor_roots"] == [
        str(backend_tmp.resolve()),
        str(scripts_root.resolve()),
    ]


def test_get_latest_status_uses_configured_root_only(monkeypatch, tmp_path):
    configured_root = tmp_path / "configured"
    other_root = tmp_path / "other"
    configured_root.mkdir(parents=True)
    other_root.mkdir(parents=True)
    selected_result = _write_monitor_artifact(
        configured_root,
        "ui_api_failure_split_selected",
        classification="ALL_PASS",
        mtime=1_700_000_010,
    )
    _write_monitor_artifact(
        other_root,
        "ui_api_failure_split_ignored",
        classification="BOTH_FAIL",
        mtime=1_700_000_999,
    )
    monkeypatch.setenv("SORISAE_FAILURE_MONITOR_ROOT", str(configured_root))

    status = service.get_latest_sorisae_failure_status()

    assert status["classification"] == "ALL_PASS"
    assert status["status"] == "ok"
    assert status["result_json_path"] == str(selected_result.resolve())
    assert status["monitor_root"] == str(configured_root.resolve())
    assert status["monitor_roots"] == [str(configured_root.resolve())]


def test_get_latest_status_accepts_rebuilt_ui_report_format(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    scripts_root = repo_root / "scripts"
    scripts_root.mkdir(parents=True)
    monkeypatch.delenv("SORISAE_FAILURE_MONITOR_ROOT", raising=False)
    monkeypatch.setattr(service, "_repo_root", lambda: repo_root)

    report_path = _write_monitor_artifact(
        scripts_root,
        "ui_api_failure_split_rebuilt",
        mtime=1_700_000_200,
        result_file_name="ui_smoke_report.json",
        summary_file_name="ui_smoke_summary.txt",
        classification=None,
        summary_text=(
            "out_dir=scripts/ui_api_failure_split_rebuilt\n"
            "ui_total=3\n"
            "ui_ok=3\n"
            "ui_fail=0\n"
            "ui_console_errors=0\n"
            "ui_page_errors=0\n"
            "ui_request_failed=0\n"
            "ui_request_failed_ignored=27\n"
            "ui_api_http_errors=0\n"
            "ui_report=scripts\\ui_api_failure_split_rebuilt\\ui_smoke_report.json\n"
        ),
    )

    status = service.get_latest_sorisae_failure_status()

    assert status["classification"] == "ALL_PASS"
    assert status["status"] == "ok"
    assert status["result_json_path"] == str(report_path.resolve())
    assert status["summary_path"] == str((report_path.parent / "ui_smoke_summary.txt").resolve())
