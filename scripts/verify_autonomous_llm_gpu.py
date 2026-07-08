"""A-3-2 GPU LLM 품질 검증 — autonomous API 경로 live probe.

Usage (GPU 서버 / vLLM 8008 가동 중):
  $env:OLLAMA_BASE="http://127.0.0.1:8008/v1"
  python scripts/verify_autonomous_llm_gpu.py

의존성 (최소): httpx (+ turn_controller 경로)
HTTP TestClient / live API: fastapi, backend requirements 전체

venv에 패키지 없으면:
  pip install -r requirements.txt
  (또는 backend가 돌아가는 Python 3.13 환경 사용)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _missing_modules(*names: str) -> list[str]:
    missing: list[str] = []
    for name in names:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    return missing


def _ensure_core_deps() -> None:
    missing = _missing_modules("httpx", "pydantic")
    if missing:
        venv_python = ROOT / "venv" / "Scripts" / "python.exe"
        hint = (
            "Missing Python packages: "
            + ", ".join(missing)
            + "\nInstall (venv): .\\venv\\Scripts\\python.exe -m pip install httpx pydantic"
            + "\nFull backend: .\\venv\\Scripts\\python.exe -m pip install -r requirements.txt"
            + "\nIf venv pip is broken (Python 3.14): py -3.13 -m venv venv"
        )
        raise SystemExit(hint)


def _quality_checks(agent: str, output: str) -> list[str]:
    checks: list[str] = []
    lowered = output.lower()
    if agent == "reasoner":
        if "##" in output or "요구" in output or "api" in lowered:
            checks.append("structure_ok")
        if len(output) >= 120:
            checks.append("length_ok")
    elif agent == "planner":
        if "구현" in output or "파일" in output or "plan" in lowered:
            checks.append("structure_ok")
        if len(output) >= 120:
            checks.append("length_ok")
    elif agent == "reviewer":
        if "검토" in output or "approved" in lowered or "품질" in output:
            checks.append("structure_ok")
        if len(output) >= 80:
            checks.append("length_ok")
    return checks


async def _resolve_live_model_id(ollama_base: str) -> str | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_base.rstrip('/')}/models")
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None
    models = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(models, list) and models:
        first = models[0]
        if isinstance(first, dict) and first.get("id"):
            return str(first["id"])
    return None


async def verify_turn_controller() -> dict:
    from backend.llm.model_config import PREFERRED_VLLM_MODEL_32B_AWQ
    from backend.orchestrator.autonomous.agents.planner import PlannerAgent
    from backend.orchestrator.autonomous.agents.reviewer import ReviewerAgent
    from backend.orchestrator.autonomous.llm_setup import build_llm_call
    from backend.orchestrator.autonomous.session import AutonomousSession
    from backend.orchestrator.autonomous.turn_controller import TurnController

    ollama_base = os.getenv("OLLAMA_BASE", "http://127.0.0.1:8008/v1").strip()
    live_model = await _resolve_live_model_id(ollama_base)
    llm_call, model_routes = build_llm_call()
    llm_setup_ok = llm_call is not None
    profile_aligned = live_model == PREFERRED_VLLM_MODEL_32B_AWQ

    controller = TurnController(llm_call=llm_call)
    session = AutonomousSession.create(
        owner_id="gpu-verify",
        mode="advisory",
        project_name="gpu-a32-verify",
        validation_profile="python_fastapi",
    )
    session.model_routes = model_routes

    advisory_result = await controller.process_turn(
        "FastAPI로 간단한 헬스체크 API 만들어줘",
        session,
    )

    planner_context = controller._build_context(session, session.task or "")
    planner_context.previous_results = list(session.agent_results)

    planner_result = await PlannerAgent(llm_call=llm_call).execute(planner_context)
    session.agent_results.append(planner_result)

    review_context = controller._build_context(session, "코드 리뷰해줘")
    review_context.previous_results = list(session.agent_results)
    reviewer_result = await ReviewerAgent(llm_call=llm_call).execute(review_context)
    session.agent_results.append(reviewer_result)

    agents: dict[str, dict] = {}
    for result in session.agent_results:
        if result.agent in ("reasoner", "planner", "reviewer"):
            agents[result.agent] = {
                "status": result.status,
                "elapsed_ms": result.elapsed_ms,
                "output_preview": result.output[:240].replace("\n", " "),
                "quality_checks": _quality_checks(result.agent, result.output),
                "llm_connected_artifact": result.artifacts.get("llm_connected"),
            }

    llm_success_statuses = {"success", "needs_revision"}
    abrain_ok = all(
        agents.get(agent, {}).get("status") in llm_success_statuses
        for agent in ("reasoner", "planner", "reviewer")
    )
    passed = (
        llm_setup_ok
        and advisory_result.get("llm_connected") is True
        and advisory_result.get("intent") == "code_generation"
        and abrain_ok
        and all(agents[a].get("llm_connected_artifact") is True for a in agents)
        and all(len(agents[a].get("quality_checks") or []) >= 1 for a in agents)
    )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ollama_base": ollama_base,
        "live_model_id": live_model,
        "preferred_model_id": PREFERRED_VLLM_MODEL_32B_AWQ,
        "profile_aligned_32b_awq": profile_aligned,
        "profile_note": (
            None
            if profile_aligned
            else "vLLM에 32B AWQ 미로드 — scripts/start_vllm_rtx5090_32b.ps1 실행 권장"
        ),
        "model_routes": model_routes,
        "llm_setup_ok": llm_setup_ok,
        "advisory": {
            "llm_connected": advisory_result.get("llm_connected"),
            "intent": advisory_result.get("intent"),
            "agent_results_summary": advisory_result.get("agent_results"),
        },
        "abrain_agents": agents,
        "passed": passed,
    }


async def verify_http_testclient() -> dict:
    """FastAPI TestClient — 실 LLM, auth override (Admin 패널과 동일 API 계약)."""
    missing = _missing_modules("fastapi")
    if missing:
        return {
            "skipped": True,
            "reason": f"optional deps missing: {', '.join(missing)} (pip install -r requirements.txt)",
        }

    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import backend.orchestrator.autonomous.router as autonomous_router_module
    from backend.auth import get_current_user
    from backend.security_gates import require_llm_mutation_quota

    test_user = SimpleNamespace(id=9901, email="gpu-verify@test", is_active=True, is_admin=True)
    app = FastAPI()
    app.include_router(autonomous_router_module.router)
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_llm_mutation_quota] = lambda: test_user

    with TestClient(app) as client:
        response = client.post(
            "/api/llm/autonomous/chat",
            json={
                "message": "FastAPI로 간단한 헬스체크 API 만들어줘",
                "mode": "advisory",
            },
        )
    payload = response.json() if response.status_code == 200 else {"error": response.text[:300]}
    statuses = [item.get("status") for item in (payload.get("agent_results") or [])]
    return {
        "http_status": response.status_code,
        "llm_connected": payload.get("llm_connected"),
        "stub_statuses": sum(1 for s in statuses if s == "stub"),
        "llm_statuses": sum(1 for s in statuses if s in {"success", "needs_revision", "error"}),
        "agent_results": payload.get("agent_results"),
        "content_preview": str(payload.get("content") or "")[:200],
        "passed": (
            response.status_code == 200
            and payload.get("llm_connected") is True
            and "stub" not in statuses
            and any(s == "success" for s in statuses)
        ),
    }


def _spawn_http_testclient_probe() -> dict:
    """Run TestClient in a child process — Starlette closes the asyncio loop on exit."""
    import subprocess

    timeout_sec = int(os.getenv("ORCHESTRATOR_CHAT_TIMEOUT_SEC", "300")) + 120
    script_path = Path(__file__).resolve()
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), "--probe", "http_testclient"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return {
            "skipped": False,
            "passed": False,
            "reason": f"subprocess timeout ({timeout_sec}s)",
        }

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {
            "skipped": False,
            "passed": False,
            "reason": (proc.stderr or f"exit {proc.returncode}").strip()[:500],
        }
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "skipped": False,
            "passed": False,
            "reason": "invalid subprocess JSON",
            "stdout_tail": stdout[-500:],
            "stderr_tail": (proc.stderr or "")[-500:],
        }


def _load_project_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _resolve_verify_admin_credentials() -> tuple[str, str]:
    """VERIFY_* env first, then FIXED_ADMIN_* / secrets file (same as backend bootstrap)."""
    email = os.getenv("VERIFY_ADMIN_EMAIL", "").strip()
    password = os.getenv("VERIFY_ADMIN_PASSWORD", "").strip()
    if email and password:
        return email, password

    email = os.getenv("FIXED_ADMIN_EMAIL", "").strip()
    password = os.getenv("FIXED_ADMIN_PASSWORD", "").strip()
    if not password:
        password_file = os.getenv(
            "FIXED_ADMIN_PASSWORD_FILE",
            str(ROOT / ".runtime" / "secrets" / "fixed_admin_password.txt"),
        ).strip()
        secret_path = Path(password_file)
        if secret_path.is_file():
            file_password = secret_path.read_text(encoding="utf-8").strip()
            if file_password and file_password != "SET_VIA_ENV_ONLY":
                password = file_password

    return email, password


async def verify_http_api() -> dict:
    import httpx

    base = os.getenv("BACKEND_BASE", "http://127.0.0.1:8000").rstrip("/")
    email, password = _resolve_verify_admin_credentials()
    if not email or not password:
        password_file = Path(
            os.getenv(
                "FIXED_ADMIN_PASSWORD_FILE",
                str(ROOT / ".runtime" / "secrets" / "fixed_admin_password.txt"),
            ).strip()
        )
        if email and password_file.is_file():
            file_hint = password_file.read_text(encoding="utf-8").strip()
            if file_hint == "SET_VIA_ENV_ONLY":
                return {
                    "skipped": True,
                    "reason": (
                        "admin password not in env — set VERIFY_ADMIN_PASSWORD "
                        "or FIXED_ADMIN_PASSWORD (secrets file is SET_VIA_ENV_ONLY)"
                    ),
                }
        return {"skipped": True, "reason": "VERIFY_ADMIN_EMAIL/PASSWORD not set"}
    if email.startswith("your-") or password.startswith("your-"):
        return {
            "skipped": True,
            "reason": "placeholder credentials detected — set real admin email/password",
        }

    async with httpx.AsyncClient(base_url=base, timeout=180.0) as client:
        login = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        if login.status_code != 200:
            detail = login.text[:200]
            hint = None
            if login.status_code == 401:
                hint = (
                    "DB bcrypt hash does not match this password. "
                    "ENABLE_FIXED_ADMIN_BOOTSTRAP is off by default — "
                    "run: $env:RESET_ADMIN_PASSWORD='...'; python scripts/reset_fixed_admin_password.py"
                )
            payload = {
                "skipped": True,
                "reason": f"login HTTP {login.status_code}",
                "body": detail,
            }
            if hint:
                payload["hint"] = hint
            return payload
        token = login.json().get("access_token")
        if not token:
            return {"skipped": True, "reason": "no access_token"}

        chat = await client.post(
            "/api/llm/autonomous/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "FastAPI로 간단한 헬스체크 API 만들어줘",
                "mode": "advisory",
            },
        )
        payload = chat.json() if chat.status_code == 200 else {"error": chat.text[:300]}
        stub_count = sum(
            1 for item in (payload.get("agent_results") or [])
            if item.get("status") == "stub"
        )
        success_count = sum(
            1 for item in (payload.get("agent_results") or [])
            if item.get("status") == "success"
        )
        llm_connected = payload.get("llm_connected")
        if llm_connected is None and chat.status_code == 200:
            # Older backend builds omitted llm_connected — infer from agent statuses.
            llm_connected = stub_count == 0 and success_count >= 1
        return {
            "skipped": False,
            "http_status": chat.status_code,
            "llm_connected": llm_connected,
            "stub_agents": stub_count,
            "success_agents": success_count,
            "agent_results": payload.get("agent_results"),
            "content_preview": str(payload.get("content") or "")[:200],
            "passed": (
                chat.status_code == 200
                and llm_connected is True
                and stub_count == 0
                and success_count >= 1
            ),
            "backend_contract_note": (
                None
                if payload.get("llm_connected") is not None
                else "API response missing llm_connected — restart backend to pick up latest autonomous router"
            ),
        }


async def main() -> int:
    _ensure_core_deps()
    _load_project_env()
    os.environ.setdefault("ORCHESTRATOR_CHAT_TIMEOUT_SEC", "300")
    # Async LLM probes first — Starlette TestClient closes the event loop on exit
    # and breaks subsequent httpx/asyncio calls if run earlier in the same process.
    report = {
        "turn_controller": await verify_turn_controller(),
        "http_api": await verify_http_api(),
        "http_testclient": _spawn_http_testclient_probe(),
    }
    report["overall_passed"] = report["turn_controller"]["passed"] and (
        report["http_testclient"].get("skipped") or report["http_testclient"].get("passed")
    ) and (
        report["http_api"].get("skipped") or report["http_api"].get("passed")
    )

    out_dir = ROOT / "evidence" / "autonomous-a32-gpu-verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"A32_GPU_VERIFY_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReport saved: {out_path}")
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--probe":
        probe = sys.argv[2]
        if probe == "http_testclient":
            _ensure_core_deps()
            os.environ.setdefault("ORCHESTRATOR_CHAT_TIMEOUT_SEC", "300")
            print(json.dumps(asyncio.run(verify_http_testclient()), ensure_ascii=False))
            raise SystemExit(0)
        raise SystemExit(f"unknown probe: {probe}")
    raise SystemExit(asyncio.run(main()))
