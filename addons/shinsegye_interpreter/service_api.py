from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


_INTERPRETER_LOCK = Lock()
_INTERPRETER_INSTANCE = None


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "ko"
    target_lang: str = "en"


def _get_interpreter():
    global _INTERPRETER_INSTANCE
    if _INTERPRETER_INSTANCE is not None:
        return _INTERPRETER_INSTANCE

    with _INTERPRETER_LOCK:
        if _INTERPRETER_INSTANCE is not None:
            return _INTERPRETER_INSTANCE
        try:
            from addons.shinsegye_interpreter.src.sorisae_interpreter import SorisaeInterpreter
        except ModuleNotFoundError:
            import importlib
            import sys

            addon_src = Path(__file__).resolve().parent / "src"
            sys.path.insert(0, str(addon_src))
            module = importlib.import_module("sorisae_interpreter")
            SorisaeInterpreter = module.SorisaeInterpreter

        _INTERPRETER_INSTANCE = SorisaeInterpreter()
        return _INTERPRETER_INSTANCE


app = FastAPI(title="Shinsegye Interpreter Service", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, object]:
    interpreter = _get_interpreter()
    return {
        "status": "ok",
        "supported_languages": interpreter.engine.supported_languages,
    }


@app.post("/translate")
def translate(payload: TranslateRequest) -> Dict[str, object]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 필수")

    interpreter = _get_interpreter()
    translated = interpreter.quick_translate(
        text,
        source_lang=payload.source_lang,
        target_lang=payload.target_lang,
    )
    return {
        "status": "ok",
        "source_text": text,
        "source_lang": payload.source_lang,
        "target_lang": payload.target_lang,
        "translated_text": translated,
    }
