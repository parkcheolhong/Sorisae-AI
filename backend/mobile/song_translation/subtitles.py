# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-SUBTITLES-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-SUBTITLES-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-SUBTITLE-EXPORT
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-SUBTITLES-001

from __future__ import annotations

import json
import re

from backend.mobile.song_translation.schemas import SongLyricSegment, SongSubtitleTimeline


LYRIC_METADATA_PATTERNS = [re.compile(r"\[[^\]]*\]"), re.compile(r"\([^\)]*\)"), re.compile(r"[♪♫♬]+")]


def normalize_lyric_line(text: str) -> str:
    normalized = str(text or "")
    for pattern in LYRIC_METADATA_PATTERNS:
        normalized = pattern.sub(" ", normalized)
    normalized = re.sub(r"\s*/\s*", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def is_likely_lyric_line(text: str) -> bool:
    value = normalize_lyric_line(text)
    if len(value) < 2:
        return False
    if value.isdigit():
        return False
    return bool(re.search(r"[A-Za-z\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff\u0600-\u06ff\u0900-\u097f\u0400-\u04ff\u0e00-\u0e7f]", value))


def format_srt_time(ms_value: int) -> str:
    total_ms = max(0, int(ms_value))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def format_vtt_time(ms_value: int) -> str:
    return format_srt_time(ms_value).replace(",", ".")


def format_lrc_time(ms_value: int) -> str:
    total_cs = max(0, int(round(ms_value / 10)))
    minutes, remainder = divmod(total_cs, 6_000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"[{minutes:02}:{seconds:02}.{centiseconds:02}]"


def render_srt(segments: list[SongLyricSegment]) -> str:
    blocks: list[str] = []
    for segment in segments:
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_srt_time(segment.start_ms)} --> {format_srt_time(segment.end_ms)}",
                    segment.translated or segment.original,
                ]
            )
        )
    return "\n\n".join(blocks).strip() + "\n"


def render_vtt(segments: list[SongLyricSegment]) -> str:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.extend(
            [
                f"{format_vtt_time(segment.start_ms)} --> {format_vtt_time(segment.end_ms)}",
                segment.translated or segment.original,
                "",
            ]
        )
    return "\n".join(blocks).strip() + "\n"


def render_lrc(segments: list[SongLyricSegment]) -> str:
    lines = [f"{format_lrc_time(segment.start_ms)}{segment.translated or segment.original}" for segment in segments]
    return "\n".join(lines).strip() + "\n"


def render_json(timeline: SongSubtitleTimeline) -> str:
    payload = timeline.model_dump() if hasattr(timeline, "model_dump") else timeline.dict()
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
