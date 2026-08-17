# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-SERVICE-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-JOB-SERVICE
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-SERVICE-001

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from backend.mobile.song_translation.language import infer_language_from_text, normalize_language_code
from backend.mobile.song_translation import models as song_models
from backend.mobile.song_translation.schemas import (
    SongJobStageValue,
    SongJobStatus,
    SongJobStatusValue,
    SongLyricSegment,
    SongSubtitleTimeline,
    VoiceConsentRequest,
    VoiceConsentResponse,
    VoiceLicenseModeValue,
    VoiceOutputScopeValue,
    VoicePolicyGateStatusValue,
    VoicePreviewRequest,
    VoicePreviewResponse,
    VoiceProfileDeleteResponse,
    VoiceProfileResponse,
)
from backend.mobile.song_translation.subtitles import is_likely_lyric_line, normalize_lyric_line
from backend.services.nadotongryoksa.translator import NadoTranslator, SUPPORTED_LANGUAGES
from backend.database import SessionLocal, engine


logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac"}
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/x-flac",
    "application/octet-stream",
}
MAX_UPLOAD_BYTES = int(os.getenv("NADOTONGRYOKSA_SONG_UPLOAD_MAX_BYTES", str(100 * 1024 * 1024)))
SUPPORTED_EXPORT_FORMATS = {"srt", "vtt", "lrc", "json"}
VOICE_ALLOWED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".webm"}
VOICE_ALLOWED_CONTENT_TYPES = {
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "application/octet-stream",
}
VOICE_MIN_SAMPLE_BYTES = int(os.getenv("NADOTONGRYOKSA_VOICE_MIN_SAMPLE_BYTES", "24"))
VOICE_MAX_SAMPLE_BYTES = int(os.getenv("NADOTONGRYOKSA_VOICE_MAX_SAMPLE_BYTES", str(20 * 1024 * 1024)))
VOICE_DATA_DIR = Path(os.getenv("NADOTONGRYOKSA_VOICE_DATA_DIR", str(Path(tempfile.gettempdir()) / "nadotongryoksa_voice_profiles")))
VOICE_APPROVAL_ALLOWLIST = {
    value.strip()
    for value in os.getenv("NADOTONGRYOKSA_VOICE_APPROVAL_ALLOWLIST", "").split(",")
    if value.strip()
}
VOICE_SYNTH_COMMAND = os.getenv("NADOTONGRYOKSA_VOICE_PREVIEW_SYNTH_COMMAND", "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_secret() -> bytes:
    raw_secret = os.getenv("NADOTONGRYOKSA_VOICE_STORAGE_SECRET") or os.getenv("SECRET_KEY") or "nadotongryoksa-local-voice-secret"
    return hashlib.sha256(raw_secret.encode("utf-8")).digest()


def _xor_stream(payload: bytes, salt: bytes) -> bytes:
    secret = _storage_secret()
    output = bytearray()
    counter = 0
    while len(output) < len(payload):
        counter_bytes = counter.to_bytes(4, "big")
        output.extend(hashlib.sha256(secret + salt + counter_bytes).digest())
        counter += 1
    return bytes(value ^ key for value, key in zip(payload, output[: len(payload)]))


def _encrypt_sample(payload: bytes) -> bytes:
    salt = os.urandom(16)
    encrypted = _xor_stream(payload, salt)
    mac = hashlib.sha256(_storage_secret() + salt + encrypted).digest()
    return b"NVVP1" + salt + mac + encrypted


def _write_encrypted_sample(profile_id: str, payload: bytes) -> str:
    VOICE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    storage_path = VOICE_DATA_DIR / f"{profile_id}.sample.enc"
    storage_path.write_bytes(_encrypt_sample(payload))
    return str(storage_path)


def _delete_storage_path(storage_key: str) -> None:
    if not storage_key:
        return
    try:
        Path(storage_key).unlink(missing_ok=True)
    except OSError:
        return


@dataclass
class SongTranslationJobRecord:
    job_id: str
    status: SongJobStatusValue
    stage: SongJobStageValue
    progress: int
    message: str
    source_language: str
    target_language: str
    quality: str
    mode: str
    original_filename: str
    file_hash: str
    content_type: str
    duration_ms: int = 0
    quality_score: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    segments: list[SongLyricSegment] = field(default_factory=list)


@dataclass
class VoiceConsentRecord:
    consent_id: str
    user_id: str
    consent_version: str
    voice_owner: str
    allow_private_preview: bool
    allow_export_for_licensed_audio: bool
    status: str
    created_at: str


@dataclass
class VoiceProfileRecord:
    voice_profile_id: str
    user_id: str
    consent_id: str
    profile_label: str
    sample_duration_ms: int
    sample_quality_score: float
    sample_sha256: str
    storage_key: str
    encrypted: bool
    status: str
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


@dataclass
class VoicePreviewRecord:
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
    created_at: str
    preview_audio_path: str | None = None
    preview_audio_format: str | None = None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _ensure_song_translation_tables() -> None:
    global _db_unavailable
    if _db_unavailable:
        return
    try:
        song_models.SongTranslationJobEntity.__table__.create(bind=engine, checkfirst=True)
        song_models.VoiceConsentEntity.__table__.create(bind=engine, checkfirst=True)
        song_models.VoiceProfileEntity.__table__.create(bind=engine, checkfirst=True)
        song_models.VoicePreviewEntity.__table__.create(bind=engine, checkfirst=True)
        song_models.VoicePolicyApprovalEntity.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        _db_unavailable = True
        logger.warning("song translation DB persistence is unavailable; falling back to in-memory store", exc_info=True)


def _db_enabled() -> bool:
    _ensure_song_translation_tables()
    return not _db_unavailable


_db_unavailable = False


class SongTranslationJobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, SongTranslationJobRecord] = {}

    def create(self, record: SongTranslationJobRecord) -> SongTranslationJobRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = song_models.SongTranslationJobEntity(
                        job_id=record.job_id,
                        status=record.status,
                        stage=record.stage,
                        progress=record.progress,
                        message=record.message,
                        source_language=record.source_language,
                        target_language=record.target_language,
                        quality=record.quality,
                        mode=record.mode,
                        original_filename=record.original_filename,
                        file_hash=record.file_hash,
                        content_type=record.content_type,
                        duration_ms=record.duration_ms,
                        quality_score=record.quality_score,
                        error_code=record.error_code,
                        error_message=record.error_message,
                        segments_json=json.dumps([segment.model_dump() for segment in record.segments], ensure_ascii=False),
                    )
                    db.merge(entity)
                    db.commit()
            except Exception:
                logger.warning("job persistence write failed, using in-memory fallback", exc_info=True)
        with self._lock:
            self._records[record.job_id] = record
        return record

    def get(self, job_id: str) -> SongTranslationJobRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = db.get(song_models.SongTranslationJobEntity, job_id)
                if entity is not None:
                    segments_payload = json.loads(entity.segments_json or "[]") # pyright: ignore[reportArgumentType]
                    segments = [SongLyricSegment.model_validate(item) for item in segments_payload]
                    return SongTranslationJobRecord(
                        job_id=entity.job_id, # type: ignore
                        status=entity.status,  # type: ignore[arg-type]
                        stage=entity.stage,  # type: ignore[arg-type]
                        progress=entity.progress, # pyright: ignore[reportArgumentType]
                        message=entity.message, # pyright: ignore[reportArgumentType]
                        source_language=entity.source_language, # pyright: ignore[reportArgumentType]
                        target_language=entity.target_language, # pyright: ignore[reportArgumentType]
                        quality=entity.quality, # pyright: ignore[reportArgumentType]
                        mode=entity.mode, # pyright: ignore[reportArgumentType]
                        original_filename=entity.original_filename, # pyright: ignore[reportArgumentType]
                        file_hash=entity.file_hash, # pyright: ignore[reportArgumentType]
                        content_type=entity.content_type, # pyright: ignore[reportArgumentType]
                        duration_ms=entity.duration_ms, # pyright: ignore[reportArgumentType]
                        quality_score=entity.quality_score, # pyright: ignore[reportArgumentType]
                        error_code=entity.error_code, # pyright: ignore[reportArgumentType]
                        error_message=entity.error_message, # pyright: ignore[reportArgumentType]
                        segments=segments,
                    )
            except Exception:
                logger.warning("job persistence read failed, using in-memory fallback", exc_info=True)
        with self._lock:
            record = self._records.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="song translation job not found")
        return record

    def update(self, job_id: str, **changes: object) -> SongTranslationJobRecord:
        record = self.get(job_id)
        for field_name, value in changes.items():
            setattr(record, field_name, value)
        self.create(record)
        return record


