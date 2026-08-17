from backend.database import SessionLocal
from backend.marketplace import models

db = SessionLocal()
try:
    order = db.query(models.AdVideoOrder).filter(models.AdVideoOrder.id == 36).first()
    if not order:
        print({"found": False, "id": 36})
    else:
        print({
            "found": True,
            "id": order.id,
            "public_job_id": order.public_job_id,
            "status": order.status,
            "engine_type": order.engine_type,
            "duration_seconds": order.duration_seconds,
            "cut_count": order.cut_count,
            "render_quality": order.render_quality,
            "output_video_key": order.output_video_key,
            "output_video_filename": order.output_video_filename,
            "quality_score": order.quality_score,
            "error_message": order.error_message,
        })
finally:
    db.close()
