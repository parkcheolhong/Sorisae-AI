# FILE-ID: FILE-BACKEND-TEST-NADOTONGRYOKSA-SONG-TRANSLATION-CONTRACT-PY
# SECTION-ID: SECTION-BACKEND-TEST-NADOTONGRYOKSA-SONG-TRANSLATION-CONTRACT-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-CONTRACT-TESTS
# CHUNK-ID: CHUNK-BACKEND-TEST-NADOTONGRYOKSA-SONG-TRANSLATION-CONTRACT-001

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.mobile.song_translation import service as song_translation_service
from backend.mobile.song_translation.router import router
from backend.mobile.song_translation.schemas import SongLyricSegment


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _create_seed_job(client: TestClient) -> str:
    response = client.post(
        "/api/mobile/song-translation/jobs",
        data={"target_language": "ko", "source_language": "auto", "quality": "advanced", "mode": "subtitle"},
        files={"file": ("foreign-song.mp3", b"Hello\nThank you\nhelp me\n", "audio/mpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"].startswith("songjob_")
    assert payload["status"] in {"queued", "processing", "completed"}
    return payload["job_id"]


def test_song_translation_job_builds_subtitle_timeline_from_seed_payload():
    client = _build_test_client()
    job_id = _create_seed_job(client)

    status_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "completed"
    assert status_payload["stage"] == "subtitle_ready"
    assert status_payload["source_language"] == "en"
    assert status_payload["target_language"] == "ko"
    assert status_payload["segment_count"] == 3
    assert status_payload["quality_score"] > 0

    subtitles_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}/subtitles")
    assert subtitles_response.status_code == 200
    subtitles_payload = subtitles_response.json()
    assert subtitles_payload["job_id"] == job_id
    assert subtitles_payload["segments"][0]["id"] == "seg_0001"
    assert subtitles_payload["segments"][0]["original"] == "Hello"
    assert subtitles_payload["segments"][0]["translated"] == "안녕하세요"
    assert subtitles_payload["segments"][0]["start_ms"] < subtitles_payload["segments"][0]["end_ms"]


def test_song_translation_segment_patch_and_exports():
    client = _build_test_client()
    job_id = _create_seed_job(client)

    patch_response = client.patch(
        f"/api/mobile/song-translation/jobs/{job_id}/segments/seg_0001",
        json={"translated": "사용자 편집 번역"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["segment"]["edited_by_user"] is True

    srt_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}/export", params={"format": "srt"})
    assert srt_response.status_code == 200
    assert "00:00:00,000 -->" in srt_response.text
    assert "사용자 편집 번역" in srt_response.text

    vtt_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}/export", params={"format": "vtt"})
    assert vtt_response.status_code == 200
    assert vtt_response.text.startswith("WEBVTT")

    lrc_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}/export", params={"format": "lrc"})
    assert lrc_response.status_code == 200
    assert "[00:00." in lrc_response.text

    json_response = client.get(f"/api/mobile/song-translation/jobs/{job_id}/export", params={"format": "json"})
    assert json_response.status_code == 200
    assert json_response.json()["job_id"] == job_id


def test_song_translation_rejects_unsupported_file_type():
    client = _build_test_client()

    response = client.post(
        "/api/mobile/song-translation/jobs",
        data={"target_language": "ko", "source_language": "auto"},
        files={"file": ("lyrics.txt", b"Hello\n", "text/plain")},
    )

    assert response.status_code == 400
    assert "확장자" in response.json()["detail"]


def test_song_translation_file_security_guards(monkeypatch):
    client = _build_test_client()

    safe_filename, content_type = song_translation_service.validate_upload_metadata("../위험한:file.mp3", "audio/mpeg", 12)
    assert safe_filename == "위험한_file.mp3"
    assert content_type == "audio/mpeg"

    mime_response = client.post(
        "/api/mobile/song-translation/jobs",
        data={"target_language": "ko", "source_language": "auto"},
        files={"file": ("foreign-song.mp3", b"Hello\n", "text/plain")},
    )
    assert mime_response.status_code == 400
    assert "MIME" in mime_response.json()["detail"]

    empty_response = client.post(
        "/api/mobile/song-translation/jobs",
        data={"target_language": "ko", "source_language": "auto"},
        files={"file": ("foreign-song.mp3", b"", "audio/mpeg")},
    )
    assert empty_response.status_code == 400
    assert "빈 노래 파일" in empty_response.json()["detail"]

    monkeypatch.setattr(song_translation_service, "MAX_UPLOAD_BYTES", 4)
    oversized_response = client.post(
        "/api/mobile/song-translation/jobs",
        data={"target_language": "ko", "source_language": "auto"},
        files={"file": ("foreign-song.mp3", b"Hello\n", "audio/mpeg")},
    )
    assert oversized_response.status_code == 413
    assert "크기 제한" in oversized_response.json()["detail"]


