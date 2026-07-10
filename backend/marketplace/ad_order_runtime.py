import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect, text

from . import models
from .database import SessionLocal, engine

logger = logging.getLogger(__name__)

_video_queue_redis_cache: Optional[Redis] = None
_video_queue_redis_cache_url: str = ""
_video_queue_redis_cache_checked_at: float = 0.0
_VIDEO_QUEUE_REDIS_CACHE_TTL_SEC = 5.0

_ad_worker_lock = threading.Lock()
_ad_enqueued_ids: set[int] = set()

VIDEO_RENDER_QUEUE_NAME = (
    os.getenv("VIDEO_RENDER_QUEUE_NAME", "video_render_queue")
    or "video_render_queue"
).strip()

_ad_worker_runtime: Dict[str, Any] = {
    "worker_id": "ad-render-worker-001",
    "connection_id": "redis:video_render_queue",
    "started_at": None,
    "last_heartbeat": None,
    "last_order_id": None,
}


def ensure_ad_video_orders_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("ad_video_orders"):
        return

    existing_columns = {col["name"] for col in inspector.get_columns("ad_video_orders")}

    column_specs = {
        "title": "VARCHAR(200)",
        "image_prompt": "TEXT",
        "portrait_image_prompt": "TEXT",
        "product_image_prompts": "TEXT",
        "storyboard_json": "TEXT",
        "storyboard_review_json": "TEXT",
        "storyboard_review_history_json": "TEXT",
        "subject_type": "VARCHAR(30)",
        "background_prompt": "TEXT",
        "caption_text": "TEXT",
        "scenario_script": "TEXT",
        "voice_gender": "VARCHAR(20)",
        "engine_type": "VARCHAR(30)",
        "action_template_key": "VARCHAR(100)",
        "motion_tempo": "VARCHAR(20)",
        "duration_seconds": "INTEGER",
        "visual_style": "VARCHAR(100)",
        "cut_count": "INTEGER",
        "subtitle_speed": "DOUBLE PRECISION",
        "render_quality": "VARCHAR(20)",
        "audio_volume": "INTEGER",
        "status": "VARCHAR(20)",
        "progress_percent": "INTEGER",
        "external_job_id": "VARCHAR(255)",
        "output_file_key": "VARCHAR(500)",
        "output_filename": "VARCHAR(255)",
        "output_video_key": "VARCHAR(500)",
        "output_video_filename": "VARCHAR(255)",
        "quality_score": "DOUBLE PRECISION",
        "quality_gate_passed": "BOOLEAN",
        "quality_feedback": "TEXT",
        "face_consistency_score": "DOUBLE PRECISION",
        "product_consistency_score": "DOUBLE PRECISION",
        "sales_quality_decision": "VARCHAR(30)",
        "quality_retry_count": "INTEGER",
        "quality_checked_at": "TIMESTAMP",
        "public_job_id": "VARCHAR(36)",
        "error_message": "TEXT",
        "download_count": "INTEGER",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    }

    with engine.begin() as conn:
        for col_name, col_type in column_specs.items():
            if col_name not in existing_columns:
                conn.execute(text(
                    f"ALTER TABLE ad_video_orders ADD COLUMN {col_name} {col_type}"
                ))
        if engine.dialect.name == "postgresql":
            conn.execute(text(
                "DO $$ BEGIN "
                "IF EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='ad_video_orders' AND column_name='product_name'"
                ") THEN "
                "ALTER TABLE ad_video_orders ALTER COLUMN product_name DROP NOT NULL; "
                "END IF; END $$"
            ))
            conn.execute(text(
                "DO $$ BEGIN "
                "IF EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='ad_video_orders' AND column_name='concept'"
                ") THEN "
                "ALTER TABLE ad_video_orders ALTER COLUMN concept DROP NOT NULL; "
                "END IF; END $$"
            ))
        conn.execute(text(
            "UPDATE ad_video_orders SET engine_type='internal_ffmpeg' WHERE engine_type IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET progress_percent=0 WHERE progress_percent IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET cut_count=12 WHERE cut_count IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET quality_gate_passed=false WHERE quality_gate_passed IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET quality_retry_count=0 WHERE quality_retry_count IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET subject_type='auto' WHERE subject_type IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET subtitle_speed=1.0 WHERE subtitle_speed IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET render_quality='high' WHERE render_quality IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET audio_volume=100 WHERE audio_volume IS NULL"
        ))
        conn.execute(text(
            "UPDATE ad_video_orders SET download_count=0 WHERE download_count IS NULL"
        ))


