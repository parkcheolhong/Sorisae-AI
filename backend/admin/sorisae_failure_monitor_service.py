from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from backend.database import SessionLocal
from backend.marketplace.database import engine as marketplace_engine
from backend.marketplace.models import User
from backend.marketplace.fcm_push import send_push_to_user
from backend.time_utils import utcnow

_MONITOR_DIR_PREFIX = "ui_api_failure_split_"
_FAILURE_CLASSIFICATIONS = {"UI_ONLY_FAILURE", "BOTH_FAIL"}
_PUSH_CHANNEL_ID = "worldlinco_chat_message"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_sorisae_monitor_roots() -> List[Path]:
    repo_root = _repo_root()
    return [
        (repo_root / "backend" / "tmp").resolve(),
        (repo_root / "scripts").resolve(),
    ]


def resolve_sorisae_monitor_root() -> Path:
    configured = str(os.getenv("SORISAE_FAILURE_MONITOR_ROOT", "")).strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_sorisae_monitor_roots()[0]


def _resolve_monitor_roots() -> List[Path]:
    configured = str(os.getenv("SORISAE_FAILURE_MONITOR_ROOT", "")).strip()
    if configured:
        return [Path(configured).expanduser().resolve()]
    return _default_sorisae_monitor_roots()


def _parse_summary_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    parsed: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _resolve_latest_monitor_dir(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates = [
        child for child in root.iterdir()
        if child.is_dir() and child.name.startswith(_MONITOR_DIR_PREFIX)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def _resolve_latest_monitor_dir_across_roots(roots: List[Path]) -> Optional[Path]:
    candidates: List[Path] = []
    for root in roots:
        latest = _resolve_latest_monitor_dir(root)
        if latest is not None:
            candidates.append(latest)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def _normalize_screenshot_items(result: Dict[str, Any]) -> List[Dict[str, str]]:
    ui_top_summary = result.get("uiTopSummary") or {}
    rows = ui_top_summary.get("screenshotTop3Items") or []
    normalized: List[Dict[str, str]] = []
    if not isinstance(rows, list):
        return normalized
    for row in rows[:3]:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "page_label": str(row.get("pageLabel") or "").strip(),
                "screenshot_path": str(row.get("screenshotPath") or "").strip(),
                "screenshot_url": str(row.get("screenshotUrl") or "").strip(),
            }
        )
    return normalized


def load_sorisae_failure_result(result_json_path: str | Path) -> Dict[str, Any]:
    result_path = Path(result_json_path).expanduser().resolve()
    result_dir = result_path.parent
    result = _load_json(result_path)
    summary = _parse_summary_file(result_dir / "smoke_summary.txt")
    ui_report_path = result_dir / "ui_smoke_report.json"

    classification = str(
        result.get("classification")
        or summary.get("classification")
        or "unknown"
    ).strip() or "unknown"
    status = (
        "critical" if classification in _FAILURE_CLASSIFICATIONS else
        "warning" if classification == "API_ONLY_FAILURE" else
        "ok" if classification == "ALL_PASS" else
        "unknown"
    )

    admin_push = result.get("adminPush") if isinstance(result.get("adminPush"), dict) else {}
    notification = result.get("notification") if isinstance(result.get("notification"), dict) else {}
    alert = result.get("alert") if isinstance(result.get("alert"), dict) else {}
    api_summary = ((result.get("api") or {}).get("summary") or {}) if isinstance(result.get("api"), dict) else {}
    ui_top_summary = result.get("uiTopSummary") if isinstance(result.get("uiTopSummary"), dict) else {}

    return {
        "status": status,
        "classification": classification,
        "started_at": result.get("startedAt"),
        "out_dir": str(result.get("outDir") or result_dir),
        "result_json_path": str(result_path),
        "summary_path": str(result_dir / "smoke_summary.txt"),
        "ui_report_path": str(ui_report_path),
        "ui_har_dir": str(result.get("uiHarDir") or ""),
        "alert_file": str(alert.get("alertFile") or ""),
        "alert_latest_file": str(alert.get("latestFile") or ""),
        "api_fail": _coerce_int(result.get("apiFail", api_summary.get("fail"))),
        "ui_fail": _coerce_int(result.get("uiFail", 1 if classification in {"UI_ONLY_FAILURE", "BOTH_FAIL"} else 0)),
        "api_probe_ok": _coerce_int(api_summary.get("ok")),
        "api_probe_total": _coerce_int(api_summary.get("total")),
        "page_top3": [str(item) for item in (ui_top_summary.get("pageTop3") or [])[:3]],
        "request_failed_top3": [str(item) for item in (ui_top_summary.get("requestFailedTop3") or [])[:3]],
        "console_error_top3": [str(item) for item in (ui_top_summary.get("consoleErrorTop3") or [])[:3]],
        "screenshots": _normalize_screenshot_items(result),
        "slack_notified": _coerce_bool(((notification.get("slack") or {}).get("sent"))),
        "teams_notified": _coerce_bool(((notification.get("teams") or {}).get("sent"))),
        "admin_push": {
            "attempted": _coerce_bool(admin_push.get("attempted")),
            "success": _coerce_bool(admin_push.get("success")),
            "classification": str(admin_push.get("classification") or classification),
            "admin_user_count": _coerce_int(admin_push.get("admin_user_count")),
            "success_user_count": _coerce_int(admin_push.get("success_user_count")),
            "failure_user_count": _coerce_int(admin_push.get("failure_user_count")),
            "sent_at": admin_push.get("sent_at"),
            "skipped_reason": admin_push.get("skipped_reason"),
            "users": admin_push.get("users") or [],
        },
    }


