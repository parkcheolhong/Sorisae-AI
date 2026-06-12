"""P3-A: FCM 푸시 어댑터(콜리 착신 알림).

Firebase Admin SDK(`firebase-admin`)와 자격(`GOOGLE_APPLICATION_CREDENTIALS` 또는
`FCM_CREDENTIALS_JSON`)이 구성된 경우에만 실제 전송한다. 미설치/미구성 시 안전하게 no-op
(`skipped`)으로 동작하므로, 의존성 없이도 서버가 정상 구동된다.

`firebase-admin`은 선택 의존성이며 `requirements.txt`에 포함하지 않는다(운영 시 설치 + 서비스
계정 키 설정 필요).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_app = None  # firebase_admin App 캐시


def is_push_configured() -> bool:
    if (os.getenv("FCM_ENABLED", "") or "").strip().lower() not in ("1", "true", "yes"):
        return False
    return bool(
        (os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "") or "").strip()
        or (os.getenv("FCM_CREDENTIALS_JSON", "") or "").strip()
    )


def _get_app():
    global _app
    if _app is not None:
        return _app
    import firebase_admin
    from firebase_admin import credentials

    creds_json = (os.getenv("FCM_CREDENTIALS_JSON", "") or "").strip()
    if creds_json:
        cred = credentials.Certificate(json.loads(creds_json))
    else:
        cred = credentials.ApplicationDefault()
    try:
        _app = firebase_admin.get_app()
    except ValueError:
        _app = firebase_admin.initialize_app(cred)
    return _app


async def send_incoming_call_push(
    tokens: List[str],
    *,
    call_id: str,
    caller_label: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """콜리 디바이스 토큰들에 착신 data 푸시. (sent, skipped, reason) 반환."""
    if not tokens:
        return {"sent": 0, "skipped": True, "reason": "no_tokens"}
    if not is_push_configured():
        return {"sent": 0, "skipped": True, "reason": "not_configured"}

    try:
        import asyncio

        from firebase_admin import messaging

        _get_app()
        payload = {
            "type": "incoming_call",
            "call_id": call_id,
            "caller_label": caller_label,
        }
        if data:
            payload.update({k: str(v) for k, v in data.items()})

        def _send() -> int:
            message = messaging.MulticastMessage(
                tokens=tokens,
                data=payload,
                android=messaging.AndroidConfig(priority="high"),
            )
            resp = messaging.send_each_for_multicast(message)
            return int(getattr(resp, "success_count", 0))

        sent = await asyncio.to_thread(_send)
        return {"sent": sent, "skipped": False, "reason": None}
    except Exception as exc:  # noqa: BLE001 — 전송 실패가 통화 생성을 막지 않도록.
        logger.warning("[VoIP] FCM 푸시 실패(무시): %s", exc)
        return {"sent": 0, "skipped": True, "reason": str(exc)}
