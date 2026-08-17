from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel


_LOCK = Lock()
_STUDIO = None
_GENERATOR = None
_FRIEND_SYSTEM = None


class ComposeEmotionRequest(BaseModel):
    emotion: str = "happy"
    intensity: float = 0.7
    theme: Optional[str] = None


class ComposeCodeRequest(BaseModel):
    code: str
    emotion: str = "calm"


def _ensure_runtime():
    global _STUDIO, _GENERATOR, _FRIEND_SYSTEM
    if _STUDIO is not None and _GENERATOR is not None and _FRIEND_SYSTEM is not None:
        return _STUDIO, _GENERATOR, _FRIEND_SYSTEM

    with _LOCK:
        if _STUDIO is not None and _GENERATOR is not None and _FRIEND_SYSTEM is not None:
            return _STUDIO, _GENERATOR, _FRIEND_SYSTEM

        import sys

        addon_src = Path(__file__).resolve().parent / "src"
        sys.path.insert(0, str(addon_src))
        from ai_music_composer import AIMusicLyricsStudio
        from emotion_based_music_generator import EmotionBasedMusicGenerator
        from music_chat_friend_system import get_friend_system

        _STUDIO = AIMusicLyricsStudio()
        _GENERATOR = EmotionBasedMusicGenerator()
        _FRIEND_SYSTEM = get_friend_system()

    return _STUDIO, _GENERATOR, _FRIEND_SYSTEM


app = FastAPI(title="Shinsegye Music System", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    studio, generator, friend_system = _ensure_runtime()
    return {
        "status": "ok",
        "compositions": len(studio.complete_songs),
        "emotion_presets": sorted(generator.emotion_parameters.keys()),
        "friend_connections": len(friend_system.friend_connections),
    }


@app.post("/compose/emotion")
def compose_by_emotion(payload: ComposeEmotionRequest) -> Dict[str, Any]:
    studio, generator, _ = _ensure_runtime()
    song = studio.create_complete_song(emotion=payload.emotion, theme=payload.theme)
    mood_track = generator.create_musical_composition(payload.emotion, payload.intensity)
    return {
        "status": "ok",
        "song_title": song["title"],
        "lyrics_title": song["lyrics"]["title"],
        "composition_title": song["composition"]["title"],
        "mood_track_title": mood_track["title"],
        "tempo": mood_track["musical_elements"]["tempo"],
        "melody_preview": mood_track["musical_elements"]["melody"][:8],
    }


@app.post("/compose/code")
def compose_from_code(payload: ComposeCodeRequest) -> Dict[str, Any]:
    studio, _, _ = _ensure_runtime()
    song = studio.create_complete_song(emotion=payload.emotion, code=payload.code)
    return {
        "status": "ok",
        "song_title": song["title"],
        "code_composition_title": song["composition"]["title"],
        "chords": song["composition"]["chords"],
        "melody": song["composition"]["melody"][:8],
    }


@app.post("/friends/demo")
def friend_demo() -> Dict[str, Any]:
    _, _, friend_system = _ensure_runtime()
    request_id = friend_system.send_friend_request("music_user_a", "music_user_b", "함께 테마송 만들어요")
    friend_system.respond_to_friend_request(request_id, "accept")
    collab_id = friend_system.start_collaboration("music_user_a", "music_user_b", "작곡", "소리새 테마")
    signals = friend_system.get_user_signals("music_user_b")
    return {
        "status": "ok",
        "request_id": request_id,
        "collaboration_id": collab_id,
        "signals": signals,
        "friends_of_a": friend_system.get_user_friends("music_user_a"),
    }