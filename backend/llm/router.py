from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.loader import llm_loader

router = APIRouter(prefix="/api/llm", tags=["llm-status"])


@router.get("/status")
async def get_llm_status():
    return llm_loader.get_status()


# ── 모바일 앱 전용 공개 번역 엔드포인트 (인증 불필요) ──
class _MobileTranslateRequest(BaseModel):
    text: str
    from_lang: str = "ko"
    to_lang: str = "en"


@router.post("/translate", tags=["mobile-public"])
async def mobile_translate(payload: _MobileTranslateRequest):
    """나도통역사 모바일 앱 전용 공개 번역 엔드포인트. 인증 불필요."""
    from backend.marketplace.interpreter_router import _get_interpreter_instance

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 필수")

    try:
        interpreter = _get_interpreter_instance()
        translated = interpreter.quick_translate(
            text,
            source_lang=payload.from_lang,
            target_lang=payload.to_lang,
        )
        return {
            "translated": translated,
            "engine": "sorisae",
            "from": payload.from_lang,
            "to": payload.to_lang,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"번역 오류: {exc}") from exc
