"""VoIP 시그널링 설정 — STUN/TURN/공개 WS 베이스 환경변수.

P1: STUN(공용) + 환경변수로 주입하는 정적 TURN. TURN 토큰화/PSTN은 후속(P3).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Any, Dict, List, Optional, Tuple


def _csv(name: str, default: str = "") -> List[str]:
    raw = (os.getenv(name, default) or "").strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


# ws 시그널링 토큰 수명(초)
def signaling_token_ttl_sec() -> int:
    try:
        return int(os.getenv("VOIP_SIGNALING_TOKEN_TTL_SEC", "600"))
    except ValueError:
        return 600


def _turn_token_ttl_sec() -> int:
    try:
        return int(os.getenv("VOIP_TURN_TOKEN_TTL_SEC", "86400"))
    except ValueError:
        return 86400


def dynamic_turn_credentials(user_key: Optional[str] = None, *, now: Optional[int] = None) -> Optional[Tuple[str, str]]:
    """P3-C: coturn `use-auth-secret`(TURN REST API) 방식의 시간제한 자격 생성.

    username = "<expiry_unix>:<user_key>"
    credential = base64(HMAC-SHA1(secret, username))
    `VOIP_TURN_STATIC_AUTH_SECRET` 미설정 시 None(정적 자격 폴백).
    """
    secret = (os.getenv("VOIP_TURN_STATIC_AUTH_SECRET", "") or "").strip()
    if not secret:
        return None
    expiry = (now if now is not None else int(time.time())) + _turn_token_ttl_sec()
    username = f"{expiry}:{user_key or 'voip'}"
    digest = hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode("ascii")
    return username, credential


def get_ice_servers(user_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """모바일 CallInitResponse.turn_servers 형식으로 ICE 서버 목록 반환.

    각 항목: {"urls": [...], "username"?, "credential"?}
    TURN 자격은 `VOIP_TURN_STATIC_AUTH_SECRET` 설정 시 통화/사용자별 시간제한 토큰(P3-C),
    아니면 정적 `VOIP_TURN_USERNAME/CREDENTIAL` 폴백.
    """
    servers: List[Dict[str, Any]] = []

    stun_urls = _csv("VOIP_STUN_URLS", "stun:stun.l.google.com:19302")
    if stun_urls:
        servers.append({"urls": stun_urls})

    turn_urls = _csv("VOIP_TURN_URLS")
    if turn_urls:
        turn: Dict[str, Any] = {"urls": turn_urls}
        dynamic = dynamic_turn_credentials(user_key)
        if dynamic is not None:
            turn["username"], turn["credential"] = dynamic
        else:
            username = (os.getenv("VOIP_TURN_USERNAME", "") or "").strip()
            credential = (os.getenv("VOIP_TURN_CREDENTIAL", "") or "").strip()
            if username:
                turn["username"] = username
            if credential:
                turn["credential"] = credential
        servers.append(turn)

    return servers


def build_signaling_url(
    *,
    call_id: str,
    token: str,
    role: str,
    request_scheme: Optional[str] = None,
    request_host: Optional[str] = None,
) -> str:
    """모바일이 그대로 `new WebSocket(url)`에 사용할 완전한 ws URL을 조립.

    우선순위: VOIP_PUBLIC_WS_BASE 환경변수 → 요청 스킴/호스트에서 유도 → 로컬 기본값.
    """
    base = (os.getenv("VOIP_PUBLIC_WS_BASE", "") or "").strip().rstrip("/")
    if not base:
        if request_host:
            scheme = "wss" if (request_scheme or "").lower() in ("https", "wss") else "ws"
            base = f"{scheme}://{request_host}"
        else:
            base = "ws://localhost:8000"
    return f"{base}/api/v1/voip/ws/{call_id}?token={token}&role={role}"
