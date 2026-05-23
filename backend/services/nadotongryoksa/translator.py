"""
나도통역사 전용 번역 엔진 (NadoTranslator)
- 소리새(SorisaeInterpreter)와 완전 독립
- 24개 언어 지원
- googletrans 3.x async + ThreadPoolExecutor (FastAPI 이벤트루프 충돌 방지)
- 자체 여행 필수 문장 사전 캐시 (DB 없이 즉시 응답)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
from threading import Lock
from typing import Dict, Optional, Tuple

logger = logging.getLogger("nado.translator")

# ──────────────────────────────────────────────
# 24개 지원 언어
# ──────────────────────────────────────────────
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "ko": "한국어",
    "en": "영어",
    "zh": "중국어(간체)",
    "zh-tw": "중국어(번체)",
    "ja": "일본어",
    "es": "스페인어",
    "fr": "프랑스어",
    "de": "독일어",
    "pt": "포르투갈어",
    "ru": "러시아어",
    "ar": "아랍어",
    "hi": "힌디어",
    "it": "이탈리아어",
    "tr": "터키어",
    "vi": "베트남어",
    "th": "태국어",
    "id": "인도네시아어",
    "ms": "말레이어",
    "nl": "네덜란드어",
    "pl": "폴란드어",
    "uk": "우크라이나어",
    "sv": "스웨덴어",
    "no": "노르웨이어",
    "da": "덴마크어",
}

# googletrans에서 사용하는 언어코드 매핑 (차이가 있는 것만)
_GTRANS_LANG_MAP: Dict[str, str] = {
    "zh": "zh-cn",
    "zh-tw": "zh-tw",
}

# ──────────────────────────────────────────────
# 여행 필수 문장 사전 (즉시 응답용 캐시)
# 키: (from_lang, to_lang, 원문 strip lowercase)
# ──────────────────────────────────────────────
_PHRASE_DICT: Dict[Tuple[str, str, str], str] = {
    # 한국어 → 영어
    ("ko", "en", "안녕하세요"): "Hello",
    ("ko", "en", "감사합니다"): "Thank you",
    ("ko", "en", "도와주세요"): "Please help me",
    ("ko", "en", "얼마예요?"): "How much is it?",
    ("ko", "en", "화장실이 어디예요?"): "Where is the restroom?",
    ("ko", "en", "물 한 잔 주세요"): "A glass of water, please",
    ("ko", "en", "택시를 불러주세요"): "Please call a taxi",
    # 한국어 → 중국어
    ("ko", "zh", "안녕하세요"): "你好",
    ("ko", "zh", "감사합니다"): "谢谢",
    ("ko", "zh", "얼마예요?"): "多少钱？",
    # 영어 → 한국어
    ("en", "ko", "hello"): "안녕하세요",
    ("en", "ko", "thank you"): "감사합니다",
    ("en", "ko", "help me"): "도와주세요",
}


class NadoTranslator:
    """나도통역사 전용 번역기. 소리새 의존성 없음."""

    _instance: Optional["NadoTranslator"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        worker_count = max(1, int(os.getenv("NADO_TRANSLATOR_MAX_WORKERS", "4")))
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=worker_count)
        self._cache: Dict[Tuple[str, str, str], str] = {}
        self._cache_lock: Lock = Lock()

    @classmethod
    def get_instance(cls) -> "NadoTranslator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────

    def translate(self, text: str, from_lang: str = "ko", to_lang: str = "en") -> str:
        """
        텍스트를 번역한다.
        1) 로컬 사전 캐시 우선
        2) googletrans fallback
        Returns translated string.
        """
        text = text.strip()
        if not text:
            return text

        from_lang = from_lang.lower().strip()
        to_lang = to_lang.lower().strip()

        # 동일 언어이면 그대로
        if from_lang == to_lang:
            return text

        # 1) 로컬 사전
        cached = _PHRASE_DICT.get((from_lang, to_lang, text.lower()))
        if cached:
            return cached

        cache_key = (from_lang, to_lang, text)
        with self._cache_lock:
            cached_remote = self._cache.get(cache_key)
        if cached_remote:
            return cached_remote

        # 2) googletrans
        translated = self._googletrans(text, from_lang, to_lang)
        with self._cache_lock:
            self._cache[cache_key] = translated
        return translated

    def supported_languages(self) -> Dict[str, str]:
        return dict(SUPPORTED_LANGUAGES)

    # ──────────────────────────────────────────────
    # 내부 구현
    # ──────────────────────────────────────────────

    def _googletrans(self, text: str, from_lang: str, to_lang: str) -> str:
        """
        googletrans 3.x async를 별도 스레드/이벤트루프에서 실행.
        FastAPI 이벤트루프와 충돌하지 않도록 ThreadPoolExecutor 사용.
        """
        src = _GTRANS_LANG_MAP.get(from_lang, from_lang)
        dest = _GTRANS_LANG_MAP.get(to_lang, to_lang)

        async def _do() -> str:
            from googletrans import Translator
            t = Translator()
            result = await t.translate(text, src=src, dest=dest)
            return result.text

        def _run() -> str:
            return asyncio.run(_do())

        try:
            future = self._pool.submit(_run)
            return future.result(timeout=20)
        except concurrent.futures.TimeoutError:
            logger.warning("googletrans timeout: %s→%s '%s'", from_lang, to_lang, text[:30])
            return text
        except Exception as exc:
            logger.warning("googletrans error: %s→%s '%s' err=%s", from_lang, to_lang, text[:30], exc)
            return text


# 모듈 레벨 편의 함수
def translate(text: str, from_lang: str = "ko", to_lang: str = "en") -> str:
    return NadoTranslator.get_instance().translate(text, from_lang, to_lang)
