"""Production golden tasks — health, WorldLinco voice/VoIP, admin settings."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


async def run_golden_tasks(
    base_url: str,
    *,
    token: Optional[str] = None,
    timeout_sec: float = 25.0,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    results: Dict[str, Any] = {}

    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        timeout=timeout_sec,
    ) as client:
        # G1: platform health
        results["G1_health"] = await _probe_health(client)

        # G2: WorldLinco product stem (voice-translate + VoIP surface)
        g2_subtasks: Dict[str, Any] = {}
        g2_subtasks["voice_translate"] = await _probe_voice_translate_smoke(client)
        g2_subtasks["voip_health"] = await _probe_voip_health(client)
        g2_subtasks["voip_initiate"] = await _probe_voip_initiate(client, headers=headers)
        g2_subtasks["openapi_markers"] = await _probe_voice_openapi_markers(client)

        g2_required_ok = all(
            bool(g2_subtasks[key].get("ok"))
            for key in ("voice_translate", "voip_health")
        )
        initiate = g2_subtasks["voip_initiate"]
        if initiate.get("ok") is not None:
            g2_required_ok = g2_required_ok and bool(initiate.get("ok"))

        results["G2_worldlinco"] = {
            "ok": g2_required_ok,
            "detail": _summarize_g2(g2_subtasks),
            "subtasks": g2_subtasks,
        }

        # G3: admin system-settings (JWT)
        results["G3_admin_settings"] = await _probe_admin_settings(client, headers=headers)

    production_green = all(
        bool(item.get("ok"))
        for item in results.values()
        if item.get("ok") is not None
    )
    worldlinco_green = bool(results.get("G2_worldlinco", {}).get("ok"))

    return {
        "golden_tasks": results,
        "production_green": production_green,
        "worldlinco_green": worldlinco_green,
    }


async def _probe_health(client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get("/api/health")
        ok = response.status_code == 200
        detail = f"status={response.status_code}"
        if ok:
            try:
                payload = response.json()
                detail = str(payload.get("status") or payload.get("detail") or detail)
            except Exception:
                pass
        return {"ok": ok, "detail": detail}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}


async def _probe_voice_translate_smoke(client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.post(
            "/api/llm/voice-translate",
            json={
                "transcript": "안녕하세요",
                "from_lang": "ko",
                "to_lang": "en",
            },
        )
        ok = response.status_code == 200
        detail = f"status={response.status_code}"
        if ok:
            payload = response.json()
            translated = str(payload.get("translated") or "").strip()
            ok = bool(translated)
            detail = (
                f"translated={translated[:80]!r} "
                f"engine={payload.get('engine') or '?'}"
            )
        else:
            try:
                body = response.json()
                detail = str(body.get("detail") or detail)[:200]
            except Exception:
                detail = (response.text or detail)[:200]
        return {"ok": ok, "detail": detail}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}


async def _probe_voip_health(client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get("/api/v1/voip/health")
        ok = response.status_code == 200
        detail = f"status={response.status_code}"
        if ok:
            payload = response.json()
            detail = (
                f"status={payload.get('status')} "
                f"active_calls={payload.get('active_calls')}"
            )
        return {"ok": ok, "detail": detail}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}


async def _probe_voip_initiate(
    client: httpx.AsyncClient,
    *,
    headers: Dict[str, str],
) -> Dict[str, Any]:
    if not headers.get("Authorization"):
        return {
            "ok": None,
            "skipped": True,
            "detail": "skipped — no JWT (provide --token or PROBE_LOGIN_* for initiate)",
        }
    try:
        response = await client.post(
            "/api/v1/voip/calls/initiate",
            json={
                "callee_phone": "+82-10-1111-2222",
                "caller_id": "golden-probe",
                "session_id": "golden-probe-session",
            },
            headers=headers,
        )
        ok = response.status_code == 200
        detail = f"status={response.status_code}"
        if ok:
            payload = response.json()
            call_id = str(payload.get("call_id") or "").strip()
            route = str(payload.get("call_route") or "")
            signaling = str(payload.get("signaling_server") or "")
            ok = bool(call_id) and (
                "/api/v1/voip/signal" in signaling or route in {"native_phone_dialer", "app_webrtc"}
            )
            detail = f"call_id={call_id} route={route} signaling={'yes' if signaling else 'no'}"
        else:
            try:
                body = response.json()
                detail = str(body.get("detail") or detail)[:200]
            except Exception:
                detail = (response.text or detail)[:200]
        return {"ok": ok, "detail": detail}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}


async def _probe_voice_openapi_markers(client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get("/openapi.json")
        if response.status_code != 200:
            return {"ok": False, "detail": f"status={response.status_code}"}
        text = response.text.lower()
        markers = (
            "voice-translate",
            "/api/v1/voip/signal",
            "/api/v1/voip/calls/initiate",
        )
        hits = [marker for marker in markers if marker in text]
        return {
            "ok": bool(hits),
            "detail": f"openapi markers: {', '.join(hits) or 'none'}",
        }
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}


def _summarize_g2(subtasks: Dict[str, Any]) -> str:
    parts = []
    for key, item in subtasks.items():
        if item.get("skipped"):
            parts.append(f"{key}=SKIP")
            continue
        parts.append(f"{key}={'PASS' if item.get('ok') else 'FAIL'}")
    return "; ".join(parts)


async def _probe_admin_settings(
    client: httpx.AsyncClient,
    *,
    headers: Dict[str, str],
) -> Dict[str, Any]:
    if not headers.get("Authorization"):
        return {
            "ok": None,
            "skipped": True,
            "detail": "skipped — no JWT (provide --token or PROBE_LOGIN_* for G3)",
        }
    try:
        response = await client.get("/api/admin/system-settings", headers=headers)
        ok = response.status_code == 200
        detail = f"status={response.status_code}"
        if ok:
            try:
                payload = response.json()
                summary = payload.get("summary") or {}
                detail = (
                    f"models={summary.get('available_model_count', '?')} "
                    f"min_files={summary.get('min_files', '?')}"
                )
            except Exception:
                pass
        return {"ok": ok, "detail": detail}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:240]}
