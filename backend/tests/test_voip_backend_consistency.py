"""Backend VoIP / voice-relay consistency regression tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.marketplace import nadotongryoksa_voip_router as voip_router


def test_collapse_voice_relay_text_removes_repeated_phrases():
    collapsed = voip_router._collapse_voice_relay_text(
        "hello everyone. hello everyone. hello everyone."
    )
    assert collapsed == "hello everyone"


def test_should_reject_identity_voice_translation_relay():
    assert voip_router._should_reject_voice_translation_relay(
        source_lang="ko",
        target_lang="en",
        transcript="hello",
        translated_text="hello",
    )
    assert not voip_router._should_reject_voice_translation_relay(
        source_lang="ko",
        target_lang="en",
        transcript="안녕하세요",
        translated_text="Hello",
    )


def test_build_voice_translation_relay_payload_rejects_identity_translation():
    payload = voip_router._build_voice_translation_relay_payload(
        {
            "transcript": "hello",
            "translated_text": "hello",
            "source_lang": "ko",
            "target_lang": "en",
        }
    )
    assert payload == {}


def test_prune_connecting_call_with_only_caller_participant(monkeypatch):
    monkeypatch.setattr(voip_router, "STALE_RESUMABLE_CALL_TTL_SECONDS", 60)

    call_state = voip_router.CallState(
        call_id="call-prune-caller-only",
        callee_phone=None,
        caller_id="caller",
        session_id="session-prune",
        caller_user_id=1,
        callee_user_id=2,
        call_route="app_webrtc",
    )
    stale_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=90)
    call_state.set_status("connecting")
    call_state.created_at = stale_at
    call_state.updated_at = stale_at
    call_state.status_changed_at = stale_at
    voip_router.call_states[call_state.call_id] = call_state
    voip_router.call_participants[call_state.call_id] = {"caller": object()}

    class _DummyDb:
        pass

    pruned = voip_router._maybe_prune_stale_resumable_call(call_state, _DummyDb())
    assert pruned is True
    assert call_state.status == "ended"
    assert call_state.error_code == "STALE_SESSION_PRUNED"
    assert call_state.call_id not in voip_router.call_participants

    voip_router.call_states.pop(call_state.call_id, None)


def test_voip_health_includes_network_test_matrix():
    import asyncio

    payload = asyncio.run(voip_router.voip_health())
    matrix = payload.get("network_test_matrix") or {}
    assert matrix.get("wifi_only_insufficient") is True
    assert "wifi_lte" in matrix.get("required_combinations", [])
    assert matrix.get("client_audit_field") == "metadata.client_network"
