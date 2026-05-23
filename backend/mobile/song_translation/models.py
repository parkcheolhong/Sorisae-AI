# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-MODELS-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-MODELS-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-VOICE-PERSISTENCE-MODELS
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-MODELS-001

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SongTranslationJobEntity(Base):
    __tablename__ = "mobile_song_translation_jobs"

    job_id = Column(String(64), primary_key=True, index=True)
    status = Column(String(20), nullable=False, index=True)
    stage = Column(String(40), nullable=False, index=True)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=False)
    source_language = Column(String(16), nullable=False)
    target_language = Column(String(16), nullable=False)
    quality = Column(String(32), nullable=False, default="advanced")
    mode = Column(String(32), nullable=False, default="subtitle")
    original_filename = Column(String(220), nullable=False)
    file_hash = Column(String(128), nullable=False, index=True)
    content_type = Column(String(120), nullable=False)
    duration_ms = Column(Integer, nullable=False, default=0)
    quality_score = Column(Float, nullable=False, default=0.0)
    error_code = Column(String(120), nullable=True)
    error_message = Column(Text, nullable=True)
    segments_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False, index=True)


class VoiceConsentEntity(Base):
    __tablename__ = "mobile_song_voice_consents"

    consent_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(80), nullable=False, index=True)
    consent_version = Column(String(80), nullable=False)
    voice_owner = Column(String(20), nullable=False)
    allow_private_preview = Column(Boolean, nullable=False, default=True)
    allow_export_for_licensed_audio = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False, index=True)


class VoiceProfileEntity(Base):
    __tablename__ = "mobile_song_voice_profiles"

    voice_profile_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(80), nullable=False, index=True)
    consent_id = Column(String(64), nullable=False, index=True)
    profile_label = Column(String(80), nullable=False)
    sample_duration_ms = Column(Integer, nullable=False)
    sample_quality_score = Column(Float, nullable=False, default=0.0)
    sample_sha256 = Column(String(128), nullable=False)
    storage_key = Column(Text, nullable=False)
    encrypted = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False, index=True)


class VoicePreviewEntity(Base):
    __tablename__ = "mobile_song_voice_previews"

    preview_id = Column(String(64), primary_key=True, index=True)
    job_id = Column(String(64), nullable=False, index=True)
    voice_profile_id = Column(String(64), nullable=False, index=True)
    license_mode = Column(String(40), nullable=False)
    requested_output_scope = Column(String(40), nullable=False)
    effective_output_scope = Column(String(40), nullable=False)
    gate_status = Column(String(20), nullable=False, index=True)
    policy_allowed = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=False)
    segment_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=False, default=0)
    preview_text = Column(Text, nullable=False)
    preview_audio_path = Column(Text, nullable=True)
    preview_audio_format = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)


class VoicePolicyApprovalEntity(Base):
    __tablename__ = "mobile_song_voice_policy_approvals"

    approval_id = Column(String(120), primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    scope = Column(String(40), nullable=False, default="voice_preview")
    issued_by = Column(String(120), nullable=False, default="system")
    job_id = Column(String(64), nullable=True, index=True)
    voice_profile_id = Column(String(64), nullable=True, index=True)
    note = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow_naive, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False, index=True)
