from __future__ import annotations

from typing import Dict, List
import json

import requests

from backend.movie_studio.adapters.azure_openai_runtime import (
    build_api_headers,
    image_reference_to_url,
    resolve_azure_openai_runtime,
)
from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract


QUALITY_VISION_SYSTEM_PROMPT = """
You are a strict photoreal movie quality gate. Evaluate the supplied image references for real-human fidelity,
hand anatomy, body anatomy, environment realism, lighting continuity, and freeze-like CTA behavior.
Return JSON only with keys: passed, score, failures.
Each failure item must contain: code, message, frame_range, severity.
Fail if the image looks cartoonish, low-fidelity, anatomically broken, identity-unstable, structurally warped,
or visually frozen in a CTA-like pose.
""".strip()


def build_quality_vision_request(payload: Dict[str, object]) -> Dict[str, object]:
    runtime = resolve_azure_openai_runtime(payload)
    image_references = [str(item).strip() for item in list(payload.get("image_references") or []) if str(item).strip()]
    request_payload = {
        "provider": "quality-vision",
        "checks": ["face", "hands", "anatomy", "environment", "flicker"],
        "vision_model": runtime.vision_deployment_name if runtime else str(payload.get("vision_deployment_name") or "gpt-4o"),
        "configured": runtime is not None,
        "image_references": image_references,
    }
    if not runtime:
        return {
            **request_payload,
            "reason": "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY is missing",
        }
    return {
        **request_payload,
        "base_url": f"{runtime.endpoint}/openai/v1/chat/completions",
        "headers": build_api_headers(runtime),
    }


def run_quality_vision_check(payload: Dict[str, object]) -> Dict[str, object]:
    request_payload = build_quality_vision_request(payload)
    if not request_payload.get("configured"):
        return {
            **request_payload,
            "executed": False,
        }
    image_urls = [
        {
            "type": "image_url",
            "image_url": {
                "url": image_reference_to_url(reference),
                "detail": "high",
            },
        }
        for reference in request_payload["image_references"]
    ]
    user_content: List[Dict[str, object]] = [
        {
            "type": "text",
            "text": str(payload.get("quality_prompt") or "Assess photoreal movie quality for face, hand, anatomy, environment, and temporal plausibility."),
        },
        *image_urls,
    ]
    try:
        response = requests.post(
            request_payload["base_url"],
            headers=request_payload["headers"],
            json={
                "model": request_payload["vision_model"],
                "messages": [
                    {"role": "system", "content": QUALITY_VISION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 1200,
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
        response.raise_for_status()
        completion = response.json()
        content = completion["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        failures = [
            QualityFailureContract(
                code=str(item.get("code") or "unknown_failure"),
                message=str(item.get("message") or "unknown failure"),
                frame_range=str(item.get("frame_range") or "scene"),
                severity=str(item.get("severity") or "high"),
            ).model_dump()
            for item in list(parsed.get("failures") or [])
        ]
        return {
            **request_payload,
            "executed": True,
            "raw_response": completion,
            "result": {
                "passed": bool(parsed.get("passed", False)),
                "score": float(parsed.get("score") or 0.0),
                "failures": failures,
                "rerender_required": not bool(parsed.get("passed", False)),
            },
        }
    except requests.RequestException as exc:
        return {
            **request_payload,
            "executed": False,
            "reason": str(exc),
        }