job_store = SongTranslationJobStore()


class VoiceConsentStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, VoiceConsentRecord] = {}

    def create(self, record: VoiceConsentRecord) -> VoiceConsentRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = song_models.VoiceConsentEntity(
                        consent_id=record.consent_id,
                        user_id=record.user_id,
                        consent_version=record.consent_version,
                        voice_owner=record.voice_owner,
                        allow_private_preview=record.allow_private_preview,
                        allow_export_for_licensed_audio=record.allow_export_for_licensed_audio,
                        status=record.status,
                        created_at=_parse_iso_datetime(record.created_at) or datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    db.merge(entity)
                    db.commit()
            except Exception:
                logger.warning("voice consent persistence failed, using in-memory fallback", exc_info=True)
        with self._lock:
            self._records[record.consent_id] = record
        return record

    def get_active(self, consent_id: str) -> VoiceConsentRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = db.get(song_models.VoiceConsentEntity, consent_id)
                if entity is not None and entity.status == "active":
                    return VoiceConsentRecord(
                        consent_id=entity.consent_id,
                        user_id=entity.user_id,
                        consent_version=entity.consent_version,
                        voice_owner=entity.voice_owner,
                        allow_private_preview=entity.allow_private_preview,
                        allow_export_for_licensed_audio=entity.allow_export_for_licensed_audio,
                        status=entity.status,
                        created_at=(entity.created_at or datetime.now(timezone.utc).replace(tzinfo=None)).isoformat(),
                    )
            except Exception:
                logger.warning("voice consent read failed, using in-memory fallback", exc_info=True)
        with self._lock:
            record = self._records.get(consent_id)
        if record is None or record.status != "active":
            raise HTTPException(status_code=403, detail="voice consent is required")
        return record


class VoiceProfileStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, VoiceProfileRecord] = {}

    def create(self, record: VoiceProfileRecord) -> VoiceProfileRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = song_models.VoiceProfileEntity(
                        voice_profile_id=record.voice_profile_id,
                        user_id=record.user_id,
                        consent_id=record.consent_id,
                        profile_label=record.profile_label,
                        sample_duration_ms=record.sample_duration_ms,
                        sample_quality_score=record.sample_quality_score,
                        sample_sha256=record.sample_sha256,
                        storage_key=record.storage_key,
                        encrypted=record.encrypted,
                        status=record.status,
                        created_at=_parse_iso_datetime(record.created_at) or datetime.now(timezone.utc).replace(tzinfo=None),
                        last_used_at=_parse_iso_datetime(record.last_used_at),
                        revoked_at=_parse_iso_datetime(record.revoked_at),
                    )
                    db.merge(entity)
                    db.commit()
            except Exception:
                logger.warning("voice profile persistence failed, using in-memory fallback", exc_info=True)
        with self._lock:
            self._records[record.voice_profile_id] = record
        return record

    def get_active(self, voice_profile_id: str) -> VoiceProfileRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = db.get(song_models.VoiceProfileEntity, voice_profile_id)
                if entity is not None and entity.status == "active":
                    return VoiceProfileRecord(
                        voice_profile_id=entity.voice_profile_id, # pyright: ignore[reportArgumentType]
                        user_id=entity.user_id, # pyright: ignore[reportArgumentType]
                        consent_id=entity.consent_id, # pyright: ignore[reportArgumentType]
                        profile_label=entity.profile_label, # pyright: ignore[reportArgumentType]
                        sample_duration_ms=entity.sample_duration_ms, # pyright: ignore[reportArgumentType]
                        sample_quality_score=entity.sample_quality_score, # pyright: ignore[reportArgumentType]
                        sample_sha256=entity.sample_sha256, # pyright: ignore[reportArgumentType]
                        storage_key=entity.storage_key, # pyright: ignore[reportArgumentType]
                        encrypted=entity.encrypted, # pyright: ignore[reportArgumentType]
                        status=entity.status, # pyright: ignore[reportArgumentType]
                        created_at=(entity.created_at or datetime.now(timezone.utc).replace(tzinfo=None)).isoformat(),
                        last_used_at=entity.last_used_at.isoformat() if entity.last_used_at else None, # pyright: ignore[reportGeneralTypeIssues]
                        revoked_at=entity.revoked_at.isoformat() if entity.revoked_at else None, # pyright: ignore[reportGeneralTypeIssues]
                    )
            except Exception:
                logger.warning("voice profile read failed, using in-memory fallback", exc_info=True)
        with self._lock:
            record = self._records.get(voice_profile_id)
        if record is None or record.status != "active":
            raise HTTPException(status_code=404, detail="voice profile not found")
        return record

    def delete(self, voice_profile_id: str) -> VoiceProfileRecord:
        record = self.get_active(voice_profile_id)
        record.status = "deleted"
        record.revoked_at = _utc_now()
        self.create(record)
        _delete_storage_path(record.storage_key)
        return record

    def touch(self, voice_profile_id: str) -> VoiceProfileRecord:
        record = self.get_active(voice_profile_id)
        record.last_used_at = _utc_now()
        self.create(record)
        return record


class VoicePreviewStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, VoicePreviewRecord] = {}

    def create(self, record: VoicePreviewRecord) -> VoicePreviewRecord:
        if _db_enabled():
            try:
                with SessionLocal() as db:
                    entity = song_models.VoicePreviewEntity(
                        preview_id=record.preview_id,
                        job_id=record.job_id,
                        voice_profile_id=record.voice_profile_id,
                        license_mode=record.license_mode,
                        requested_output_scope=record.requested_output_scope,
                        effective_output_scope=record.effective_output_scope,
                        gate_status=record.gate_status,
                        policy_allowed=record.policy_allowed,
                        message=record.message,
                        segment_count=record.segment_count,
                        duration_ms=record.duration_ms,
                        preview_text=record.preview_text,
                        preview_audio_path=record.preview_audio_path,
                        preview_audio_format=record.preview_audio_format,
                        created_at=_parse_iso_datetime(record.created_at) or datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    db.merge(entity)
                    db.commit()
            except Exception:
                logger.warning("voice preview persistence failed, using in-memory fallback", exc_info=True)
        with self._lock:
            self._records[record.preview_id] = record
        return record


voice_consent_store = VoiceConsentStore()
voice_profile_store = VoiceProfileStore()
voice_preview_store = VoicePreviewStore()


def sanitize_filename(filename: str) -> str:
    basename = Path(str(filename or "song-upload")).name.strip() or "song-upload"
    return re.sub(r"[^A-Za-z0-9가-힣._ -]", "_", basename)[:180]


def validate_upload_metadata(filename: str, content_type: str, size_bytes: int) -> tuple[str, str]:
    safe_filename = sanitize_filename(filename)
    extension = Path(safe_filename).suffix.lower()
    normalized_content_type = str(content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="지원하지 않는 노래 파일 확장자입니다.")
    if normalized_content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="지원하지 않는 노래 파일 MIME 타입입니다.")
    if size_bytes <= 0:
        raise HTTPException(status_code=400, detail="빈 노래 파일은 처리할 수 없습니다.")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="노래 파일 크기 제한을 초과했습니다.")
    return safe_filename, normalized_content_type


