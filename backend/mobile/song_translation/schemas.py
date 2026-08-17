# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-SCHEMAS-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-SCHEMAS-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-SCHEMAS
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-SCHEMAS-001

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SongJobStatusValue = Literal["queued", "processing", "completed", "failed"]
VoiceConsentStatusValue = Literal["active", "revoked"]
VoiceProfileStatusValue = Literal["active", "revoked", "deleted"]
VoiceLicenseModeValue = Literal[
    "self_created",
    "licensed",
    "public_domain",
    "private_preview_unverified",
    "policy_approved_distribution",
]
VoiceOutputScopeValue = Literal["private_preview", "user_saved_preview", "policy_review_export", "policy_approved_export"]
VoicePolicyGateStatusValue = Literal["allowed", "review_required", "blocked"]
SongJobStageValue = Literal[
    "queued",
    "validating",
    "normalizing",
    "transcribing",
    "translating",
    "subtitle_ready",
    "failed",
]
SongDetectedByValue = Literal["voice", "script", "manual", "seed"]
SongExportFormatValue = Literal["srt", "vtt", "lrc", "json"]


class SongLyricSegment(BaseModel):
    id: str
    index: int
    start_ms: int
    end_ms: int
    original: str
    normalized: str
    translated: str
    source_language: str
    target_language: str
    confidence: float = Field(ge=0.0, le=1.0)
    detected_by: SongDetectedByValue
    edited_by_user: bool = False
    quality_flags: list[str] = Field(default_factory=list)


class SongJobStatus(BaseModel):
    job_id: str
    status: SongJobStatusValue
    stage: SongJobStageValue
    progress: int = Field(ge=0, le=100)
    message: str
    source_language: str
    target_language: str
    quality: str
    mode: str
    original_filename: str
    file_hash: str
    duration_ms: int = 0
    segment_count: int = 0
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    error_code: str | None = None
    error_message: str | None = None


class SongSubtitleTimeline(BaseModel):
    job_id: str
    source_language: str
    target_language: str
    duration_ms: int
    segment_count: int
    quality_score: float = Field(ge=0.0, le=1.0)
    segments: list[SongLyricSegment]


class SongSegmentPatchRequest(BaseModel):
    translated: str


class SongSegmentPatchResponse(BaseModel):
    job_id: str
    segment: SongLyricSegment


class VoiceConsentRequest(BaseModel):
    consent_version: str = Field(min_length=3, max_length=80)
    voice_owner: Literal["self"] = "self"
    allow_private_preview: bool = True
    allow_export_for_licensed_audio: bool = False
    user_id: str = Field(default="mobile-user", min_length=1, max_length=80)


class VoiceConsentResponse(BaseModel):
    consent_id: str
    user_id: str
    consent_version: str
    voice_owner: str
    allow_private_preview: bool
    allow_export_for_licensed_audio: bool
    status: VoiceConsentStatusValue
    created_at: str


class VoiceProfileResponse(BaseModel):
    voice_profile_id: str
    user_id: str
    consent_id: str
    profile_label: str
    sample_duration_ms: int
    sample_quality_score: float = Field(ge=0.0, le=1.0)
    sample_sha256: str
    encrypted: bool
    status: VoiceProfileStatusValue
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


class VoiceProfileDeleteResponse(BaseModel):
    voice_profile_id: str
    deleted: bool
    status: VoiceProfileStatusValue


class VoicePreviewRequest(BaseModel):
    voice_profile_id: str = Field(min_length=1, max_length=80)
    license_mode: VoiceLicenseModeValue = "private_preview_unverified"
    preview_mode: Literal["translated_lyric_voice"] = "translated_lyric_voice"
    output_scope: VoiceOutputScopeValue = "private_preview"
    rights_acknowledged: bool = False
    approval_id: str | None = Field(default=None, max_length=120)


class VoicePreviewResponse(BaseModel):
    preview_id: str
    job_id: str
    voice_profile_id: str
    license_mode: VoiceLicenseModeValue
    requested_output_scope: VoiceOutputScopeValue
    effective_output_scope: VoiceOutputScopeValue
    gate_status: VoicePolicyGateStatusValue
    policy_allowed: bool
    message: str
    segment_count: int
    duration_ms: int
    preview_text: str
    preview_audio_base64: str | None = None
    preview_audio_format: str | None = None
    preview_audio_available: bool = False
    created_at: str
