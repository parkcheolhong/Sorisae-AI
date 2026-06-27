from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import service_account
except ImportError:  # pragma: no cover - optional dependency
    GoogleAuthRequest = None
    service_account = None

logger = logging.getLogger("marketplace.fcm_push")

device_registrations: Dict[int, List[Dict[str, str]]] = {}


def _stringify_push_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _post_fcm_legacy(server_key: str, payload: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        "https://fcm.googleapis.com/fcm/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"key={server_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.read().decode("utf-8", errors="replace"),
        )


def _load_fcm_service_account_info() -> Optional[dict[str, Any]]:
    if inline_json := os.getenv("FCM_SERVICE_ACCOUNT_JSON", "").strip():
        return json.loads(inline_json)

    if inline_b64 := os.getenv("FCM_SERVICE_ACCOUNT_JSON_B64", "").strip():
        decoded = base64.b64decode(inline_b64.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)

    json_path = os.getenv("FCM_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    return None


def _post_fcm_v1(
    service_account_info: dict[str, Any],
    project_id: str,
    payload: dict,
) -> tuple[int, str]:
    if service_account is None or GoogleAuthRequest is None:
        raise RuntimeError(
            "google-auth dependency is required for FCM v1 push delivery."
        )

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    credentials.refresh(GoogleAuthRequest())
    request = urllib.request.Request(
        f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.read().decode("utf-8", errors="replace"),
        )


def register_device_token(
    user_id: int,
    fcm_token: str,
    platform: str = "android",
) -> int:
    token = str(fcm_token or "").strip()
    if user_id <= 0 or not token:
        return 0
    rows = device_registrations.setdefault(user_id, [])
    rows[:] = [
        row for row in rows if str(row.get("fcm_token") or "") != token
    ]
    rows.append(
        {
            "fcm_token": token,
            "platform": platform,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return len(rows)


def _collect_user_tokens(user_id: int) -> list[str]:
    token_targets: list[str] = []
    for row in device_registrations.get(int(user_id), []):
        token = str(row.get("fcm_token") or "").strip()
        if token and token not in token_targets:
            token_targets.append(token)
    return token_targets


async def send_push_to_user(
    user_id: int,
    *,
    data_payload: dict[str, Any],
    title: str,
    body: str,
    channel_id: str,
    topic: Optional[str] = None,
) -> bool:
    server_key = os.getenv("FCM_SERVER_KEY", "").strip()
    service_account_info = _load_fcm_service_account_info()
    project_id = (
        os.getenv("FCM_PROJECT_ID", "").strip()
        or str((service_account_info or {}).get("project_id") or "").strip()
    )
    token_targets = _collect_user_tokens(user_id)
    if not topic and not token_targets:
        return False

    normalized_data = {
        key: _stringify_push_value(value)
        for key, value in data_payload.items()
        if value is not None
    }
    notification_body = {"title": title, "body": body}
    android_notification = {
        "channel_id": channel_id,
        "sound": "default",
        "notification_priority": "PRIORITY_MAX",
        "visibility": "PUBLIC",
        "default_vibrate_timings": True,
    }

    def _build_v1_message(target: dict) -> dict:
        return {
            "message": {
                **target,
                "data": normalized_data,
                "notification": notification_body,
                "android": {
                    "priority": "HIGH",
                    "notification": android_notification,
                },
            }
        }

    any_success = False
    errors: list[str] = []

    try:
        if server_key:
            if topic:
                legacy_payload = {
                    "to": f"/topics/{topic}",
                    "priority": "high",
                    "data": normalized_data,
                    "notification": notification_body,
                }
                status_code, response_body = await asyncio.to_thread(
                    _post_fcm_legacy,
                    server_key,
                    legacy_payload,
                )
                topic_ok = 200 <= status_code < 300 and (
                    '"message_id"' in response_body
                    or '"success":1' in response_body
                    or '"success": 1' in response_body
                )
                any_success = any_success or topic_ok
                if not topic_ok:
                    errors.append(f"topic:{status_code}:{response_body[:200]}")
            for token in token_targets:
                legacy_payload = {
                    "to": token,
                    "priority": "high",
                    "data": normalized_data,
                    "notification": notification_body,
                }
                status_code, response_body = await asyncio.to_thread(
                    _post_fcm_legacy,
                    server_key,
                    legacy_payload,
                )
                token_ok = 200 <= status_code < 300 and (
                    '"message_id"' in response_body
                    or '"success":1' in response_body
                    or '"success": 1' in response_body
                )
                any_success = any_success or token_ok
                if not token_ok:
                    errors.append(f"token:{status_code}:{response_body[:120]}")
        elif service_account_info and project_id:
            if topic:
                status_code, response_body = await asyncio.to_thread(
                    _post_fcm_v1,
                    service_account_info,
                    project_id,
                    _build_v1_message({"topic": topic}),
                )
                topic_ok = 200 <= status_code < 300 and '"name"' in response_body
                any_success = any_success or topic_ok
                if not topic_ok:
                    errors.append(f"topic:{status_code}:{response_body[:200]}")
            for token in token_targets:
                status_code, response_body = await asyncio.to_thread(
                    _post_fcm_v1,
                    service_account_info,
                    project_id,
                    _build_v1_message({"token": token}),
                )
                token_ok = 200 <= status_code < 300 and '"name"' in response_body
                any_success = any_success or token_ok
                if not token_ok:
                    errors.append(f"token:{status_code}:{response_body[:120]}")
    except Exception as exc:
        logger.warning(
            "[FCM] push failed | user_id=%s | channel=%s | err=%s",
            user_id,
            channel_id,
            exc,
        )
        return False

    if errors and not any_success:
        logger.warning(
            "[FCM] push rejected | user_id=%s | channel=%s | errors=%s",
            user_id,
            channel_id,
            "; ".join(errors[:3]),
        )
    return any_success
