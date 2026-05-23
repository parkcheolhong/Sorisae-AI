from __future__ import annotations

import os
from threading import Lock
from typing import Any, Dict

from backend.services.shinsegye.interpreter.sorisae_interpreter import SorisaeInterpreter

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


_INTERPRETER_LOCK = Lock()
_INTERPRETER_INSTANCE = None


class InterpreterTranslateRequest(BaseModel):
    text: str
    source_lang: str = "ko"
    target_lang: str = "en"


def _get_interpreter_instance():
    global _INTERPRETER_INSTANCE
    if _INTERPRETER_INSTANCE is not None:
        return _INTERPRETER_INSTANCE

    with _INTERPRETER_LOCK:
        if _INTERPRETER_INSTANCE is not None:
            return _INTERPRETER_INSTANCE
        _INTERPRETER_INSTANCE = SorisaeInterpreter()
    return _INTERPRETER_INSTANCE


def build_interpreter_router(contract: Any) -> APIRouter:
    router = APIRouter(prefix="/interpreter", tags=["marketplace-interpreter"])

    @router.get("/health")
    def interpreter_health(current_user=Depends(contract.get_current_user)) -> Dict[str, Any]:
        service_url = (os.getenv("INTERPRETER_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                if response.ok:
                    payload = response.json()
                    payload["mode"] = "service"
                    return payload
            except Exception:
                pass

        interpreter = _get_interpreter_instance()
        return {
            "status": "ok",
            "mode": "embedded",
            "supported_languages": interpreter.engine.supported_languages,
        }

    @router.post("/translate")
    def interpreter_translate(
        payload: InterpreterTranslateRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        text = payload.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="text 필수")

        service_url = (os.getenv("INTERPRETER_SERVICE_URL", "") or "").strip().rstrip("/")
        if service_url:
            try:
                response = requests.post(
                    f"{service_url}/translate",
                    json={
                        "text": text,
                        "source_lang": payload.source_lang,
                        "target_lang": payload.target_lang,
                    },
                    timeout=15,
                )
                if response.ok:
                    translated_payload = response.json()
                    translated_payload["mode"] = "service"
                    return translated_payload
            except Exception:
                # 외부 서비스가 일시 불안정하면 임베디드 엔진으로 즉시 폴백합니다.
                pass

        interpreter = _get_interpreter_instance()
        translated = interpreter.quick_translate(
            text,
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
        )
        return {
            "status": "ok",
            "mode": "embedded",
            "source_text": text,
            "source_lang": payload.source_lang,
            "target_lang": payload.target_lang,
            "translated_text": translated,
        }

    return router
