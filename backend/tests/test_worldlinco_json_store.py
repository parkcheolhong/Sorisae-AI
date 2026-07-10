"""WorldLinco JSON document store — file backend roundtrip."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.marketplace.worldlinco_json_store import (
    STORE_KEY_REFERRALS,
    load_json_document,
    save_json_document,
)


@pytest.fixture
def referral_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "worldlinco_referrals.json"
    monkeypatch.setenv("WORLDLINCO_JSON_STORE_BACKEND", "file")
    return path


def test_load_defaults_when_missing(referral_file: Path) -> None:
    defaults = {"version": 1, "codes": {}}
    loaded = load_json_document(
        store_key=STORE_KEY_REFERRALS,
        defaults=defaults,
        file_path=referral_file,
    )
    assert loaded == defaults


def test_save_and_load_roundtrip(referral_file: Path) -> None:
    defaults = {"version": 1, "codes": {}, "signups": []}
    payload = {"version": 1, "codes": {"WLTEST": {"user_id": 1}}, "signups": []}
    save_json_document(store_key=STORE_KEY_REFERRALS, file_path=referral_file, payload=payload)
    loaded = load_json_document(
        store_key=STORE_KEY_REFERRALS,
        defaults=defaults,
        file_path=referral_file,
    )
    assert loaded["codes"]["WLTEST"]["user_id"] == 1
    on_disk = json.loads(referral_file.read_text(encoding="utf-8"))
    assert on_disk["codes"]["WLTEST"]["user_id"] == 1
