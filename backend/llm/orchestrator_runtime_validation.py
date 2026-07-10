"""오케스트레이터 실행-검증기 / 라이브 통합 테스트 엔진 (orchestrator.py 에서 분리).

생성 산출물을 실제로 부팅/실행해 검증한다: venv 구성·pip·compileall·pytest, FastAPI 스탠드얼론
기동 + HTTP 프로브, 도메인 통합 테스트 엔진, shipping zip 재현 검증 등(subprocess·httpx·zip I/O).
외부 의존은 표준 라이브러리뿐 — orchestrator 와 순환 import 없음.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# orchestrator.py 에서 함께 이관한 클러스터 전용 상수.
ORCH_VALIDATION_WORK_ROOT = "uploads/tmp/orchestrator_validation"


def _log_integration_validation_phase(
    phase: str,
    started_at: float,
    *,
    project_root: Path,
    validation_profile: str,
) -> None:
    logger.info(
        "integration_test_engine phase=%s elapsed_sec=%.2f project_root=%s validation_profile=%s",
        phase,
        max(0.0, time.perf_counter() - started_at),
        str(project_root),
        validation_profile,
    )


def _run_framework_e2e_validator(
    *,
    output_dir: Path,
    validation_profile: str,
) -> Dict[str, Any]:
    commands_run: List[str] = []
    failures: List[str] = []

    if validation_profile == "python_fastapi":
        compile_targets = _build_python_fastapi_validation_targets(output_dir)["compile_targets"]
        commands_run.append("python -m compileall " + " ".join(compile_targets or ["app", "backend", "tests"]))
        try:
            if not compile_targets:
                failures.append("fastapi e2e validator missing compile targets")
                return {
                    "engine": "framework-e2e-validator",
                    "validation_profile": validation_profile,
                    "commands_run": commands_run,
                    "ok": False,
                    "failures": failures,
                }
            result = subprocess.run(
                [sys.executable, "-m", "compileall", *compile_targets],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(output_dir),
            )
            if result.returncode != 0:
                failures.append((result.stderr or result.stdout or "compileall failed").strip()[:1200])
        except Exception as exc:
            failures.append(f"fastapi e2e validator error: {exc}")
    elif validation_profile == "nextjs_app":
        package_json = output_dir / "package.json"
        commands_run.append("package.json contract inspection")
        if not package_json.exists():
            failures.append("package.json not found for Next.js E2E validation")
        else:
            try:
                package_payload = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append(f"package.json parse error: {exc}")
            else:
                scripts = package_payload.get("scripts") or {}
                dependencies = package_payload.get("dependencies") or {}
                if "build" not in scripts:
                    failures.append("npm build script missing")
                if "start" not in scripts:
                    failures.append("npm start script missing")
                if "next" not in dependencies:
                    failures.append("next dependency missing")
                if "react" not in dependencies:
                    failures.append("react dependency missing")
        for rel_path in ["app/layout.tsx", "app/page.tsx", "scripts/check.sh"]:
            commands_run.append(f"exists:{rel_path}")
            if not (output_dir / rel_path).exists():
                failures.append(f"missing Next.js runtime file: {rel_path}")

    return {
        "engine": "framework-live-e2e-validator",
        "validation_profile": validation_profile,
        "commands_run": commands_run,
        "ok": len(failures) == 0,
        "failures": failures,
    }


def _run_external_integration_validator(
    *,
    output_dir: Path,
    order_profile: Dict[str, Any],
) -> Dict[str, Any]:
    profile_id = str(order_profile.get("profile_id") or "")
    checks: List[str] = []
    failures: List[str] = []
    expected_paths: List[str] = []

    if profile_id in {"commerce_platform", "trading_system", "automation_service"}:
        expected_paths.extend([
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
        ])

    if profile_id == "trading_system":
        expected_paths.append("backend/app/connectors/shopify.py")

    for rel_path in expected_paths:
        checks.append(f"exists:{rel_path}")
        if not (output_dir / rel_path).exists():
            failures.append(f"missing external integration boundary: {rel_path}")

    return {
        "engine": "external-integration-validator",
        "profile_id": profile_id,
        "checks_run": checks,
        "ok": len(failures) == 0,
        "failures": failures,
    }


def _read_validation_log_tail(log_path: Path, max_chars: int = 1600) -> str:
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    return content[-max_chars:].strip()


def _repair_python_validation_venv(project_root: Path, target_venv: Path) -> Optional[str]:
    shutil.rmtree(target_venv, ignore_errors=True)
    virtualenv_command = [sys.executable, "-m", "virtualenv", str(target_venv)]
    bootstrap_result = subprocess.run(
        virtualenv_command,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if bootstrap_result.returncode == 0:
        return None

    install_virtualenv_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "virtualenv"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if install_virtualenv_result.returncode != 0:
        return (install_virtualenv_result.stderr or install_virtualenv_result.stdout or "virtualenv bootstrap install failed").strip()[:1600]

    bootstrap_result = subprocess.run(
        virtualenv_command,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if bootstrap_result.returncode != 0:
        return (bootstrap_result.stderr or bootstrap_result.stdout or "virtualenv create failed").strip()[:1600]
    return None


def _venv_python_path(venv_path: Path) -> Path:
    return venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _build_python_fastapi_validation_targets(project_root: Path) -> Dict[str, List[str]]:
    compile_targets = [name for name in ["app", "backend", "tests", "ai"] if (project_root / name).exists()]
    app_services_init = project_root / "app" / "services" / "__init__.py"
    app_main = project_root / "app" / "main.py"
    ai_contract_enabled = False
    ai_router_enabled = False
    try:
        if app_services_init.exists():
            ai_contract_enabled = "build_ai_runtime_contract" in app_services_init.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        ai_contract_enabled = False
    try:
        if app_main.exists():
            app_main_text = app_main.read_text(encoding="utf-8", errors="ignore")
            ai_router_enabled = "from ai.router import router as ai_router" in app_main_text and "include_router(ai_router)" in app_main_text
    except Exception:
        ai_router_enabled = False
    pytest_targets = [
        test_path
        for test_path in [
            "tests/test_health.py",
            "tests/test_routes.py",
            "tests/test_runtime.py",
            "tests/test_catalog_flow.py",
            "tests/test_order_workflow.py",
            "tests/test_publish_payload.py",
            *(["tests/test_ai_pipeline.py"] if ai_contract_enabled else []),
        ]
        if (project_root / test_path).exists()
    ]
    api_paths = [api_path for api_path in ["/health", "/runtime", "/order-profile", "/report"] if (project_root / "app").exists()]
    if (project_root / "ai" / "router.py").exists() and ai_router_enabled:
        api_paths.append("/ai/health")
    return {
        "compile_targets": compile_targets,
        "pytest_targets": pytest_targets,
        "api_paths": list(dict.fromkeys(api_paths)),
    }


def _run_python_fastapi_live_api_validation(
    *,
    project_root: Path,
    venv_python: Path,
    checks_run: List[str],
    failures: List[str],
) -> None:
    live_api_started_at = time.perf_counter()
    if not (project_root / "app" / "main.py").exists():
        failures.append("standalone runtime missing app/main.py")
        _log_integration_validation_phase("standalone_boot_missing_main", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
        return

    startup_log = project_root / ".orchestrator_runtime_validation.log"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])

    command = [
        str(venv_python),
        "-m",
        "uvicorn",
        "app.main:create_application",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    _log_integration_validation_phase("standalone_boot_start", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
    checks_run.append("standalone_boot:uvicorn app.main:create_application --factory")
    log_handle = startup_log.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=str(project_root),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        boot_ready = False
        for _ in range(40):
            if process.poll() is not None:
                break
            try:
                response = httpx.get(f"{base_url}/health", timeout=5.0)
                if response.status_code < 500:
                    boot_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not boot_ready:
            failures.append(
                "standalone runtime boot failed"
                + (f": {_read_validation_log_tail(startup_log)}" if _read_validation_log_tail(startup_log) else "")
            )
            _log_integration_validation_phase("standalone_boot_failed", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
            return

        _log_integration_validation_phase("standalone_boot_ready", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")

        targets = _build_python_fastapi_validation_targets(project_root)
        with httpx.Client(timeout=10.0) as client:
            for api_path in targets["api_paths"]:
                checks_run.append(f"http_get:{api_path}")
                _log_integration_validation_phase(f"standalone_http_start:{api_path}", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
                try:
                    response = client.get(f"{base_url}{api_path}")
                except Exception as exc:
                    failures.append(f"standalone api request failed {api_path}: {exc}")
                    _log_integration_validation_phase(f"standalone_http_failed:{api_path}", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
                    continue
                if response.status_code >= 400:
                    failures.append(f"standalone api returned {response.status_code} for {api_path}")
                    _log_integration_validation_phase(f"standalone_http_status_error:{api_path}", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
                else:
                    _log_integration_validation_phase(f"standalone_http_ok:{api_path}", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()
        log_handle.close()
        _log_integration_validation_phase("standalone_boot_cleanup", live_api_started_at, project_root=project_root, validation_profile="python_fastapi")


def _run_domain_integration_test_engine(
    *,
    output_dir: Path,
    validation_profile: str,
    integration_test_plan: Dict[str, Any],
) -> Dict[str, Any]:
    engine_started_at = time.perf_counter()
    logger.info(
        "integration_test_engine entered project_root=%s validation_profile=%s required_test_count=%s",
        str(output_dir),
        validation_profile,
        len(list(integration_test_plan.get("required_tests") or [])),
    )
    required_tests = [str(item).strip() for item in (integration_test_plan.get("required_tests") or []) if str(item).strip()]
    checks_run: List[str] = []
    failures: List[str] = []

    _log_integration_validation_phase("engine_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

    for test_path in required_tests:
        checks_run.append(f"exists:{test_path}")
        if not (output_dir / test_path).exists():
            failures.append(f"missing integration test file: {test_path}")

    runtime_file_targets = [
        "README.md",
        "docs/runtime.md",
        "docs/deployment.md",
        "docs/testing.md",
        "configs/app.env.example",
        "scripts/check.sh",
        "requirements.delivery.lock.txt",
    ]
    for file_path in runtime_file_targets:
        checks_run.append(f"exists:{file_path}")
        if not (output_dir / file_path).exists():
            failures.append(f"missing runtime/package file: {file_path}")

    if validation_profile == "python_fastapi":
        requirements_lock_path = output_dir / "requirements.delivery.lock.txt"
        if not requirements_lock_path.exists():
            requirements_lock_path.write_text(
                "fastapi==0.104.1\n"
                "starlette==0.27.0\n"
                "uvicorn==0.30.6\n"
                "pytest==8.4.2\n"
                "pydantic==2.11.7\n"
                "httpx==0.27.2\n"
                "sqlalchemy==2.0.43\n"
                "python-jose==3.5.0\n"
                "prometheus-client==0.22.1\n",
                encoding="utf-8",
            )
        requirements_path = output_dir / "requirements.txt"
        checks_run.append("exists:requirements.txt")
        if not requirements_path.exists():
            failures.append("missing requirements.txt for delivery validation")
        _log_integration_validation_phase("requirements_checked", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

        venv_dir = output_dir / ".delivery-venv"
        shutil.rmtree(venv_dir, ignore_errors=True)
        checks_run.append("python -m venv .delivery-venv")
        _log_integration_validation_phase("venv_create_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        try:
            venv_create_result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(output_dir),
            )
            venv_python = _venv_python_path(venv_dir)
            if venv_create_result.returncode != 0 or not venv_python.exists():
                checks_run.append("virtualenv fallback")
                _log_integration_validation_phase("venv_create_fallback", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
                repair_error = _repair_python_validation_venv(output_dir, venv_dir)
                if repair_error:
                    failures.append(f"delivery venv create failed: {repair_error}")
                    _log_integration_validation_phase("venv_create_failed", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
                    return {
                        "engine": "automatic-domain-integration-test-engine",
                        "validation_profile": validation_profile,
                        "required_tests": required_tests,
                        "checks_run": checks_run,
                        "ok": False,
                        "failures": failures,
                    }
            _log_integration_validation_phase("venv_create_ok", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        except Exception as exc:
            failures.append(f"delivery venv create error: {exc}")
            _log_integration_validation_phase("venv_create_exception", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            return {
                "engine": "automatic-domain-integration-test-engine",
                "validation_profile": validation_profile,
                "required_tests": required_tests,
                "checks_run": checks_run,
                "ok": False,
                "failures": failures,
            }

        venv_python = _venv_python_path(venv_dir)
        checks_run.append("python -m pip install --upgrade pip")
        _log_integration_validation_phase("pip_upgrade_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        try:
            pip_upgrade_result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if pip_upgrade_result.returncode != 0:
                failures.append((pip_upgrade_result.stderr or pip_upgrade_result.stdout or "delivery pip bootstrap failed").strip()[:1600])
                _log_integration_validation_phase("pip_upgrade_failed", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            else:
                _log_integration_validation_phase("pip_upgrade_ok", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        except Exception as exc:
            failures.append(f"delivery pip bootstrap error: {exc}")
            _log_integration_validation_phase("pip_upgrade_exception", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

        checks_run.append("pip install -r requirements.delivery.lock.txt")
        _log_integration_validation_phase("pip_install_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        try:
            install_result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", "requirements.delivery.lock.txt"],
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )
            if install_result.returncode != 0:
                failures.append((install_result.stderr or install_result.stdout or "delivery pip install failed").strip()[:1600])
                _log_integration_validation_phase("pip_install_failed", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            else:
                _log_integration_validation_phase("pip_install_ok", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
        except Exception as exc:
            failures.append(f"delivery pip install error: {exc}")
            _log_integration_validation_phase("pip_install_exception", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

        targets = _build_python_fastapi_validation_targets(output_dir)
        compile_targets = targets["compile_targets"]
        if compile_targets:
            checks_run.append("python -m compileall " + " ".join(compile_targets))
            _log_integration_validation_phase("compileall_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            try:
                compile_result = subprocess.run(
                    [str(venv_python), "-m", "compileall", *compile_targets],
                    cwd=str(output_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if compile_result.returncode != 0:
                    failures.append((compile_result.stderr or compile_result.stdout or "compileall failed").strip()[:1600])
                    _log_integration_validation_phase("compileall_failed", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
                else:
                    _log_integration_validation_phase("compileall_ok", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            except Exception as exc:
                failures.append(f"compileall error: {exc}")
                _log_integration_validation_phase("compileall_exception", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

        pytest_targets = required_tests or targets["pytest_targets"]
        if pytest_targets:
            checks_run.append("pytest -q " + " ".join(pytest_targets))
            _log_integration_validation_phase("pytest_start", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            try:
                pytest_env = os.environ.copy()
                pytest_tmp = output_dir / ".pytest-tmp"
                pytest_tmp.mkdir(parents=True, exist_ok=True)
                pytest_env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
                pytest_env["TMPDIR"] = str(pytest_tmp)
                pytest_env["TMP"] = str(pytest_tmp)
                pytest_env["TEMP"] = str(pytest_tmp)
                pytest_command = [str(venv_python), "-m", "pytest", "-q", "-s", *pytest_targets]
                pytest_result = subprocess.run(
                    pytest_command,
                    cwd=str(output_dir),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=pytest_env,
                )
                if pytest_result.returncode != 0:
                    failures.append((((pytest_result.stdout or "") + "\n" + (pytest_result.stderr or "")).strip() or "pytest failed")[:2000])
                    _log_integration_validation_phase("pytest_failed", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
                else:
                    _log_integration_validation_phase("pytest_ok", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            except Exception as exc:
                failures.append(f"pytest error: {exc}")
                _log_integration_validation_phase("pytest_exception", engine_started_at, project_root=output_dir, validation_profile=validation_profile)

        if not failures:
            _log_integration_validation_phase("standalone_boot_dispatch", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
            _run_python_fastapi_live_api_validation(
                project_root=output_dir,
                venv_python=venv_python,
                checks_run=checks_run,
                failures=failures,
            )
            _log_integration_validation_phase("standalone_boot_returned", engine_started_at, project_root=output_dir, validation_profile=validation_profile)
    elif validation_profile == "nextjs_app":
        package_json = output_dir / "package.json"
        app_page = output_dir / "app" / "page.tsx"
        layout_file = output_dir / "app" / "layout.tsx"
        checks_run.extend(["exists:package.json", "exists:app/page.tsx"])
        if not package_json.exists():
            failures.append("missing Next.js package.json")
        if not app_page.exists():
            failures.append("missing Next.js app/page.tsx")
        checks_run.append("exists:app/layout.tsx")
        if not layout_file.exists():
            failures.append("missing Next.js app/layout.tsx")
        if package_json.exists():
            try:
                package_payload = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append(f"package.json parse error: {exc}")
            else:
                dependencies = package_payload.get("dependencies") or {}
                if "next" not in dependencies:
                    failures.append("package.json missing next dependency")
                if "react" not in dependencies:
                    failures.append("package.json missing react dependency")
                if "build" not in (package_payload.get("scripts") or {}):
                    failures.append("package.json missing build script")
        checks_run.append("npm-build-contract-ready")

    result = {
        "engine": "automatic-domain-integration-test-engine",
        "validation_profile": validation_profile,
        "required_tests": required_tests,
        "checks_run": checks_run,
        "ok": len(failures) == 0,
        "failures": failures,
    }
    logger.info(
        "integration_test_engine exiting elapsed_sec=%.2f project_root=%s validation_profile=%s ok=%s failure_count=%s",
        max(0.0, time.perf_counter() - engine_started_at),
        str(output_dir),
        validation_profile,
        bool(result.get("ok")),
        len(list(result.get("failures") or [])),
    )
    return result


def _run_shipping_zip_reproduction_validation(
    *,
    output_dir: Path,
    archive_path: Path,
    validation_profile: str,
    integration_test_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    work_root = Path(ORCH_VALIDATION_WORK_ROOT).resolve()
    failures: List[str] = []
    checks_run: List[str] = []
    extracted_root = work_root / f"zip_repro_{hashlib.sha256(str(archive_path).encode('utf-8', errors='ignore')).hexdigest()[:12]}"

    if not archive_path.exists():
        return {
            "engine": "shipping-zip-reproduction-validator",
            "validation_profile": validation_profile,
            "ok": False,
            "checks_run": ["archive_exists"],
            "failures": [f"shipment archive not found: {archive_path}"],
            "extracted_root": str(extracted_root),
        }

    shutil.rmtree(extracted_root, ignore_errors=True)
    extracted_root.mkdir(parents=True, exist_ok=True)
    checks_run.append("extract_zip")
    try:
        with zipfile.ZipFile(archive_path, mode="r") as zf:
            zf.extractall(extracted_root)
    except Exception as exc:
        failures.append(f"zip extraction failed: {exc}")
        return {
            "engine": "shipping-zip-reproduction-validator",
            "validation_profile": validation_profile,
            "ok": False,
            "checks_run": checks_run,
            "failures": failures,
            "extracted_root": str(extracted_root),
        }

    if validation_profile == "python_fastapi":
        requirements_lock_path = extracted_root / "requirements.delivery.lock.txt"
        requirements_path = extracted_root / "requirements.txt"
        install_requirements_path = requirements_lock_path if requirements_lock_path.exists() else requirements_path
        checks_run.append(f"exists:{install_requirements_path.name}")
        if not install_requirements_path.exists():
            failures.append("zip reproduction missing requirements file")
        cache_basis = install_requirements_path.read_text(encoding="utf-8", errors="ignore") if install_requirements_path.exists() else ""
        cache_key = hashlib.sha256((cache_basis + sys.version).encode("utf-8", errors="ignore")).hexdigest()[:12]
        cached_venv_dir = work_root / f"zip_venv_cache_{cache_key}"
        venv_dir = cached_venv_dir if cache_basis else extracted_root / ".zip-venv"
        venv_python = _venv_python_path(venv_dir)
        if venv_python.exists():
            checks_run.append(f"reuse cached zip validation venv:{venv_dir.name}")
        else:
            checks_run.append(f"python -m venv {venv_dir.name}")
            try:
                venv_create_result = subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_dir)],
                    cwd=str(work_root if venv_dir == cached_venv_dir else extracted_root),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                venv_python = _venv_python_path(venv_dir)
                if venv_create_result.returncode != 0 or not venv_python.exists():
                    checks_run.append("virtualenv fallback")
                    repair_error = _repair_python_validation_venv(work_root if venv_dir == cached_venv_dir else extracted_root, venv_dir)
                    if repair_error:
                        failures.append(f"zip reproduction venv create failed: {repair_error}")
                        return {
                            "engine": "shipping-zip-reproduction-validator",
                            "validation_profile": validation_profile,
                            "ok": False,
                            "checks_run": checks_run,
                            "failures": failures,
                            "extracted_root": str(extracted_root),
                        }
            except Exception as exc:
                failures.append(f"zip reproduction venv create failed: {exc}")
                return {
                    "engine": "shipping-zip-reproduction-validator",
                    "validation_profile": validation_profile,
                    "ok": False,
                    "checks_run": checks_run,
                    "failures": failures,
                    "extracted_root": str(extracted_root),
                }

            checks_run.append("python -m ensurepip --upgrade")
            try:
                ensurepip_result = subprocess.run(
                    [str(venv_python), "-m", "ensurepip", "--upgrade"],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                ensurepip_output = (ensurepip_result.stderr or ensurepip_result.stdout or "").strip()
                if ensurepip_result.returncode != 0 and "No module named ensurepip" not in ensurepip_output:
                    failures.append(ensurepip_output[:1600] or "zip reproduction ensurepip failed")
            except Exception as exc:
                failures.append(f"zip reproduction ensurepip error: {exc}")

            checks_run.append("python -m pip install --upgrade pip")
            try:
                pip_upgrade_result = subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if pip_upgrade_result.returncode != 0:
                    failures.append((pip_upgrade_result.stderr or pip_upgrade_result.stdout or "zip reproduction pip bootstrap failed").strip()[:1600])
            except Exception as exc:
                failures.append(f"zip reproduction pip bootstrap error: {exc}")

            checks_run.append(f"pip install -r {install_requirements_path.name}")
            try:
                install_result = subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "-r", install_requirements_path.name],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if install_result.returncode != 0:
                    failures.append((install_result.stderr or install_result.stdout or "zip reproduction pip install failed").strip()[:1600])
            except Exception as exc:
                failures.append(f"zip reproduction pip install error: {exc}")

        compile_targets = _build_python_fastapi_validation_targets(extracted_root)["compile_targets"]
        checks_run.append("python -m compileall " + " ".join(compile_targets or ["app", "backend", "tests"]))
        try:
            compile_result = subprocess.run(
                [str(venv_python), "-m", "compileall", *(compile_targets or ["app", "backend", "tests"])],
                cwd=str(extracted_root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if compile_result.returncode != 0:
                failures.append((compile_result.stderr or compile_result.stdout or "zip reproduction compileall failed").strip()[:1600])
        except Exception as exc:
            failures.append(f"zip reproduction compileall error: {exc}")

        planned_pytest_targets = [
            str(item).strip()
            for item in ((integration_test_plan or {}).get("required_tests") or [])
            if str(item).strip()
        ]
        pytest_targets = planned_pytest_targets or _build_python_fastapi_validation_targets(extracted_root)["pytest_targets"]
        checks_run.append("pytest -q -s " + " ".join(pytest_targets or ["tests/test_health.py", "tests/test_routes.py", "tests/test_runtime.py"]))
        try:
            pytest_command = [str(venv_python), "-m", "pytest", "-q", "-s", *(pytest_targets or ["tests/test_health.py", "tests/test_routes.py", "tests/test_runtime.py"])]
            pytest_env = os.environ.copy()
            pytest_env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
            pytest_env.setdefault("TMPDIR", str(extracted_root / ".pytest-tmp"))
            Path(pytest_env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
            pytest_env["TMP"] = pytest_env["TMPDIR"]
            pytest_env["TEMP"] = pytest_env["TMPDIR"]
            pytest_result = subprocess.run(
                pytest_command,
                cwd=str(extracted_root),
                capture_output=True,
                text=True,
                timeout=600,
                env=pytest_env,
            )
            pytest_output = ((pytest_result.stdout or "") + "\n" + (pytest_result.stderr or "")).strip()
            if pytest_result.returncode != 0:
                failures.append((pytest_output or "zip reproduction pytest failed")[:2000])
        except Exception as exc:
            failures.append(f"zip reproduction pytest error: {exc}")

        if not failures:
            _run_python_fastapi_live_api_validation(
                project_root=extracted_root,
                venv_python=venv_python,
                checks_run=checks_run,
                failures=failures,
            )

        dockerfile_path = extracted_root / "Dockerfile"
        checks_run.append("exists:Dockerfile")
        if not dockerfile_path.exists():
            failures.append("zip reproduction missing Dockerfile")

        if shutil.which("docker"):
            image_tag = f"zip-repro-{hashlib.sha256(str(archive_path).encode('utf-8', errors='ignore')).hexdigest()[:10]}"
            checks_run.append("docker build")
            try:
                build_result = subprocess.run(
                    ["docker", "build", "-t", image_tag, "."],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    timeout=1200,
                )
                if build_result.returncode != 0:
                    failures.append((build_result.stderr or build_result.stdout or "zip reproduction docker build failed").strip()[:2000])
            except Exception as exc:
                failures.append(f"zip reproduction docker build error: {exc}")
        else:
            checks_run.append("docker unavailable in validator environment")
    else:
        checks_run.append("validation_profile_unsupported")
        failures.append(f"zip reproduction validator not implemented for profile: {validation_profile}")

    return {
        "engine": "shipping-zip-reproduction-validator",
        "validation_profile": validation_profile,
        "ok": len(failures) == 0,
        "checks_run": checks_run,
        "failures": failures,
        "extracted_root": str(extracted_root),
        "archive_path": str(archive_path),
    }