def _get_video_queue_redis() -> Optional[Redis]:
    global _video_queue_redis_cache
    global _video_queue_redis_cache_url
    global _video_queue_redis_cache_checked_at

    redis_url = (os.getenv("REDIS_URL", "") or "").strip()
    if not redis_url:
        _video_queue_redis_cache = None
        _video_queue_redis_cache_url = ""
        _video_queue_redis_cache_checked_at = time.time()
        return None

    now = time.time()
    if (
        _video_queue_redis_cache_url == redis_url
        and (now - _video_queue_redis_cache_checked_at) < _VIDEO_QUEUE_REDIS_CACHE_TTL_SEC
    ):
        return _video_queue_redis_cache

    try:
        client = _video_queue_redis_cache
        if client is None or _video_queue_redis_cache_url != redis_url:
            client = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
                health_check_interval=30,
            )
        client.ping()
        _video_queue_redis_cache = client
        _video_queue_redis_cache_url = redis_url
        _video_queue_redis_cache_checked_at = now
        return client
    except RedisError:
        _video_queue_redis_cache = None
        _video_queue_redis_cache_url = redis_url
        _video_queue_redis_cache_checked_at = now
        return None


def _require_video_queue_redis() -> Redis:
    client = _get_video_queue_redis()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Redis queue unavailable. video_render_queue is required by "
                "the video rendering spec."
            ),
        )
    return client


def _enqueue_ad_order(order_id: int, public_job_id: Optional[str] = None) -> bool:
    with _ad_worker_lock:
        if order_id in _ad_enqueued_ids:
            return False
        _ad_enqueued_ids.add(order_id)

    queue_item = {
        "order_id": order_id,
        "job_id": public_job_id or "",
        "status": models.AdVideoOrderStatus.PENDING.value,
        "queue": VIDEO_RENDER_QUEUE_NAME,
    }
    try:
        redis_client = _require_video_queue_redis()
        redis_client.lpush(VIDEO_RENDER_QUEUE_NAME, json.dumps(queue_item))
        return True
    except Exception:
        with _ad_worker_lock:
            _ad_enqueued_ids.discard(order_id)
        raise


def discard_enqueued_ad_order(order_id: int) -> None:
    with _ad_worker_lock:
        _ad_enqueued_ids.discard(order_id)


def _recover_interrupted_ad_orders() -> int:
    db = SessionLocal()
    try:
        rows = (
            db.query(
                models.AdVideoOrder.id,
                models.AdVideoOrder.public_job_id,
            )
            .filter(
                models.AdVideoOrder.status.in_(
                    [
                        models.AdVideoOrderStatus.QUEUED.value,
                        models.AdVideoOrderStatus.PENDING.value,
                        models.AdVideoOrderStatus.PROCESSING.value,
                        models.AdVideoOrderStatus.RENDERING.value,
                    ]
                ),
                models.AdVideoOrder.output_video_key.is_(None),
            )
            .order_by(models.AdVideoOrder.created_at.asc())
            .all()
        )
    finally:
        db.close()

    recovered = 0
    for row in rows:
        order_id = int(row[0])
        public_job_id = str(getattr(row, "public_job_id", "") or "").strip() or None
        if _enqueue_ad_order(order_id, public_job_id):
            recovered += 1
    if recovered:
        logger.info("[marketplace] recovered %s interrupted ad order(s)", recovered)
    return recovered


