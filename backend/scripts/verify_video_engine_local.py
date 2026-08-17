from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.marketplace.ffmpeg_render_executor import render_final_video
from backend.marketplace.video_generation_engine import run_video_engine_smoke_test, run_video_generation_engine
from backend.marketplace.self_run_video_worker import (
    enqueue_self_run_video_job,
    get_self_run_video_job,
    get_self_run_video_worker_status,
)


def main() -> int:
    tmp_dir = ROOT / "uploads" / "tmp" / "video_engine_smoke"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ffconcat_path = tmp_dir / "empty.ffconcat"
    ffconcat_path.write_text("ffconcat version 1.0\n", encoding="utf-8")

    render_result = render_final_video(
        {
            "title": "smoke-test",
            "ffconcat_path": str(ffconcat_path),
            "output_dir": str(tmp_dir),
            "output_basename": "smoke.mp4",
        }
    )

    planner_result = run_video_generation_engine(
        {
            "title": "video-engine-planner-smoke",
            "duration_seconds": 60,
            "cut_count": 12,
            "subject_type": "product",
            "product_image_prompts": ["https://example.invalid/product-1.png"],
            "background_prompt": "premium studio set",
            "caption_text": "문제 제기부터 CTA까지 이어지는 1분 광고 카피",
            "scenario_script": "문제 인식, 제품 소개, 핵심 기능, 사용 장면, 오퍼, CTA로 이어지는 12컷 광고",
            "render_quality": "high",
        }
    )

    smoke_test_result = run_video_engine_smoke_test(
        {
            "title": "video-engine-smoke-contract",
            "subject_type": "product",
            "product_image_prompts": ["https://example.invalid/product-1.png"],
            "background_prompt": "premium studio set",
            "caption_text": "스모크 테스트용 1분 광고 카피",
            "scenario_script": "12컷 고정 스모크 테스트",
        }
    )

    job = enqueue_self_run_video_job(
        {
            "title": "self-run-smoke",
            "scenario_script": "여성이 컵을 들고 마신 뒤 전화한다",
            "duration_seconds": 5,
            "frames_per_second": 8,
            "subtitle_speed": 1.0,
        }
    )

    result = {
        "render_result": render_result,
        "planner_result": planner_result,
        "smoke_test_result": smoke_test_result,
        "self_run_job": job,
        "self_run_job_lookup": get_self_run_video_job(str(job.get("job_id") or "")),
        "worker_status": get_self_run_video_worker_status(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