def get_latest_sorisae_failure_status() -> Dict[str, Any]:
    monitor_roots = _resolve_monitor_roots()
    monitor_root = monitor_roots[0]
    latest_dir = _resolve_latest_monitor_dir_across_roots(monitor_roots)
    if latest_dir is None:
        return {
            "status": "unknown",
            "classification": "unknown",
            "message": "소리새 장애감지 스모크 결과가 아직 없습니다.",
            "monitor_root": str(monitor_root),
            "monitor_roots": [str(root) for root in monitor_roots],
        }

    result_path = latest_dir / "smoke_result.json"
    if not result_path.exists():
        return {
            "status": "unknown",
            "classification": "unknown",
            "message": "최신 소리새 장애감지 결과 디렉터리에 smoke_result.json 이 없습니다.",
            "monitor_root": str(monitor_root),
            "monitor_roots": [str(root) for root in monitor_roots],
            "out_dir": str(latest_dir),
        }

    payload = load_sorisae_failure_result(result_path)
    payload["monitor_root"] = str(monitor_root)
    payload["monitor_roots"] = [str(root) for root in monitor_roots]
    return payload


def get_latest_sorisae_failure_result_json_payload() -> Dict[str, Any]:
    status = get_latest_sorisae_failure_status()
    result_json_path = str(status.get("result_json_path") or "").strip()
    if not result_json_path:
        raise FileNotFoundError("최신 소리새 장애감지 result_json_path 를 찾지 못했습니다.")

    result_path = Path(result_json_path).expanduser().resolve()
    if not result_path.exists():
        raise FileNotFoundError("최신 소리새 장애감지 smoke_result.json 파일이 없습니다.")

    payload = _load_json(result_path)
    if not payload:
        raise ValueError("최신 소리새 장애감지 smoke_result.json 을 파싱하지 못했습니다.")

    return {
        "result_json_path": str(result_path),
        "payload": payload,
    }


async def push_sorisae_failure_to_admins(result_json_path: str | Path) -> Dict[str, Any]:
    payload = load_sorisae_failure_result(result_json_path)
    classification = str(payload.get("classification") or "unknown")
    result_path = Path(str(payload.get("result_json_path") or result_json_path)).resolve()

    if classification not in _FAILURE_CLASSIFICATIONS:
        push_meta = {
            "attempted": False,
            "success": False,
            "classification": classification,
            "admin_user_count": 0,
            "success_user_count": 0,
            "failure_user_count": 0,
            "sent_at": utcnow().isoformat() + "Z",
            "skipped_reason": "classification_not_pushable",
            "users": [],
        }
        existing = _load_json(result_path)
        existing["adminPush"] = push_meta
        result_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return push_meta

    if SessionLocal.kw.get("bind") is None:
        SessionLocal.configure(bind=marketplace_engine)

    # Helper scripts run in isolated Python processes, so ensure in-memory
    # token registrations are hydrated from DB before attempting push delivery.
    try:
        from backend.marketplace.fcm_push import hydrate_device_registrations_from_db

        hydrate_device_registrations_from_db()
    except Exception:
        pass

    users: List[User] = []
    try:
        db = SessionLocal()
        try:
            users = (
                db.query(User)
                .filter(User.is_active == True)  # noqa: E712
                .filter(or_(User.is_admin == True, User.is_superuser == True))  # noqa: E712
                .order_by(User.id.asc())
                .all()
            )
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        push_meta = {
            "attempted": False,
            "success": False,
            "classification": classification,
            "admin_user_count": 0,
            "success_user_count": 0,
            "failure_user_count": 0,
            "sent_at": utcnow().isoformat() + "Z",
            "skipped_reason": "db_unavailable",
            "error": str(exc),
            "users": [],
        }
        existing = _load_json(result_path)
        existing["adminPush"] = push_meta
        result_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return push_meta

    top_page = next((item for item in payload.get("page_top3") or [] if str(item).strip()), "")
    title = "소리새 장애감지 경고"
    body = (
        f"{classification} · {top_page}"
        if top_page
        else f"{classification} · 관리자 대시보드에서 상세 로그를 확인하세요."
    )
    data_payload = {
        "type": "sorisae_admin_alert",
        "classification": classification,
        "status": payload.get("status") or "unknown",
        "result_json_path": payload.get("result_json_path") or "",
        "out_dir": payload.get("out_dir") or "",
        "ui_report_path": payload.get("ui_report_path") or "",
        "page_top_1": top_page,
    }

    user_results: List[Dict[str, Any]] = []
    success_count = 0
    for user in users:
        success = await send_push_to_user(
            int(user.id),
            data_payload=data_payload,
            title=title,
            body=body,
            channel_id=_PUSH_CHANNEL_ID,
        )
        if success:
            success_count += 1
        user_results.append(
            {
                "user_id": int(user.id),
                "email": str(user.email or ""),
                "success": success,
            }
        )

    push_meta = {
        "attempted": True,
        "success": success_count > 0,
        "classification": classification,
        "admin_user_count": len(users),
        "success_user_count": success_count,
        "failure_user_count": max(0, len(users) - success_count),
        "sent_at": utcnow().isoformat() + "Z",
        "skipped_reason": None,
        "users": user_results,
    }

    existing = _load_json(result_path)
    existing["adminPush"] = push_meta
    result_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return push_meta


async def push_latest_sorisae_failure_to_admins() -> Dict[str, Any]:
    status = get_latest_sorisae_failure_status()
    result_json_path = str(status.get("result_json_path") or "").strip()
    if not result_json_path:
        raise FileNotFoundError("최신 소리새 장애감지 result_json_path 를 찾지 못했습니다.")

    push_meta = await push_sorisae_failure_to_admins(result_json_path)
    return {
        "result_json_path": result_json_path,
        "classification": str(status.get("classification") or "unknown"),
        "admin_push": push_meta,
    }
