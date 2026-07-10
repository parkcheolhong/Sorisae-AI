"""Voice translation relay metadata passthrough."""

from __future__ import annotations

from backend.marketplace.nadotongryoksa_voip_router import _build_voice_translation_relay_payload


def test_voice_translation_relay_payload_includes_chunk_metadata():
    payload = _build_voice_translation_relay_payload(
        {
            "transcript": "hello world",
            "translated_text": "안녕하세요",
            "source_lang": "en",
            "target_lang": "ko",
            "seq_id": 7,
            "utterance_id": "call-1-170000",
            "chunk_index": 2,
            "is_final": False,
            "detected_lang": "en",
        }
    )

    assert payload["type"] == "voice_translation"
    assert payload["seq_id"] == 7
    assert payload["utterance_id"] == "call-1-170000"
    assert payload["chunk_index"] == 2
    assert payload["is_final"] is False
    assert payload["detected_lang"] == "en"
