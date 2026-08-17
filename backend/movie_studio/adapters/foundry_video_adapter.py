from __future__ import annotations

from typing import Dict, List
import time

import requests

from backend.movie_studio.adapters.azure_openai_runtime import (
    build_api_headers,
    resolve_azure_openai_runtime,
)


def build_foundry_video_request(payload: Dict[str, object]) -> Dict[str, object]:
    runtime = resolve_azure_openai_runtime(payload)
    prompt = str(payload.get("prompt") or payload.get("synopsis") or payload.get("title") or "").strip()
    size = str(payload.get("size") or payload.get("target_resolution") or "1280x720").lower().replace("*", "x")
    seconds = max(1, min(20, int(payload.get("seconds") or payload.get("target_duration_seconds") or 8)))
    source_type = "azure-openai-sora-2" if runtime else "unconfigured"
    request_payload = {
        "provider": "foundry-video",
        "source_type": source_type,
        "mode": "photoreal-cinematic",
        "model": runtime.video_deployment_name if runtime else str(payload.get("video_deployment_name") or "sora-2"),
        "prompt": prompt,
        "size": size,
        "seconds": seconds,
        "input_reference": payload.get("input_reference"),
        "target_resolution": str(payload.get("target_resolution") or size),
    }
    if not runtime:
        return {
            **request_payload,
            "configured": False,
            "reason": "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY is missing",
        }

    base_url = f"{runtime.endpoint}/openai/v1"
    return {
        **request_payload,
        "configured": True,
        "base_url": base_url,
        "headers": build_api_headers(runtime),
    }


def submit_foundry_video_generation(payload: Dict[str, object]) -> Dict[str, object]:
    request_payload = build_foundry_video_request(payload)
    if not request_payload.get("configured"):
        return {
            **request_payload,
            "submitted": False,
        }

    body = {
        "model": request_payload["model"],
        "prompt": request_payload["prompt"],
        "size": request_payload["size"],
        "seconds": request_payload["seconds"],
    }
    input_reference = request_payload.get("input_reference")
    if input_reference:
        body["input_reference"] = input_reference
    response = requests.post(
        f"{request_payload['base_url']}/videos",
        headers=request_payload["headers"],
        json=body,
        timeout=180,
    )
    response.raise_for_status()
    result = response.json()
    return {
        **request_payload,
        "submitted": True,
        "job": result,
    }


def poll_foundry_video_generation(job_bundle: Dict[str, object], poll_interval_seconds: int = 20, max_attempts: int = 30) -> Dict[str, object]:
    if not job_bundle.get("submitted"):
        return job_bundle
    video = dict(job_bundle.get("job") or {})
    video_id = str(video.get("id") or "").strip()
    if not video_id:
        return {
            **job_bundle,
            "submitted": False,
            "reason": "video job id missing",
        }
    status = str(video.get("status") or "queued")
    attempts = 0
    while status not in {"completed", "failed", "cancelled"} and attempts < max_attempts:
        time.sleep(max(1, poll_interval_seconds))
        response = requests.get(
            f"{job_bundle['base_url']}/videos/{video_id}",
            headers=job_bundle["headers"],
            timeout=60,
        )
        response.raise_for_status()
        video = response.json()
        status = str(video.get("status") or status)
        attempts += 1
    return {
        **job_bundle,
        "job": video,
        "status": status,
        "poll_attempts": attempts,
    }


def build_foundry_download_info(job_bundle: Dict[str, object]) -> Dict[str, object]:
    if not job_bundle.get("submitted"):
        return job_bundle
    video = dict(job_bundle.get("job") or {})
    video_id = str(video.get("id") or "").strip()
    if not video_id:
        return job_bundle
    return {
        **job_bundle,
        "download_url": f"{job_bundle['base_url']}/videos/{video_id}/content/video",
    }
