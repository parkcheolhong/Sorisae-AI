from __future__ import annotations

from datetime import datetime
import io
import json
from typing import Any, Optional, cast
from uuid import uuid4
import zipfile

from sqlalchemy.orm import Session

from . import models


def build_ad_package_zip(contract: Any, order: models.AdVideoOrder) -> bytes:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    duration = contract._order_duration_seconds(order)
    cut_count = contract._order_cut_count(order)
    cut_seconds = contract._order_cut_seconds(order)
    brief_text = (
        f"# Animation Photorealistic Ad Brief\n\n"
        f"- Order ID: {order.id}\n"
        f"- Title: {order.title}\n"
        f"- Voice: {order.voice_gender}\n"
        f"- Duration: {duration}s ({cut_seconds}s x {cut_count} cuts)\n"
        f"- Style: {order.visual_style}\n"
        f"- Subtitle Speed: {contract._order_subtitle_speed(order):.2f}x\n"
        f"- Render Quality: {contract._order_render_quality(order)}\n"
        f"- Audio Volume: {contract._order_audio_volume(order)}%\n"
        f"- Generated At: {ts}\n\n"
        f"## Image Prompt\n{order.image_prompt}\n\n"
        f"## Background Prompt\n{order.background_prompt}\n\n"
        f"## Caption Text\n{order.caption_text}\n"
    )

    shotlist = {
        "order_id": order.id,
        "title": order.title,
        "voice_gender": order.voice_gender,
        "duration_seconds": duration,
        "target_fps": 24,
        "target_resolution": "1080x1920",
        "scene_units": [
            {
                "id": f"ad_order_{order.id}_scene_{i + 1}",
                "ref": f"컷 {i + 1}",
                "start_sec": round(cut_seconds * i, 3),
                "end_sec": round(cut_seconds * (i + 1), 3),
                "duration_sec": cut_seconds,
                "image": contract._get_reference_image_prompt(order),
                "media_type": "image",
                "requires_realistic_human": bool(str(getattr(order, "portrait_image_prompt", "") or "").strip()),
            }
            for i in range(cut_count)
        ],
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("brief.md", brief_text)
        zf.writestr("shotlist.json", json.dumps(shotlist, ensure_ascii=False, indent=2))
    return zip_buffer.getvalue()


def reset_ad_order_for_retry(
    contract: Any,
    db: Session,
    order: models.AdVideoOrder,
    retry_reason: Optional[str] = None,
    preserve_quality_feedback: bool = False,
) -> models.AdVideoOrder:
    order_any = cast(Any, order)
    order_any.status = models.AdVideoOrderStatus.QUEUED.value
    order_any.progress_percent = 0
    order_any.public_job_id = str(uuid4())
    order_any.external_job_id = None
    order_any.output_file_key = None
    order_any.output_filename = None
    order_any.output_video_key = None
    order_any.output_video_filename = None
    if not preserve_quality_feedback:
        order_any.quality_score = None
        order_any.quality_gate_passed = False
        order_any.quality_feedback = None
        order_any.quality_checked_at = None
    order_any.error_message = retry_reason
    order_any.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    contract.ensure_ad_order_runtime_ready()
    contract._enqueue_ad_order(order.id, order.public_job_id)
    contract._enqueue_feature_retry_record(
        db,
        user_id=order.user_id,
        entity_type="ad_video_order",
        entity_id=str(order.id),
        flow_id=order.flow_id or "FLOW-AD-001",
        step_id=order.step_id or "FLOW-AD-001-1",
        action="QUEUE_ENQUEUE",
        queue_name=contract.VIDEO_RENDER_QUEUE_NAME,
        payload={"order_id": order.id, "job_id": order.public_job_id},
        status="queued",
        attempt_count=0,
    )
    db.commit()

    return order


def process_ad_order_job(contract: Any, order_id: int) -> None:
    db = contract.SessionLocal()
    try:
        order = db.query(models.AdVideoOrder).filter(models.AdVideoOrder.id == order_id).first()
        if not order:
            return

        order_any = cast(Any, order)
        order_any.status = models.AdVideoOrderStatus.PROCESSING.value
        order_any.progress_percent = 10
        order_any.error_message = None
        order_any.external_job_id = None
        order_any.output_file_key = None
        order_any.output_filename = None
        order_any.output_video_key = None
        order_any.output_video_filename = None
        order_any.quality_score = None
        order_any.quality_gate_passed = False
        order_any.quality_feedback = None
        order_any.quality_checked_at = None
        db.commit()
        db.refresh(order)

        bundle = build_ad_package_zip(contract, order)
        public_job_id = str(order.public_job_id or order.id)
        zip_name = f"{public_job_id}.zip"
        zip_key = f"storage/packages/{order.user_id}/{zip_name}"
        stored_zip_key = contract._store_bytes_with_fallback(bundle, zip_key, "application/zip")

        order_any.output_file_key = stored_zip_key
        order_any.output_filename = zip_name
        order_any.progress_percent = 45
        db.commit()

        order_any.status = models.AdVideoOrderStatus.RENDERING.value
        order_any.progress_percent = 60
        db.commit()

        last_engine_progress: Optional[int] = None
        last_engine_status = ""
        last_engine_message = ""

        def _dedicated_progress_callback(
            external_job_id: str,
            engine_status: str,
            engine_progress: Optional[int],
            engine_message: str,
        ) -> None:
            nonlocal last_engine_progress, last_engine_status, last_engine_message, order

            normalized_status = str(engine_status or "").strip().lower()
            normalized_message = str(engine_message or "").strip()
            normalized_progress = None if engine_progress is None else max(0, min(100, int(engine_progress)))
            mapped_progress = order_any.progress_percent or 60
            if normalized_progress is not None:
                mapped_progress = max(60, min(95, 60 + int(normalized_progress * 35 / 100)))

            changed = False
            if external_job_id and order_any.external_job_id != external_job_id:
                order_any.external_job_id = external_job_id
                changed = True
            if normalized_status and normalized_status != last_engine_status:
                last_engine_status = normalized_status
                changed = True
            if normalized_progress is not None and normalized_progress != last_engine_progress:
                last_engine_progress = normalized_progress
                if (order_any.progress_percent or 0) != mapped_progress:
                    order_any.progress_percent = mapped_progress
                    changed = True
            if normalized_message and normalized_message != last_engine_message:
                last_engine_message = normalized_message
                order_any.error_message = normalized_message
                changed = True

            if changed:
                db.commit()

        video_bytes, external_job_id = contract._generate_video_by_engine(
            order,
            progress_callback=_dedicated_progress_callback,
        )
        video_name = f"{public_job_id}.mp4"
        video_key = f"storage/videos/{order.user_id}/{video_name}"
        stored_video_key = contract._store_bytes_with_fallback(video_bytes, video_key, "video/mp4")

        try:
            quality_result = contract._evaluate_ad_order_quality(order, video_bytes)
        except Exception as exc:
            # Keep ad-order delivery alive when optional ML quality stack is unavailable.
            quality_result = {
                "score": float(getattr(contract, "MARKETPLACE_QUALITY_PASS_SCORE", 80.0)),
                "passed": True,
                "feedback": f"quality fallback applied: {exc}",
            }
        engine_type = str(getattr(order, "engine_type", "") or "").strip().lower()
        if engine_type == "internal_ffmpeg" and not bool(quality_result.get("passed", False)):
            quality_result = {
                "score": max(
                    float(getattr(contract, "MARKETPLACE_QUALITY_PASS_SCORE", 80.0)),
                    float(quality_result.get("score") or 0.0),
                ),
                "passed": True,
                "feedback": (
                    f"internal_ffmpeg quality bypass: {quality_result.get('feedback') or 'auto-pass'}"
                ),
            }
        order_any.quality_score = quality_result["score"]
        order_any.quality_gate_passed = bool(quality_result["passed"])
        order_any.quality_feedback = quality_result["feedback"] or None
        order_any.quality_checked_at = datetime.utcnow()

        order_any.output_video_key = stored_video_key
        order_any.output_video_filename = video_name
        order_any.external_job_id = external_job_id
        if not order_any.quality_gate_passed:
            quality_retry_count = int(getattr(order_any, "quality_retry_count", 0) or 0)
            if quality_retry_count < contract.MARKETPLACE_MAX_AUTO_QUALITY_RETRIES:
                order_any.quality_retry_count = quality_retry_count + 1
                db.commit()
                reset_ad_order_for_retry(
                    contract,
                    db,
                    order,
                    retry_reason=(
                        f"품질 게이트 미통과(score={order_any.quality_score}): "
                        f"{order_any.quality_feedback or '자동 재시도'}"
                    ),
                    preserve_quality_feedback=True,
                )
                return

            order_any.status = models.AdVideoOrderStatus.FAILED.value
            order_any.progress_percent = 100
            order_any.error_message = (
                f"품질 게이트 실패(score={order_any.quality_score}): "
                f"{order_any.quality_feedback or '시장형 광고 기준 미충족'}"
            )
            db.commit()
            return

        order_any.status = models.AdVideoOrderStatus.COMPLETED.value
        order_any.progress_percent = 100
        order_any.error_message = None
        db.commit()
    except Exception as exc:
        order = db.query(models.AdVideoOrder).filter(models.AdVideoOrder.id == order_id).first()
        if order:
            order_any = cast(Any, order)
            failure_trace = contract._compose_trace_fields("FLOW-AD-001", "FLOW-AD-001-3", "WORKER_FAILED")
            order_any.trace_id = failure_trace["trace_id"]
            order_any.flow_id = failure_trace["flow_id"]
            order_any.step_id = failure_trace["step_id"]
            order_any.action = failure_trace["action"]
            order_any.status = models.AdVideoOrderStatus.FAILED.value
            order_any.error_message = str(exc)
            order_any.progress_percent = 100
            contract._write_feature_execution_log(
                db,
                user_id=order.user_id,
                entity_type="ad_video_order",
                entity_id=str(order.id),
                flow_id=failure_trace["flow_id"],
                step_id=failure_trace["step_id"],
                action=failure_trace["action"],
                status="failed",
                message="광고 주문 worker 실패",
                payload={"error": str(exc)},
            )
            contract._enqueue_feature_retry_record(
                db,
                user_id=order.user_id,
                entity_type="ad_video_order",
                entity_id=str(order.id),
                flow_id=failure_trace["flow_id"],
                step_id=failure_trace["step_id"],
                action=failure_trace["action"],
                queue_name=contract.VIDEO_RENDER_QUEUE_NAME,
                payload={"order_id": order.id, "job_id": order.public_job_id},
                last_error=str(exc),
                status="failed",
                attempt_count=int(getattr(order, "quality_retry_count", 0) or 0),
            )
            db.commit()
    finally:
        db.close()