async def read_and_validate_upload(file: UploadFile) -> tuple[bytes, str, str, str]:
    payload = await file.read()
    safe_filename, content_type = validate_upload_metadata(file.filename or "song.mp3", file.content_type or "", len(payload))
    file_hash = hashlib.sha256(payload).hexdigest()
    return payload, safe_filename, content_type, file_hash


def build_status(record: SongTranslationJobRecord) -> SongJobStatus:
    return SongJobStatus(
        job_id=record.job_id,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
        message=record.message,
        source_language=record.source_language,
        target_language=record.target_language,
        quality=record.quality,
        mode=record.mode,
        original_filename=record.original_filename,
        file_hash=record.file_hash,
        duration_ms=record.duration_ms,
        segment_count=len(record.segments),
        quality_score=record.quality_score,
        error_code=record.error_code,
        error_message=record.error_message,
    )


def _build_voice_consent(record: VoiceConsentRecord) -> VoiceConsentResponse:
    return VoiceConsentResponse(
        consent_id=record.consent_id,
        user_id=record.user_id,
        consent_version=record.consent_version,
        voice_owner=record.voice_owner,
        allow_private_preview=record.allow_private_preview,
        allow_export_for_licensed_audio=record.allow_export_for_licensed_audio,
        status=record.status,  # type: ignore[arg-type]
        created_at=record.created_at,
    )


def _build_voice_profile(record: VoiceProfileRecord) -> VoiceProfileResponse:
    return VoiceProfileResponse(
        voice_profile_id=record.voice_profile_id,
        user_id=record.user_id,
        consent_id=record.consent_id,
        profile_label=record.profile_label,
        sample_duration_ms=record.sample_duration_ms,
        sample_quality_score=record.sample_quality_score,
        sample_sha256=record.sample_sha256,
        encrypted=record.encrypted,
        status=record.status,  # type: ignore[arg-type]
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )


def _build_voice_preview(record: VoicePreviewRecord) -> VoicePreviewResponse:
    preview_audio_base64: str | None = None
    if record.preview_audio_path:
        audio_path = Path(record.preview_audio_path)
        try:
            if audio_path.exists() and audio_path.is_file():
                preview_audio_base64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        except Exception:
            logger.warning("voice preview audio load failed", exc_info=True)
    return VoicePreviewResponse(
        preview_id=record.preview_id,
        job_id=record.job_id,
        voice_profile_id=record.voice_profile_id,
        license_mode=record.license_mode,
        requested_output_scope=record.requested_output_scope,
        effective_output_scope=record.effective_output_scope,
        gate_status=record.gate_status,
        policy_allowed=record.policy_allowed,
        message=record.message,
        segment_count=record.segment_count,
        duration_ms=record.duration_ms,
        preview_text=record.preview_text,
        preview_audio_base64=preview_audio_base64,
        preview_audio_format=record.preview_audio_format,
        preview_audio_available=bool(preview_audio_base64),
        created_at=record.created_at,
    )


def build_timeline(record: SongTranslationJobRecord) -> SongSubtitleTimeline:
    if record.status == "failed":
        raise HTTPException(status_code=409, detail=record.error_message or "song translation job failed")
    if record.status != "completed":
        raise HTTPException(status_code=202, detail="song translation job is not completed yet")
    return SongSubtitleTimeline(
        job_id=record.job_id,
        source_language=record.source_language,
        target_language=record.target_language,
        duration_ms=record.duration_ms,
        segment_count=len(record.segments),
        quality_score=record.quality_score,
        segments=list(record.segments),
    )


def create_voice_consent(payload: VoiceConsentRequest) -> VoiceConsentResponse:
    if not payload.allow_private_preview:
        raise HTTPException(status_code=400, detail="private voice preview consent is required")
    record = VoiceConsentRecord(
        consent_id=f"voiceconsent_{uuid4().hex[:16]}",
        user_id=str(payload.user_id).strip() or "mobile-user",
        consent_version=str(payload.consent_version).strip(),
        voice_owner=payload.voice_owner,
        allow_private_preview=payload.allow_private_preview,
        allow_export_for_licensed_audio=payload.allow_export_for_licensed_audio,
        status="active",
        created_at=_utc_now(),
    )
    return _build_voice_consent(voice_consent_store.create(record))


def _validate_voice_sample_metadata(filename: str, content_type: str, size_bytes: int) -> tuple[str, str]:
    safe_filename = sanitize_filename(filename or "voice-sample.m4a")
    extension = Path(safe_filename).suffix.lower()
    normalized_content_type = str(content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if extension not in VOICE_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="지원하지 않는 음성 샘플 확장자입니다.")
    if normalized_content_type not in VOICE_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="지원하지 않는 음성 샘플 MIME 타입입니다.")
    if size_bytes < VOICE_MIN_SAMPLE_BYTES:
        raise HTTPException(status_code=400, detail="음성 샘플이 너무 짧거나 비어 있습니다.")
    if size_bytes > VOICE_MAX_SAMPLE_BYTES:
        raise HTTPException(status_code=413, detail="음성 샘플 크기 제한을 초과했습니다.")
    return safe_filename, normalized_content_type


