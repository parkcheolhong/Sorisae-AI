from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import mimetypes
import os
from typing import Dict, Optional


@dataclass(frozen=True)
class AzureOpenAIRuntimeConfig:
    endpoint: str
    api_key: str
    video_deployment_name: str
    vision_deployment_name: str


def _clean(value: object) -> str:
    return str(value or "").strip()


def resolve_azure_openai_runtime(payload: Dict[str, object]) -> AzureOpenAIRuntimeConfig | None:
    endpoint = _clean(payload.get("azure_openai_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT"))
    api_key = _clean(payload.get("azure_openai_api_key") or os.getenv("AZURE_OPENAI_API_KEY"))
    video_deployment_name = _clean(payload.get("video_deployment_name") or os.getenv("AZURE_OPENAI_VIDEO_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or "sora-2")
    vision_deployment_name = _clean(payload.get("vision_deployment_name") or os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT_NAME") or "gpt-4o")
    if not endpoint or not api_key:
        return None
    return AzureOpenAIRuntimeConfig(
        endpoint=endpoint.rstrip("/"),
        api_key=api_key,
        video_deployment_name=video_deployment_name,
        vision_deployment_name=vision_deployment_name,
    )


def build_api_headers(config: AzureOpenAIRuntimeConfig) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "api-key": config.api_key,
    }


def local_file_to_data_url(path_value: str) -> str:
    path = Path(path_value)
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def image_reference_to_url(image_reference: str) -> str:
    value = _clean(image_reference)
    if value.startswith("http://") or value.startswith("https://") or value.startswith("data:"):
        return value
    path = Path(value)
    if path.exists() and path.is_file():
        return local_file_to_data_url(str(path))
    raise FileNotFoundError(f"Quality reference image not found: {value}")
