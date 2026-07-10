"""PostgreSQL-backed JSON document store for WorldLinco ledgers (multi-instance SSOT).

Referral and sales-commission ledgers share one table keyed by store_key.
File fallback remains for local dev/tests (WORLDLINCO_JSON_STORE_BACKEND=file).
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from backend.time_utils import utcnow

STORE_KEY_REFERRALS = "worldlinco_referrals"
STORE_KEY_SALES_COMMISSION = "worldlinco_sales_commission"


def _backend_mode() -> str:
    return (os.getenv("WORLDLINCO_JSON_STORE_BACKEND") or "auto").strip().lower()


def _file_mirror_enabled() -> bool:
    return (os.getenv("WORLDLINCO_JSON_STORE_FILE_MIRROR") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def use_postgres() -> bool:
    mode = _backend_mode()
    if mode == "file":
        return False
    if mode == "postgres":
        return True
    try:
        from backend.marketplace.database import check_database_availability

        ok, _ = check_database_availability()
        return ok
    except Exception:
        return False


def _load_from_file(file_path: Path) -> Optional[Dict[str, Any]]:
    if not file_path.is_file():
        return None
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return raw
    except (OSError, json.JSONDecodeError):
        return None


def _save_to_file(file_path: Path, payload: Dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_table() -> None:
    from backend.marketplace.database import Base, _get_or_create_engine
    from backend.marketplace.models import WorldlincoJsonDocument  # noqa: F401

    Base.metadata.create_all(bind=_get_or_create_engine(), tables=[WorldlincoJsonDocument.__table__])


def _read_postgres(store_key: str) -> Optional[Dict[str, Any]]:
    from backend.marketplace.database import SessionLocal
    from backend.marketplace.models import WorldlincoJsonDocument

    db = SessionLocal()
    try:
        row = db.query(WorldlincoJsonDocument).filter(WorldlincoJsonDocument.store_key == store_key).first()
        if row is None:
            return None
        raw = json.loads(row.payload_json)
        return raw if isinstance(raw, dict) else None
    finally:
        db.close()


def _write_postgres(store_key: str, payload: Dict[str, Any]) -> None:
    from backend.marketplace.database import SessionLocal
    from backend.marketplace.models import WorldlincoJsonDocument

    now = utcnow()
    payload_text = json.dumps(payload, ensure_ascii=False)
    db = SessionLocal()
    try:
        row = db.query(WorldlincoJsonDocument).filter(WorldlincoJsonDocument.store_key == store_key).first()
        if row is None:
            row = WorldlincoJsonDocument(
                store_key=store_key,
                payload_json=payload_text,
                version=1,
                updated_at=now,
            )
            db.add(row)
        else:
            row.payload_json = payload_text
            row.version = int(row.version or 0) + 1
            row.updated_at = now
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_json_document(
    *,
    store_key: str,
    defaults: Dict[str, Any],
    file_path: Path,
) -> Dict[str, Any]:
    base = deepcopy(defaults)
    if use_postgres():
        try:
            _ensure_table()
            raw = _read_postgres(store_key)
            if raw is None:
                file_raw = _load_from_file(file_path)
                if file_raw is not None:
                    merged = {**base, **file_raw}
                    _write_postgres(store_key, merged)
                    return merged
                return base
            return {**base, **raw}
        except Exception:
            pass
    file_raw = _load_from_file(file_path)
    if file_raw is None:
        return base
    return {**base, **file_raw}


def save_json_document(
    *,
    store_key: str,
    file_path: Path,
    payload: Dict[str, Any],
) -> None:
    if use_postgres():
        try:
            _ensure_table()
            _write_postgres(store_key, payload)
            if _file_mirror_enabled():
                _save_to_file(file_path, payload)
            return
        except Exception:
            pass
    _save_to_file(file_path, payload)