def _score_voice_sample(payload: bytes) -> tuple[int, float]:
    if not payload or len(set(payload[: min(len(payload), 4096)])) <= 1:
        raise HTTPException(status_code=400, detail="무음 또는 손상된 음성 샘플로 판단되었습니다.")
    sample_window = payload[: min(len(payload), 8192)]
    unique_ratio = len(set(sample_window)) / max(1, len(sample_window))
    quality_score = round(max(0.35, min(0.98, 0.55 + unique_ratio * 1.8)), 2)
    duration_ms = max(1000, min(60000, int(len(payload) / 32)))
    return duration_ms, quality_score


async def read_voice_sample_upload(file: UploadFile) -> tuple[bytes, str, str, str, int, float]:
    payload = await file.read()
    safe_filename, content_type = _validate_voice_sample_metadata(file.filename or "voice-sample.m4a", file.content_type or "", len(payload))
    duration_ms, quality_score = _score_voice_sample(payload)
    sample_hash = hashlib.sha256(payload).hexdigest()
    return payload, safe_filename, content_type, sample_hash, duration_ms, quality_score


def create_voice_profile(
    *,
    consent_id: str,
    profile_label: str,
    sample_bytes: bytes,
    sample_sha256: str,
    sample_duration_ms: int,
    sample_quality_score: float,
) -> VoiceProfileResponse:
    consent = voice_consent_store.get_active(str(consent_id or "").strip())
    profile_id = f"voiceprofile_{uuid4().hex[:16]}"
    storage_key = _write_encrypted_sample(profile_id, sample_bytes)
    record = VoiceProfileRecord(
        voice_profile_id=profile_id,
        user_id=consent.user_id,
        consent_id=consent.consent_id,
        profile_label=str(profile_label or "내 목소리").strip()[:80] or "내 목소리",
        sample_duration_ms=sample_duration_ms,
        sample_quality_score=sample_quality_score,
        sample_sha256=sample_sha256,
        storage_key=storage_key,
        encrypted=True,
        status="active",
        created_at=_utc_now(),
    )
    return _build_voice_profile(voice_profile_store.create(record))


def get_voice_profile(voice_profile_id: str) -> VoiceProfileResponse:
    return _build_voice_profile(voice_profile_store.get_active(voice_profile_id))


def delete_voice_profile(voice_profile_id: str) -> VoiceProfileDeleteResponse:
    record = voice_profile_store.delete(voice_profile_id)
    return VoiceProfileDeleteResponse(voice_profile_id=record.voice_profile_id, deleted=True, status="deleted")


def _is_valid_approval_id_format(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,119}", value))


def _is_policy_approval_valid(approval_id: str, *, job_id: str, voice_profile_id: str) -> bool:
    if not _is_valid_approval_id_format(approval_id):
        return False
    if approval_id in VOICE_APPROVAL_ALLOWLIST:
        return True
    _ensure_song_translation_tables()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        approval = db.get(song_models.VoicePolicyApprovalEntity, approval_id)
        if approval is None or approval.status != "active": # pyright: ignore[reportGeneralTypeIssues]
            return False
        if approval.expires_at and approval.expires_at < now: # pyright: ignore[reportGeneralTypeIssues]
            return False
        if approval.scope not in {"voice_preview", "policy_approved_distribution", "all"}:
            return False
        if approval.job_id and approval.job_id != job_id: # pyright: ignore[reportGeneralTypeIssues]
            return False
        if approval.voice_profile_id and approval.voice_profile_id != voice_profile_id: # pyright: ignore[reportGeneralTypeIssues]
            return False
        return True