def test_song_translation_marks_translation_quality_fallbacks(monkeypatch):
    class _SameTextTranslator:
        def translate(self, text: str, from_lang: str = "en", to_lang: str = "ko") -> str:
            return text

    monkeypatch.setattr(song_translation_service.NadoTranslator, "get_instance", classmethod(lambda cls: _SameTextTranslator()))
    segment = SongLyricSegment(
        id="seg_test",
        index=1,
        start_ms=0,
        end_ms=1800,
        original="unknown lyric",
        normalized="unknown lyric",
        translated="",
        source_language="en",
        target_language="ko",
        confidence=0.82,
        detected_by="seed",
        quality_flags=[],
    )

    translated_segments = song_translation_service._translate_segments([segment], "ko")

    assert translated_segments[0].translated == "unknown lyric"
    assert "translation_retry_candidate" in translated_segments[0].quality_flags


def _valid_voice_sample_bytes() -> bytes:
    return bytes((index * 37) % 251 for index in range(256))


def _create_voice_consent(client: TestClient, *, allow_export: bool = True) -> str:
    response = client.post(
        "/api/mobile/song-translation/voice-consents",
        json={
            "consent_version": "2026-05-voice-v1",
            "voice_owner": "self",
            "allow_private_preview": True,
            "allow_export_for_licensed_audio": allow_export,
            "user_id": "contract-user",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_id"].startswith("voiceconsent_")
    assert payload["status"] == "active"
    return payload["consent_id"]


def _create_voice_profile(client: TestClient, consent_id: str) -> str:
    response = client.post(
        "/api/mobile/song-translation/voice-profiles",
        data={"consent_id": consent_id, "profile_label": "계약 테스트 목소리"},
        files={"sample": ("sample.m4a", _valid_voice_sample_bytes(), "audio/m4a")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["voice_profile_id"].startswith("voiceprofile_")
    assert payload["consent_id"] == consent_id
    assert payload["encrypted"] is True
    assert payload["sample_quality_score"] > 0
    return payload["voice_profile_id"]


def test_voice_consent_gate_blocks_profile_creation_without_consent(tmp_path, monkeypatch):
    monkeypatch.setattr(song_translation_service, "VOICE_DATA_DIR", tmp_path)
    client = _build_test_client()

    response = client.post(
        "/api/mobile/song-translation/voice-profiles",
        data={"profile_label": "동의 없는 목소리"},
        files={"sample": ("sample.m4a", _valid_voice_sample_bytes(), "audio/m4a")},
    )

    assert response.status_code == 403
    assert "consent" in response.json()["detail"]


def test_voice_profile_upload_validates_sample_and_delete_revokes_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(song_translation_service, "VOICE_DATA_DIR", tmp_path)
    client = _build_test_client()
    consent_id = _create_voice_consent(client)

    bad_sample = client.post(
        "/api/mobile/song-translation/voice-profiles",
        data={"consent_id": consent_id, "profile_label": "무음"},
        files={"sample": ("silent.m4a", b"\x00" * 64, "audio/m4a")},
    )
    assert bad_sample.status_code == 400
    assert "무음" in bad_sample.json()["detail"]

    profile_id = _create_voice_profile(client, consent_id)
    stored_files = list(tmp_path.glob("*.sample.enc"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes().startswith(b"NVVP1")

    delete_response = client.delete(f"/api/mobile/song-translation/voice-profiles/{profile_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert not stored_files[0].exists()

    get_deleted = client.get(f"/api/mobile/song-translation/voice-profiles/{profile_id}")
    assert get_deleted.status_code == 404


def test_voice_preview_policy_gate_keeps_unverified_exports_open_for_review(tmp_path, monkeypatch):
    monkeypatch.setattr(song_translation_service, "VOICE_DATA_DIR", tmp_path)
    monkeypatch.setattr(song_translation_service, "VOICE_APPROVAL_ALLOWLIST", {"admin-approval-001"})
    client = _build_test_client()
    job_id = _create_seed_job(client)
    consent_id = _create_voice_consent(client, allow_export=True)
    profile_id = _create_voice_profile(client, consent_id)

    unverified_response = client.post(
        f"/api/mobile/song-translation/jobs/{job_id}/voice-preview",
        json={
            "voice_profile_id": profile_id,
            "license_mode": "private_preview_unverified",
            "preview_mode": "translated_lyric_voice",
            "output_scope": "policy_review_export",
            "rights_acknowledged": False,
        },
    )
    assert unverified_response.status_code == 200
    unverified_payload = unverified_response.json()
    assert unverified_payload["effective_output_scope"] == "private_preview"
    assert unverified_payload["gate_status"] == "review_required"
    assert unverified_payload["policy_allowed"] is False
    assert unverified_payload["segment_count"] == 3
    assert "안녕하세요" in unverified_payload["preview_text"]

    approved_response = client.post(
        f"/api/mobile/song-translation/jobs/{job_id}/voice-preview",
        json={
            "voice_profile_id": profile_id,
            "license_mode": "policy_approved_distribution",
            "preview_mode": "translated_lyric_voice",
            "output_scope": "policy_approved_export",
            "rights_acknowledged": True,
            "approval_id": "admin-approval-001",
        },
    )
    assert approved_response.status_code == 200
    approved_payload = approved_response.json()
    assert approved_payload["effective_output_scope"] == "policy_approved_export"
    assert approved_payload["gate_status"] == "allowed"
    assert approved_payload["policy_allowed"] is True


def test_voice_preview_contract_rejects_clone_cover_and_marketplace_export_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(song_translation_service, "VOICE_DATA_DIR", tmp_path)
    monkeypatch.setattr(song_translation_service, "VOICE_APPROVAL_ALLOWLIST", {"admin-approval-001"})
    client = _build_test_client()
    job_id = _create_seed_job(client)

    third_party_consent = client.post(
        "/api/mobile/song-translation/voice-consents",
        json={
            "consent_version": "2026-05-voice-v1",
            "voice_owner": "third_party",
            "allow_private_preview": True,
            "allow_export_for_licensed_audio": True,
            "user_id": "contract-user",
        },
    )
    assert third_party_consent.status_code == 422

    consent_id = _create_voice_consent(client, allow_export=True)
    profile_id = _create_voice_profile(client, consent_id)

    cover_mastering_response = client.post(
        f"/api/mobile/song-translation/jobs/{job_id}/voice-preview",
        json={
            "voice_profile_id": profile_id,
            "license_mode": "policy_approved_distribution",
            "preview_mode": "cover_audio_mastering",
            "output_scope": "policy_approved_export",
            "rights_acknowledged": True,
            "approval_id": "admin-approval-001",
        },
    )
    assert cover_mastering_response.status_code == 422

    marketplace_export_response = client.post(
        f"/api/mobile/song-translation/jobs/{job_id}/voice-preview",
        json={
            "voice_profile_id": profile_id,
            "license_mode": "policy_approved_distribution",
            "preview_mode": "translated_lyric_voice",
            "output_scope": "marketplace_export",
            "rights_acknowledged": True,
            "approval_id": "admin-approval-001",
        },
    )
    assert marketplace_export_response.status_code == 422

    missing_approval_response = client.post(
        f"/api/mobile/song-translation/jobs/{job_id}/voice-preview",
        json={
            "voice_profile_id": profile_id,
            "license_mode": "policy_approved_distribution",
            "preview_mode": "translated_lyric_voice",
            "output_scope": "policy_approved_export",
            "rights_acknowledged": True,
        },
    )
    assert missing_approval_response.status_code == 200
    missing_approval_payload = missing_approval_response.json()
    assert missing_approval_payload["effective_output_scope"] == "policy_review_export"
    assert missing_approval_payload["gate_status"] == "review_required"
    assert missing_approval_payload["policy_allowed"] is False
