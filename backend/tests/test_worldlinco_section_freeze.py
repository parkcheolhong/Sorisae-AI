"""섹션 freeze SSOT · VoIP/소리새 TTS 운율 경계 회귀 테스트."""
from __future__ import annotations

import pytest

from backend.marketplace.worldlinco_section_freeze import (
    frozen_sorisae_edge_tts_prosody_ko,
    frozen_voip_edge_tts_prosody_ko_default,
    load_worldlinco_section_freeze,
)


def test_section_freeze_manifest_has_sorisae_and_voip_prosody():
    freeze = load_worldlinco_section_freeze()
    sorisae = (freeze["sections"]["sorisae"]["edge_tts_prosody_ko"])
    voip = (freeze["sections"]["voip"]["edge_tts_prosody_ko_default"])
    assert sorisae == ["-1%", "+18%", "+2Hz"]
    assert voip == ["-4%", "+6%", "+1Hz"]


def test_freeze_loaders_match_manifest():
    assert frozen_sorisae_edge_tts_prosody_ko() == ("-1%", "+18%", "+2Hz")
    assert frozen_voip_edge_tts_prosody_ko_default() == ("-4%", "+6%", "+1Hz")


def test_resolve_edge_tts_prosody_splits_sorisae_and_voip():
    from backend.llm.voice_gateway import _edge_tts_prosody_defaults, _resolve_edge_tts_prosody

    default = _edge_tts_prosody_defaults("ko")
    face = _resolve_edge_tts_prosody("ko", "face.interpret")
    sorisae = _resolve_edge_tts_prosody("ko", "sorisae.friend")
    voip = _resolve_edge_tts_prosody("ko", "voip.voice_relay")
    none_fid = _resolve_edge_tts_prosody("ko", None)

    assert face == ("-1%", "+28%", "+2Hz")
    assert sorisae == frozen_sorisae_edge_tts_prosody_ko()
    assert voip == frozen_voip_edge_tts_prosody_ko_default()
    assert none_fid == default == frozen_voip_edge_tts_prosody_ko_default()
    assert face != sorisae != voip


def test_voip_tts_prosody_module_isolated():
    from backend.voip.voip_tts_prosody import resolve_voip_edge_tts_prosody

    assert resolve_voip_edge_tts_prosody("ko") == frozen_voip_edge_tts_prosody_ko_default()


def test_voip_feature_id_never_gets_sorisae_boost():
    from backend.llm.voice_gateway import _resolve_edge_tts_prosody

    for fid in ("voip.voice_relay", "voip.other", ""):
        got = _resolve_edge_tts_prosody("ko", fid or None)
        assert got == frozen_voip_edge_tts_prosody_ko_default()
