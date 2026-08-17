# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-ROUTER-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-ROUTER-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-API
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-ROUTER-001

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from backend.mobile.song_translation.schemas import (
    SongJobStatus,
    SongSegmentPatchRequest,
    SongSegmentPatchResponse,
    SongSubtitleTimeline,
    VoiceConsentRequest,
    VoiceConsentResponse,
    VoicePreviewRequest,
    VoicePreviewResponse,
    VoiceProfileDeleteResponse,
    VoiceProfileResponse,
)
from backend.mobile.song_translation.service import (
    SUPPORTED_EXPORT_FORMATS,
    build_status,
    build_timeline,
    create_voice_consent,
    create_voice_preview,
    create_voice_profile,
    create_job_record,
    delete_voice_profile,
    get_voice_profile,
    job_store,
    patch_segment_translation,
    process_song_translation_job,
    read_voice_sample_upload,
    read_and_validate_upload,
)
from backend.mobile.song_translation.subtitles import render_json, render_lrc, render_srt, render_vtt


router = APIRouter(prefix="/api/mobile/song-translation", tags=["mobile-song-translation"])


@router.post("/jobs", response_model=SongJobStatus)
async def create_song_translation_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_language: str = Form("ko"),
    source_language: str = Form("auto"),
    quality: str = Form("advanced"),
    mode: str = Form("subtitle"),
) -> SongJobStatus:
    audio_bytes, safe_filename, content_type, file_hash = await read_and_validate_upload(file)
    record = create_job_record(
        filename=safe_filename,
        content_type=content_type,
        file_hash=file_hash,
        source_language=source_language,
        target_language=target_language,
        quality=quality,
        mode=mode,
    )
    background_tasks.add_task(process_song_translation_job, record.job_id, audio_bytes)
    return build_status(record)


@router.get("/jobs/{job_id}", response_model=SongJobStatus)
async def get_song_translation_job(job_id: str) -> SongJobStatus:
    return build_status(job_store.get(job_id))


@router.get("/jobs/{job_id}/subtitles", response_model=SongSubtitleTimeline)
async def get_song_translation_subtitles(job_id: str) -> SongSubtitleTimeline:
    return build_timeline(job_store.get(job_id))


@router.patch("/jobs/{job_id}/segments/{segment_id}", response_model=SongSegmentPatchResponse)
async def patch_song_translation_segment(job_id: str, segment_id: str, payload: SongSegmentPatchRequest) -> SongSegmentPatchResponse:
    segment = patch_segment_translation(job_id, segment_id, payload.translated)
    return SongSegmentPatchResponse(job_id=job_id, segment=segment)


@router.get("/jobs/{job_id}/export")
async def export_song_translation_subtitles(job_id: str, format: str = "srt"):
    export_format = str(format or "srt").strip().lower()
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail="unsupported export format")
    timeline = build_timeline(job_store.get(job_id))
    if export_format == "json":
        return PlainTextResponse(render_json(timeline), media_type="application/json; charset=utf-8")
    if export_format == "vtt":
        return PlainTextResponse(render_vtt(timeline.segments), media_type="text/vtt; charset=utf-8")
    if export_format == "lrc":
        return PlainTextResponse(render_lrc(timeline.segments), media_type="text/plain; charset=utf-8")
    return PlainTextResponse(render_srt(timeline.segments), media_type="application/x-subrip; charset=utf-8")


@router.post("/voice-consents", response_model=VoiceConsentResponse)
async def create_song_voice_consent(payload: VoiceConsentRequest) -> VoiceConsentResponse:
    return create_voice_consent(payload)


@router.post("/voice-profiles", response_model=VoiceProfileResponse)
async def create_song_voice_profile(
    sample: UploadFile = File(...),
    consent_id: str = Form(""),
    profile_label: str = Form("내 목소리"),
) -> VoiceProfileResponse:
    sample_bytes, _safe_filename, _content_type, sample_hash, duration_ms, quality_score = await read_voice_sample_upload(sample)
    return create_voice_profile(
        consent_id=consent_id,
        profile_label=profile_label,
        sample_bytes=sample_bytes,
        sample_sha256=sample_hash,
        sample_duration_ms=duration_ms,
        sample_quality_score=quality_score,
    )


@router.get("/voice-profiles/{voice_profile_id}", response_model=VoiceProfileResponse)
async def get_song_voice_profile(voice_profile_id: str) -> VoiceProfileResponse:
    return get_voice_profile(voice_profile_id)


@router.delete("/voice-profiles/{voice_profile_id}", response_model=VoiceProfileDeleteResponse)
async def delete_song_voice_profile(voice_profile_id: str) -> VoiceProfileDeleteResponse:
    return delete_voice_profile(voice_profile_id)


@router.post("/jobs/{job_id}/voice-preview", response_model=VoicePreviewResponse)
async def create_song_voice_preview(job_id: str, payload: VoicePreviewRequest) -> VoicePreviewResponse:
    return create_voice_preview(job_id, payload)
