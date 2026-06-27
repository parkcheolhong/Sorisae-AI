"""11단계 오케스트레이터 로컬 프로브 — 단계별 명령 실행 + 로그 JSON 저장.

Usage:
  # stub (LLM 없음, 구조·라우팅 검증, ~1분)
  python scripts/run_11stage_orchestrator_probe.py --mode stub

  # live TurnController + vLLM (GPU 서버)
  $env:OLLAMA_BASE="http://127.0.0.1:8008/v1"
  python scripts/run_11stage_orchestrator_probe.py --mode live

  # Docker backend — Admin UI /admin/llm (API: /api/llm/orchestrate/chat)
  # 백엔드 SSOT 포트: 8000 (devanalysis114-backend). 대체 포트(8001 등) 사용하지 않음.
  docker restart devanalysis114-backend
  python scripts/run_11stage_orchestrator_probe.py --mode http --admin

  # Docker backend — Marketplace /marketplace/orchestrator
  python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace `
    --email you@example.com --password your-password

  # 환경변수 / JWT
  $env:PROBE_LOGIN_EMAIL="you@example.com"
  $env:PROBE_LOGIN_PASSWORD="your-password"
  python scripts/run_11stage_orchestrator_probe.py --mode http --marketplace
  python scripts/run_11stage_orchestrator_probe.py --mode http --admin --token YOUR_JWT

출력: evidence/orchestrator-11stage-probe-<timestamp>/report.json + probe.log
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestrator.autonomous.stage_definitions import (  # noqa: E402
    STAGE_DEFINITIONS,
    STAGE_NUMBER_BY_INDEX,
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _build_command_sequence() -> List[Dict[str, str]]:
    """단계별 자연어 명령 시퀀스 — init은 task만 등록, 설계는 design-1."""
    commands: List[Dict[str, str]] = [
        {"step": "register-task", "message": "FastAPI 헬스체크 API 만들어줘"},
        {"step": "design-1", "message": "설계해줘"},
        {"step": "execute-1", "message": "진행해"},
    ]
    for index in range(1, len(STAGE_DEFINITIONS)):
        number = STAGE_NUMBER_BY_INDEX[index]
        commands.append(
            {
                "step": f"execute-{number:g}",
                "message": f"{number:g}단계 진행해줘",
            }
        )
        if index == 3:  # 4단계 후 협업 Q&A 샘플
            commands.append(
                {
                    "step": "discuss-4",
                    "message": "4단계 Redis 캐시 아이디어 제안해줘",
                }
            )
    return commands


def _stage_status_snapshot(session: Any) -> List[Dict[str, Any]]:
    return [
        {
            "id": s.stage_id,
            "label": s.stage_label,
            "status": s.status,
        }
        for s in (getattr(session, "stages", None) or [])
    ]


def _arch_stage_status(synced: Optional[Dict[str, Any]], arch_id: str) -> Optional[str]:
    if not synced:
        return None
    for stage in synced.get("stages") or []:
        if str(stage.get("id") or "").upper() == arch_id.upper():
            return str(stage.get("status") or "")
    return None


def _validate_discuss4_stub_turn(
    turn_record: Dict[str, Any],
    session: Any,
    errors: List[str],
) -> Dict[str, Any]:
    """G-4-3: discuss-4 턴에서 autonomous intent·active_stage_number=4 고정."""
    extra = getattr(session, "extra", None) or {}
    assertion: Dict[str, Any] = {
        "step": "discuss-4",
        "mode": "stub",
        "intent": turn_record.get("intent"),
        "stage_number": turn_record.get("stage_number"),
        "active_stage_command": extra.get("active_stage_command"),
        "active_stage_number": extra.get("active_stage_number"),
        "current_stage_index": getattr(session, "current_stage_index", None),
        "ok": True,
        "issues": [],
    }
    if turn_record.get("intent") != "stage_discuss":
        msg = f"discuss-4: expected intent=stage_discuss got {turn_record.get('intent')!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    if extra.get("active_stage_command") != "discuss":
        msg = f"discuss-4: expected active_stage_command=discuss got {extra.get('active_stage_command')!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    active_number = extra.get("active_stage_number")
    if active_number != 4 and active_number != 4.0:
        msg = f"discuss-4: expected active_stage_number=4 got {active_number!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    stage_number = turn_record.get("stage_number")
    if stage_number not in (4, 4.0):
        msg = f"discuss-4: expected stage_number=4 got {stage_number!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    assertion["ok"] = not assertion["issues"]
    return assertion


def _validate_discuss4_http_turn(
    turn_record: Dict[str, Any],
    synced: Optional[Dict[str, Any]],
    errors: List[str],
) -> Dict[str, Any]:
    """G-4-3: discuss-4 턴에서 stage_run이 ARCH-004 고정 · ARCH-005 pending 유지."""
    current = turn_record.get("stage_run_current") or (synced or {}).get("current_stage_id")
    arch5_status = _arch_stage_status(synced, "ARCH-005")
    assertion: Dict[str, Any] = {
        "step": "discuss-4",
        "mode": "http",
        "autonomous_intent": turn_record.get("autonomous_intent"),
        "stage_run_current": current,
        "arch005_status": arch5_status,
        "ok": True,
        "issues": [],
    }
    if turn_record.get("autonomous_intent") != "stage_discuss":
        msg = (
            "discuss-4: expected autonomous_intent=stage_discuss "
            f"got {turn_record.get('autonomous_intent')!r}"
        )
        assertion["issues"].append(msg)
        errors.append(msg)
    if synced is None:
        assertion["skipped"] = "no stage_run (admin surface)"
        assertion["ok"] = not assertion["issues"]
        return assertion
    if str(current or "").upper() != "ARCH-004":
        msg = f"discuss-4: expected stage_run_current=ARCH-004 got {current!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    if arch5_status != "pending":
        msg = f"discuss-4: expected ARCH-005 status=pending got {arch5_status!r}"
        assertion["issues"].append(msg)
        errors.append(msg)
    assertion["ok"] = not assertion["issues"]
    return assertion


def _validate_orchestrator_core_http_turns(
    turns: List[Dict[str, Any]],
    errors: List[str],
) -> Dict[str, Any]:
    """DoD-1: manual orchestrator HTTP turns must expose autonomous_turn_controller."""
    assertion: Dict[str, Any] = {
        "step": "orchestrator-core-http",
        "ok": True,
        "issues": [],
        "checked_turns": 0,
    }
    for turn in turns:
        if turn.get("http_status") != 200:
            continue
        step = str(turn.get("step") or "")
        if step in {"register-task"}:
            continue
        core = turn.get("orchestrator_core")
        assertion["checked_turns"] += 1
        if core != "autonomous_turn_controller":
            msg = f"{step}: expected orchestrator_core=autonomous_turn_controller got {core!r}"
            assertion["issues"].append(msg)
            errors.append(msg)
    assertion["ok"] = not assertion["issues"]
    return assertion


def _verify_discuss4_stage_run_sync_inline() -> Dict[str, Any]:
    """G-4-3: stage_run_sync discuss 턴 단위 self-test (pytest와 동일 계약)."""
    from backend.orchestration_stage_service import initialize_stage_run
    from backend.orchestrator.autonomous.agents.base import AgentResult
    from backend.orchestrator.autonomous.session import AutonomousSession, StageState
    from backend.orchestrator.autonomous.stage_run_sync import sync_stage_run_from_autonomous_session
    from backend.orchestrator.autonomous.turn_controller import STAGE_DEFINITIONS

    issues: List[str] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        stage_run_dir = Path(tmp_dir) / "stage_runs"
        stage_run_dir.mkdir(parents=True, exist_ok=True)
        import backend.orchestration_stage_service as stage_service

        original_root = stage_service._STAGE_RUN_ROOT
        stage_service._STAGE_RUN_ROOT = stage_run_dir
        try:
            stage_run = initialize_stage_run(
                scope="marketplace",
                project_name="discuss4-probe",
                mode="full",
                requested_by={"id": "probe"},
            )
            run_id = stage_run["run_id"]

            session = AutonomousSession.create(owner_id="probe", mode="semi_auto")
            session.execution_state = "executing"
            session.approval_state = "none"
            session.extra = {"active_stage_command": "discuss", "active_stage_number": 4}
            session.stages = [
                StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
                for s in STAGE_DEFINITIONS
            ]
            session.stages[3].status = "in_progress"
            session.current_stage_index = 3
            session.agent_results = [
                AgentResult(agent="reasoner", status="success", output="redis idea"),
                AgentResult(agent="planner", status="success", output="plan"),
            ]

            synced = sync_stage_run_from_autonomous_session(stage_run_id=run_id, session=session)
            if synced is None:
                issues.append("discuss-4-sync: sync_stage_run_from_autonomous_session returned None")
            else:
                if synced.get("current_stage_id") != "ARCH-004":
                    issues.append(
                        f"discuss-4-sync: expected ARCH-004 got {synced.get('current_stage_id')!r}"
                    )
                arch5 = _arch_stage_status(synced, "ARCH-005")
                if arch5 != "pending":
                    issues.append(f"discuss-4-sync: expected ARCH-005 pending got {arch5!r}")
        finally:
            stage_service._STAGE_RUN_ROOT = original_root

    return {"step": "discuss-4-sync-inline", "ok": not issues, "issues": issues}


async def _run_stub_probe(task: str, out_dir: Path) -> Dict[str, Any]:
    from backend.orchestrator.autonomous.session import AutonomousSession
    from backend.orchestrator.autonomous.turn_controller import TurnController

    session_dir = out_dir / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    os.environ["AUTONOMOUS_SESSION_DIR"] = str(session_dir)

    session = AutonomousSession.create(
        owner_id="11stage-probe",
        mode="semi_auto",
        project_name="health-api-probe",
        validation_profile="python_fastapi",
    )
    session.task = task
    controller = TurnController(llm_call=None)

    turns: List[Dict[str, Any]] = []
    errors: List[str] = []
    discuss4_assertions: List[Dict[str, Any]] = []

    for item in _build_command_sequence():
        step = item["step"]
        message = item["message"]
        started = time.perf_counter()
        turn_record: Dict[str, Any] = {
            "step": step,
            "message": message,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            payload = await controller.process_turn(message, session)
            elapsed = time.perf_counter() - started
            turn_record.update(
                {
                    "elapsed_sec": round(elapsed, 3),
                    "intent": payload.get("intent"),
                    "requires_approval": payload.get("requires_approval"),
                    "execution_state": payload.get("execution_state"),
                    "approval_state": payload.get("approval_state"),
                    "current_stage": payload.get("current_stage"),
                    "stages_completed": payload.get("stages_completed"),
                    "stage_command": payload.get("stage_command"),
                    "stage_number": payload.get("stage_number"),
                    "content_preview": str(payload.get("content") or "")[:400],
                    "stage_snapshot": _stage_status_snapshot(session),
                    "agent_count": len(payload.get("agent_results") or []),
                }
            )
            if payload.get("intent") == "stage_execute" and "이전 단계" in str(payload.get("content")):
                turn_record["blocked"] = True
                errors.append(f"{step}: blocked — {payload.get('content', '')[:120]}")
            if step == "discuss-4" and not turn_record.get("error"):
                discuss4_assertions.append(
                    _validate_discuss4_stub_turn(turn_record, session, errors),
                )
        except Exception as exc:
            turn_record["error"] = str(exc)
            turn_record["traceback"] = traceback.format_exc()
            errors.append(f"{step}: {exc}")
        turns.append(turn_record)

    completed = sum(1 for s in session.stages if s.status == "completed")
    return {
        "mode": "stub",
        "session_id": session.session_id,
        "task": task,
        "stages_total": len(session.stages),
        "stages_completed": completed,
        "execution_state": session.execution_state,
        "errors": errors,
        "discuss4_assertions": discuss4_assertions,
        "turns": turns,
    }


async def _run_live_probe(task: str, out_dir: Path) -> Dict[str, Any]:
    from backend.orchestrator.autonomous.llm_setup import build_llm_call
    from backend.orchestrator.autonomous.session import AutonomousSession
    from backend.orchestrator.autonomous.turn_controller import TurnController

    session_dir = out_dir / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    os.environ["AUTONOMOUS_SESSION_DIR"] = str(session_dir)

    os.environ.setdefault("OLLAMA_BASE", "http://127.0.0.1:8008/v1")
    llm_call, model_routes = build_llm_call()
    session = AutonomousSession.create(
        owner_id="11stage-probe-live",
        mode="semi_auto",
        project_name="health-api-probe-live",
        validation_profile="python_fastapi",
    )
    session.task = task
    session.model_routes = model_routes
    controller = TurnController(llm_call=llm_call)

    turns: List[Dict[str, Any]] = []
    errors: List[str] = []
    report_path = out_dir / "report.json"

    def _flush_partial() -> None:
        partial: Dict[str, Any] = {
            "mode": "live",
            "llm_connected": llm_call is not None,
            "session_id": session.session_id,
            "output_dir": session.output_dir,
            "stages_completed": sum(1 for s in session.stages if s.status == "completed"),
            "stages_total": len(session.stages),
            "execution_state": session.execution_state,
            "errors": errors,
            "turns": turns,
            "in_progress": True,
        }
        report_path.write_text(
            json.dumps(partial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    for item in _build_command_sequence():
        step = item["step"]
        message = item["message"]
        started = time.perf_counter()
        turn_record: Dict[str, Any] = {"step": step, "message": message}
        try:
            payload = await controller.process_turn(message, session)
            elapsed = time.perf_counter() - started
            turn_record.update(
                {
                    "elapsed_sec": round(elapsed, 3),
                    "intent": payload.get("intent"),
                    "requires_approval": payload.get("requires_approval"),
                    "execution_state": payload.get("execution_state"),
                    "current_stage": payload.get("current_stage"),
                    "stages_completed": payload.get("stages_completed"),
                    "content_preview": str(payload.get("content") or "")[:600],
                    "stage_snapshot": _stage_status_snapshot(session),
                    "llm_connected": payload.get("llm_connected"),
                }
            )
        except Exception as exc:
            turn_record["error"] = str(exc)
            errors.append(f"{step}: {exc}")
        turns.append(turn_record)
        _flush_partial()

    completed = sum(1 for s in session.stages if s.status == "completed")
    return {
        "mode": "live",
        "llm_connected": llm_call is not None,
        "session_id": session.session_id,
        "output_dir": session.output_dir,
        "stages_completed": completed,
        "stages_total": len(session.stages),
        "execution_state": session.execution_state,
        "errors": errors,
        "turns": turns,
    }


async def _login_token(base_url: str, email: str, password: str) -> str:
    import httpx

    if email in {"...", "YOUR_EMAIL"} or password in {"...", "YOUR_PASSWORD"}:
        raise RuntimeError(
            "로그인 자격 증명이 placeholder입니다. "
            "실제 --email / --password 또는 PROBE_LOGIN_EMAIL / PROBE_LOGIN_PASSWORD 를 사용하세요."
        )

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code == 401:
            detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else response.text
            raise RuntimeError(
                f"로그인 실패 (401): {detail or '이메일 또는 비밀번호 불일치'}. "
                f"마켓플레이스에 가입된 계정인지 확인하세요 ({base_url}/api/auth/login)."
            )
        response.raise_for_status()
        payload = response.json()
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("login succeeded but access_token missing")
        return token


async def _create_marketplace_stage_run(base_url: str, token: str, task: str) -> str:
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post(
            "/api/marketplace/customer-orchestrate/stage-runs",
            json={
                "task": task,
                "project_name": "probe-health-api",
                "mode": "manual_10step",
            },
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id.startswith("stage_run_"):
            raise RuntimeError(f"unexpected stage run id: {run_id}")
        return run_id


async def _run_http_probe(
    task: str,
    out_dir: Path,
    *,
    base_url: str,
    token: str,
    surface: str = "admin",
) -> Dict[str, Any]:
    import httpx

    use_marketplace = surface == "marketplace"
    headers = {"Authorization": f"Bearer {token}"}
    turns: List[Dict[str, Any]] = []
    errors: List[str] = []
    session_id: Optional[str] = None
    stage_run_id: Optional[str] = None
    sync_checks: List[Dict[str, Any]] = []
    discuss4_assertions: List[Dict[str, Any]] = []
    stages_completed = 0

    chat_path = (
        "/api/marketplace/customer-orchestrate/chat"
        if use_marketplace
        else "/api/llm/orchestrate/chat"
    )
    ui_surface = (
        "/marketplace/orchestrator" if use_marketplace else "/admin/llm"
    )
    orchestrate_mode = "manual_10step" if use_marketplace else "manual_9step"

    if use_marketplace:
        try:
            stage_run_id = await _create_marketplace_stage_run(base_url, token, task)
        except Exception as exc:
            errors.append(f"stage_run_create: {exc}")

    async with httpx.AsyncClient(base_url=base_url, timeout=300.0) as client:
        for item in _build_command_sequence():
            step = item["step"]
            message = item["message"]
            body: Dict[str, Any] = {
                "task": task,
                "message": message,
                "mode": orchestrate_mode,
                "manual_mode": True,
                "multi_turn_enabled": True,
                "project_name": "probe-health-api",
            }
            if session_id:
                body["session_id"] = session_id
            if stage_run_id:
                body["run_id"] = stage_run_id

            started = time.perf_counter()
            turn_record: Dict[str, Any] = {"step": step, "message": message}
            try:
                response = await client.post(
                    chat_path,
                    json=body,
                    headers=headers,
                )
                elapsed = time.perf_counter() - started
                turn_record["elapsed_sec"] = round(elapsed, 3)
                turn_record["http_status"] = response.status_code
                if response.status_code != 200:
                    turn_record["error"] = response.text[:500]
                    errors.append(f"{step}: HTTP {response.status_code}")
                else:
                    data = response.json()
                    session_id = data.get("session_id") or session_id
                    diag = data.get("diagnostics") or {}
                    synced = diag.get("synced_stage_run")
                    turn_record.update(
                        {
                            "session_id": session_id,
                            "conversation_stage": data.get("conversation_stage"),
                            "autonomous_intent": diag.get("autonomous_intent"),
                            "stages_completed": diag.get("stages_completed"),
                            "stages_total": diag.get("stages_total"),
                            "stage_command": diag.get("stage_command"),
                            "llm_connected": diag.get("llm_connected"),
                            "orchestrator_core": diag.get("orchestrator_core"),
                            "content_preview": str(
                                (data.get("reply") or {}).get("content") or data.get("content") or ""
                            )[:600],
                            "stage_run_synced": synced is not None,
                            "stage_run_current": (synced or {}).get("current_stage_id"),
                            "synced_stages": (synced or {}).get("stages"),
                        }
                    )
                    if diag.get("stages_completed") is not None:
                        stages_completed = int(diag.get("stages_completed") or 0)
                    if synced and step.startswith("execute"):
                        sync_checks.append(
                            {
                                "step": step,
                                "current_stage_id": synced.get("current_stage_id"),
                                "passed_stages": [
                                    s.get("id")
                                    for s in (synced.get("stages") or [])
                                    if str(s.get("status") or "").lower() == "passed"
                                ],
                            }
                        )
                    if step == "discuss-4" and response.status_code == 200:
                        assertion = _validate_discuss4_http_turn(turn_record, synced, errors)
                        discuss4_assertions.append(assertion)
                        sync_checks.append(
                            {
                                "step": step,
                                "current_stage_id": synced.get("current_stage_id") if synced else None,
                                "arch005_status": assertion.get("arch005_status"),
                                "ok": assertion.get("ok"),
                            }
                        )
            except Exception as exc:
                turn_record["error"] = str(exc)
                errors.append(f"{step}: {exc}")
            turns.append(turn_record)

    core_assertion = _validate_orchestrator_core_http_turns(turns, errors)

    return {
        "mode": "http",
        "surface": surface,
        "ui_surface": ui_surface,
        "base_url": base_url,
        "chat_path": chat_path,
        "session_id": session_id,
        "stage_run_id": stage_run_id,
        "stages_completed": stages_completed,
        "stages_total": len(STAGE_DEFINITIONS),
        "sync_checks": sync_checks,
        "discuss4_assertions": discuss4_assertions,
        "orchestrator_core_assertion": core_assertion,
        "errors": errors,
        "turns": turns,
    }


def _print_summary(report: Dict[str, Any]) -> None:
    print("\n=== 11-stage probe summary ===")
    print(f"mode: {report.get('mode')}")
    if report.get("surface"):
        print(f"surface: {report.get('surface')} ({report.get('ui_surface')})")
    print(f"session_id: {report.get('session_id')}")
    if "stages_completed" in report:
        print(
            f"stages: {report.get('stages_completed')}/{report.get('stages_total')} completed"
        )
    print(f"execution_state: {report.get('execution_state')}")
    if "engineering_green" in report:
        print(f"engineering_green: {report.get('engineering_green')}")
    if "production_green" in report:
        print(f"production_green: {report.get('production_green')}")
    if "worldlinco_green" in report:
        print(f"worldlinco_green: {report.get('worldlinco_green')}")
    golden = report.get("golden_tasks") or {}
    if golden:
        for task_id, item in golden.items():
            if item.get("skipped"):
                print(f"  golden {task_id}: SKIP — {item.get('detail', '')[:120]}")
                continue
            status = "PASS" if item.get("ok") else "FAIL"
            print(f"  golden {task_id}: {status} — {item.get('detail', '')[:120]}")
            subtasks = item.get("subtasks") if isinstance(item, dict) else None
            if isinstance(subtasks, dict):
                for sub_id, sub_item in subtasks.items():
                    if sub_item.get("skipped"):
                        print(f"    · {sub_id}: SKIP — {str(sub_item.get('detail', ''))[:100]}")
                        continue
                    sub_status = "PASS" if sub_item.get("ok") else "FAIL"
                    print(f"    · {sub_id}: {sub_status} — {str(sub_item.get('detail', ''))[:100]}")
    print(f"errors: {len(report.get('errors') or [])}")
    for assertion in report.get("discuss4_assertions") or []:
        status = "PASS" if assertion.get("ok") else "FAIL"
        label = assertion.get("step") or assertion.get("mode") or "discuss-4"
        detail = assertion.get("stage_run_current") or assertion.get("current_stage_index") or ""
        if assertion.get("issues"):
            detail = "; ".join(assertion.get("issues") or [])
        print(f"  discuss4 {label}: {status} {detail}")
    core_assertion = report.get("orchestrator_core_assertion")
    if core_assertion:
        status = "PASS" if core_assertion.get("ok") else "FAIL"
        checked = core_assertion.get("checked_turns", 0)
        print(f"  orchestrator_core: {status} ({checked} http turns)")
        if core_assertion.get("issues"):
            print(f"    issues: {'; '.join(core_assertion.get('issues') or [])}")
    for turn in report.get("turns") or []:
        blocked = " [BLOCKED]" if turn.get("blocked") else ""
        err = f" [ERR: {turn.get('error')}]" if turn.get("error") else ""
        print(
            f"  {turn.get('step'):14} intent={turn.get('intent') or turn.get('autonomous_intent')} "
            f"{turn.get('elapsed_sec', '?')}s "
            f"stage={turn.get('current_stage') or '-'} "
            f"completed={turn.get('stages_completed')}{blocked}{err}"
        )


async def _run_golden_tasks(
    base_url: str,
    *,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.orchestrator.autonomous.golden_tasks import run_golden_tasks

    return await run_golden_tasks(base_url, token=token)


async def _resolve_golden_token(
    base_url: str,
    *,
    cli_token: str,
    cli_email: str,
    cli_password: str,
) -> tuple[str, Dict[str, Any]]:
    """JWT for golden G2/G3 — all probe modes (live/stub/http)."""
    token = (cli_token.strip() or os.getenv("ADMIN_JWT", "").strip())
    if token:
        return token, {"ok": True, "source": "token"}

    probe_email, probe_password = _resolve_probe_credentials("", "")
    if not probe_email or not probe_password:
        probe_email, probe_password = _resolve_probe_credentials(cli_email, cli_password)

    if not probe_email or not probe_password:
        return "", {
            "ok": False,
            "source": None,
            "detail": "no credentials (--token, ADMIN_JWT, or PROBE_LOGIN_*)",
        }

    try:
        token = await _login_token(base_url, probe_email, probe_password)
    except Exception as exc:
        return "", {
            "ok": False,
            "source": "login",
            "email": probe_email,
            "detail": str(exc)[:240],
        }

    return token, {"ok": True, "source": "login", "email": probe_email}


def _annotate_engineering_green(report: Dict[str, Any]) -> None:
    stages_total = int(report.get("stages_total") or 0)
    stages_completed = int(report.get("stages_completed") or 0)
    turn_errors = [
        turn.get("error")
        for turn in (report.get("turns") or [])
        if turn.get("error")
    ]
    report["engineering_green"] = bool(
        stages_total > 0
        and stages_completed >= stages_total
        and not turn_errors
        and not (report.get("errors") or [])
    )


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


def _resolve_probe_credentials(email: str, password: str) -> tuple[str, str]:
    """PROBE_* → VERIFY_* → FIXED_ADMIN_* → secrets file."""
    resolved_email = email.strip()
    resolved_password = password.strip()
    if resolved_email and resolved_password:
        return resolved_email, resolved_password

    _load_project_env()
    if not resolved_email:
        resolved_email = (
            os.getenv("PROBE_LOGIN_EMAIL", "").strip()
            or os.getenv("VERIFY_ADMIN_EMAIL", "").strip()
            or os.getenv("FIXED_ADMIN_EMAIL", "").strip()
        )
    if not resolved_password:
        resolved_password = (
            os.getenv("PROBE_LOGIN_PASSWORD", "").strip()
            or os.getenv("VERIFY_ADMIN_PASSWORD", "").strip()
            or os.getenv("FIXED_ADMIN_PASSWORD", "").strip()
        )
        if not resolved_password:
            password_file = Path(
                os.getenv(
                    "FIXED_ADMIN_PASSWORD_FILE",
                    str(ROOT / ".runtime" / "secrets" / "fixed_admin_password.txt"),
                ).strip()
            )
            if password_file.is_file():
                file_password = password_file.read_text(encoding="utf-8").strip()
                if file_password and file_password != "SET_VIA_ENV_ONLY":
                    resolved_password = file_password
    return resolved_email, resolved_password


async def main() -> int:
    parser = argparse.ArgumentParser(description="11단계 오케스트레이터 로컬 프로브")
    parser.add_argument(
        "--mode",
        choices=("stub", "live", "http"),
        default="stub",
        help="stub=LLM 없음, live=TurnController+LLM, http=Docker API",
    )
    parser.add_argument(
        "--task",
        default="FastAPI 헬스체크 API 만들어줘",
        help="프로젝트 태스크",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--token", default=os.getenv("ADMIN_JWT", ""))
    parser.add_argument("--email", default=os.getenv("PROBE_LOGIN_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("PROBE_LOGIN_PASSWORD", ""))
    parser.add_argument(
        "--admin",
        action="store_true",
        help="HTTP 모드: Admin /admin/llm → /api/llm/orchestrate/chat (기본 surface)",
    )
    parser.add_argument(
        "--marketplace",
        action="store_true",
        help="HTTP 모드: Marketplace /marketplace/orchestrator + stage_run 동기화 검증",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="결과 저장 디렉터리 (기본: evidence/orchestrator-11stage-probe-<ts>)",
    )
    args = parser.parse_args()

    stamp = _utc_stamp()
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "evidence" / f"orchestrator-11stage-probe-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    if args.mode == "stub":
        report = await _run_stub_probe(args.task, out_dir)
    elif args.mode == "live":
        report = await _run_live_probe(args.task, out_dir)
    else:
        if args.admin and args.marketplace:
            print("--admin 과 --marketplace 는 동시에 사용할 수 없습니다.", file=sys.stderr)
            return 2
        http_surface = "marketplace" if args.marketplace else "admin"

        token = args.token.strip()
        probe_email, probe_password = _resolve_probe_credentials(args.email, args.password)
        if not token and probe_email and probe_password:
            try:
                token = await _login_token(
                    args.base_url.rstrip("/"),
                    probe_email,
                    probe_password,
                )
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 2
        if not token:
            print(
                "HTTP 모드는 --token, ADMIN_JWT, 또는 --email/--password 가 필요합니다.",
                file=sys.stderr,
            )
            return 2
        report = await _run_http_probe(
            args.task,
            out_dir,
            base_url=args.base_url.rstrip("/"),
            token=token,
            surface=http_surface,
        )

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["total_elapsed_sec"] = round(time.perf_counter() - started, 3)
    report["out_dir"] = str(out_dir)

    if report.get("stages_total") and report.get("stages_completed", 0) < report["stages_total"]:
        incomplete = (
            f"incomplete: {report.get('stages_completed')}/{report.get('stages_total')} stages"
        )
        report.setdefault("errors", []).append(incomplete)

    _annotate_engineering_green(report)

    discuss4_inline = _verify_discuss4_stage_run_sync_inline()
    report.setdefault("discuss4_assertions", []).append(discuss4_inline)
    if not discuss4_inline.get("ok"):
        report.setdefault("errors", []).extend(discuss4_inline.get("issues") or [])

    golden_token, golden_login = await _resolve_golden_token(
        args.base_url.rstrip("/"),
        cli_token=args.token,
        cli_email=args.email,
        cli_password=args.password,
    )
    report["golden_login"] = golden_login
    if not golden_login.get("ok") and golden_login.get("detail"):
        print(f"  golden_login: SKIP — {golden_login.get('detail')[:120]}")

    try:
        golden = await _run_golden_tasks(
            args.base_url.rstrip("/"),
            token=golden_token or None,
        )
        report.update(golden)
        if args.mode == "http" and not golden.get("production_green"):
            report.setdefault("errors", []).append("golden_tasks: production_green=false")
    except Exception as exc:
        report["golden_tasks"] = {"probe_error": {"ok": False, "detail": str(exc)[:240]}}
        report["production_green"] = False
        report.setdefault("errors", []).append(f"golden_tasks probe failed: {exc}")

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_summary(report)
    print(f"\nReport: {report_path}")
    return 1 if report.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
