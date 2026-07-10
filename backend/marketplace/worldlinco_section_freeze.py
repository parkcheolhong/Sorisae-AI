"""WorldLinco 섹션 freeze SSOT — knowledge/worldlinco_section_freeze.json 읽기 전용.

소리새·VoIP·공유 오디오 경계의 단일 진실원천. 의도적 재기준화 PR 없이
코드에 운율·타이밍을 하드코딩해 양파 패치하지 않는다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Tuple

_ROOT = Path(__file__).resolve().parents[2]
_FREEZE_PATH = _ROOT / "knowledge" / "worldlinco_section_freeze.json"
_APK_BASELINE_PATH = _ROOT / "knowledge" / "worldlinco_apk_baseline.json"

ProsodyTriple = Tuple[str, str, str]


@lru_cache(maxsize=1)
def load_worldlinco_apk_baseline() -> dict:
    if not _APK_BASELINE_PATH.is_file():
        raise FileNotFoundError(f"apk baseline missing: {_APK_BASELINE_PATH}")
    return json.loads(_APK_BASELINE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_worldlinco_section_freeze() -> dict:
    if not _FREEZE_PATH.is_file():
        raise FileNotFoundError(f"section freeze missing: {_FREEZE_PATH}")
    return json.loads(_FREEZE_PATH.read_text(encoding="utf-8"))


def _prosody_triple(raw: object) -> ProsodyTriple:
    if not isinstance(raw, list) or len(raw) != 3:
        raise ValueError(f"invalid prosody triple: {raw!r}")
    return (str(raw[0]), str(raw[1]), str(raw[2]))


def frozen_sorisae_edge_tts_prosody_ko() -> ProsodyTriple:
    """소리새·대면(face.interpret) — freeze sections.sorisae.edge_tts_prosody_ko."""
    freeze = load_worldlinco_section_freeze()
    sorisae = (freeze.get("sections") or {}).get("sorisae") or {}
    return _prosody_triple(sorisae.get("edge_tts_prosody_ko"))


def frozen_voip_edge_tts_prosody_ko_default() -> ProsodyTriple:
    """VoIP 기본(브리지·릴레이) — freeze sections.voip.edge_tts_prosody_ko_default."""
    freeze = load_worldlinco_section_freeze()
    voip = (freeze.get("sections") or {}).get("voip") or {}
    return _prosody_triple(voip.get("edge_tts_prosody_ko_default"))


def frozen_sorisae_playback_cap_ms() -> int:
    freeze = load_worldlinco_section_freeze()
    sorisae = (freeze.get("sections") or {}).get("sorisae") or {}
    return int(sorisae.get("playback_cap_ms", 50_000))
