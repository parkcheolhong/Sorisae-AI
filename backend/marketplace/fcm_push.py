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


def _persist_token_to_db(user_id: int, token: str, platform: str) -> None:
    """FCM 토큰을 DB에 영속(upsert). best-effort — 실패해도 인메모리 등록은 유지."""
    try:
        from .database import SessionLocal
        from . import models

        db = SessionLocal()
        try:
            existing = (
                db.query(models.VoipDeviceToken)
                .filter(models.VoipDeviceToken.fcm_token == token)
                .first()
            )
            if existing is None:
                db.add(
                    models.VoipDeviceToken(
                        user_id=int(user_id),
                        fcm_token=token,
                        platform=platform,
                    )
                )
            else:
                # 같은 토큰이 다른 계정에서 재로그인된 경우 소유 계정을 갱신(단말 1 → 계정 1).
                existing.user_id = int(user_id)
                existing.platform = platform
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[fcm] token DB persist failed (kept in-memory)", exc_info=True)


def _remove_token_from_db(token: str) -> None:
    try:
        from .database import SessionLocal
        from . import models

        db = SessionLocal()
        try:
            db.query(models.VoipDeviceToken).filter(
                models.VoipDeviceToken.fcm_token == token
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[fcm] token DB remove failed", exc_info=True)


def _remove_other_tokens_for_user_from_db(user_id: int, keep_token: str) -> None:
    """사용자당 1개 활성 토큰만 유지하도록 DB에서 나머지 토큰을 정리한다."""
    try:
        from .database import SessionLocal
        from . import models

        db = SessionLocal()
        try:
            db.query(models.VoipDeviceToken).filter(
                models.VoipDeviceToken.user_id == int(user_id),
                models.VoipDeviceToken.fcm_token != keep_token,
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[fcm] extra token prune failed", exc_info=True)


def hydrate_device_registrations_from_db() -> int:
    """기동 시 DB의 토큰을 인메모리 레지스트리로 적재(재시작 후에도 푸시 대상 유지)."""
    try:
        from .database import SessionLocal
        from . import models

        db = SessionLocal()
        try:
            rows = db.query(models.VoipDeviceToken).all()
            loaded = 0
            for row in rows:
                uid = int(row.user_id or 0)
                token = str(row.fcm_token or "").strip()
                if uid <= 0 or not token:
                    continue
                bucket = device_registrations.setdefault(uid, [])
                if all(str(b.get("fcm_token") or "") != token for b in bucket):
                    bucket.append(
                        {
                            "fcm_token": token,
                            "platform": str(row.platform or "android"),
                            "registered_at": (
                                row.updated_at or row.created_at
                            ).isoformat()
                            if (row.updated_at or row.created_at)
                            else datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    loaded += 1
            logger.info("[fcm] hydrated %d device token(s) from DB", loaded)
            return loaded
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        logger.warning("[fcm] device token hydrate failed", exc_info=True)
        return 0


def register_device_token(
    user_id: int,
    fcm_token: str,
    platform: str = "android",
) -> int:
    token = str(fcm_token or "").strip()
    if user_id <= 0 or not token:
        return 0
    # 같은 토큰이 다른 계정에 남아 있으면 제거(단말은 한 번에 한 계정만 수신).
    for other_uid, other_rows in list(device_registrations.items()):
        if other_uid == user_id:
            continue
        other_rows[:] = [
            row for row in other_rows if str(row.get("fcm_token") or "") != token
        ]
    rows = device_registrations.setdefault(user_id, [])
    rows[:] = []
    rows.append(
        {
            "fcm_token": token,
            "platform": platform,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _persist_token_to_db(user_id, token, platform)
    _remove_other_tokens_for_user_from_db(user_id, token)
    return len(rows)


def remove_device_token(fcm_token: str) -> bool:
    """단말 토큰 해제(로그아웃 등). 인메모리 + DB 모두 제거."""
    token = str(fcm_token or "").strip()
    if not token:
        return False
    removed = False
    for _uid, rows in list(device_registrations.items()):
        before = len(rows)
        rows[:] = [row for row in rows if str(row.get("fcm_token") or "") != token]
        if len(rows) != before:
            removed = True
    _remove_token_from_db(token)
    return removed


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
