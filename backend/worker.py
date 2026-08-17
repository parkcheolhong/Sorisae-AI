import logging
import os
import threading

from backend.bootstrap import (
    ensure_supported_python_runtime,
    enable_qdrant_rest_only_mode,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    ensure_supported_python_runtime()
    enable_qdrant_rest_only_mode()

    logger.info("[worker] Starting backend video worker...")

    threads = []
    
    # Ad order worker
    enable_ad_worker = os.getenv("ENABLE_AD_ORDER_WORKER_BOOTSTRAP", "true").strip().lower() in {"1", "true", "yes", "on"}
    if enable_ad_worker:
        from backend.application.marketplace.ad_order_queue_service import run_ad_order_worker
        ad_thread = threading.Thread(target=run_ad_order_worker, name="ad-render-worker-001", daemon=True)
        ad_thread.start()
        threads.append(ad_thread)
        logger.info("[worker] ad order worker thread started")

    # Self-run video worker
    enable_self_run_worker = os.getenv("ENABLE_SELF_RUN_VIDEO_WORKER_BOOTSTRAP", "true").strip().lower() in {"1", "true", "yes", "on"}
    if enable_self_run_worker:
        try:
            from backend.marketplace.self_run_video_worker import run_self_run_video_worker
            self_run_thread = threading.Thread(target=run_self_run_video_worker, name="self-run-video-worker-001", daemon=True)
            self_run_thread.start()
            threads.append(self_run_thread)
            logger.info("[worker] self-run video worker thread started")
        except ImportError as e:
            logger.warning(f"[worker] self_run_video_worker module not found: {e}")

    if not threads:
        logger.warning("[worker] No workers were enabled to start. Exiting.")
        return

    logger.info("[worker] All enabled workers started. Waiting for work...")
    try:
        # keep main thread alive
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("[worker] Stopping workers due to KeyboardInterrupt...")

if __name__ == "__main__":
    main()
