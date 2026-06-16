from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session


def build_customer_orchestrate_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.post("/customer-orchestrate/chat", response_model=contract.OrchestratorChatResponse)
    async def customer_orchestrator_chat(
        request_context: Request,
        request: contract.CustomerOrchestratorChatRequest,
        current_user=Depends(contract.get_current_user),
    ):
        stage_run_payload = None
        if request.run_id:
            stage_run_payload = contract._load_customer_stage_run_for_user(request.run_id, current_user)

        from backend.orchestrator.autonomous.surface_adapter import run_autonomous_surface_chat

        project_name = str(request.project_name or (stage_run_payload or {}).get("project_name") or "customer-product").strip() or "customer-product"
        chat_response = await run_autonomous_surface_chat(
            message=str(request.message or "").strip(),
            owner_id=str(getattr(current_user, "id", "unknown")),
            surface="marketplace",
            session_id=request.session_id,
            run_id=request.run_id,
            stage_run_id=request.run_id if str(request.run_id or "").startswith("stage_run_") else None,
            task=str(request.task or "").strip() or project_name,
            project_name=project_name,
            mode="manual_10step",
            manual_mode=True,
            conversation=list(request.conversation or []),
            context_tags=list(request.context_tags or []) + ["customer", "stage-run", "manual-10step"],
        )
        chat_response.stage_chat = contract._build_customer_stage_chat_context(stage_run_payload, request)
        chat_response.diagnostics = {
            **dict(chat_response.diagnostics or {}),
            "customer_user_id": getattr(current_user, "id", None),
            "customer_project_name": project_name,
            "stage_run_connected": bool(stage_run_payload),
        }
        return chat_response

    @router.post("/customer-orchestrate/stage-runs")
    def create_customer_orchestrate_stage_run(
        request: contract.CustomerOrchestrateRequest,
        current_user=Depends(contract.get_current_user),
    ):
        project_name = (request.project_name or "customer-product").strip() or "customer-product"
        payload = contract.initialize_stage_run(
            scope="marketplace",
            project_name=project_name,
            mode=request.mode,
            requested_by={
                "id": current_user.id,
                "email": getattr(current_user, "email", ""),
            },
            metadata={
                "task": request.task,
            },
        )
        return payload

    @router.post("/customer-orchestrate/accepted", response_model=contract.CustomerOrchestrateAcceptedResponse)
    def accept_customer_orchestrate_request(
        request: contract.CustomerOrchestrateRequest,
        current_user=Depends(contract.get_current_user),
    ):
        stage_run_payload = contract._ensure_customer_stage_run_payload(request, current_user)
        return contract.CustomerOrchestrateAcceptedResponse(
            accepted=True,
            run_id=str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
            stage_run=stage_run_payload,
            status="accepted",
            message="고객 오케스트레이터 요청을 수락했습니다. 이어지는 stream 단계에서 실제 생성과 검증을 수행합니다.",
        )

    @router.post("/customer-orchestrate/stream")
    async def stream_customer_orchestrate_result(
        request: contract.CustomerOrchestrateRequest,
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        stage_run_payload = contract._ensure_customer_stage_run_payload(request, current_user)
        contract._guard_customer_orchestrate_execution(stage_run_payload)
        effective_request = request.model_copy(
            update={
                "stage_run_id": str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
                "stage_id": str(request.stage_id or stage_run_payload.get("current_stage_id") or "ARCH-001").strip() or "ARCH-001",
            }
        )
        stage_run_id = str(effective_request.stage_run_id or "").strip()
        if not stage_run_id:
            raise HTTPException(status_code=400, detail="stage run id가 필요합니다.")
        execution_lock = contract._get_customer_orchestrate_run_lock(stage_run_id)
        if not execution_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="같은 stage run 생성이 이미 실행 중입니다.")

        contract._update_customer_stage_execution_metadata(
            stage_run_id,
            status="running",
            started_at=contract.datetime.now(contract.timezone.utc).isoformat(),
            output_dir=None,
            error_message=None,
        )
        orchestration_request = contract._build_customer_orchestrate_request(effective_request, current_user.id)

        async def _event_stream():
            stream_state: dict[str, Any] = {
                "done": False,
                "response": None,
                "error": None,
            }
            finalized = False

            def _worker() -> None:
                try:
                    stream_state["response"] = contract.asyncio.run(
                        contract._run_customer_orchestration_request(
                            orchestration_request,
                            owner_id=str(getattr(current_user, "id", "unknown")),
                        )
                    )
                except Exception as exc:  # pragma: no cover - exercised via SSE error path
                    stream_state["error"] = exc
                finally:
                    stream_state["done"] = True

            worker = contract.threading.Thread(
                target=_worker,
                name=f"customer-orchestrate-stream-{str(effective_request.stage_run_id or 'unknown')[:12]}",
                daemon=True,
            )
            worker.start()

            try:
                yield contract._build_customer_orchestrate_sse_event(
                    "accepted",
                    {
                        "run_id": effective_request.stage_run_id,
                        "stage_run": stage_run_payload,
                        "message": "고객 오케스트레이터 실행을 시작합니다.",
                    },
                )

                heartbeat_started_at = contract.time.monotonic()
                while not stream_state["done"]:
                    await contract.asyncio.sleep(1)
                    elapsed = contract.time.monotonic() - heartbeat_started_at
                    if elapsed < 5:
                        continue
                    heartbeat_started_at = contract.time.monotonic()
                    yield contract._build_customer_orchestrate_sse_event(
                        "progress",
                        {
                            "run_id": effective_request.stage_run_id,
                            "stage_id": effective_request.stage_id,
                            "status": "running",
                            "message": "고객 오케스트레이터 생성 및 검증을 계속 진행 중입니다.",
                        },
                    )

                try:
                    if stream_state["error"] is not None:
                        raise stream_state["error"]

                    response = stream_state["response"]
                    result_event_payload = contract._build_customer_orchestrate_result_payload(
                        response=response,
                        request=effective_request,
                        current_user=current_user,
                        stage_run_payload=stage_run_payload,
                    )
                    contract._persist_customer_orchestrator_completion(
                        db,
                        current_user=current_user,
                        request=effective_request,
                        result_payload=dict(result_event_payload.get("result") or {}),
                    )
                    db.commit()
                    result_payload = dict(result_event_payload.get("result") or {})
                    contract._update_customer_stage_execution_metadata(
                        stage_run_id,
                        status="completed",
                        completed_at=contract.datetime.now(contract.timezone.utc).isoformat(),
                        output_dir=result_payload.get("output_dir"),
                        error_message=None,
                    )
                    finalized = True
                    yield contract._build_customer_orchestrate_sse_event("result", result_event_payload)
                except Exception as exc:
                    if hasattr(db, "rollback"):
                        db.rollback()
                    error_message = str(exc) or "고객 오케스트레이터 실행 중 오류가 발생했습니다."
                    contract._update_customer_stage_execution_metadata(
                        stage_run_id,
                        status="failed",
                        completed_at=contract.datetime.now(contract.timezone.utc).isoformat(),
                        error_message=error_message,
                    )
                    finalized = True
                    yield contract._build_customer_orchestrate_sse_event(
                        "error",
                        contract._build_customer_orchestrate_error_payload(
                            error_message=error_message,
                            request=effective_request,
                            stage_run_payload=stage_run_payload,
                        ),
                    )
            finally:
                if not finalized:
                    if hasattr(db, "rollback"):
                        db.rollback()
                    error = stream_state.get("error")
                    error_message = (
                        str(error)
                        if error is not None
                        else "고객 오케스트레이터 스트림 연결이 완료 전에 종료되었습니다."
                    )
                    contract._update_customer_stage_execution_metadata(
                        stage_run_id,
                        status="failed",
                        completed_at=contract.datetime.now(contract.timezone.utc).isoformat(),
                        error_message=error_message,
                    )
                execution_lock.release()

        return contract.StreamingResponse(_event_stream(), media_type="text/event-stream")

    @router.get("/customer-orchestrate/stage-runs/{run_id}")
    def get_customer_orchestrate_stage_run(
        run_id: str,
        current_user=Depends(contract.get_current_user),
    ):
        return contract._load_customer_stage_run_for_user(run_id, current_user)

    @router.post("/customer-orchestrate/stage-runs/update")
    def update_customer_orchestrate_stage_run(
        payload: contract.CustomerOrchestrateStageUpdateRequest,
        current_user=Depends(contract.get_current_user),
    ):
        try:
            contract._load_customer_stage_run_for_user(payload.run_id, current_user)
            return contract.update_stage_run(
                run_id=payload.run_id,
                stage_id=payload.stage_id,
                status=payload.status,
                note=payload.note,
                manual_correction=payload.manual_correction,
                substep_checks=payload.substep_checks,
                revision_note=payload.revision_note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/customer-orchestrate/generated-programs/latest", response_model=contract.CustomerGeneratedProgramSummary)
    def get_latest_customer_generated_program_summary(
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        latest = (
            db.query(contract.models.CustomerOrchestratorCompletion)
            .filter(contract.models.CustomerOrchestratorCompletion.user_id == current_user.id)
            .order_by(contract.models.CustomerOrchestratorCompletion.created_at.desc())
            .first()
        )
        if latest is None:
            return contract.CustomerGeneratedProgramSummary()

        output_dir = str(getattr(latest, "output_dir", "") or "").strip()
        if not output_dir:
            return contract.CustomerGeneratedProgramSummary()

        output_path = contract._validate_customer_generated_output_dir(contract.Path(output_dir), current_user.id)
        validation_result_path = output_path / "docs" / "automatic_validation_result.json"
        shipping_readme_path = output_path / "docs" / "shipping_readme.md"
        payload: dict[str, Any] = {}
        if validation_result_path.exists():
            try:
                payload = contract.json.loads(validation_result_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}

        validation_engines = payload.get("validation_engines") or {}
        publish_payload = (((payload.get("completion_judge") or {}).get("packaging_audit") or {}).get("publish_payload")) if isinstance(payload.get("completion_judge"), dict) else None
        if not isinstance(publish_payload, dict):
            publish_payload = {}
        retry_queue_count = (
            db.query(contract.models.FeatureRetryQueue)
            .filter(contract.models.FeatureRetryQueue.user_id == current_user.id)
            .count()
        )
        completion_count = (
            db.query(contract.models.CustomerOrchestratorCompletion)
            .filter(contract.models.CustomerOrchestratorCompletion.user_id == current_user.id)
            .count()
        )
        log_count = (
            db.query(contract.models.FeatureExecutionLog)
            .filter(contract.models.FeatureExecutionLog.user_id == current_user.id)
            .count()
        )
        approval_history_count = (
            db.query(contract.models.FeatureExecutionLog)
            .filter(
                contract.models.FeatureExecutionLog.user_id == current_user.id,
                contract.models.FeatureExecutionLog.entity_type == "customer_orchestrator_completion",
            )
            .count()
        )
        stage_run_status = str((payload.get("stage_run") or {}).get("status") or "") or None if isinstance(payload.get("stage_run"), dict) else None
        hard_gate_failed_stages = [
            str(item)
            for item in ((((payload.get("completion_judge") or {}).get("product_readiness_hard_gate") or {}).get("failed_stages") or []))
            if str(item).strip()
        ] if isinstance(payload.get("completion_judge"), dict) else []
        runtime_score = 0
        runtime_score += 35 if str(payload.get("status") or "") != "passed" else 0
        runtime_score += 25 if not (bool(publish_payload.get("ready")) or shipping_readme_path.exists()) else 0
        runtime_score += min(20, retry_queue_count * 5)
        runtime_score += min(10, len([item for item in (((validation_engines.get("integration_test_engine") or {}).get("required_tests") or [])) if str(item).strip()]) * 2)
        runtime_score += min(10, approval_history_count * 2)
        runtime_score += min(10, len(hard_gate_failed_stages) * 3)
        if stage_run_status in {"failed", "manual_correction"}:
            runtime_score += 10
        priority_history = contract._append_customer_follow_up_history(
            history_id=f"customer:{current_user.id}:{output_path.name}",
            score=runtime_score,
        )

        return contract.CustomerGeneratedProgramSummary(
            output_dir=str(output_path),
            output_archive_path=str(payload.get("output_archive_path") or "") or None,
            delivery_gate_blocked=str(payload.get("status") or "") != "passed",
            delivery_gate_message="; ".join(list(payload.get("failed_reasons") or [])[:8]) or None,
            publish_ready=bool(publish_payload.get("ready")) or shipping_readme_path.exists(),
            publish_targets=[str(item) for item in (publish_payload.get("publish_targets") or []) if str(item).strip()],
            shipping_zip_ok=bool((validation_engines.get("shipping_zip_validation") or {}).get("ok")),
            validation_profile=str(payload.get("validation_profile") or "") or None,
            required_tests=[str(item) for item in (((validation_engines.get("integration_test_engine") or {}).get("required_tests") or [])) if str(item).strip()],
            priority_average_score=int(priority_history.get("average_score") or 0),
            priority_peak_score=int(priority_history.get("peak_score") or 0),
            priority_latest_score=int(priority_history.get("latest_score") or 0),
            priority_previous_score=priority_history.get("previous_score"),
            priority_momentum=int(priority_history.get("momentum") or 0),
            priority_cumulative_score=int(priority_history.get("cumulative_score") or 0),
            approval_history_count=approval_history_count,
            stage_run_status=stage_run_status,
            hard_gate_failed_stages=hard_gate_failed_stages,
        )

    @router.get("/customer-orchestrate/completions/my")
    def list_my_customer_orchestrate_completions(
        limit: int = 20,
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        safe_limit = max(1, min(int(limit or 20), 50))
        rows = (
            db.query(contract.models.CustomerOrchestratorCompletion)
            .filter(contract.models.CustomerOrchestratorCompletion.user_id == current_user.id)
            .order_by(contract.models.CustomerOrchestratorCompletion.created_at.desc())
            .limit(safe_limit)
            .all()
        )
        items = [
            {
                "id": int(getattr(item, "id", 0) or 0),
                "trace_id": getattr(item, "trace_id", None),
                "flow_id": getattr(item, "flow_id", None),
                "step_id": getattr(item, "step_id", None),
                "action": getattr(item, "action", None),
                "project_name": str(getattr(item, "project_name", "") or ""),
                "mode": str(getattr(item, "mode", "") or ""),
                "attempts": int(getattr(item, "attempts", 0) or 0),
                "output_dir": getattr(item, "output_dir", None),
                "postcheck_ok": getattr(item, "postcheck_ok", None),
                "gate_passed": bool(getattr(item, "gate_passed", False)),
                "override_used": bool(getattr(item, "override_used", False)),
                "created_at": getattr(item, "created_at", datetime.now()).isoformat(),
                "connection_id": contract._customer_orchestrate_connection_id(
                    getattr(item, "trace_id", None),
                    getattr(item, "flow_id", None),
                    getattr(item, "step_id", None),
                    getattr(item, "action", None),
                ),
            }
            for item in rows
        ]
        return {"items": items, "count": len(items), "limit": safe_limit}

    @router.get("/customer-orchestrate/logs/my")
    def list_my_customer_orchestrate_logs(
        limit: int = 30,
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        safe_limit = max(1, min(int(limit or 30), 100))
        rows = (
            db.query(contract.models.FeatureExecutionLog)
            .filter(contract.models.FeatureExecutionLog.user_id == current_user.id)
            .order_by(contract.models.FeatureExecutionLog.created_at.desc())
            .limit(safe_limit)
            .all()
        )
        items = [
            {
                "id": int(getattr(item, "id", 0) or 0),
                "trace_id": str(getattr(item, "trace_id", "") or ""),
                "flow_id": str(getattr(item, "flow_id", "") or ""),
                "step_id": str(getattr(item, "step_id", "") or ""),
                "action": str(getattr(item, "action", "") or ""),
                "entity_type": str(getattr(item, "entity_type", "") or ""),
                "entity_id": str(getattr(item, "entity_id", "") or ""),
                "status": str(getattr(item, "status", "") or ""),
                "message": str(getattr(item, "message", "") or ""),
                "payload_json": getattr(item, "payload_json", None),
                "created_at": getattr(item, "created_at", datetime.now()).isoformat(),
                "connection_id": contract._customer_orchestrate_connection_id(
                    getattr(item, "trace_id", None),
                    getattr(item, "flow_id", None),
                    getattr(item, "step_id", None),
                    getattr(item, "action", None),
                ),
            }
            for item in rows
        ]
        return {"items": items, "count": len(items), "limit": safe_limit}

    @router.get("/customer-orchestrate/retry-queue/my")
    def list_my_customer_orchestrate_retry_queue(
        limit: int = 30,
        db: Session = Depends(contract.get_db),
        current_user=Depends(contract.get_current_user),
    ):
        safe_limit = max(1, min(int(limit or 30), 100))
        rows = (
            db.query(contract.models.FeatureRetryQueue)
            .filter(contract.models.FeatureRetryQueue.user_id == current_user.id)
            .order_by(contract.models.FeatureRetryQueue.updated_at.desc(), contract.models.FeatureRetryQueue.created_at.desc())
            .limit(safe_limit)
            .all()
        )
        items = [
            {
                "id": int(getattr(item, "id", 0) or 0),
                "trace_id": str(getattr(item, "trace_id", "") or ""),
                "flow_id": str(getattr(item, "flow_id", "") or ""),
                "step_id": str(getattr(item, "step_id", "") or ""),
                "action": str(getattr(item, "action", "") or ""),
                "entity_type": str(getattr(item, "entity_type", "") or ""),
                "entity_id": str(getattr(item, "entity_id", "") or ""),
                "queue_name": str(getattr(item, "queue_name", "") or ""),
                "status": str(getattr(item, "status", "") or ""),
                "payload_json": getattr(item, "payload_json", None),
                "attempt_count": int(getattr(item, "attempt_count", 0) or 0),
                "max_attempts": int(getattr(item, "max_attempts", 0) or 0),
                "last_error": getattr(item, "last_error", None),
                "updated_at": getattr(item, "updated_at", None).isoformat() if getattr(item, "updated_at", None) else None,
                "created_at": getattr(item, "created_at", datetime.now()).isoformat(),
                "connection_id": contract._customer_orchestrate_connection_id(
                    getattr(item, "trace_id", None),
                    getattr(item, "flow_id", None),
                    getattr(item, "step_id", None),
                    getattr(item, "action", None),
                ),
            }
            for item in rows
        ]
        return {"items": items, "count": len(items), "limit": safe_limit}

    return router