def _synthesize_preview_audio(preview_id: str, preview_text: str, sample_storage_key: str) -> tuple[str | None, str | None]:
    command = VOICE_SYNTH_COMMAND
    if not command:
        return None, None
    sample_bytes = _read_encrypted_sample(sample_storage_key) # type: ignore
    preview_audio_path = VOICE_DATA_DIR / f"{preview_id}.wav"
    sample_path = VOICE_DATA_DIR / f"{preview_id}.sample"
    sample_path.write_bytes(sample_bytes)
    try:
        proc = subprocess.run(
            [command, str(sample_path), preview_text, str(preview_audio_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not preview_audio_path.exists():
            logger.warning("voice preview synthesis failed: %s", (proc.stderr or "").strip() or "unknown")
            return None, None
        return str(preview_audio_path), "audio/wav"
    finally:
        try:
            sample_path.unlink(missing_ok=True)
        except Exception:
            logger.debug("temporary sample cleanup failed", exc_info=True)


def _decide_voice_policy(
    *,
    job_id: str,
    voice_profile_id: str,
    consent: VoiceConsentRecord,
    license_mode: VoiceLicenseModeValue,
    requested_scope: VoiceOutputScopeValue,
    rights_acknowledged: bool,
    approval_id: str | None,
) -> tuple[VoiceOutputScopeValue, VoicePolicyGateStatusValue, bool, str]:
    if requested_scope in {"private_preview", "user_saved_preview"}:
        return requested_scope, "allowed", True, "개인 번역가사 preview가 허용되었습니다."
    if license_mode == "private_preview_unverified" and not rights_acknowledged:
        return "private_preview", "review_required", False, "권리 확인 전이므로 개인 preview로 보류되었습니다."
    if license_mode in {"self_created", "licensed", "public_domain"}:
        if rights_acknowledged and consent.allow_export_for_licensed_audio:
            return requested_scope, "allowed", True, "권리 확인과 책임 고지를 통과해 export 후보가 허용되었습니다."
        return "private_preview", "review_required", False, "export를 열려면 권리 확인과 export 동의가 필요합니다."
    if license_mode == "policy_approved_distribution":
        normalized_approval_id = str(approval_id or "").strip()
        if rights_acknowledged and normalized_approval_id and _is_policy_approval_valid(
            normalized_approval_id,
            job_id=job_id,
            voice_profile_id=voice_profile_id,
        ):
            return "policy_approved_export", "allowed", True, "운영 정책 승인에 따라 공유/export가 활성화되었습니다."
        return "policy_review_export", "review_required", False, "유효한 운영 승인 ID가 필요합니다."
    return "private_preview", "blocked", False, "지원하지 않는 권리 정책입니다."


def create_voice_preview(job_id: str, payload: VoicePreviewRequest) -> VoicePreviewResponse:
    timeline = build_timeline(job_store.get(job_id))
    profile = voice_profile_store.get_active(payload.voice_profile_id)
    consent = voice_consent_store.get_active(profile.consent_id)
    effective_scope, gate_status, policy_allowed, message = _decide_voice_policy(
        job_id=job_id,
        voice_profile_id=profile.voice_profile_id,
        consent=consent,
        license_mode=payload.license_mode,
        requested_scope=payload.output_scope,
        rights_acknowledged=payload.rights_acknowledged,
        approval_id=payload.approval_id,
    )
    voice_profile_store.touch(profile.voice_profile_id)
    preview_lines = [segment.translated.strip() or segment.normalized.strip() for segment in timeline.segments]
    preview_text = "\n".join(line for line in preview_lines if line)[:6000]
    preview_id = f"voicepreview_{uuid4().hex[:16]}"
    preview_audio_path: str | None = None
    preview_audio_format: str | None = None
    if policy_allowed:
        preview_audio_path, preview_audio_format = _synthesize_preview_audio(
            preview_id,
            preview_text,
            profile.storage_key,
        )
    record = VoicePreviewRecord(
        preview_id=preview_id,
        job_id=job_id,
        voice_profile_id=profile.voice_profile_id,
        license_mode=payload.license_mode,
        requested_output_scope=payload.output_scope,
        effective_output_scope=effective_scope,
        gate_status=gate_status,
        policy_allowed=policy_allowed,
        message=message,
        segment_count=timeline.segment_count,
        duration_ms=timeline.duration_ms,
        preview_text=preview_text,
        preview_audio_path=preview_audio_path,
        preview_audio_format=preview_audio_format,
        created_at=_utc_now(),
    )
    return _build_voice_preview(voice_preview_store.create(record))


def create_job_record(
    *,
    filename: str,
    content_type: str,
    file_hash: str,
    source_language: str,
    target_language: str,
    quality: str,
    mode: str,
) -> SongTranslationJobRecord:
    normalized_source = normalize_language_code(source_language, allow_auto=True, fallback="auto")
    normalized_target = normalize_language_code(target_language, fallback="ko")
    if normalized_target == "auto":
        normalized_target = "ko"
    if normalized_target not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="지원하지 않는 목표 언어입니다.")
    record = SongTranslationJobRecord(
        job_id=f"songjob_{uuid4().hex[:16]}",
        status="queued",
        stage="queued",
        progress=0,
        message="노래 번역 작업이 대기열에 등록되었습니다.",
        source_language=normalized_source,
        target_language=normalized_target,
        quality=str(quality or "advanced").strip().lower() or "advanced",
        mode=str(mode or "subtitle").strip().lower() or "subtitle",
        original_filename=filename,
        file_hash=file_hash,
        content_type=content_type,
    )
    return job_store.create(record)


def _decode_text_seed(audio_bytes: bytes) -> list[str]:
    if not audio_bytes:
        return []
    try:
        decoded = audio_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return []
    if "\x00" in decoded:
        return []
    lines = [normalize_lyric_line(line) for line in decoded.replace("\r\n", "\n").split("\n")]
    return [line for line in lines if is_likely_lyric_line(line)]


def _run_faster_whisper_segments(audio_bytes: bytes, source_language: str) -> tuple[list[dict], str | None]:
    model_name = os.getenv("FASTER_WHISPER_MODEL", "tiny")
    device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
    timeout_sec = int(os.getenv("NADOTONGRYOKSA_SONG_STT_TIMEOUT_SEC", "300"))
    language_hint = "" if source_language == "auto" else normalize_language_code(source_language, fallback="")
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "song_input.bin"
        audio_path.write_bytes(audio_bytes)
        script = """
import json
import sys
from faster_whisper import WhisperModel

audio_path = sys.argv[1]
model_name = sys.argv[2]
device = sys.argv[3]
compute_type = sys.argv[4]
language_hint = sys.argv[5] if len(sys.argv) > 5 else ""

model = WhisperModel(model_name, device=device, compute_type=compute_type)
kwargs = {}
if language_hint:
    kwargs["language"] = language_hint
segments, info = model.transcribe(audio_path, **kwargs)
payload = []
for index, segment in enumerate(segments, start=1):
    payload.append({
        "index": index,
        "start": float(getattr(segment, "start", 0.0) or 0.0),
        "end": float(getattr(segment, "end", 0.0) or 0.0),
        "text": str(getattr(segment, "text", "") or "").strip(),
        "avg_logprob": float(getattr(segment, "avg_logprob", -0.2) or -0.2),
    })
detected = str(getattr(info, "language", "") or "").strip()
print(json.dumps({"segments": payload, "detected_language": detected}, ensure_ascii=False))
"""
        command = [sys.executable, "-c", script, str(audio_path), model_name, device, compute_type]
        if language_hint:
            command.append(language_hint)
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout_sec)
        if process.returncode != 0:
            raise RuntimeError((process.stderr or "").strip() or "faster-whisper failed")
        parsed = json.loads((process.stdout or "{}").strip() or "{}")
        return list(parsed.get("segments") or []), str(parsed.get("detected_language") or "").strip() or None


def _segment_confidence(raw_segment: dict) -> float:
    avg_logprob = float(raw_segment.get("avg_logprob", -0.2) or -0.2)
    return max(0.25, min(0.99, round(0.85 + avg_logprob / 3.0, 2)))


def _build_seed_segments(lines: list[str], source_language: str) -> tuple[list[SongLyricSegment], str]:
    detected_source = source_language if source_language != "auto" else infer_language_from_text("\n".join(lines), "en")
    segments: list[SongLyricSegment] = []
    cursor_ms = 0
    for index, line in enumerate(lines, start=1):
        duration_ms = max(1800, min(8000, 1400 + len(line) * 80))
        segments.append(
            SongLyricSegment(
                id=f"seg_{index:04d}",
                index=index,
                start_ms=cursor_ms,
                end_ms=cursor_ms + duration_ms,
                original=line,
                normalized=line,
                translated="",
                source_language=detected_source,
                target_language="ko",
                confidence=0.82,
                detected_by="seed",
                quality_flags=["text_seed"],
            )
        )
        cursor_ms += duration_ms + 250
    return segments, detected_source


def _build_whisper_segments(raw_segments: list[dict], source_language: str, detected_language: str | None) -> tuple[list[SongLyricSegment], str]:
    detected_source = source_language if source_language != "auto" else normalize_language_code(detected_language, fallback="en")
    segments: list[SongLyricSegment] = []
    for raw_segment in raw_segments:
        original = normalize_lyric_line(str(raw_segment.get("text") or ""))
        if not is_likely_lyric_line(original):
            continue
        index = len(segments) + 1
        start_ms = max(0, int(float(raw_segment.get("start") or 0.0) * 1000))
        end_ms = max(start_ms + 1000, int(float(raw_segment.get("end") or 0.0) * 1000))
        confidence = _segment_confidence(raw_segment)
        quality_flags: list[str] = []
        if confidence < 0.65:
            quality_flags.append("low_confidence")
        if end_ms - start_ms > 8000:
            quality_flags.append("long_segment")
        segments.append(
            SongLyricSegment(
                id=f"seg_{index:04d}",
                index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                original=original,
                normalized=original,
                translated="",
                source_language=detected_source,
                target_language="ko",
                confidence=confidence,
                detected_by="voice",
                quality_flags=quality_flags,
            )
        )
    return segments, detected_source


def _translate_segments(segments: list[SongLyricSegment], target_language: str) -> list[SongLyricSegment]:
    translator = NadoTranslator.get_instance()
    translated_segments: list[SongLyricSegment] = []
    translation_cache: dict[tuple[str, str, str], str] = {}
    
    # ===== TRANSLATION PHASE TIMING BREAKDOWN =====
    segment_timing = []
    cache_hits = 0
    cache_misses = 0
    
    for i, segment in enumerate(segments):
        cache_key = (segment.source_language, target_language, segment.normalized)
        segment_start = time.time()
        
        translated = translation_cache.get(cache_key)
        if translated is None:
            # ===== LLM INFERENCE TIMING =====
            llm_start = time.time()
            translated = translator.translate(segment.normalized, from_lang=segment.source_language, to_lang=target_language)
            llm_elapsed = time.time() - llm_start
            translation_cache[cache_key] = translated
            cache_misses += 1
            is_cache_hit = False
        else:
            llm_elapsed = 0.0
            cache_hits += 1
            is_cache_hit = True
        
        segment_elapsed = time.time() - segment_start
        segment_timing.append({
            'index': i,
            'text_len': len(segment.normalized),
            'total_ms': round(segment_elapsed * 1000, 1),
            'llm_ms': round(llm_elapsed * 1000, 1),
            'cache_hit': is_cache_hit,
        })
        
        quality_flags = list(segment.quality_flags)
        if not translated.strip():
            translated = segment.normalized
            quality_flags.append("empty_translation_fallback")
        if translated.strip().lower() == segment.normalized.strip().lower() and segment.source_language != target_language:
            quality_flags.append("translation_retry_candidate")
        translated_segments.append(
            _copy_segment(
                segment,
                {
                    "translated": translated.strip(),
                    "target_language": target_language,
                    "quality_flags": sorted(set(quality_flags)),
                },
            )
        )
    
    # ===== LOG SEGMENT-LEVEL BREAKDOWN =====
    avg_segment_time = sum(t['total_ms'] for t in segment_timing) / len(segment_timing) if segment_timing else 0
    max_segment_time = max((t['total_ms'] for t in segment_timing), default=0)
    cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
    
    logger.info(
        f"[TRANSLATE_SEGMENTS] segments={len(segments)} | "
        f"cache_hits={cache_hits} cache_misses={cache_misses} hit_rate={cache_hit_rate:.1f}% | "
        f"avg_segment={avg_segment_time:.1f}ms max_segment={max_segment_time:.1f}ms"
    )
    
    # Log slowest segments for debugging
    sorted_segments = sorted(segment_timing, key=lambda x: x['total_ms'], reverse=True)
    for seg in sorted_segments[:3]:  # Top 3 slowest
        logger.debug(
            f"[SLOW_SEGMENT] idx={seg['index']} text_len={seg['text_len']} "
            f"total={seg['total_ms']}ms llm={seg['llm_ms']}ms cache_hit={seg['cache_hit']}"
        )
    
    return translated_segments


def _calculate_quality_score(segments: list[SongLyricSegment]) -> float:
    if not segments:
        return 0.0
    confidence_score = sum(segment.confidence for segment in segments) / len(segments)
    penalty = min(0.35, sum(len(segment.quality_flags) for segment in segments) * 0.015)
    return round(max(0.0, min(1.0, confidence_score - penalty)), 2)


def _copy_segment(segment: SongLyricSegment, update: dict[str, object]) -> SongLyricSegment:
    if hasattr(segment, "model_copy"):
        return segment.model_copy(update=update)
    return segment.copy(update=update)


def process_song_translation_job(job_id: str, audio_bytes: bytes) -> None:
    try:
        # Timing tracking for performance analysis
        timing_log = {}
        
        record = job_store.update(job_id, status="processing", stage="validating", progress=10, message="노래 파일 검증을 완료했습니다.")
        job_store.update(job_id, stage="normalizing", progress=25, message="음원 정규화 단계를 준비했습니다.")
        job_store.update(job_id, stage="transcribing", progress=45, message="가사 구간을 추출하고 있습니다.")
        
        # ===== TRANSCRIBING PHASE TIMING =====
        transcribe_start = time.time()
        text_seed_lines = _decode_text_seed(audio_bytes)
        if text_seed_lines:
            segments, detected_source = _build_seed_segments(text_seed_lines, record.source_language)
        else:
            raw_segments, detected_language = _run_faster_whisper_segments(audio_bytes, record.source_language)
            segments, detected_source = _build_whisper_segments(raw_segments, record.source_language, detected_language)
        transcribe_elapsed = time.time() - transcribe_start
        timing_log['transcribing_sec'] = round(transcribe_elapsed, 2)
        logger.info(f"[JOB {job_id}] TRANSCRIBING={transcribe_elapsed:.2f}s (segments={len(segments) if segments else 0})")
        
        if not segments:
            raise RuntimeError("가사로 판단되는 세그먼트를 찾지 못했습니다.")
        job_store.update(job_id, source_language=detected_source, stage="translating", progress=72, message="세그먼트별 가사를 번역하고 있습니다.")
        
        # ===== TRANSLATING PHASE TIMING =====
        translate_start = time.time()
        translated_segments = _translate_segments(segments, record.target_language)
        translate_elapsed = time.time() - translate_start
        timing_log['translating_sec'] = round(translate_elapsed, 2)
        logger.info(f"[JOB {job_id}] TRANSLATING={translate_elapsed:.2f}s (segments={len(translated_segments)})")
        # ===== SUMMARY TIMING LOG =====
        total_elapsed = transcribe_elapsed + translate_elapsed
        logger.info(
            f"[JOB {job_id}] TOTAL={total_elapsed:.2f}s | "
            f"TRANSCRIBE={timing_log['transcribing_sec']}s | "
            f"TRANSLATE={timing_log['translating_sec']}s | "
            f"SEGMENTS={len(translated_segments)}"
        )
        
        duration_ms = max(segment.end_ms for segment in translated_segments)
        quality_score = _calculate_quality_score(translated_segments)
        job_store.update(
            job_id,
            status="completed",
            stage="subtitle_ready",
            progress=100,
            message="번역 자막 타임라인이 준비되었습니다.",
            segments=translated_segments,
            duration_ms=duration_ms,
            quality_score=quality_score,
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status="failed",
            stage="failed",
            progress=100,
            message="노래 번역 작업이 실패했습니다.",
            error_code="SONG_TRANSLATION_FAILED",
            error_message=str(exc),
        )


def patch_segment_translation(job_id: str, segment_id: str, translated: str) -> SongLyricSegment:
    translated_text = str(translated or "").strip()
    if not translated_text:
        raise HTTPException(status_code=400, detail="translated text is required")
    record = job_store.get(job_id)
    updated_segments: list[SongLyricSegment] = []
    updated_segment: SongLyricSegment | None = None
    for segment in record.segments:
        if segment.id == segment_id:
            updated_segment = _copy_segment(segment, {"translated": translated_text, "edited_by_user": True})
            updated_segments.append(updated_segment)
        else:
            updated_segments.append(segment)
    if updated_segment is None:
        raise HTTPException(status_code=404, detail="song subtitle segment not found")
    job_store.update(job_id, segments=updated_segments, quality_score=_calculate_quality_score(updated_segments))
    return updated_segment
