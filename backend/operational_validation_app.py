from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

from backend.time_utils import utcnow

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.admin_router import router as admin_router
from backend.auth import get_password_hash, verify_password
from backend.auth_router import router as auth_router
from backend.database import ensure_user_role_columns
from backend.llm.admin_capabilities import router as admin_orchestrator_router
from backend.llm.orchestrator import router as llm_orchestrator_router
from backend.marketplace.router import router as marketplace_router
from backend.marketplace.database import Base, SessionLocal, engine
from backend.marketplace.stats_router import router as marketplace_stats_router
from backend.models import User


logger = logging.getLogger(__name__)


def _bootstrap_fixed_admin_account() -> None:
    enabled = str(os.getenv("ENABLE_FIXED_ADMIN_BOOTSTRAP") or "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return

    fixed_admin_email = str(os.getenv("FIXED_ADMIN_EMAIL") or "").strip()
    fixed_admin_password = str(os.getenv("FIXED_ADMIN_PASSWORD") or "").strip()
    if not fixed_admin_email or not fixed_admin_password:
        logger.warning("[WARN] fixed admin bootstrap skipped: email/password env missing")
        return

    ensure_user_role_columns()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = db.query(User).filter((User.email == fixed_admin_email) | (User.username == fixed_admin_email)).first()
        if user is None:
            user = User(
                username=fixed_admin_email,
                email=fixed_admin_email,
                hashed_password=get_password_hash(fixed_admin_password),
                is_active=True,
                is_admin=True,
                is_superuser=True,
            )
            db.add(user)
            db.commit()
            logger.info("[OK] fixed admin account created: %s", fixed_admin_email)
            return

        updated = False
        if getattr(user, "username", None) != fixed_admin_email:
            user.username = fixed_admin_email
            updated = True
        if getattr(user, "email", None) != fixed_admin_email:
            user.email = fixed_admin_email
            updated = True
        if not getattr(user, "is_active", False):
            user.is_active = True
            updated = True
        if not getattr(user, "is_admin", False):
            user.is_admin = True
            updated = True
        if not getattr(user, "is_superuser", False):
            user.is_superuser = True
            updated = True
        hashed_password = str(getattr(user, "hashed_password", "") or "")
        if not hashed_password or not verify_password(fixed_admin_password, hashed_password):
            user.hashed_password = get_password_hash(fixed_admin_password)
            updated = True
        if updated:
            db.add(user)
            db.commit()
            logger.info("[OK] fixed admin account updated: %s", fixed_admin_email)
    finally:
        db.close()


def _bootstrap_validation_demo_data() -> None:
    enabled = str(os.getenv("ENABLE_FIXED_ADMIN_BOOTSTRAP") or "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return

    fixed_admin_email = str(os.getenv("FIXED_ADMIN_EMAIL") or "").strip()
    if not fixed_admin_email:
        return

    from backend.marketplace.models import AdVideoOrder, CustomerOrchestratorCompletion, FeatureExecutionLog, FeatureRetryQueue

    db = SessionLocal()
    try:
        user = db.query(User).filter((User.email == fixed_admin_email) | (User.username == fixed_admin_email)).first()
        if user is None:
            return

        now = utcnow()

        if db.query(CustomerOrchestratorCompletion).count() == 0:
            db.add_all([
                CustomerOrchestratorCompletion(
                    user_id=user.id,
                    trace_id="TRACE-ADM-AUTO-001",
                    flow_id="FLOW-ADM-AUTO-HOME-1",
                    step_id="STEP-VERIFY-RUNTIME",
                    action="SYNC_EVIDENCE",
                    project_name="admin-runtime-evidence-sync",
                    mode="auto",
                    attempts=1,
                    output_dir="uploads/tmp/admin-runtime-evidence-sync",
                    postcheck_ok=True,
                    gate_passed=True,
                    override_used=False,
                    created_at=now - timedelta(minutes=9),
                ),
                CustomerOrchestratorCompletion(
                    user_id=user.id,
                    trace_id="TRACE-ADM-AUTO-002",
                    flow_id="FLOW-ADM-AUTO-HOME-2",
                    step_id="STEP-REFRESH-HISTORY",
                    action="REFRESH_GRAPH",
                    project_name="admin-auto-connect-refresh",
                    mode="review",
                    attempts=2,
                    output_dir="uploads/tmp/admin-auto-connect-refresh",
                    postcheck_ok=True,
                    gate_passed=True,
                    override_used=False,
                    created_at=now - timedelta(minutes=4),
                ),
            ])

        if db.query(FeatureExecutionLog).count() == 0:
            db.add_all([
                FeatureExecutionLog(
                    user_id=user.id,
                    feature_id="admin-auto-connect",
                    status="completed",
                    trace_id="TRACE-ADM-AUTO-001",
                    flow_id="FLOW-ADM-AUTO-HOME-1",
                    step_id="STEP-VERIFY-RUNTIME",
                    action="SYNC_EVIDENCE",
                    run_id="RUN-ADM-AUTO-001",
                    prompt="runtime evidence bootstrap",
                    output_payload_json=json.dumps({"source": "validation-bootstrap", "runtime_probe": "authenticated"}, ensure_ascii=False),
                    error_message=None,
                    created_at=now - timedelta(minutes=8),
                ),
                FeatureExecutionLog(
                    user_id=user.id,
                    feature_id="admin-auto-connect",
                    status="queued",
                    trace_id="TRACE-ADM-AUTO-002",
                    flow_id="FLOW-ADM-AUTO-HOME-2",
                    step_id="STEP-REFRESH-HISTORY",
                    action="REFRESH_GRAPH",
                    run_id="RUN-ADM-AUTO-002",
                    prompt="auto-connect refresh",
                    output_payload_json=json.dumps({"source": "validation-bootstrap", "queue": "history-refresh"}, ensure_ascii=False),
                    error_message=None,
                    created_at=now - timedelta(minutes=3),
                ),
            ])

        if db.query(FeatureRetryQueue).count() == 0:
            db.add(
                FeatureRetryQueue(
                    feature_id="admin-auto-connect",
                    status="pending",
                    trace_id="TRACE-ADM-AUTO-002",
                    flow_id="FLOW-ADM-AUTO-HOME-2",
                    step_id="STEP-REFRESH-HISTORY",
                    action="REFRESH_GRAPH",
                    payload_json=json.dumps({"reason": "validation bootstrap retry seed"}, ensure_ascii=False),
                    retry_count=1,
                    created_at=now - timedelta(minutes=2),
                    updated_at=now - timedelta(minutes=1),
                )
            )

        if db.query(AdVideoOrder).count() == 0:
            db.add_all([
                AdVideoOrder(
                    public_job_id="ADM-VIDEO-001",
                    trace_id="TRACE-ADM-VIDEO-001",
                    flow_id="FLOW-ADM-VIDEO-1",
                    step_id="STEP-STORYBOARD",
                    action="GENERATE_VIDEO",
                    user_id=user.id,
                    title="운영형 샘플 광고 영상",
                    image_prompt="premium product hero shot",
                    background_prompt="clean studio background",
                    caption_text="운영 검증용 샘플 광고",
                    voice_gender="female",
                    engine_type="dedicated_engine",
                    duration_seconds=45,
                    visual_style="photorealistic",
                    render_quality="high",
                    status="completed",
                    progress_percent=100,
                    quality_score=9.1,
                    quality_gate_passed=True,
                    download_count=3,
                    created_at=now - timedelta(hours=6),
                    updated_at=now - timedelta(hours=5, minutes=45),
                ),
                AdVideoOrder(
                    public_job_id="ADM-VIDEO-002",
                    trace_id="TRACE-ADM-VIDEO-002",
                    flow_id="FLOW-ADM-VIDEO-2",
                    step_id="STEP-RENDER",
                    action="GENERATE_VIDEO",
                    user_id=user.id,
                    title="리프레시 큐 샘플 광고 영상",
                    image_prompt="dynamic lifestyle campaign",
                    background_prompt="sunrise city backdrop",
                    caption_text="자동 연결 보강 확인용",
                    voice_gender="male",
                    engine_type="express_engine",
                    duration_seconds=30,
                    visual_style="cinematic",
                    render_quality="medium",
                    status="processing",
                    progress_percent=62,
                    quality_score=7.4,
                    quality_gate_passed=False,
                    download_count=0,
                    created_at=now - timedelta(hours=2),
                    updated_at=now - timedelta(minutes=20),
                ),
            ])

        db.commit()
    finally:
        db.close()


def create_operational_validation_app() -> FastAPI:
    app = FastAPI(
        title="CodeAI Operational Validation API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3005",
            "http://localhost:3005",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(admin_router)
    app.include_router(admin_orchestrator_router)
    app.include_router(llm_orchestrator_router)
    app.include_router(marketplace_router, prefix="/api/marketplace")
    app.include_router(marketplace_stats_router, prefix="/api/marketplace")

    @app.on_event("startup")
    async def bootstrap_operational_validation_admin() -> None:
        _bootstrap_fixed_admin_account()
        _bootstrap_validation_demo_data()

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "status": "ok",
            "mode": "operational-validation",
        }

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "routes": {
                "auth": "/api/auth/login",
                "admin_runtime_verification": "/api/admin/orchestrator/runtime-verification",
                "admin_normalize": "/api/admin/workspace-self-run-record/normalize",
                "llm_orchestrator": "/api/llm/orchestrate/chat/light",
                "marketplace_catalog": "/api/marketplace/feature-catalog",
                "marketplace_stage_runs": "/api/marketplace/customer-orchestrate/stage-runs",
                "marketplace_projects": "/api/marketplace/projects",
                "marketplace_stats": "/api/marketplace/stats/overview",
            },
        }

    return app


app = create_operational_validation_app()