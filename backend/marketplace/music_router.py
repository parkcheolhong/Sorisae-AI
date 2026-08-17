from __future__ import annotations

import os
from threading import Lock
from typing import Any, Dict, Optional

from backend.services.shinsegye.music.ai_music_composer import AIMusicLyricsStudio
from backend.services.shinsegye.music.emotion_based_music_generator import EmotionBasedMusicGenerator
from backend.services.shinsegye.music.music_chat_friend_system import get_friend_system

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


_MUSIC_LOCK = Lock()
_MUSIC_STUDIO = None
_MUSIC_GENERATOR = None
_MUSIC_FRIEND_SYSTEM = None


class MusicComposeEmotionRequest(BaseModel):
    emotion: str = "happy"
    intensity: float = 0.7
    theme: Optional[str] = None


class MusicComposeCodeRequest(BaseModel):
    code: str
    emotion: str = "calm"


def _get_music_runtime():
    global _MUSIC_STUDIO, _MUSIC_GENERATOR, _MUSIC_FRIEND_SYSTEM
    if _MUSIC_STUDIO is not None and _MUSIC_GENERATOR is not None and _MUSIC_FRIEND_SYSTEM is not None:
        return _MUSIC_STUDIO, _MUSIC_GENERATOR, _MUSIC_FRIEND_SYSTEM

    with _MUSIC_LOCK:
        if _MUSIC_STUDIO is not None and _MUSIC_GENERATOR is not None and _MUSIC_FRIEND_SYSTEM is not None:
            return _MUSIC_STUDIO, _MUSIC_GENERATOR, _MUSIC_FRIEND_SYSTEM

        _MUSIC_STUDIO = AIMusicLyricsStudio()
        _MUSIC_GENERATOR = EmotionBasedMusicGenerator()
        _MUSIC_FRIEND_SYSTEM = get_friend_system()

    return _MUSIC_STUDIO, _MUSIC_GENERATOR, _MUSIC_FRIEND_SYSTEM


def build_music_router(contract: Any) -> APIRouter:
    router = APIRouter(prefix="/music", tags=["marketplace-music"])

    @router.get("/health")
    def music_health(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        service_url = (os.getenv("MUSIC_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                if response.ok:
                    payload = response.json()
                    payload["mode"] = "service"
                    return payload
            except Exception:
                pass

        studio, generator, friend_system = _get_music_runtime()
        return {
            "status": "ok",
            "mode": "embedded",
            "compositions": len(studio.complete_songs),
            "emotion_presets": sorted(generator.emotion_parameters.keys()),
            "friend_connections": len(friend_system.friend_connections),
        }

    @router.post("/compose/emotion")
    def music_compose_emotion(
        payload: MusicComposeEmotionRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        service_url = (os.getenv("MUSIC_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.post(
                    f"{service_url}/compose/emotion",
                    json=payload.model_dump(),
                    timeout=20,
                )
                if response.ok:
                    data = response.json()
                    data["mode"] = "service"
                    return data
            except Exception:
                pass

        studio, generator, _ = _get_music_runtime()
        song = studio.create_complete_song(emotion=payload.emotion, theme=payload.theme or "")
        mood_track = generator.create_musical_composition(payload.emotion, payload.intensity)
        return {
            "status": "ok",
            "mode": "embedded",
            "song_title": song["title"],
            "lyrics_title": song["lyrics"]["title"],
            "composition_title": song["composition"]["title"],
            "mood_track_title": mood_track["title"],
            "tempo": mood_track["musical_elements"]["tempo"],
            "melody_preview": mood_track["musical_elements"]["melody"][:8],
        }

    @router.post("/compose/code")
    def music_compose_code(
        payload: MusicComposeCodeRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        code = payload.code.strip()
        if not code:
            raise HTTPException(status_code=400, detail="code 필수")

        service_url = (os.getenv("MUSIC_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.post(
                    f"{service_url}/compose/code",
                    json={"code": code, "emotion": payload.emotion},
                    timeout=20,
                )
                if response.ok:
                    data = response.json()
                    data["mode"] = "service"
                    return data
            except Exception:
                pass

        studio, _, _ = _get_music_runtime()
        song = studio.create_complete_song(emotion=payload.emotion, code=code)
        return {
            "status": "ok",
            "mode": "embedded",
            "song_title": song["title"],
            "code_composition_title": song["composition"]["title"],
            "chords": song["composition"]["chords"],
            "melody": song["composition"]["melody"][:8],
        }

    @router.post("/friends/demo")
    def music_friend_demo(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        service_url = (os.getenv("MUSIC_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.post(f"{service_url}/friends/demo", timeout=15)
                if response.ok:
                    data = response.json()
                    data["mode"] = "service"
                    return data
            except Exception:
                pass

        _, _, friend_system = _get_music_runtime()
        request_id = friend_system.send_friend_request("music_user_a", "music_user_b", "함께 테마송 만들어요")
        friend_system.respond_to_friend_request(request_id, "accept")
        collab_id = friend_system.start_collaboration("music_user_a", "music_user_b", "작곡", "소리새 테마")
        signals = friend_system.get_user_signals("music_user_b")
        return {
            "status": "ok",
            "mode": "embedded",
            "request_id": request_id,
            "collaboration_id": collab_id,
            "signals": signals,
            "friends_of_a": friend_system.get_user_friends("music_user_a"),
        }

    return router