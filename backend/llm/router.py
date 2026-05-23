from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.loader import llm_loader

router = APIRouter(prefix="/api/llm", tags=["llm-status"])


@router.get("/status")
async def get_llm_status():
    return llm_loader.get_status()


# ── 나도통역사 전용 공개 번역 엔드포인트 (인증 불필요, 소리새 독립) ──
class _MobileTranslateRequest(BaseModel):
    text: str
    from_lang: str = "ko"
    to_lang: str = "en"


@router.post("/translate", tags=["mobile-public"])
async def mobile_translate(payload: _MobileTranslateRequest):
    """나도통역사 모바일 앱 전용 번역 엔드포인트. 소리새와 완전 독립. 24개 언어 지원."""
    from backend.services.nadotongryoksa.translator import NadoTranslator, SUPPORTED_LANGUAGES

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 필수")

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 출발 언어: {from_lang}")
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 도착 언어: {to_lang}")

    try:
        translator = NadoTranslator.get_instance()
        translated = translator.translate(text, from_lang=from_lang, to_lang=to_lang)
        return {
            "translated": translated,
            "engine": "nado",
            "from": from_lang,
            "to": to_lang,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"번역 오류: {exc}") from exc


@router.get("/translate/languages", tags=["mobile-public"])
async def get_supported_languages():
    """나도통역사 지원 언어 목록 반환 (24개국어)."""
    from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES
    return {"languages": SUPPORTED_LANGUAGES, "count": len(SUPPORTED_LANGUAGES)}