def ensure_ad_order_runtime_ready() -> int:
    logger.info(
        "[marketplace][runtime_recovery] ensure_ad_order_runtime_ready invoked; "
        "runtime recovery stage owns Redis reconnect and interrupted order recovery"
    )
    _require_video_queue_redis()
    return _recover_interrupted_ad_orders()


def _mark_ad_worker_heartbeat(order_id: Optional[int] = None) -> None:
    now = time.time()
    with _ad_worker_lock:
        if _ad_worker_runtime["started_at"] is None:
            _ad_worker_runtime["started_at"] = now
        _ad_worker_runtime["last_heartbeat"] = now
        if order_id is not None:
            _ad_worker_runtime["last_order_id"] = order_id


def get_ad_queue_runtime_status() -> Dict[str, Dict[str, Any]]:
    connection_id = f"redis:{VIDEO_RENDER_QUEUE_NAME}"
    worker_id = str(_ad_worker_runtime.get("worker_id") or "ad-render-worker-001")
    worker_bootstrap_enabled = (os.getenv("ENABLE_AD_ORDER_WORKER_BOOTSTRAP", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}

    redis_client = _get_video_queue_redis()
    queue_depth: Optional[int] = None
    redis_error: Optional[str] = None
    redis_available = redis_client is not None
    if redis_client is not None:
        try:
            queue_depth = int(redis_client.llen(VIDEO_RENDER_QUEUE_NAME))
        except RedisError as exc:
            redis_available = False
            redis_error = str(exc)

    with _ad_worker_lock:
        started_at = _ad_worker_runtime.get("started_at")
        last_heartbeat = _ad_worker_runtime.get("last_heartbeat")
        last_order_id = _ad_worker_runtime.get("last_order_id")

    now = time.time()
    heartbeat_age_sec: Optional[float] = None
    if isinstance(last_heartbeat, (int, float)):
        heartbeat_age_sec = round(max(0.0, now - float(last_heartbeat)), 1)
    worker_started = isinstance(started_at, (int, float))
    worker_alive = worker_started and heartbeat_age_sec is not None and heartbeat_age_sec <= 120.0

    redis_state = "ok" if redis_available else "warning"
    redis_note = (
        f"{connection_id} 연결 정상, queue={VIDEO_RENDER_QUEUE_NAME}, depth={queue_depth if queue_depth is not None else '-'}"
        if redis_available
        else "REDIS_URL 미설정 또는 Redis 연결 실패로 video_render_queue를 사용할 수 없습니다."
    )
    if not worker_bootstrap_enabled:
        worker_state = "ok"
        worker_note = "광고 주문 worker bootstrap이 비활성화되어 heartbeat를 생성하지 않습니다. 프로파일러/진단 실행에서는 정상입니다."
    else:
        worker_state = "ok" if worker_alive else "warning"
        worker_note = (
            f"worker_id={worker_id} heartbeat 정상, last_order_id={last_order_id or '-'}"
            if worker_alive
            else "광고 주문 worker heartbeat가 오래됐습니다. 장시간 렌더 중인지와 worker 루프 상태를 확인하세요."
        )

    return {
        "redis_queue": {
            "available": redis_available,
            "state": redis_state,
            "note": redis_note,
            "connection_id": connection_id,
            "queue_name": VIDEO_RENDER_QUEUE_NAME,
            "queue_depth": queue_depth,
            "worker_id": worker_id,
            "error": redis_error,
        },
        "ad_worker": {
            "available": worker_alive if worker_bootstrap_enabled else True,
            "state": worker_state,
            "note": worker_note,
            "connection_id": connection_id,
            "queue_name": VIDEO_RENDER_QUEUE_NAME,
            "queue_depth": queue_depth,
            "worker_id": worker_id,
            "bootstrap_enabled": worker_bootstrap_enabled,
            "started": worker_started,
            "heartbeat_age_sec": heartbeat_age_sec,
            "last_order_id": last_order_id,
        },
    }
